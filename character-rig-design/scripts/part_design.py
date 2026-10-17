"""Validation of stage-02 cutouts shared by generation and checkpoint review."""
import base64
import io
import math

from PIL import Image

from build_rig_editor import validate as validate_structure


STAGE = "02-part-separation"


def decode_png(src):
    if not isinstance(src, str) or not src.startswith("data:image/png;base64,"):
        raise ValueError("Layer assets must be embedded PNGs")
    with Image.open(io.BytesIO(base64.b64decode(src.split(",", 1)[1], validate=True))) as image:
        image.load()
        return image.convert("RGBA")


def validate(data):
    validate_structure(data)
    parts = data["parts"]
    ids = {p["id"] for p in parts}
    if not parts or set(data.get("order", [])) != ids or len(data.get("order", [])) != len(ids):
        raise ValueError("order must list every part exactly once, back to front")
    for p in parts:
        if not isinstance(p.get("label"), str) or not isinstance(p.get("color"), str):
            raise ValueError("Each layer needs a label and color")
        color = p["color"]
        if len(color) != 7 or color[0] != "#" or any(c not in "0123456789abcdefABCDEF" for c in color[1:]):
            raise ValueError("Layer colors must be #RRGGBB")
        if p.get("review") not in ("proposed", "adjusted", "confirmed") or p.get("quality") not in ("pending", "accepted", "needs_repair"):
            raise ValueError("Invalid layer review or quality state")
        for key in ("x", "y", "w", "h"):
            if isinstance(p.get(key), bool) or not isinstance(p.get(key), int):
                raise ValueError("Layer bounds must use integer image pixels")
        if p["x"] < 0 or p["y"] < 0 or p["w"] <= 0 or p["h"] <= 0 or p["x"] + p["w"] > data["image"]["width"] or p["y"] + p["h"] > data["image"]["height"]:
            raise ValueError("Layer bounds exceed original image")
        tile = decode_png(p.get("src"))
        if tile.size != (p["w"], p["h"]) or not tile.getchannel("A").getbbox():
            raise ValueError("Layer PNG has invalid dimensions or is empty")
        if decode_png(p.get("outline_src")).size != tile.size:
            raise ValueError("Layer outline dimensions do not match")
        point = p.get("label_point", [])
        if len(point) != 2 or any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in point):
            raise ValueError("Invalid layer label position")
        px, py = int(point[0] - p["x"]), int(point[1] - p["y"])
        if not (0 <= px < p["w"] and 0 <= py < p["h"]) or tile.getpixel((px, py))[3] == 0:
            raise ValueError("Numeric layer label must lie inside the actual alpha silhouette")
    face = data.get("face")
    if not isinstance(face, dict) or face.get("base_part") not in ids or not face.get("feature_ids"):
        raise ValueError("Separate blank face base and expression layers are required")
    if len(set(face["feature_ids"])) != len(face["feature_ids"]) or face["base_part"] in face["feature_ids"]:
        raise ValueError("Expression layers must be unique and separate from the face base")
    if face.get("review") not in ("proposed", "adjusted", "confirmed"):
        raise ValueError("Invalid face review status")
    by_id = {p["id"]: p for p in parts}
    for key in face["feature_ids"]:
        if key not in ids or by_id[key].get("category") != "expression":
            raise ValueError("Missing independent expression layer")
        if data["order"].index(key) <= data["order"].index(face["base_part"]):
            raise ValueError("Expressions must be drawn above the blank face base")
    roi = face.get("roi", [])
    if len(roi) != 4 or not all(isinstance(v, int) and not isinstance(v, bool) for v in roi) or not (0 <= roi[0] < roi[2] <= data["image"]["width"] and 0 <= roi[1] < roi[3] <= data["image"]["height"]):
        raise ValueError("Face ROI must lie inside the original image")
    underlay = face.get("underlay")
    if underlay is not None:
        if not isinstance(underlay, dict) or any(isinstance(underlay.get(k), bool) or not isinstance(underlay.get(k), int) for k in ("x", "y", "w", "h")):
            raise ValueError("Face underlay must have integer image bounds")
        if not (0 <= underlay["x"] < underlay["x"] + underlay["w"] <= data["image"]["width"] and 0 <= underlay["y"] < underlay["y"] + underlay["h"] <= data["image"]["height"]):
            raise ValueError("Face underlay exceeds original image")
        if decode_png(underlay.get("src")).size != (underlay["w"], underlay["h"]):
            raise ValueError("Face underlay PNG dimensions do not match")


def confirm_design(data):
    if data.get("demo"):
        raise ValueError("This is a demonstration, not a production checkpoint")
    if any(p["quality"] == "needs_repair" for p in data["parts"]):
        raise ValueError("Repair layers marked needs_repair before confirming")
    for p in data["parts"]:
        p.update(review="confirmed", quality="accepted")
    data["face"]["review"] = "confirmed"


def is_confirmed(data):
    return (not data.get("demo") and data["face"]["review"] == "confirmed"
            and all(p["review"] == "confirmed" and p["quality"] == "accepted" for p in data["parts"]))
