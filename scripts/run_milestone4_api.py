"""Run the Milestone 4 API checks against a live InfraScan server.

This is the executable equivalent of postman/InfraScan_API_Tests.postman_collection.json.
It uses httpx. It does not claim to be the Postman desktop application.
Passwords and tokens are never printed. The JSON and HTML reports mask them.

Required environment variable:
  INFRASCAN_DEMO_PASSWORD  seeded demo password, not written to the report

Optional:
  INFRASCAN_BASE_URL       default http://127.0.0.1:8000
  INFRASCAN_SAMPLE_IMAGE   default docs/eda_outputs/samples/deepcrack/11120.jpg
  INFRASCAN_EVIDENCE_DIR   default evidence/milestone_4
                           Set this to another folder when a re-run must not
                           overwrite the recorded Milestone 4 evidence.
"""

from __future__ import annotations

import html
import json
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path(os.environ.get("INFRASCAN_EVIDENCE_DIR", str(ROOT / "evidence" / "milestone_4")))
BASE = os.environ.get("INFRASCAN_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
SAMPLE = Path(
    os.environ.get(
        "INFRASCAN_SAMPLE_IMAGE",
        str(ROOT / "docs" / "eda_outputs" / "samples" / "deepcrack" / "11120.jpg"),
    )
)
PASSWORD = os.environ.get("INFRASCAN_DEMO_PASSWORD", "")

CHECKS: list[dict] = []


_JWT_ALPHABET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


def _looks_like_jwt(value: str) -> bool:
    parts = value.split(".")
    if len(parts) != 3:
        return False
    return all(len(part) >= 8 and set(part) <= _JWT_ALPHABET for part in parts)


def mask(value):
    secret_keys = {"access_token", "password", "password_hash", "authorization", "demo_password"}
    if isinstance(value, dict):
        masked = {}
        for key, item in value.items():
            if key.lower() in secret_keys:
                masked[key] = "***masked***"
            else:
                masked[key] = mask(item)
        return masked
    if isinstance(value, list):
        return [mask(item) for item in value]
    if isinstance(value, str) and _looks_like_jwt(value):
        return "***masked-jwt***"
    return value


def record(name: str, passed: bool, status: int | None, detail: str, body=None, skipped: bool = False) -> None:
    CHECKS.append({
        "name": name,
        "passed": passed,
        "skipped": skipped,
        "status": status,
        "detail": detail,
        "body": mask(body) if body is not None else None,
    })
    label = "SKIP" if skipped else ("PASS" if passed else "FAIL")
    print(f"[{label}] {name} status={status} {detail}")


def expect(name: str, response: httpx.Response, code: int, detail: str, body=None) -> bool:
    ok = response.status_code == code
    shown = body if body is not None else _safe_json(response)
    record(name, ok, response.status_code, detail if ok else f"expected {code}: {detail}", shown)
    return ok


def _safe_json(response: httpx.Response):
    try:
        return response.json()
    except Exception:
        text = response.text[:500]
        return {"non_json": text}


def login(client: httpx.Client, email: str) -> dict | None:
    response = client.post("/auth/login", data={"username": email, "password": PASSWORD})
    body = _safe_json(response)
    if response.status_code != 200 or "access_token" not in body:
        record(f"Login {email}", False, response.status_code, "login failed", body)
        return None
    record(
        f"Login {email}",
        True,
        200,
        f"role={body.get('user', {}).get('role', {}).get('name')}",
        body,
    )
    return body


def write_reports(newman_note: str) -> None:
    passed = sum(1 for row in CHECKS if row["passed"] and not row["skipped"])
    failed = sum(1 for row in CHECKS if not row["passed"] and not row["skipped"])
    skipped = sum(1 for row in CHECKS if row["skipped"])
    summary = {
        "runner": "scripts/run_milestone4_api.py",
        "runner_kind": "Python httpx acceptance run. Not the Postman desktop application.",
        "base_url": BASE,
        "total": len(CHECKS),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "newman": newman_note,
        "checks": CHECKS,
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "api_results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    sections: dict[str, list[dict]] = {
        "health": [],
        "login": [],
        "protected": [],
        "invalid": [],
        "authorization": [],
        "assets": [],
        "inspections": [],
        "upload": [],
        "analysis": [],
        "other": [],
    }
    for row in CHECKS:
        name = row["name"].lower()
        if "health" in name:
            bucket = "health"
        elif "login" in name:
            bucket = "login"
        elif "invalid" in name or "missing token" in name:
            bucket = "invalid"
        elif "profile" in name or "protected" in name or name.startswith("get /auth/me"):
            bucket = "protected"
        elif "cannot" in name or "inspector can" in name or "manager cannot" in name:
            bucket = "authorization"
        elif "asset" in name or "persist" in name or "delet" in name:
            bucket = "assets"
        elif "inspection" in name or "history" in name:
            bucket = "inspections"
        elif "upload" in name or "image list" in name:
            bucket = "upload"
        elif "analy" in name or "model status" in name or "stats" in name or "geometry" in name or "classification" in name or "detection" in name or "segmentation" in name:
            bucket = "analysis"
        else:
            bucket = "other"
        sections[bucket].append(row)

    def render_rows(rows: list[dict]) -> str:
        if not rows:
            return "<p>No checks in this section.</p>"
        blocks = []
        for row in rows:
            state = "skipped" if row["skipped"] else ("pass" if row["passed"] else "fail")
            body = ""
            if row["body"] is not None:
                pretty = json.dumps(row["body"], indent=2)
                body = f"<pre>{html.escape(pretty)}</pre>"
            blocks.append(
                "<article class='check {state}'>"
                "<h3>{state_label} · {name}</h3>"
                "<p>HTTP {status}. {detail}</p>"
                "{body}</article>".format(
                    state=state,
                    state_label=state.upper(),
                    name=html.escape(row["name"]),
                    status=html.escape(str(row["status"])),
                    detail=html.escape(row["detail"]),
                    body=body,
                )
            )
        return "\n".join(blocks)

    collection_path = ROOT / "postman" / "InfraScan_API_Tests.postman_collection.json"
    collection = json.loads(collection_path.read_text(encoding="utf-8"))
    tree = []
    for folder in collection["item"]:
        names = "".join(f"<li>{html.escape(child['name'])} · {html.escape(child['request']['method'])} {html.escape(child['request']['url'])}</li>" for child in folder["item"])
        tree.append(f"<h3>{html.escape(folder['name'])}</h3><ul>{names}</ul>")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>InfraScan API acceptance report</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 32px; color: #122033; background: #f4f7fb; }}
    h1 {{ margin-bottom: 0; }}
    .banner {{ background: #10233f; color: white; padding: 20px 24px; border-radius: 12px; }}
    .banner p {{ margin: 8px 0 0; max-width: 860px; }}
    .summary {{ display: flex; gap: 16px; margin: 20px 0; }}
    .summary div {{ background: white; border-radius: 12px; padding: 16px 20px; min-width: 120px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
    .summary strong {{ display: block; font-size: 28px; }}
    section {{ background: white; border-radius: 12px; padding: 20px; margin: 16px 0; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
    .pass h3 {{ color: #0f7b3a; }}
    .fail h3 {{ color: #a32020; }}
    .skipped h3 {{ color: #8a5a00; }}
    pre {{ background: #0f172a; color: #e2e8f0; padding: 12px; border-radius: 8px; overflow: auto; white-space: pre-wrap; }}
    code {{ font-family: Consolas, monospace; }}
  </style>
</head>
<body>
  <div class="banner">
    <h1>InfraScan API acceptance report</h1>
    <p>Produced by <code>scripts/run_milestone4_api.py</code> with Python httpx against {html.escape(BASE)}. This is not a Postman desktop screenshot. The importable collection is <code>postman/InfraScan_API_Tests.postman_collection.json</code>.</p>
    <p>{html.escape(newman_note)}</p>
  </div>
  <div class="summary" id="summary">
    <div><strong>{len(CHECKS)}</strong>Total requests</div>
    <div><strong>{passed}</strong>Passed</div>
    <div><strong>{failed}</strong>Failed</div>
    <div><strong>{skipped}</strong>Skipped</div>
  </div>
  <section id="collection"><h2>Postman collection contents</h2>{''.join(tree)}</section>
  <section id="health"><h2>Health check</h2>{render_rows(sections['health'])}</section>
  <section id="login"><h2>Login and JWT (token masked)</h2>{render_rows(sections['login'])}</section>
  <section id="protected"><h2>Protected endpoint</h2>{render_rows(sections['protected'])}</section>
  <section id="invalid"><h2>Invalid and missing token</h2>{render_rows(sections['invalid'])}</section>
  <section id="authorization"><h2>Role authorization</h2>{render_rows(sections['authorization'])}</section>
  <section id="assets"><h2>Asset API</h2>{render_rows(sections['assets'])}</section>
  <section id="inspections"><h2>Inspection API</h2>{render_rows(sections['inspections'])}</section>
  <section id="upload"><h2>Image upload</h2>{render_rows(sections['upload'])}</section>
  <section id="analysis"><h2>Image analysis</h2>{render_rows(sections['analysis'])}</section>
</body>
</html>
"""
    (EVIDENCE / "api_report.html").write_text(page, encoding="utf-8")
    print(f"TOTAL={len(CHECKS)} PASSED={passed} FAILED={failed} SKIPPED={skipped}")
    print(f"Wrote {EVIDENCE / 'api_results.json'}")


def main() -> int:
    if not PASSWORD:
        print("INFRASCAN_DEMO_PASSWORD is not set. Refusing to embed a password in this script.", file=sys.stderr)
        return 2
    newman_note = os.environ.get("INFRASCAN_NEWMAN_NOTE", "Newman was not used for this report.")
    timeout = httpx.Timeout(180.0, connect=10.0)
    try:
        with httpx.Client(base_url=BASE, timeout=timeout) as client:
            health = client.get("/health")
            body = _safe_json(health)
            ok = health.status_code == 200 and body.get("status") == "ok" and body.get("app") == "InfraScan"
            record("API health check", ok, health.status_code, "status, app, and version checked", body)

            bad = client.post("/auth/login", data={"username": "nobody@infrascan.com", "password": "wrong-password"})
            bad_body = _safe_json(bad)
            record(
                "Invalid login",
                bad.status_code == 401 and "access_token" not in bad_body,
                bad.status_code,
                "unknown user rejected",
                bad_body,
            )

            inspector_login = login(client, "inspector@infrascan.com")
            manager_login = login(client, "manager@infrascan.com")
            if not inspector_login or not manager_login:
                write_reports(newman_note)
                return 1
            inspector = inspector_login["access_token"]
            manager = manager_login["access_token"]
            inspector_id = inspector_login["user"]["id"]
            manager_id = manager_login["user"]["id"]
            inspector_headers = {"Authorization": f"Bearer {inspector}"}
            manager_headers = {"Authorization": f"Bearer {manager}"}

            me = client.get("/auth/me", headers=inspector_headers)
            me_body = _safe_json(me)
            record(
                "Authenticated profile GET /auth/me",
                me.status_code == 200
                and me_body.get("email") == "inspector@infrascan.com"
                and me_body.get("role", {}).get("name") == "Infrastructure Inspector"
                and "password_hash" not in me_body,
                me.status_code,
                "inspector profile",
                me_body,
            )

            missing = client.get("/auth/me")
            record("Missing token is rejected", missing.status_code == 401, missing.status_code, "no Authorization header", _safe_json(missing))
            invalid = client.get("/auth/me", headers={"Authorization": "Bearer not-a-valid-token"})
            invalid_body = _safe_json(invalid)
            record(
                "Invalid token is rejected",
                invalid.status_code == 401 and invalid_body.get("detail") == "Could not validate credentials",
                invalid.status_code,
                "bogus bearer token",
                invalid_body,
            )

            assets = client.get("/assets/", params={"page": 1, "size": 10}, headers=inspector_headers)
            assets_body = _safe_json(assets)
            record(
                "Inspector can list assets",
                assets.status_code == 200 and isinstance(assets_body.get("items"), list),
                assets.status_code,
                f"total={assets_body.get('total')}",
                assets_body,
            )

            deny_asset = client.post("/assets/", headers=inspector_headers, json={
                "asset_code": f"PM-DENY-{int(time.time())}",
                "name": "Denied",
                "type": "Road",
            })
            record("Inspector cannot create an asset", deny_asset.status_code == 403, deny_asset.status_code, "manager-only create", _safe_json(deny_asset))
            deny_users_i = client.get("/users/", headers=inspector_headers)
            record("Inspector cannot list users", deny_users_i.status_code == 403, deny_users_i.status_code, "admin-only users", _safe_json(deny_users_i))
            deny_users_m = client.get("/users/", headers=manager_headers)
            record("Manager cannot list users", deny_users_m.status_code == 403, deny_users_m.status_code, "admin-only users", _safe_json(deny_users_m))

            code = f"PM-{int(time.time())}"
            created = client.post("/assets/", headers=manager_headers, json={
                "asset_code": code,
                "name": "Postman Milestone Asset",
                "type": "Bridge",
                "location_text": "API test site",
                "latitude": 12.97,
                "longitude": 77.59,
                "construction_year": 2001,
            })
            created_body = _safe_json(created)
            record(
                "Manager creates an asset",
                created.status_code == 201 and created_body.get("asset_code") == code,
                created.status_code,
                "created Postman Milestone Asset",
                created_body,
            )
            if created.status_code != 201:
                write_reports(newman_note)
                return 1
            asset_id = created_body["id"]

            fetched = client.get(f"/assets/{asset_id}", headers=manager_headers)
            fetched_body = _safe_json(fetched)
            record("Manager retrieves the asset", fetched.status_code == 200 and fetched_body.get("id") == asset_id, fetched.status_code, "GET asset", fetched_body)

            updated = client.put(f"/assets/{asset_id}", headers=manager_headers, json={"location_text": "API test site, updated"})
            updated_body = _safe_json(updated)
            record(
                "Manager updates the asset",
                updated.status_code == 200 and updated_body.get("location_text") == "API test site, updated",
                updated.status_code,
                "location updated",
                updated_body,
            )
            persisted = client.get(f"/assets/{asset_id}", headers=inspector_headers)
            persisted_body = _safe_json(persisted)
            record(
                "Database persistence re-read",
                persisted.status_code == 200 and persisted_body.get("location_text") == "API test site, updated",
                persisted.status_code,
                "inspector read matches the update",
                persisted_body,
            )

            disposable = client.post("/assets/", headers=manager_headers, json={
                "asset_code": f"PM-DEL-{code}",
                "name": "Disposable API Asset",
                "type": "Road",
            })
            disposable_body = _safe_json(disposable)
            record("Manager creates a disposable asset", disposable.status_code == 201, disposable.status_code, "asset to delete", disposable_body)
            if disposable.status_code == 201:
                delete_id = disposable_body["id"]
                deleted = client.delete(f"/assets/{delete_id}", headers=manager_headers)
                record("Manager deletes the disposable asset", deleted.status_code == 204, deleted.status_code, "204 empty body", {"body": "empty" if deleted.status_code == 204 else deleted.text[:200]})
                gone = client.get(f"/assets/{delete_id}", headers=manager_headers)
                record("Deleted asset is gone", gone.status_code == 404, gone.status_code, "GET after delete", _safe_json(gone))

            inspection = client.post("/inspections/", headers=inspector_headers, json={
                "asset_id": asset_id,
                "inspector_id": inspector_id,
                "inspection_date": "2026-11-18",
                "notes": "Milestone 4 API inspection",
                "status": "pending",
            })
            inspection_body = _safe_json(inspection)
            record(
                "Inspector creates an inspection",
                inspection.status_code == 201 and inspection_body.get("status") == "pending",
                inspection.status_code,
                "assigned to inspector",
                inspection_body,
            )
            denied_assign = client.post("/inspections/", headers=inspector_headers, json={
                "asset_id": asset_id,
                "inspector_id": manager_id,
                "inspection_date": "2026-11-18",
                "notes": "Should be rejected",
            })
            record("Inspector cannot assign another user", denied_assign.status_code == 403, denied_assign.status_code, "self-assignment rule", _safe_json(denied_assign))

            if inspection.status_code != 201:
                write_reports(newman_note)
                return 1
            inspection_id = inspection_body["id"]
            got = client.get(f"/inspections/{inspection_id}", headers=inspector_headers)
            got_body = _safe_json(got)
            record("Retrieve the inspection", got.status_code == 200 and got_body.get("id") == inspection_id, got.status_code, "GET inspection", got_body)
            history = client.get("/inspections/", params={"asset_id": asset_id}, headers=inspector_headers)
            history_body = _safe_json(history)
            found = isinstance(history_body, list) and any(row.get("id") == inspection_id for row in history_body)
            record("Inspection history for the asset", history.status_code == 200 and found, history.status_code, "history contains the new inspection", history_body)

            if not SAMPLE.is_file():
                record("Upload an inspection image", False, None, f"sample image missing: {SAMPLE.name}", skipped=True)
                record("Run image analysis", False, None, "skipped because the sample image is missing", skipped=True)
            else:
                upload = client.post(
                    f"/inspections/{inspection_id}/images",
                    headers=inspector_headers,
                    files={"files": (SAMPLE.name, SAMPLE.read_bytes(), "image/jpeg")},
                )
                upload_body = _safe_json(upload)
                uploaded_ok = (
                    upload.status_code == 201
                    and isinstance(upload_body, list)
                    and len(upload_body) > 0
                )
                record("Upload an inspection image", uploaded_ok, upload.status_code, SAMPLE.name, upload_body)
                if not uploaded_ok:
                    write_reports(newman_note)
                    return 1
                image_id = upload_body[0]["id"]
                images = client.get(f"/inspections/{inspection_id}/images", headers=inspector_headers)
                images_body = _safe_json(images)
                listed = isinstance(images_body, list) and any(row.get("id") == image_id for row in images_body)
                record("Image list contains the upload", images.status_code == 200 and listed, images.status_code, "GET images", images_body)

                analyzed = client.post(f"/images/{image_id}/analyze", headers=inspector_headers)
                analyzed_body = _safe_json(analyzed)
                analysis_ok = _analysis_ok(analyzed.status_code, analyzed_body)
                record("Run image analysis", analysis_ok, analyzed.status_code, _analysis_detail(analyzed_body), analyzed_body)
                saved = client.get(f"/images/{image_id}/analysis", headers=inspector_headers)
                saved_body = _safe_json(saved)
                record("Read saved analysis", _analysis_ok(saved.status_code, saved_body), saved.status_code, "persisted analysis row", saved_body)
                analyses = client.get(f"/inspections/{inspection_id}/analyses", headers=inspector_headers)
                analyses_body = _safe_json(analyses)
                record(
                    "Inspection analyses",
                    analyses.status_code == 200 and isinstance(analyses_body, list) and len(analyses_body) > 0,
                    analyses.status_code,
                    "analysis history",
                    analyses_body,
                )

            models = client.get("/models/status", headers=inspector_headers)
            models_body = _safe_json(models)
            record(
                "Model status",
                models.status_code == 200 and "available" in models_body.get("classifier", {}),
                models.status_code,
                "weights availability",
                models_body,
            )
            stats = client.get("/stats", headers=inspector_headers)
            stats_body = _safe_json(stats)
            record(
                "Dashboard stats",
                stats.status_code == 200 and all(isinstance(stats_body.get(key), int) for key in ("assets", "inspections", "images", "analyses")),
                stats.status_code,
                "live counts",
                stats_body,
            )
            blocked = client.delete(f"/assets/{asset_id}", headers=manager_headers)
            record("Protected asset delete is blocked while inspections exist", blocked.status_code == 409, blocked.status_code, "409 conflict", _safe_json(blocked))
    except httpx.HTTPError as exc:
        record("Server connection", False, None, exc.__class__.__name__)
        write_reports(newman_note)
        return 1

    write_reports(newman_note)
    failed = sum(1 for row in CHECKS if not row["passed"] and not row["skipped"])
    return 1 if failed else 0


def _analysis_ok(status: int, body: dict) -> bool:
    if status != 200 or not isinstance(body, dict):
        return False
    allowed = {"completed", "unavailable", "failed"}
    if body.get("classification_status") not in allowed:
        return False
    if body.get("detection_status") not in allowed:
        return False
    if body.get("segmentation_status") not in allowed:
        return False
    if not isinstance(body.get("classification"), dict):
        return False
    if not isinstance(body.get("detection"), dict):
        return False
    if not isinstance(body.get("segmentation"), dict):
        return False
    if not isinstance(body.get("geometry"), dict):
        return False
    if body.get("quality", {}).get("valid") is not True:
        return False
    if body.get("detection_status") == "completed":
        detection = body["detection"]
        if detection.get("reliable") is not False:
            return False
        if detection.get("detections") != []:
            return False
        if "No reliable bounding boxes generated." not in str(detection.get("detail")):
            return False
    if body.get("geometry", {}).get("status") == "completed":
        if body["geometry"].get("measurements", {}).get("unit") != "pixels":
            return False
    return True


def _analysis_detail(body: dict) -> str:
    if not isinstance(body, dict):
        return "non-json analysis response"
    return (
        f"classification={body.get('classification_status')}:{body.get('classification_label')} "
        f"detection={body.get('detection_status')} "
        f"segmentation={body.get('segmentation_status')} "
        f"geometry={body.get('geometry', {}).get('status')}"
    )


if __name__ == "__main__":
    sys.exit(main())
