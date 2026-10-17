"""Cut a character into alpha-shaped layers, separate facial expression assets, and build a review page.

python build_part_review.py --upstream review.workflow --config split.json --out parts-review.html
Requires Pillow, numpy and scipy. Production requires a valid stage-01 checkpoint.
--demo uses the upstream draft for a clearly marked, non-approvable tool demonstration.
"""
import argparse
import base64
import colorsys
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage, sparse
from scipy.sparse.linalg import spsolve

from part_design import STAGE, validate
from review_checkpoint import checkpoint, digest, initialize, read


def layer_color(index):
    rgb = colorsys.hls_to_rgb((index * 0.61803398875 + 0.015) % 1, 0.47, 0.57)
    return "#" + "".join(f"{round(c * 255):02x}" for c in rgb)


def encode(image):
    output = io.BytesIO()
    image.save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")


def mask_from(spec, size, directory):
    """Use explicit raster masks, polygons or ellipses; never infer a boundary from a joint."""
    if "mask" in spec:
        with Image.open(directory / spec["mask"]) as image:
            if image.size != size:
                raise ValueError("Masks must use full original image dimensions")
            result = image.getchannel("A") if image.mode == "RGBA" else image.convert("L")
            return np.asarray(result) > 127
    mask = Image.new("L", size)
    draw = ImageDraw.Draw(mask)
    polygons = spec.get("polygons", [spec["poly"]] if "poly" in spec else [])
    for polygon in polygons:
        if len(polygon) < 3:
            raise ValueError("A polygon needs at least three points")
        draw.polygon([tuple(p) for p in polygon], fill=255)
    for ellipse in spec.get("ellipses", []):
        draw.ellipse(tuple(ellipse), fill=255)
    if not mask.getbbox():
        raise ValueError("Provide a nonempty mask, polygon or ellipse")
    return np.asarray(mask) > 127


def harmonic_fill(rgb, erase, valid):
    """Solve a Laplace fill inside annotated facial regions using nearby known skin as boundary.

    This preserves a smooth spatial skin gradient, but cannot reconstruct missing texture.
    The review must verify hair/face boundaries and shading rather than treating the fill as ground truth.
    """
    erase = erase & valid
    if not erase.any():
        raise ValueError("Facial feature masks are empty")
    _, components = ndimage.label(valid)
    if components < 1 or not (valid & ~erase).any():
        raise ValueError("Facial repair requires known skin pixels")
    coordinates = np.argwhere(erase)
    indices = np.full(erase.shape, -1, dtype=np.int32)
    indices[erase] = np.arange(len(coordinates))
    rows, cols, values = [], [], []
    rhs = np.zeros((len(coordinates), 3), dtype=float)
    height, width = erase.shape
    for i, (y, x) in enumerate(coordinates):
        count = 0
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            yy, xx = y + dy, x + dx
            if not (0 <= yy < height and 0 <= xx < width and valid[yy, xx]):
                continue
            count += 1
            if erase[yy, xx]:
                rows.append(i); cols.append(int(indices[yy, xx])); values.append(-1)
            else:
                rhs[i] += rgb[yy, xx]
        if not count:
            raise ValueError("A facial repair region has no boundary")
        rows.append(i); cols.append(i); values.append(count)
    matrix = sparse.csr_matrix((values, (rows, cols)), shape=(len(coordinates), len(coordinates)))
    filled = spsolve(matrix, rhs)
    if not np.isfinite(filled).all():
        raise ValueError("Facial repair could not find a valid skin boundary")
    result = rgb.copy()
    result[erase] = np.clip(np.rint(filled), 0, 255).astype(np.uint8)
    return result


def sampled_skin_fill(rgb, erase, samples, valid):
    """Fit a smooth skin-color plane from explicitly annotated known skin samples."""
    if len(samples) < 3:
        raise ValueError("Skin surface repair requires at least three known skin samples")
    points, colors = [], []
    height, width = erase.shape
    for x, y in samples:
        if not (2 <= x < width-2 and 2 <= y < height-2) or erase[y-2:y+3, x-2:x+3].any() or not valid[y-2:y+3, x-2:x+3].all():
            raise ValueError("Skin samples must be known skin outside the erased expression area")
        points.append([1, x/width, y/height])
        colors.append(np.median(rgb[y-2:y+3, x-2:x+3], axis=(0, 1)))
    matrix = np.asarray(points)
    if np.linalg.matrix_rank(matrix) < 3:
        raise ValueError("Skin sample points must not all lie on one line")
    coefficients = np.linalg.lstsq(matrix, np.asarray(colors), rcond=None)[0]
    ys, xs = np.where(erase)
    result = rgb.copy()
    result[erase] = np.clip(np.rint(np.column_stack([np.ones(len(xs)), xs/width, ys/height]) @ coefficients), 0, 255).astype(np.uint8)
    return result


