"""Verify local design assets against the supplied SVG; never modify the reference."""

import argparse
import base64
import hashlib
import json
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("svg", type=Path)
    parser.add_argument("--pixels", action="store_true", help="Also verify decoded RGBA identity (Pillow)")
    parser.add_argument("--output", type=Path, default=ROOT / ".verification/design/asset-checks.json")
    args = parser.parse_args()
    raw = args.svg.read_bytes()
    svg = ET.fromstring(raw)
    images = {
        n.get("id"): base64.b64decode(n.get("{http://www.w3.org/1999/xlink}href").split(",", 1)[1])
        for n in svg.iter()
        if n.tag.endswith("image")
    }
    manifest = json.loads((ROOT / "frontend/public/design/assets.json").read_text())
    css = (ROOT / "frontend/src/styles.css").read_text()
    checks = []
    for asset in manifest:
        original = images[asset["id"]]
        output = ROOT / asset["file"]
        data = output.read_bytes()
        assert hashlib.sha256(original).hexdigest() == asset["source_sha256"]
        assert len(data) == asset["byte_length"] > 0
        assert hashlib.sha256(data).hexdigest() == asset["sha256"]
        assert "/design/" + output.name in css
        if args.pixels:
            from PIL import Image

            before, after = Image.open(BytesIO(original)), Image.open(output)
            assert before.size == after.size == (asset["width"], asset["height"])
            assert before.convert("RGBA").tobytes() == after.convert("RGBA").tobytes()
        checks.append(
            {
                "asset": output.name,
                "hashes_and_callsite": "passed",
                "pixel_identity": "passed" if args.pixels else "not_checked",
            }
        )
    result = {
        "source_svg_sha256": hashlib.sha256(raw).hexdigest(),
        "source_dimensions": [svg.get("width"), svg.get("height")],
        "checks": checks,
        "total_asset_bytes": sum(a["byte_length"] for a in manifest),
        "omitted_asset": "image1_0_1 is the LIVE dot, not applicable without an accepted market feed.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"Verified {len(checks)} design assets; pixel identity {'checked' if args.pixels else 'not checked'}"
    )


if __name__ == "__main__":
    main()
