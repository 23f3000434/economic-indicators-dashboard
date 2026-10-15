"""Assemble an allowlisted API runtime; exclude tests, fixtures, secrets and local data."""

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(output):
    output = output.resolve()
    if not output.is_relative_to(ROOT / ".delivery"):
        raise ValueError("Runtime output must be inside the ignored .delivery directory")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copyfile(ROOT / name, output / name)
    for name in ("app", "migrations"):
        shutil.copytree(
            ROOT / "backend" / name,
            output / "backend" / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    print("Prepared API runtime from backend/app, backend/migrations and locked dependency metadata only.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".delivery/api")
    prepare(parser.parse_args().output)
