"""Verify generated artwork hashes and, with the reference SVG, exact resized RGBA pixels."""

import argparse
import base64
import hashlib
import json
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("svg", type=Path, nargs="?")
    parser.add_argument("--pixels", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / ".verification/design/asset-checks.json")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "frontend/public/design/assets.json").read_text())
    images = {}
    if args.svg:
        raw = args.svg.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == manifest["source_svg_sha256"]
        svg = ET.fromstring(raw)
        images = {
            n.get("id"): base64.b64decode(n.get("{http://www.w3.org/1999/xlink}href").split(",", 1)[1])
            for n in svg.iter()
            if n.tag.endswith("image")
        }
    if args.pixels and not images:
        parser.error("--pixels requires the supplied SVG")
    calls = (ROOT / "frontend/src/artwork.ts").read_text() + (ROOT / "frontend/src/artwork.css").read_text()
    checks = []
    for asset in manifest["assets"]:
        if images:
            original = images[asset["id"]]
            assert hashlib.sha256(original).hexdigest() == asset["source_sha256"]
            before = Image.open(BytesIO(original)).convert("RGBA")
            assert before.size == (asset["source_width"], asset["source_height"])
        for variant in asset["variants"]:
            output = ROOT / variant["file"]
            data = output.read_bytes()
            assert len(data) == variant["byte_length"] > 0
            assert hashlib.sha256(data).hexdigest() == variant["sha256"]
            assert "/design/" + output.name in calls
            after = Image.open(output).convert("RGBA")
            assert after.size == (variant["width"], variant["height"])
            if args.pixels:
                resized = (
                    before
                    if before.size == after.size
                    else before.resize(after.size, Image.Resampling.LANCZOS)
                )
                assert resized.tobytes() == after.tobytes(), output.name
            checks.append(
                {
                    "asset": output.name,
                    "hashes_dimensions_callsite": "passed",
                    "resized_pixel_identity": "passed" if args.pixels else "not_checked",
                }
            )
    result = {
        "source_svg_sha256": manifest["source_svg_sha256"],
        "source_dimensions": manifest["source_dimensions"],
        "checks": checks,
        "total_asset_bytes": sum(v["byte_length"] for a in manifest["assets"] for v in a["variants"]),
        "omitted_asset": "image1_0_1 is the illustrative LIVE dot; actual ticker state comes from stored quotes/status.",
    }
    layouts = json.loads((ROOT / "frontend/public/design/layout.json").read_text())
    assert layouts["source_svg_sha256"] == manifest["source_svg_sha256"]
    layout_calls = (ROOT / "frontend/src/layout.ts").read_text()
    for entry in layouts["entries"]:
        path = ROOT / "frontend/public/design" / entry["file"]
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        assert len(raw) == entry["bytes"] and entry["file"] in layout_calls
        tree = ET.fromstring(raw)
        assert not list(tree.iter("{http://www.w3.org/2000/svg}text"))
        if entry["density"] == "mobile":
            assert not list(tree.iter("{http://www.w3.org/2000/svg}image"))
    result["decorative_layouts_verified"] = len(layouts["entries"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"Verified {len(checks)} artwork variants; resized pixels {'checked' if args.pixels else 'not checked'}"
    )


if __name__ == "__main__":
    main()
