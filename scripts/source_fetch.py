"""Bounded source evidence fetch. HTTP success is not adapter completion. All output stays in this repo."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def fetch(url, name, output, limit=32 * 1024 * 1024):
    at = datetime.now(timezone.utc).isoformat()
    report = {"url": url, "checked_at": at, "name": name}
    try:
        with httpx.Client(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": "EconomicIndicatorsAssignment/0.2", "Accept": "*/*"},
        ) as client:
            with client.stream("GET", url) as response:
                report.update(
                    status=response.status_code,
                    final_url=str(response.url),
                    content_type=response.headers.get("content-type"),
                    retry_after=response.headers.get("retry-after"),
                )
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > limit:
                        raise ValueError("response exceeds byte budget")
                report.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
                (output / f"{name}.body").write_bytes(body)
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc))
    (output / f"{name}.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--output", default=".verification/multi")
    args = parser.parse_args()
    path = (ROOT / args.output).resolve()
    if not path.is_relative_to(ROOT) or "/" in args.name or ".." in args.name:
        parser.error("Output must stay inside the workspace")
    path.mkdir(parents=True, exist_ok=True)
    print(json.dumps(fetch(args.url, args.name, path)))
