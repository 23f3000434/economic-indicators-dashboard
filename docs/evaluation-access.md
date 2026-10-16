# Private evaluation access

No default or public test password exists. Local random verification accounts are not production evaluation credentials. No hosted evaluation account or credential delivery is claimed yet; see [delivery status](delivery-status.md).

## Operator provisioning

Render Free has no shell/SSH or one-off jobs. Provision on ordinary API startup with server-only `BOOTSTRAP_USERNAME` and an Argon2id `BOOTSTRAP_PASSWORD_HASH`. Generate a unique password of at least12 characters in a password manager, hash it locally using the locked `argon2-cffi`, and configure only the hash in the private Render environment. Never put a plaintext evaluator password in Git, Vercel or a command argument. The bootstrap operation inserts only an absent username; a restart cannot overwrite a password or reactivate a disabled account. Remove the bootstrap pair after provisioning if practical; preserve the three signing/rotation secrets across restarts.

For local SQLite or a securely attached disposable PostgreSQL environment, interactive administration remains available:

```sh
PYTHONPATH=backend .venv/bin/python -m app.cli create-user evaluation-2026
```

Do not open the production database's external ingress to run this command. No production evaluator has been provisioned or privately handed off yet.

Privately share only the intended evaluator's frontend URL, username/password and access window through an owner-approved secret/password-manager channel. Give each evaluator a separate account where practical. Keep account and host secrets out of Git, CI output, screenshots and public tickets. Repository invitation is a separate action requiring the evaluator's GitHub identity; keep the repository private unless the owner explicitly changes that decision.

## Evaluator instructions

1. Open the supplied frontend HTTPS URL and sign in. Data is protected; the public API documentation does not grant dashboard access.
2. Reload normally: the persistent HttpOnly refresh cookie restores the session automatically. The15-minute access JWT is kept only in browser memory; renewal does not require signing in again during the absolute session lifetime.
3. Open Details for canonical tables, exact periods, source links, estimates and methodology. Period selections/legend controls affect the same data. Charts support pointer/tap selection and keyboard arrows, Enter and Escape.
4. Inspect source/as-of/state information. Snapshot/Delayed/Stale/Closed labels reflect actual exchange timestamps and schedule; unchanged quotes are legitimate. Refresh view reads storage, not providers.
5. Sign out when finished. Server revocation rejects associated access tokens immediately and cross-tab notifications clear authenticated data/dialogs. A session expires at its original absolute deadline, at most seven days after sign-in.

On the free provider URLs, cookie actions use the frontend's auth-only rewrite while protected data reads go directly to Render. The HttpOnly cookie belongs to the frontend site. If sign-in/reload fails, give the operator the time, browser and safe error text, never a token/cookie/password. Avoid exporting an unredacted browser HAR.

## Close access after evaluation

Logout revokes one session; it does not disable the account/password. The operator must disable the evaluation user and revoke its sessions after the agreed review window. There is no automated account expiry feature. Using a separately authorised internal operator procedure, use a short transaction with **bound parameters**: `UPDATE users SET active = 0 WHERE username = ?`, and set `sessions.revoked_at` for that user's sessions. Verify affected identity/count before committing, preserve other accounts, and confirm fresh login plus an old access token are rejected. Do not concatenate a username into SQL. Free Render has no deployed account-admin interface or shell; post-review disabling must be completed through an authorised internal maintenance procedure, without opening public DB ingress. Recovery limits are explicit; see [recovery](deployment.md#consistent-backup-and-restore).

No account is created, disabled or messaged to another person merely by writing these instructions.
