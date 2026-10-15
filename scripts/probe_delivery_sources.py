"""One bounded, honest request per unresolved route; diagnostic evidence, not collectors."""

import argparse
import asyncio
import hashlib
import json
import socket
import ssl
from datetime import UTC, datetime
from pathlib import Path

import httpx
import truststore

ROOT = Path(__file__).resolve().parents[1]
ROUTES = {
    "control": "https://example.com/",
    "imf_general_government_debt": "https://www.imf.org/external/datamapper/api/v2/GGXWDG_NGDP/IND/USA?periods=2020,2021,2022,2023,2024,2025",
    "fred_india_metadata": "https://fred.stlouisfed.org/series/GGGDTAINA188N",
    "fred_us_metadata": "https://fred.stlouisfed.org/series/GGGDTAUSA188N",
    "fred_india_csv": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GGGDTAINA188N",
    "fred_us_csv": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GGGDTAUSA188N",
    "nse_public_indices": "https://www.nseindia.com/api/allIndices",
    "bse_publication_only": "https://www.bseindices.com/indices-details/code/16",
}


async def main(output):
    output = output.resolve()
    if not output.is_relative_to(ROOT / ".verification"):
        raise ValueError("Diagnostics must remain inside the ignored workspace .verification directory")
    output.mkdir(parents=True, exist_ok=False)
    semaphore = asyncio.Semaphore(4)
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    async with httpx.AsyncClient(
        verify=context,
        timeout=12,
        follow_redirects=True,
        headers={"User-Agent": "EconomicIndicatorsAssignmentSourceVerification/0.2"},
    ) as client:

        async def probe(name, url):
            async with semaphore:
                result = {
                    "source": name,
                    "url": url,
                    "attempted_at": datetime.now(UTC).isoformat(),
                    "status": "unverified",
                    "collector_completed": False,
                }
                try:
                    socket.getaddrinfo(httpx.URL(url).host, 443, type=socket.SOCK_STREAM)
                    result["dns"] = "resolved"
                    async with asyncio.timeout(18), client.stream("GET", url) as response:
                        result.update(
                            http_status=response.status_code,
                            final_url=str(response.url),
                            content_type=response.headers.get("content-type"),
                            stage="http",
                        )
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > 4 * 1024 * 1024:
                                raise ValueError("Body exceeds 4 MiB diagnostic limit")
                        result.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
                        (output / f"{name}.body").write_bytes(body)
                        if response.status_code >= 400:
                            result.update(status="blocked", reason="HTTP route/provider rejection")
                        else:
                            result["reason"] = (
                                "Response obtained; definitions/coverage/access and complete adapter not established"
                            )
                except socket.gaierror:
                    result.update(status="blocked", stage="dns", reason="Runtime DNS failed before HTTP")
                except (httpx.TimeoutException, TimeoutError):
                    result.update(
                        status="blocked",
                        stage="transport",
                        reason="Timeout before complete response; no rejection inferred",
                    )
                except (httpx.RequestError, ValueError) as error:
                    result.update(
                        status="blocked",
                        stage="transport_or_body",
                        reason=type(error).__name__,
                        detail=str(error),
                    )
                result["finished_at"] = datetime.now(UTC).isoformat()
                return result

        results = await asyncio.gather(*(probe(name, url) for name, url in ROUTES.items()))
    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "scope": "network-enabled local runtime, not hosting egress",
        "method": "One request per route, no retries, credentials, browser impersonation or TLS bypass; 12s I/O / 18s total / 4MiB bounds",
        "results": results,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    for result in results:
        print(
            json.dumps(
                {
                    k: result[k]
                    for k in ("source", "status", "stage", "http_status", "bytes", "reason")
                    if k in result
                }
            )
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / ".verification/hardening" / datetime.now(UTC).strftime("sources-%Y%m%dT%H%M%S%fZ"),
    )
    asyncio.run(main(parser.parse_args().output_dir))
