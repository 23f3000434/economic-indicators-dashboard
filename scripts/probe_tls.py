#!/usr/bin/env python3
"""Compare verified Python/curl GETs for the proposed Gazette policy source.

Optional diagnostic: requires curl >= 7.70. Neither client disables TLS checks.
"""
import argparse
import hashlib
import json
import subprocess

from probe_sources import MAX_BYTES, SOURCES, now, probe, workspace_path, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=".verification/tls")
    args = parser.parse_args()
    output = workspace_path(args.output_dir)
    if output.exists():
        parser.error("Use a new output directory to preserve earlier evidence")
    output.mkdir(parents=True, mode=0o700)
    python_result = probe("inflation_target", output, 12)
    body_path = output / "gazette-curl.body"
    try:
        result = subprocess.run([
            "curl", "--disable", "--silent", "--show-error", "--max-time", "15",
            "--max-filesize", str(MAX_BYTES), "--proto", "=https",
            "--output", str(body_path), "--write-out", "%{json}",
            SOURCES["inflation_target"]["url"],
        ], capture_output=True, text=True, timeout=20)
        info = json.loads(result.stdout) if result.stdout.strip() else {}
        curl_result = {
            "exit_code": result.returncode, "http_status": info.get("http_code"),
            "ssl_verify_result": info.get("ssl_verify_result"),
            "content_type": info.get("content_type"), "url": info.get("url_effective"),
            "sha256": hashlib.sha256(body_path.read_bytes()).hexdigest() if body_path.exists() else None,
            "detail": result.stderr.strip(),
        }
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        curl_result = {"detail": str(exc), "status": "blocked"}
    report = {"recorded_at": now(), "method": "GET", "tls_verification_disabled": False, "python": python_result, "curl": curl_result, "coverage": "unverified; successful PDF transport is not a policy observation parser"}
    write_json(output / "report.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
