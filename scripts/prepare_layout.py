"""Extract decorative SVG geometry, retaining measured crops and optimised source artwork.

No sample numbers, axes, economic curves or labels enter the panel skins. The static
masthead title uses the supplied outlined artwork; all economic content remains React.
"""

import argparse
import base64
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
ET.register_namespace("", NS)
ET.register_namespace("xlink", XLINK)
PANELS = {"gdp": 5, "trade": 6, "inflation": 7, "debt": 8, "gst": 9, "expenditure": 10}


def sha(body):
    return hashlib.sha256(body).hexdigest()


def decorative(group, surface_only=False):
    """Keep panel/glass/corner graphics; remove every sample text/plot mark."""
    result = ET.Element(group.tag, group.attrib)
    base_x = float(group[0].get("x"))
    corners = 0
    for node in group:
        tag = node.tag.rsplit("}", 1)[-1]
        if tag == "g" and node.get("clip-path"):
            card = ET.Element(node.tag, node.attrib)
            for child in node:
                if surface_only and child.get("fill", "").startswith("url(#pattern"):
                    continue
                if child.tag == f"{{{NS}}}rect" or child.get("filter"):
                    card.append(copy.deepcopy(child))
            result.append(card)
        elif (
            node.get("filter")
            or (tag == "rect" and node.get("fill") in {"#001671", "#2C2C2D"})
            or (
                tag == "path"
                and node.get("fill", "").startswith("url(#paint")
                and abs(float(re.match(r"M([\d.]+)", node.get("d", ""))[1]) - base_x) < 1.5
            )
            or (tag == "line" and node.get("stroke", "").startswith("url(#paint"))
        ):
            result.append(copy.deepcopy(node))
            if tag == "path":
                corners += 1
    if corners != 1:
        raise ValueError("Expected one decorative corner and no economic curve")
    return result


def document(nodes, bounds, definitions, images, density, stretch=False):
    svg = ET.Element(
        f"{{{NS}}}svg",
        {
            "width": str(bounds[2]),
            "height": str(bounds[3]),
            "viewBox": " ".join(map(str, bounds)),
            "fill": "none",
            "preserveAspectRatio": "none" if stretch else "xMidYMid meet",
        },
    )
    for node in nodes:
        svg.append(copy.deepcopy(node))
    defs = ET.SubElement(svg, f"{{{NS}}}defs")
    included = set()

    def references(node):
        raw = ET.tostring(node, encoding="unicode")
        return set(re.findall(r"url\(#([\w-]+)\)|(?:xlink:)?href=\"#([\w-]+)\"", raw))

    pending = {a or b for node in nodes for a, b in references(node)}
    while pending:
        identity = sorted(pending)[0]
        pending.remove(identity)
        if identity in included:
            continue
        node = copy.deepcopy(definitions[identity])
        if identity in images:
            variants = images[identity]["variants"]
            variant = variants[min(density - 1, len(variants) - 1)]
            payload = (ROOT / variant["file"]).read_bytes()
            node.set(f"{{{XLINK}}}href", "data:image/webp;base64," + base64.b64encode(payload).decode())
        pending |= {a or b for a, b in references(node)} - included
        included.add(identity)
        defs.append(node)
    return ET.tostring(svg, encoding="utf-8"), sorted(included)


def prepare(path):
    raw = path.read_bytes()
    source = ET.fromstring(raw)
    manifest = json.loads((ROOT / "frontend/public/design/assets.json").read_text())
    if sha(raw) != manifest["source_svg_sha256"]:
        raise ValueError("Artwork and layout must use the same supplied SVG")
    definitions = {node.get("id"): node for node in source[-1]}
    images = {a["id"]: a for a in manifest["assets"]}
    root = source[1]
    output = ROOT / "frontend/public/design"
    entries = []
    for name, index in PANELS.items():
        group = root[index]
        bounds = [float(group[0].get(k)) for k in ("x", "y", "width", "height")]
        nodes = [decorative(group)]
        # GDP's header rule is a sibling of its clipped group in the original export.
        if name == "gdp":
            nodes.append(root[11])
        for density in (1, 2):
            body, refs = document(nodes, bounds, definitions, images, density)
            file = f"{name}-layout-{density}x-{sha(body)[:12]}.svg"
            (output / file).write_bytes(body)
            entries.append(
                {
                    "name": name,
                    "density": density,
                    "file": file,
                    "sha256": sha(body),
                    "bytes": len(body),
                    "bounds": bounds,
                    "source_definitions": refs,
                }
            )
        surfaces = [decorative(group, surface_only=True)]
        if name == "gdp":
            surfaces.append(root[11])
        body, refs = document(surfaces, bounds, definitions, images, 1, stretch=True)
        if any(ref.startswith("image") for ref in refs):
            raise ValueError("Mobile surface must contain no raster artwork")
        file = f"{name}-layout-mobile-{sha(body)[:12]}.svg"
        (output / file).write_bytes(body)
        entries.append(
            {
                "name": name,
                "density": "mobile",
                "file": file,
                "sha256": sha(body),
                "bytes": len(body),
                "bounds": bounds,
                "source_definitions": refs,
            }
        )
    # Exact background rotation, overlay, masthead crop and outlined static title.
    # Ticker text/prices/state are intentionally absent; its gradient comes from the reference.
    for density in (1, 2):
        body, refs = document(
            [source[0], root[0], root[1], root[2][0], root[3], root[4]],
            [0, 0, 1248, 2193],
            definitions,
            images,
            density,
        )
        file = f"canvas-layout-{density}x-{sha(body)[:12]}.svg"
        (output / file).write_bytes(body)
        entries.append(
            {
                "name": "canvas",
                "density": density,
                "file": file,
                "sha256": sha(body),
                "bytes": len(body),
                "bounds": [0, 0, 1248, 2193],
                "source_definitions": refs,
            }
        )
    keep = {e["file"] for e in entries}
    for old in output.glob("*-layout-*.svg"):
        if old.name not in keep:
            old.unlink()
    (output / "layout.json").write_text(
        json.dumps(
            {
                "source_svg_sha256": sha(raw),
                "method": "Original SVG decorative nodes and clipping; existing deterministic WebP variants; no sample observations/text/curves in panel skins.",
                "entries": entries,
            },
            indent=2,
        )
        + "\n"
    )
    props = {
        name: {
            "src": "/design/" + next(e["file"] for e in entries if e["name"] == name and e["density"] == 1),
            "srcSet": ", ".join(
                f"/design/{e['file']} {e['density']}x"
                for e in entries
                if e["name"] == name and e["density"] != "mobile"
            ),
            "mobileSrc": next(
                ("/design/" + e["file"] for e in entries if e["name"] == name and e["density"] == "mobile"),
                None,
            ),
        }
        for name in [*PANELS, "canvas"]
    }
    (ROOT / "frontend/src/layout.ts").write_text(
        "// Generated by scripts/prepare_layout.py from supplied decorative geometry.\n"
        "export const layout: Record<string, {src:string;srcSet:string;mobileSrc:string|null}> = "
        + json.dumps(props, indent=2)
        + ";\n"
    )
    subprocess.run(
        [str(ROOT / "frontend/node_modules/.bin/prettier"), "--write", str(ROOT / "frontend/src/layout.ts")],
        check=True,
        cwd=ROOT,
    )
    print(
        f"Prepared {len(entries)} decorative layouts ({sum(e['bytes'] for e in entries):,} bytes); zero sample economic values."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("svg", type=Path)
    prepare(parser.parse_args().svg)