def build(upstream, config_path, out_path, project=None, demo=False):
    gate = checkpoint(upstream)
    if not demo and (gate["status"] != "confirmed" or gate.get("approval_scope") != "skeleton-layout"):
        raise ValueError("Stage 01 must have a valid human-confirmed skeleton checkpoint")
    state = read(upstream / "workflow.json")
    source = read(upstream / "draft.json") if demo else read(Path(gate["confirmed_file"]))["design"]
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    original = Image.open(io.BytesIO(base64.b64decode(source["image"]["src"].split(",", 1)[1]))).convert("RGBA")
    rgba = np.asarray(original)
    inside = rgba[:, :, 3] > 0
    if "foreground" in config:
        inside &= mask_from(config["foreground"], original.size, config_path.parent)
    elif inside.all():
        raise ValueError("An opaque source needs an explicit foreground mask to exclude the background")
    specs = config["parts"]
    ids = [p["id"] for p in specs]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Part IDs must be unique")
    labels = np.full(inside.shape, -1, dtype=np.int16)
    hsv = np.asarray(original.convert("RGB").convert("HSV"))
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    predicates = {"light": (v > 165) & (s < 95), "white": (v > 185) & (s < 55),
                  "red": ((h < 20) | (h > 227)) & (s > 80)}
    predicates["not_light"] = ~predicates["light"]
    for i, spec in enumerate(specs):
        mask = mask_from(spec, original.size, config_path.parent) & inside
        if "color_rule" in spec:
            mask &= predicates[spec["color_rule"]]
        labels[mask & (labels < 0)] = i
    unclaimed = inside & (labels < 0)
    if unclaimed.any():
        if config.get("unclaimed", "error") != "nearest":
            raise ValueError(f"{int(unclaimed.sum())} foreground pixels are unassigned; refine masks or explicitly use unclaimed=nearest")
        if not (labels >= 0).any():
            raise ValueError("No part pixels were assigned")
        _, nearest = ndimage.distance_transform_edt(labels < 0, return_indices=True)
        labels[unclaimed] = labels[tuple(nearest[:, unclaimed])]
    images = {}
    for i, key in enumerate(ids):
        tile = rgba.copy()
        tile[:, :, 3] = np.where(labels == i, rgba[:, :, 3], 0)
        if not tile[:, :, 3].any():
            raise ValueError(f"Part {key} is empty")
        images[key] = tile

    face_spec = config["face"]
    base_id = face_spec["base_part"]
    if base_id not in images:
        raise ValueError("Facial base must be an existing part")
    base = images[base_id]
    features = face_spec["features"]
    if not features:
        raise ValueError("Define the visible facial expression elements")
    feature_masks, erase = {}, np.zeros(inside.shape, dtype=bool)
    for spec in features:
        key = spec["id"]
        if key in ids or key in feature_masks:
            raise ValueError("Facial feature IDs must be unique and different from body parts")
        mask = mask_from(spec, original.size, config_path.parent) & (base[:, :, 3] > 0)
        if not mask.any() or (mask & erase).any():
            raise ValueError(f"Facial feature {key} is empty or overlaps another feature mask")
        feature_masks[key] = mask
        erase |= mask
    feather = int(face_spec.get("feather_px", 3))
    if not 0 <= feather <= 20:
        raise ValueError("face.feather_px must be between 0 and 20")
    if feather:
        seed = np.full(erase.shape, -1, dtype=np.int16)
        for i, feature in enumerate(features):
            seed[feature_masks[feature["id"]]] = i
        distance, nearest = ndimage.distance_transform_edt(~erase, return_indices=True)
        grown = (distance <= feather) & (base[:, :, 3] > 0)
        assignment = seed[tuple(nearest)]
        feature_masks = {feature["id"]: grown & (assignment == i) for i, feature in enumerate(features)}
        erase = grown
    if "clean_base" in face_spec:
        with Image.open(config_path.parent / face_spec["clean_base"]) as edited:
            if edited.size != original.size:
                raise ValueError("Edited blank face must use the full original image dimensions")
            repaired = np.asarray(edited.convert("RGBA"))[:, :, :3].copy()
        repair_method = "designer-supplied"
    elif "skin_samples" in face_spec:
        repaired = sampled_skin_fill(rgba[:, :, :3], erase, face_spec["skin_samples"], base[:, :, 3] > 0)
        if feather:
            blend = np.clip(ndimage.distance_transform_edt(erase)/feather, 0, 1)[:, :, None]
            repaired = np.rint(repaired*blend + rgba[:, :, :3]*(1-blend)).astype(np.uint8)
        repair_method = "sampled-skin-surface"
    else:
        repaired = harmonic_fill(rgba[:, :, :3], erase, base[:, :, 3] > 0)
        repair_method = "harmonic-fill"
    base[:, :, :3] = repaired
    # Original features are independent opaque cutouts; no original feature pixels remain underneath.
    for spec in features:
        tile = rgba.copy()
        tile[:, :, 3] = np.where(feature_masks[spec["id"]], rgba[:, :, 3], 0)
        images[spec["id"]] = tile
    base_order = config.get("order", ids)
    if set(base_order) != set(ids) or len(base_order) != len(ids):
        raise ValueError("order must list each body part once; facial layers are inserted above their base")
    order = list(base_order)
    position = order.index(base_id) + 1
    order[position:position] = [f["id"] for f in features]
    out_dir = out_path.with_name(out_path.stem + ".assets")
    out_dir.mkdir(parents=True, exist_ok=True)
    result_parts = []
    all_specs = {p["id"]: p for p in specs + features}
    known_nodes = {n["id"] for n in source["nodes"]}
    for i, key in enumerate(order):
        spec = all_specs[key]
        full = Image.fromarray(images[key])
        bbox = full.getchannel("A").getbbox()
        tile = full.crop(bbox)
        x0, y0, x1, y1 = bbox
        alpha = tile.getchannel("A")
        binary = np.asarray(alpha) > 0
        # Pad so edge-adjacent silhouettes also get a complete boundary.
        padded = Image.new("L", (tile.width + 4, tile.height + 4))
        padded.paste(alpha.point(lambda p: 255 if p else 0), (2, 2))
        edge = np.asarray(padded.filter(ImageFilter.MaxFilter(3)), dtype=int) - np.asarray(padded.filter(ImageFilter.MinFilter(3)), dtype=int)
        outline = Image.new("RGBA", tile.size, (255, 255, 255, 0))
        outline.putalpha(Image.fromarray(np.clip(edge[2:-2, 2:-2], 0, 255).astype(np.uint8)))
        distances = ndimage.distance_transform_edt(np.pad(binary, 1))[1:-1, 1:-1]
        py, px = np.unravel_index(np.argmax(distances), distances.shape)
        filename = f"{i+1:02d}-{key}.png"
        if any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in key):
            raise ValueError("Part IDs used as filenames must use letters, digits, underscore or hyphen")
        tile.save(out_dir / filename)
        node_ids = spec.get("node_ids", [face_spec["node_id"]] if key in feature_masks and face_spec.get("node_id") else [])
        if any(n not in known_nodes for n in node_ids):
            raise ValueError("Part references an unknown skeleton node")
        result_parts.append({"id": key, "label": spec.get("label", key), "x": x0, "y": y0,
                             "w": x1-x0, "h": y1-y0, "src": encode(tile), "outline_src": encode(outline),
                             "label_point": [int(x0+px), int(y0+py)],
                             "color": spec.get("color", layer_color(i)),
                             "category": "expression" if key in feature_masks else "face_base" if key == base_id else "body",
                             "feature_kind": spec.get("kind"), "node_ids": node_ids,
                             "review": "proposed", "quality": "pending", "note": spec.get("note", ""),
                             "file": filename})
    nodes = json.loads(json.dumps(source["nodes"]))
    for node in nodes:
        node["parts"] = [p["id"] for p in result_parts if node["id"] in p["node_ids"]]
    data = {"schema_version": 1, "title": config.get("title", "角色切片与图层检查"),
            "image": source["image"], "coordinate_system": source["coordinate_system"],
            "nodes": nodes, "parts": result_parts, "order": order,
            "face": {"base_part": base_id, "feature_ids": [f["id"] for f in features],
                     "roi": face_spec["roi"], "review": "proposed", "repair_method": repair_method,
                     "note": "已移除标注的表情像素并修补底色；需要检查肤色、发际和五官残留。"},
            "demo": demo, "unclaimed_pixels": int(unclaimed.sum()),
            "note": "演示：沿用旧女巫切片和推测面部范围，仅展示第二阶段工具，不能放行正式流程。" if demo else config.get("note", source.get("note", "")),
            "upstream": {"project": str(upstream.resolve()), "run_id": state["run_id"],
                         "revision": state["revision"], "design_sha256": digest(source)}}
    validate(data)
    project = project or out_path.with_name(out_path.stem + ".workflow")
    data = initialize(project.resolve(), data, out_path, stage=STAGE)
    template = (Path(__file__).resolve().parent.parent / "assets" / "part-review.html").read_text(encoding="utf-8")
    opening = '<script id="rig-data" type="application/json">'
    start = template.index(opening) + len(opening)
    end = template.index("</script>", start)
    html = template[:start] + json.dumps(data, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c") + template[end:]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    (out_dir / "parts.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    np.save(out_dir / "labels.npy", labels)
    (out_dir / "labels-order.json").write_text(json.dumps(ids, ensure_ascii=False), encoding="utf-8")
    Image.fromarray(erase.astype(np.uint8)*255).save(out_dir / "face-erased-mask.png")
    print(json.dumps({"preview": str(out_path.resolve()), "project": str(project.resolve()),
                      "assets": str(out_dir.resolve()), "layers": len(result_parts), "demo": demo}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    build(args.upstream.resolve(), args.config.resolve(), args.out.resolve(), args.project, args.demo)
