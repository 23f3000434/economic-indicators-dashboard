#!/bin/sh
set -eu
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.verification/uv-cache}"
# Build has no database credentials. PostgreSQL migrations/ownership run at startup.
python -c 'import subprocess, sys; assert sys.version_info[:3] == (3, 12, 14); assert subprocess.check_output(["uv", "--version"], text=True).split()[1] == "0.10.2"'
python deploy/prepare_api.py
uv sync --project .delivery/api --python "$(python -c 'import sys; print(sys.executable)')" --frozen --no-dev --no-install-project
.delivery/api/.venv/bin/python -c 'import sys; assert sys.version_info[:3] == (3, 12, 14)'
