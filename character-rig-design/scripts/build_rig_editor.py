"""Embed a character image and proposed nodes in the stage-01 browser editor.

Usage: python build_rig_editor.py --image character.png --config structure.json --out review.html
Omit --config to produce a blank editor with the selected image. Requires Pillow.
Also creates <output-stem>.workflow; use review_checkpoint.py serve to enable human confirmation.
"""
import argparse
import base64
import io
import json
import math
from pathlib import Path

from PIL import Image, ImageOps


COORDINATES = {"origin": "top-left", "units": "px", "x": "right", "y": "down"}


def validate(data):
    if data.get("schema_version", 1) != 1:
        raise ValueError("Unsupported schema_version")
    if data.get("coordinate_system", COORDINATES) != COORDINATES:
        raise ValueError("Coordinates must use original image pixels, top-left origin")
    nodes = data.get("nodes", [])
    if not isinstance(nodes, list):
        raise ValueError("nodes must be an array")
    by_id = {}
    width, height = data["image"]["width"], data["image"]["height"]
    for n in nodes:
        key = n.get("id")
        if not isinstance(key, str) or not key.strip() or key in by_id:
            raise ValueError("Node IDs must be nonempty and unique")
        for axis, limit in (("x", width), ("y", height)):
            value = n.get(axis)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= limit:
                raise ValueError(f"Invalid {axis} coordinate for {key}")
        n.setdefault("parent", None)
        n.setdefault("label", key)
        n.setdefault("type", "joint")
        n.setdefault("placement", "visible")
        n.setdefault("review", "proposed")
        n.setdefault("parts", [])
        n.setdefault("note", "")
        if (n["type"] not in ("joint", "anchor", "control")
                or n["placement"] not in ("visible", "inferred")
                or n["review"] not in ("proposed", "adjusted", "confirmed")
                or not isinstance(n["label"], str) or not isinstance(n["note"], str)
                or not isinstance(n["parts"], list) or any(not isinstance(p, str) for p in n["parts"])
                or n["parent"] is not None and not isinstance(n["parent"], str)):
            raise ValueError(f"Invalid node attributes for {key}")
        by_id[key] = n
    for n in nodes:
        seen = {n["id"]}
        parent = n["parent"]
        while parent is not None:
            if parent not in by_id:
                raise ValueError(f"Missing parent: {parent}")
            if parent in seen:
                raise ValueError("Node hierarchy contains a cycle")
            seen.add(parent)
            parent = by_id[parent]["parent"]
    parts = data.get("parts", [])
    if not isinstance(parts, list):
        raise ValueError("parts must be an array")
    part_ids = set()
    for part in parts:
        key = part.get("id")
        if not isinstance(key, str) or not key.strip() or key in part_ids:
            raise ValueError("Part IDs must be nonempty and unique")
        part_ids.add(key)
        if "node_ids" in part and (not isinstance(part["node_ids"], list) or any(not isinstance(k, str) or k not in by_id for k in part["node_ids"])):
            raise ValueError(f"Part {key} references missing nodes")


def build(image_path, config_path, out_path, project_path=None):
    data = json.loads(config_path.read_text(encoding="utf-8-sig")) if config_path else {}
    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
        width, height = image.size
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
    previous = data.get("image") or {}
    if previous.get("width", width) != width or previous.get("height", height) != height:
        raise ValueError("Config image dimensions do not match the image after EXIF orientation")
    data["image"] = {**previous, "name": image_path.name, "width": width, "height": height,
                     "src": "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")}
    data.setdefault("schema_version", 1)
    data.setdefault("title", image_path.stem)
    data.setdefault("coordinate_system", COORDINATES.copy())
    data.setdefault("nodes", [])
    data.setdefault("parts", [])
    validate(data)
    # Import lazily so the bridge can reuse validation without an import-time cycle.
    from review_checkpoint import initialize
    project_path = project_path or out_path.with_name(out_path.stem + ".workflow")
    data = initialize(project_path.resolve(), data, out_path)
    template = (Path(__file__).resolve().parent.parent / "assets" / "rig-editor.html").read_text(encoding="utf-8")
    opening = '<script id="rig-data" type="application/json">'
    start = template.index(opening) + len(opening)
    end = template.index('</script>', start)
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    page = template[:start] + payload + template[end:]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    print(f"Created {out_path.resolve()} ({width} x {height}, {len(data['nodes'])} nodes)")
    print(f"Checkpoint project: {project_path.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--project", type=Path, help="Checkpoint directory (default: <output-stem>.workflow)")
    args = parser.parse_args()
    build(args.image, args.config, args.out, args.project)
