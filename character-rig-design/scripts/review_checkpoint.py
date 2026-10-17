"""Local review bridge and per-stage human checkpoint gates.

serve --project DIR: serve the editor and persist human edits/confirmation.
check --project DIR: exit 0 only for a current valid human confirmation; 2 = waiting.
wait --project DIR --timeout 30: bounded polling, with the same exit codes.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from build_rig_editor import validate


STAGE = "01-character-structure"
PART_STAGE = "02-part-separation"
MATERIAL_STAGE = "03-material-completion"
RESULT_STAGE = "04-material-result"
ANIMATION_STAGE = "05-skeleton-animation"
MOTION_STAGE = "06-motion-production"
SCOPES = {STAGE: "skeleton-layout", PART_STAGE: "part-separation", MATERIAL_STAGE: "material-repair-plan", RESULT_STAGE: "material-repair-result", ANIMATION_STAGE: "skeleton-animation-rig", MOTION_STAGE:"animation-clips"}
UPSTREAM_STAGES = {PART_STAGE:STAGE,MATERIAL_STAGE:PART_STAGE,RESULT_STAGE:MATERIAL_STAGE,ANIMATION_STAGE:RESULT_STAGE,MOTION_STAGE:ANIMATION_STAGE}


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value):
    content = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def image_digest(data):
    return hashlib.sha256(base64.b64decode(data["image"]["src"].split(",", 1)[1], validate=True)).hexdigest()


def atomic_write(path, value):
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(temp, path)


def clean_design(value):
    data = json.loads(json.dumps(value, allow_nan=False))
    data.pop("updated_at", None)
    if data.get("workflow", {}).get("stage") == MOTION_STAGE:
        from motion_design import validate as validate_motion
        validate_motion(data)
    elif data.get("workflow", {}).get("stage") == ANIMATION_STAGE:
        from animation_design import validate as validate_animation
        validate_animation(data)
    elif data.get("workflow", {}).get("stage") == RESULT_STAGE:
        from material_result import validate as validate_result
        validate_result(data)
    elif data.get("workflow", {}).get("stage") == MATERIAL_STAGE:
        from material_plan import validate as validate_plan
        validate_plan(data)
    elif data.get("workflow", {}).get("stage") == PART_STAGE:
        from part_design import validate as validate_parts
        validate_parts(data)
    else:
        validate(data)
    if not data.get("image"):
        raise ValueError("A review needs an image")
    return data


def initialize(project, data, preview, stage=STAGE):
    """Always start a new run; an earlier confirmation cannot approve a rebuilt design."""
    project.mkdir(parents=True, exist_ok=True)
    run_id = secrets.token_hex(16)
    if stage not in SCOPES:
        raise ValueError("Unsupported review stage")
    data["workflow"] = {"run_id": run_id, "stage": stage}
    data = clean_design(data)
    state = {"schema_version": 1, "run_id": run_id, "stage": stage,
             "status": "awaiting_review", "revision": 0, "created_at": now(),
             "preview_path": str(preview.resolve()), "image_sha256": image_digest(data),
             "image_width": data["image"]["width"], "image_height": data["image"]["height"],
             "design_sha256": digest(data)}
    if stage in UPSTREAM_STAGES:
        state["upstream"] = data["upstream"]
        state["demo"] = bool(data.get("demo"))
    if stage == MATERIAL_STAGE:
        from material_plan import source_fingerprint
        state["input_sha256"] = source_fingerprint(data)
    if stage == RESULT_STAGE:
        from material_result import source_fingerprint
        state["input_sha256"] = source_fingerprint(data)
    if stage == ANIMATION_STAGE:
        from animation_design import source_fingerprint
        state["input_sha256"] = source_fingerprint(data)
    if stage == MOTION_STAGE:
        from motion_design import source_fingerprint
        state["input_sha256"] = source_fingerprint(data)
    # Publish the waiting marker before changing the draft. Failures remain closed.
    atomic_write(project / "workflow.json", state)
    atomic_write(project / "draft.json", data)
    return data


def validate_for_run(data, state):
    data = clean_design(data)
    if data.get("workflow") != {"run_id": state["run_id"], "stage": state["stage"]}:
        raise ValueError("Review belongs to a different run")
    if (image_digest(data) != state["image_sha256"]
            or data["image"]["width"] != state["image_width"]
            or data["image"]["height"] != state["image_height"]):
        raise ValueError("Image changed; create a new review run")
    if state["stage"] in UPSTREAM_STAGES and (data.get("upstream") != state.get("upstream") or bool(data.get("demo")) != state.get("demo")):
        raise ValueError("Upstream dependency or demo flag changed")
    if state["stage"] == MATERIAL_STAGE:
        from material_plan import source_fingerprint
        if source_fingerprint(data) != state.get("input_sha256"):
            raise ValueError("Plan input assets or AI evidence changed; rebuild review")
    if state["stage"] == RESULT_STAGE:
        from material_result import source_fingerprint
        if source_fingerprint(data) != state.get("input_sha256"):
            raise ValueError("Repair result changed; rebuild review instead of overwriting assets")
    if state["stage"] == ANIMATION_STAGE:
        from animation_design import source_fingerprint
        if source_fingerprint(data) != state.get("input_sha256"):
            raise ValueError('Source bones, artwork or layer order changed; rebuild animation review')
    if state["stage"] == MOTION_STAGE:
        from motion_design import source_fingerprint
        if source_fingerprint(data) != state.get("input_sha256"):
            raise ValueError('Confirmed rig or source artwork changed; rebuild motion production')
    return data


def checkpoint(project, visited=None):
    try:
        visited = set() if visited is None else visited
        resolved = str(project.resolve())
        if resolved in visited:
            raise ValueError("Checkpoint dependency contains a cycle")
        visited.add(resolved)
        state = read(project / "workflow.json")
        stage = state["stage"]
        if stage not in SCOPES:
            raise ValueError("Unsupported checkpoint stage")
        if state["status"] != "confirmed":
            return {"status": "awaiting_review", "run_id": state["run_id"], "revision": state["revision"]}
        approval = read(project / "confirmed.json")
        draft = validate_for_run(read(project / "draft.json"), state)
        design = validate_for_run(approval["design"], state)
        if stage == STAGE:
            if not design["nodes"] or any(n["review"] != "confirmed" for n in design["nodes"]):
                raise ValueError("Nodes have not been confirmed")
        else:
            if stage == MATERIAL_STAGE:
                from material_plan import is_confirmed
            elif stage == MOTION_STAGE:
                from motion_design import is_confirmed
            elif stage == ANIMATION_STAGE:
                from animation_design import is_confirmed
            else:
                from part_design import is_confirmed
            if not is_confirmed(design):
                raise ValueError("Skeleton binding and motion have not been confirmed" if stage == ANIMATION_STAGE else "Material repair plan has not been confirmed" if stage == MATERIAL_STAGE else "Parts, blank face and expression layers have not been confirmed")
            dependency = state["upstream"]
            gate = checkpoint(Path(dependency["project"]), visited)
            expected_scope = SCOPES[UPSTREAM_STAGES[stage]]
            if gate["status"] != "confirmed" or gate.get("approval_scope") != expected_scope:
                raise ValueError("Upstream confirmation is no longer valid")
            upstream = read(Path(dependency["project"]) / "confirmed.json")
            if any(upstream[key] != dependency[key] for key in ("run_id", "revision", "design_sha256")):
                raise ValueError("Upstream revision changed; rebuild downstream review")
        if (approval["status"] != "confirmed" or approval["stage"] != stage
                or approval["run_id"] != state["run_id"] or approval["revision"] != state["revision"]
                or approval["approval_scope"] != SCOPES[stage] or not approval.get("confirmed_at")
                or approval["design_sha256"] != digest(design)
                or state["design_sha256"] != digest(design) or digest(draft) != digest(design)):
            raise ValueError("Checkpoint is stale or its data changed")
        if read(project / "workflow.json") != state:
            raise ValueError("Review changed while checking; retry")
        return {"status": "confirmed", "run_id": state["run_id"], "revision": state["revision"],
                "approval_scope": SCOPES[stage], "confirmed_file": str((project / "confirmed.json").resolve()),
                "confirmed_at": approval["confirmed_at"], "next_stage": PART_STAGE if stage == STAGE else MATERIAL_STAGE if stage == PART_STAGE else RESULT_STAGE if stage == MATERIAL_STAGE else ANIMATION_STAGE if stage == RESULT_STAGE else MOTION_STAGE if stage == ANIMATION_STAGE else "delivery"}
    except (OSError, ValueError, KeyError, TypeError) as e:
        return {"status": "awaiting_review", "reason": str(e)}


def serve(project, port):
    state = read(project / "workflow.json")
    validate_for_run(read(project / "draft.json"), state)
    run_id, token = state["run_id"], secrets.token_urlsafe(32)
    lock = threading.Lock()
    base_url = ""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, status, body, content_type="application/json; charset=utf-8"):
            payload = body.encode("utf-8") if isinstance(body, str) else json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == "/review-history.html" or self.path.startswith("/history/"):
                name = self.path.removeprefix("/history/")
                if self.path == "/review-history.html":
                    target = project.parent / "review-history.html"
                elif Path(name).name == name and name.endswith(".html"):
                    target = project.parent / "history" / name
                else:
                    return self.respond(404, {"error": "Not found"})
                try:
                    return self.respond(200, target.read_text(encoding="utf-8"), "text/html; charset=utf-8")
                except OSError:
                    return self.respond(404, {"error": "History snapshot not found"})
            if self.path not in ("/", "/index.html"):
                return self.respond(404, {"error": "Not found"})
            try:
                with lock:
                    current = read(project / "workflow.json")
                    if current["run_id"] != run_id:
                        raise ValueError("Run changed; restart the review server")
                    data = validate_for_run(read(project / "draft.json"), current)
                    page = Path(current["preview_path"]).read_text(encoding="utf-8")
                    for ident, value in (("rig-data", data), ("checkpoint-config", {
                            "run_id": run_id, "token": token, "base_url": base_url,
                            "revision": current["revision"], "status": checkpoint(project)["status"]})):
                        opening = f'<script id="{ident}" type="application/json">'
                        start = page.index(opening) + len(opening)
                        end = page.index("</script>", start)
                        payload = json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")
                        page = page[:start] + payload + page[end:]
                self.respond(200, page, "text/html; charset=utf-8")
            except (OSError, ValueError, KeyError) as e:
                self.respond(409, {"error": str(e)})

        def do_POST(self):
            if (self.path not in ("/api/draft", "/api/confirm", "/api/erase", "/api/paint")
                    or self.headers.get("X-Review-Token") != token
                    or self.headers.get("Origin") != base_url):
                return self.respond(403, {"error": "Review session mismatch"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 50 * 1024 * 1024:
                    raise ValueError("Invalid review payload size")
                request = json.loads(self.rfile.read(length))
                with lock:
                    current = read(project / "workflow.json")
                    if current["run_id"] != run_id or request.get("run_id") != run_id:
                        raise ValueError("Run changed; reopen the review page")
                    if request.get("revision") != current["revision"]:
                        raise ValueError("Another page changed this review; reload before continuing")
                    if self.path in ("/api/erase", "/api/paint"):
                        if current['stage'] != RESULT_STAGE:
                            raise ValueError('Pixel eraser is only available in result review')
                        from pixel_erase import apply_erase,apply_paint,persist_assets
                        from material_result import source_fingerprint
                        from export_review_history import export_stage
                        original = validate_for_run(read(project / 'draft.json'),current)
                        if self.path == '/api/paint':
                            data = apply_paint(original,request.get('part_id'),request.get('png'),request.get('mask'),request.get('paint_mask'))
                        else:
                            data = apply_erase(original,request.get('part_id'),request.get('png'))
                        export_stage(project)
                        persist_assets(data,project)
                        clean_design(data)
                        current.update(status='awaiting_review',revision=current['revision']+1,
                                       design_sha256=digest(data),input_sha256=source_fingerprint(data),updated_at=now())
                        current.pop('confirmed_at',None)
                        atomic_write(project / 'workflow.json',current)
                        atomic_write(project / 'draft.json',data)
                        result={'status':current['status'],'revision':current['revision'],'design':data}
                        try:export_stage(project)
                        except (OSError,ValueError,KeyError) as e:result['history_error']=str(e)
                        return self.respond(200,result)
                    data = validate_for_run(request["design"], current)
                    edited_materials = False
                    if current['stage'] == MOTION_STAGE and self.path == '/api/draft':
                        old = read(project / 'draft.json')['production']
                        edited_materials = any(old.get(key) != data['production'].get(key)
                                               for key in ('material_overrides','layer_order','face_underlay'))
                        if edited_materials:
                            from export_review_history import export_stage
                            export_stage(project)
                    if self.path == "/api/confirm":
                        if current["stage"] == STAGE:
                            if not data["nodes"]:
                                raise ValueError("Add at least one node before confirming")
                            for node in data["nodes"]:
                                node["review"] = "confirmed"
                        else:
                            if current["stage"] == MATERIAL_STAGE:
                                from material_plan import confirm_design
                            elif current["stage"] == MOTION_STAGE:
                                from motion_design import confirm_design
                            elif current["stage"] == ANIMATION_STAGE:
                                from animation_design import confirm_design
                            else:
                                from part_design import confirm_design
                            confirm_design(data)
                            dependency = current["upstream"]
                            gate = checkpoint(Path(dependency["project"]))
                            if gate["status"] != "confirmed":
                                raise ValueError("Upstream stage needs valid human confirmation")
                            approved = read(Path(dependency["project"]) / "confirmed.json")
                            if any(approved[key] != dependency[key] for key in ("run_id", "revision", "design_sha256")):
                                raise ValueError("Upstream revision changed; rebuild this stage")
                    current.update(status="awaiting_review", revision=current["revision"] + 1,
                                   design_sha256=digest(data), updated_at=now())
                    current.pop("confirmed_at", None)
                    # Invalidate first, so crashes or partial writes cannot approve an old snapshot.
                    atomic_write(project / "workflow.json", current)
                    atomic_write(project / "draft.json", data)
                    if self.path == "/api/confirm":
                        approved_at = now()
                        approval = {"schema_version": 1, "run_id": run_id, "stage": current["stage"],
                                    "status": "confirmed", "revision": current["revision"],
                                    "approval_scope": SCOPES[current["stage"]], "confirmed_at": approved_at,
                                    "design_sha256": digest(data), "design": data}
                        atomic_write(project / "confirmed.json", approval)
                        current.update(status="confirmed", confirmed_at=approved_at)
                        atomic_write(project / "workflow.json", current)
                    result = {"status": current["status"], "revision": current["revision"]}
                    if self.path == "/api/confirm" or edited_materials:
                        try:
                            from export_review_history import export_stage
                            export_stage(project)
                        except (OSError, ValueError, KeyError) as e:
                            # Approval already succeeded; do not invite a
                            # duplicate submission when only history failed.
                            result["history_error"] = str(e)
                    self.respond(200, result)
            except (OSError, ValueError, KeyError, TypeError) as e:
                self.respond(409, {"error": str(e)})

    # Some Windows hosts allocate ephemeral ports that Chromium blocks (e.g. 5061).
    for _ in range(32):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port or 20000 + secrets.randbelow(40000)), Handler)
            break
        except OSError:
            if port:
                raise
    else:
        raise OSError("Could not allocate a browser-compatible local port")
    base_url = f"http://127.0.0.1:{server.server_port}"
    atomic_write(project / "server.json", {"run_id": run_id, "pid": os.getpid(), "url": base_url})
    print(json.dumps({"url": base_url, "project": str(project), "run_id": run_id}), flush=True)
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("serve", "check", "wait"))
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    project = args.project.resolve()
    if args.command == "serve":
        serve(project, args.port)
    else:
        deadline = time.monotonic() + max(0, min(50, args.timeout)) if args.command == "wait" else 0
        while True:
            result = checkpoint(project)
            if result["status"] == "confirmed" or time.monotonic() >= deadline:
                print(json.dumps(result, ensure_ascii=False), flush=True)
                sys.exit(0 if result["status"] == "confirmed" else 2)
            time.sleep(0.5)
