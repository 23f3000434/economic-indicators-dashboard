#!/bin/sh
set -eu
umask 077
cd .delivery/api
export PYTHONPATH=backend
exec .venv/bin/python -m app.serve
