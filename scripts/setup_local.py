"""Generate local-only secrets without printing them; never overwrites existing configuration."""
from pathlib import Path
import os
import secrets

ROOT = Path(__file__).resolve().parents[1]
target = ROOT / ".env"
if target.exists():
    raise SystemExit(".env already exists; edit it explicitly rather than replacing signing keys.")
content = (ROOT / ".env.example").read_text()
for name in ("JWT_SECRET", "CSRF_SECRET", "ROTATION_SECRET"):
    content = content.replace(f"{name}=\n", f"{name}={secrets.token_urlsafe(48)}\n")
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as output:
    output.write(content)
frontend = ROOT / "frontend/.env"
if not frontend.exists():
    frontend.write_text((ROOT / "frontend/.env.example").read_text())
print("Created private local configuration. Next migrate and provision a user with the CLI.")
