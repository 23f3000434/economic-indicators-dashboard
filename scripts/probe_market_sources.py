"""Bounded real market responses. Credential is read server-side; never written to evidence."""

import argparse
import asyncio
import hashlib
import json
import ssl
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
import truststore
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import Settings  # noqa: E402
from app.markets import BSE_URL, IST, NSE_URL, STATUS_URL, TIMINGS_URL, parse_bse, parse_nse, parse_status  # noqa: E402


async def probe(output):
    output = output.resolve()
    if not output.is_relative_to(ROOT / ".verification"):
        raise ValueError("Raw responses must stay inside ignored .verification")
    output.mkdir(parents=True, exist_ok=True)
    settings = Settings.load()
    routes = {
        "nse_quotes": NSE_URL,
        "upstox_sensex": BSE_URL,
        "upstox_status_nse": STATUS_URL + "NSE",
        "upstox_status_bse": STATUS_URL + "BSE",
    }
    result = {}
    async with httpx.AsyncClient(
        verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        timeout=15,
        follow_redirects=False,
        headers={"User-Agent": "EconomicIndicatorsDashboard/0.3"},
    ) as client:
        for name, url in routes.items():
            headers = {}
            if url.startswith("https://api.upstox.com/"):
                if not settings.upstox_analytics_token:
                    result[name] = {"status": "blocked", "reason": "UPSTOX_ANALYTICS_TOKEN missing"}
                    continue
                headers["Authorization"] = "Bearer " + settings.upstox_analytics_token
            entry = {"url": url}
            try:
                async with asyncio.timeout(18), client.stream("GET", url, headers=headers) as response:
                    entry["http_status"] = response.status_code
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > 2 * 1024 * 1024:
                            raise ValueError("Market response exceeds budget")
                    response.raise_for_status()
                raw = bytes(body)
                (output / f"{name}.body").write_bytes(raw)
                at = datetime.now(UTC).isoformat()
                timings = b""
                timings_url = ""
                if "status" in name:
                    transition = json.loads(raw)["data"]["last_updated"]
                    day = datetime.fromtimestamp(int(transition) / 1000, IST).date().isoformat()
                    timings_url = TIMINGS_URL + day
                    async with (
                        asyncio.timeout(18),
                        client.stream("GET", timings_url, headers=headers) as timing_response,
                    ):
                        timing_response.raise_for_status()
                        chunks = bytearray()
                        async for chunk in timing_response.aiter_bytes():
                            chunks.extend(chunk)
                            if len(chunks) > 2 * 1024 * 1024:
                                raise ValueError("Market timetable exceeds budget")
                    timings = bytes(chunks)
                    (output / f"upstox_timings_{day}.body").write_bytes(timings)
                parsed = (
                    parse_nse(raw, at)
                    if name == "nse_quotes"
                    else parse_bse(raw, at)
                    if name == "upstox_sensex"
                    else [parse_status(raw, name.rsplit("_", 1)[-1].upper(), at, timings, timings_url)]
                )
                entry.update(
                    status="validated_response",
                    retrieved_at=at,
                    sha256=hashlib.sha256(raw).hexdigest(),
                    bytes=len(raw),
                    normalised=[p.model_dump(mode="json") for p in parsed],
                )
            except Exception as exc:
                # No request objects, Authorization headers or raw exception text in public diagnostics.
                entry.update(status="blocked", reason=type(exc).__name__)
            result[name] = entry
    (output / "market-probe.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: {f: v[f] for f in ("status", "http_status", "bytes", "reason") if f in v}
                for k, v in result.items()
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".verification/completion/market-source")
    load_dotenv(ROOT / ".env")
    asyncio.run(probe(parser.parse_args().output))
