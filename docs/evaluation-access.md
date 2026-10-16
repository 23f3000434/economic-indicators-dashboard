# Private evaluation access

No default or public test password exists. Local random verification accounts are not production evaluation credentials. No hosted evaluation account or credential delivery is claimed yet; see [delivery status](delivery-status.md).

## Operator provisioning

On the **disk-owning Render service**, open its private authenticated shell. From the deployed repository root:

```sh
cd .delivery/api
PYTHONPATH=backend .venv/bin/python -m app.cli create-user evaluation-2026
```

The ordinary production configuration must already identify `/var/data/private/dashboard.sqlite3`; the service starts/migrates that mounted database before provisioning. The CLI prompts twice for a unique password of at least 12 characters. Use a password manager, not a literal command argument or environment value in shell history. Do not use a predeploy/one-off machine: it cannot access the attached disk. Do not run a second collector or API process. A duplicate username is rejected; there is no password-reset/account-admin UI.

Privately share only the intended evaluator's frontend URL, username/password and access window through an owner-approved secret/password-manager channel. Give each evaluator a separate account where practical. Keep account and host secrets out of Git, CI output, screenshots and public tickets. Repository invitation is a separate action requiring the evaluator's GitHub identity; keep the repository private unless the owner explicitly changes that decision.

## Evaluator instructions

1. Open the supplied frontend HTTPS URL and sign in. Data is protected; the public API documentation does not grant dashboard access.
2. Reload normally: the persistent HttpOnly refresh cookie restores the session automatically. The15-minute access JWT is kept only in browser memory; renewal does not require signing in again during the absolute session lifetime.
3. Open Details for canonical tables, exact periods, source links, estimates and methodology. Period selections/legend controls affect the same data. Charts support pointer/tap selection and keyboard arrows, Enter and Escape.
4. Inspect source/as-of/state information. Snapshot/Delayed/Stale/Closed labels reflect actual exchange timestamps and schedule; unchanged quotes are legitimate. Refresh view reads storage, not providers.
5. Sign out when finished. Server revocation rejects associated access tokens immediately and cross-tab notifications clear authenticated data/dialogs. A session expires at its original absolute deadline, at most seven days after sign-in.

Default provider URLs on unrelated sites are not the accepted production cookie setup. If sign-in/reload fails, give the operator the time, browser and safe error text, never a token/cookie/password. Avoid exporting an unredacted browser HAR.

## Close access after evaluation

Logout revokes one session; it does not disable the account/password. The operator must disable the evaluation user and revoke its sessions after the agreed review window. There is no automated account expiry feature. On the private disk owner, use a short transaction with **bound parameters**: `UPDATE users SET active = 0 WHERE username = ?`, and set `sessions.revoked_at` for that user's sessions. Verify affected identity/count before committing, preserve other accounts, and confirm fresh login plus an old access token are rejected. Do not concatenate a username into SQL. Back up consistently before an administrative change; see [recovery](deployment.md#consistent-backup-and-restore).

No account is created, disabled or messaged to another person merely by writing these instructions.
