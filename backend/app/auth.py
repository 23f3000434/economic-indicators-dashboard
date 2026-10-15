"""Revocable access sessions and delivery-confirmed, hashes-only refresh rotation."""

import base64
import hashlib
import hmac
import secrets
import threading
import uuid
from collections import defaultdict, deque

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from .config import Settings
from .db import Database
from .gdp import timestamp


class AuthError(Exception):
    def __init__(self, code="invalid_session", message="Please sign in again.", status=401):
        self.code, self.message, self.status = code, message, status


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Auth:
    def __init__(self, settings: Settings, database: Database, clock):
        self.settings, self.db, self.clock = settings, database, clock
        self.hasher = PasswordHasher()
        self.dummy_hash = self.hasher.hash(secrets.token_urlsafe(24))
        self.attempts = defaultdict(deque)
        self.attempts_lock = threading.Lock()

    def create_user(self, username, password):
        if not 1 <= len(username) <= 100 or not 12 <= len(password) <= 1024:
            raise ValueError("Username must be 1..100 and password 12..1024 characters")
        with self.db.connect(write=True) as db:
            db.execute(
                "INSERT INTO users(id, username, password_hash) VALUES (?, ?, ?)",
                (str(uuid.uuid4()), username, self.hasher.hash(password)),
            )

    def csrf(self, sid):
        return hmac.new(
            self.settings.csrf_secret.encode(), ("csrf:v1:" + sid).encode(), hashlib.sha256
        ).hexdigest()

    def successor(self, token):
        raw = hmac.new(
            self.settings.rotation_secret.encode(), ("refresh:v1:" + token).encode(), hashlib.sha256
        ).digest()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    def active(self, row):
        if (
            not row
            or row["revoked_at"] is not None
            or not row["active"]
            or row["expires_at"] <= int(self.clock())
        ):
            raise AuthError()
        return row

    @staticmethod
    def session(db, sid):
        return db.execute(
            "SELECT s.*, u.username, u.active FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.id=?",
            (sid,),
        ).fetchone()

    @staticmethod
    def cookie_identity(db, token):
        if not token or len(token) > 256:
            return None
        return db.execute("SELECT * FROM refresh_tokens WHERE digest=?", (digest(token),)).fetchone()

    def cookie_session(self, db, token, csrf=None, allow_retired=False):
        identity = self.cookie_identity(db, token)
        if not identity:
            raise AuthError()
        row = self.active(self.session(db, identity["session_id"]))
        if csrf is not None and not hmac.compare_digest(csrf.encode(), self.csrf(row["id"]).encode()):
            raise AuthError("csrf_failed", "Request verification failed.", 403)
        if identity["state"] == "retired" and not allow_retired:
            if int(self.clock()) - identity["retired_at"] > self.settings.settle_seconds:
                raise AuthError("refresh_reused")
        return row, identity

    def info(self, row):
        return dict(
            session_expires_at=timestamp(row["expires_at"]),
            csrf_token=self.csrf(row["id"]),
            user=dict(id=row["user_id"], username=row["username"]),
        )

    def tokens(self, row):
        now = int(self.clock())
        expiry = min(now + 900, row["expires_at"])
        token = jwt.encode(
            dict(
                iss=self.settings.issuer,
                aud=self.settings.audience,
                sub=row["user_id"],
                sid=row["id"],
                iat=now,
                exp=expiry,
            ),
            self.settings.jwt_secret,
            algorithm="HS256",
        )
        return dict(
            **self.info(row),
            access_token=token,
            token_type="bearer",
            expires_in=expiry - now,
            access_expires_at=timestamp(expiry),
        )

    def bearer(self, token):
        try:
            claims = jwt.decode(
                token,
                self.settings.jwt_secret,
                algorithms=["HS256"],
                issuer=self.settings.issuer,
                audience=self.settings.audience,
                options={
                    "require": ["iss", "aud", "sub", "sid", "iat", "exp"],
                    "verify_exp": False,
                    "verify_iat": False,
                },
            )
            if any(type(claims[k]) is not int for k in ("iat", "exp")) or not isinstance(claims["sid"], str):
                raise jwt.InvalidTokenError()
            if claims["iat"] > int(self.clock()) + 5 or claims["exp"] - claims["iat"] > 900:
                raise jwt.InvalidTokenError()
            if claims["exp"] <= int(self.clock()):
                raise AuthError("access_token_expired", "Your access token needs renewal.")
        except jwt.PyJWTError:
            raise AuthError("invalid_access_token") from None
        with self.db.connect() as db:
            row = self.active(self.session(db, claims["sid"]))
        if row["user_id"] != claims["sub"]:
            raise AuthError("invalid_access_token")
        return row

    def login(self, username, password, client):
        now = int(self.clock())
        # Single-instance, bounded in-memory limiter. Trust the socket peer, not arbitrary forwarding headers.
        with self.attempts_lock:
            for key in list(self.attempts):
                while self.attempts[key] and self.attempts[key][0] < now - 60:
                    self.attempts[key].popleft()
                if not self.attempts[key]:
                    del self.attempts[key]
            attempts = self.attempts[client]
            if len(attempts) >= 5 or len(self.attempts) > 10000:
                raise AuthError("rate_limited", "Too many attempts. Try again in a minute.", 429)
            attempts.append(now)
        with self.db.connect() as db:
            user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        try:
            self.hasher.verify(user["password_hash"] if user else self.dummy_hash, password)
            valid = bool(user and user["active"])
        except VerificationError:
            valid = False
        if not valid:
            raise AuthError("invalid_credentials", "Username or password is incorrect.")
        sid, refresh = str(uuid.uuid4()), secrets.token_urlsafe(32)
        with self.db.connect(write=True) as db:
            db.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
            db.execute(
                "INSERT INTO sessions(id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (sid, user["id"], now, now + self.settings.session_max_age),
            )
            db.execute(
                "INSERT INTO refresh_tokens(digest, session_id, state, created_at) VALUES (?, ?, 'active', ?)",
                (digest(refresh), sid, now),
            )
            row = self.session(db, sid)
        return self.tokens(row), refresh, row["expires_at"]

    def bootstrap(self, token):
        with self.db.connect() as db:
            row, _ = self.cookie_session(db, token)
            return self.info(row)

    def refresh(self, token, csrf):
        now = int(self.clock())
        with self.db.connect(write=True) as db:
            row, identity = self.cookie_session(db, token, csrf, allow_retired=True)
            if identity["state"] == "retired":
                if now - identity["retired_at"] > self.settings.settle_seconds:
                    db.execute("UPDATE sessions SET revoked_at=? WHERE id=?", (now, row["id"]))
                    db.commit()  # Persist detected reuse even though the response is an error.
                    raise AuthError("refresh_reused")
                successor = self.successor(token)
                target = self.cookie_identity(db, successor)
                if not target or target["state"] != "active":
                    raise AuthError("refresh_reused")
            elif identity["state"] == "pending":
                successor = token
            elif (
                row["confirmed_at"] is not None and now - row["confirmed_at"] <= self.settings.settle_seconds
            ):
                successor = token
            else:
                successor = self.successor(token)
                db.execute(
                    "INSERT OR IGNORE INTO refresh_tokens(digest, session_id, state, created_at) VALUES (?, ?, 'pending', ?)",
                    (digest(successor), row["id"], now),
                )
            response = self.tokens(row)
        return response, successor, row["expires_at"]

    def confirm(self, token, csrf):
        now = int(self.clock())
        with self.db.connect(write=True) as db:
            row, identity = self.cookie_session(db, token, csrf)
            if identity["state"] == "pending":
                db.execute(
                    "UPDATE refresh_tokens SET state='retired', retired_at=? WHERE session_id=? AND state='active'",
                    (now, row["id"]),
                )
                db.execute("UPDATE refresh_tokens SET state='active' WHERE digest=?", (digest(token),))
                db.execute("UPDATE sessions SET confirmed_at=? WHERE id=?", (now, row["id"]))

    def logout(self, bearer, cookie, csrf):
        authority = self.bearer(bearer) if bearer else None
        with self.db.connect(write=True) as db:
            identity = self.cookie_identity(db, cookie)
            if authority and identity and identity["session_id"] != authority["id"]:
                raise AuthError(
                    "session_identity_conflict",
                    "Session identities disagree. Reload before signing out.",
                    409,
                )
            if authority:
                # Recheck while holding the write lock; never rely on a stale authority snapshot.
                row = self.active(self.session(db, authority["id"]))
            elif identity:
                row, _ = self.cookie_session(db, cookie, csrf, allow_retired=True)
            else:
                return
            db.execute("UPDATE sessions SET revoked_at=? WHERE id=?", (int(self.clock()), row["id"]))
