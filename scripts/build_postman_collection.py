"""Write the InfraScan Postman collection. No passwords or tokens are embedded."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "postman" / "InfraScan_API_Tests.postman_collection.json"


def event(listen: str, script: str) -> dict:
    lines = [line for line in script.strip("\n").split("\n")]
    return {"listen": listen, "script": {"type": "text/javascript", "exec": lines}}


def item(
    name: str,
    method: str,
    path: str,
    *,
    auth: str | None = None,
    description: str = "",
    tests: str = "",
    prerequest: str = "",
    raw: str | None = None,
    urlencoded: list[dict] | None = None,
    formdata: list[dict] | None = None,
) -> dict:
    headers = []
    if auth == "inspector":
        headers.append({"key": "Authorization", "value": "Bearer {{inspector_token}}"})
    elif auth == "manager":
        headers.append({"key": "Authorization", "value": "Bearer {{manager_token}}"})
    elif auth == "invalid":
        headers.append({"key": "Authorization", "value": "Bearer not-a-valid-token"})
    body = None
    if raw is not None:
        headers.append({"key": "Content-Type", "value": "application/json"})
        body = {"mode": "raw", "raw": raw, "options": {"raw": {"language": "json"}}}
    elif urlencoded is not None:
        body = {"mode": "urlencoded", "urlencoded": urlencoded}
    elif formdata is not None:
        body = {"mode": "formdata", "formdata": formdata}
    request = {
        "method": method,
        "header": headers,
        "url": "{{base_url}}" + path,
        "description": description,
    }
    if body is not None:
        request["body"] = body
    events = []
    if prerequest:
        events.append(event("prerequest", prerequest))
    if tests:
        events.append(event("test", tests))
    return {"name": name, "request": request, "event": events}


LOGIN_INSPECTOR = """
pm.test("inspector login returns 200", function () {
  pm.response.to.have.status(200);
});
const body = pm.response.json();
pm.test("JWT access token is present and not logged", function () {
  pm.expect(body.token_type).to.eql("bearer");
  pm.expect(body.access_token).to.be.a("string").and.not.empty;
  pm.expect(body.user.role.name).to.eql("Infrastructure Inspector");
  pm.expect(body.user).to.not.have.property("password");
  pm.expect(body.user).to.not.have.property("password_hash");
});
function saveVar(key, value) {
  pm.collectionVariables.set(key, value);
  try { pm.environment.set(key, value); } catch (error) {}
}
saveVar("inspector_token", body.access_token);
saveVar("access_token", body.access_token);
saveVar("inspector_user_id", String(body.user.id));
"""

LOGIN_MANAGER = """
pm.test("manager login returns 200", function () {
  pm.response.to.have.status(200);
});
const body = pm.response.json();
pm.test("manager JWT contains the manager role", function () {
  pm.expect(body.token_type).to.eql("bearer");
  pm.expect(body.access_token).to.be.a("string").and.not.empty;
  pm.expect(body.user.role.name).to.eql("Infrastructure Manager");
});
function saveVar(key, value) {
  pm.collectionVariables.set(key, value);
  try { pm.environment.set(key, value); } catch (error) {}
}
saveVar("manager_token", body.access_token);
saveVar("manager_user_id", String(body.user.id));
"""

SAVE_ASSET = """
pm.test("asset created", function () {
  pm.response.to.have.status(201);
});
const body = pm.response.json();
pm.test("asset payload has id and code", function () {
  pm.expect(body.id).to.be.a("number");
  pm.expect(body.asset_code).to.eql(pm.collectionVariables.get("asset_code"));
  pm.expect(body.name).to.eql("Postman Milestone Asset");
  pm.expect(body).to.not.have.property("password");
});
function saveVar(key, value) {
  pm.collectionVariables.set(key, value);
  try { pm.environment.set(key, value); } catch (error) {}
}
saveVar("asset_id", String(body.id));
"""

SAVE_INSPECTION = """
pm.test("inspection created", function () {
  pm.response.to.have.status(201);
});
const body = pm.response.json();
pm.test("inspection is pending and assigned to the inspector", function () {
  pm.expect(body.id).to.be.a("number");
  pm.expect(body.status).to.eql("pending");
  pm.expect(String(body.inspector_id)).to.eql(String(pm.collectionVariables.get("inspector_user_id")));
  pm.expect(body.notes).to.eql("Milestone 4 API inspection");
});
function saveVar(key, value) {
  pm.collectionVariables.set(key, value);
  try { pm.environment.set(key, value); } catch (error) {}
}
saveVar("inspection_id", String(body.id));
"""

SAVE_IMAGE = """
pm.test("image upload returns 201", function () {
  pm.response.to.have.status(201);
});
const body = pm.response.json();
pm.test("uploaded image has an id and file metadata", function () {
  pm.expect(body).to.be.an("array").that.is.not.empty;
  pm.expect(body[0].id).to.be.a("number");
  pm.expect(body[0].width).to.be.above(0);
  pm.expect(body[0].height).to.be.above(0);
  pm.expect(body[0].original_filename).to.be.a("string");
});
function saveVar(key, value) {
  pm.collectionVariables.set(key, value);
  try { pm.environment.set(key, value); } catch (error) {}
}
saveVar("image_id", String(body[0].id));
"""

ANALYSIS = """
pm.test("analysis returns 200", function () {
  pm.response.to.have.status(200);
});
const body = pm.response.json();
pm.test("classification, detection, segmentation, and geometry are present", function () {
  pm.expect(["completed", "unavailable", "failed"]).to.include(body.classification_status);
  pm.expect(["completed", "unavailable", "failed"]).to.include(body.detection_status);
  pm.expect(["completed", "unavailable", "failed"]).to.include(body.segmentation_status);
  pm.expect(body.classification).to.be.an("object");
  pm.expect(body.detection).to.be.an("object");
  pm.expect(body.segmentation).to.be.an("object");
  pm.expect(body.geometry).to.be.an("object");
  pm.expect(body.quality.valid).to.eql(true);
});
pm.test("unreliable detection does not invent boxes", function () {
  if (body.detection_status === "completed") {
    pm.expect(body.detection.reliable).to.eql(false);
    pm.expect(body.detection.detections).to.eql([]);
    pm.expect(body.detection.detail).to.include("No reliable bounding boxes generated.");
  }
});
pm.test("geometry stays in pixels when a mask exists", function () {
  if (body.geometry.status === "completed") {
    pm.expect(body.geometry.measurements.unit).to.eql("pixels");
  }
});
"""


def status_test(code: int, extra: str = "") -> str:
    return f"""
pm.test("status is {code}", function () {{
  pm.response.to.have.status({code});
}});
{extra}
"""


def main() -> None:
    login_fields = lambda email: [
        {"key": "username", "value": email, "type": "text"},
        {"key": "password", "value": "{{demo_password}}", "type": "text"},
    ]
    collection = {
        "info": {
            "name": "InfraScan API Tests",
            "description": (
                "Milestone 4 API checks for the running InfraScan FastAPI app. "
                "Set demo_password and sample_image in the environment before running. "
                "Do not commit real passwords or access tokens. "
                "Bearer tokens are used because the API authenticates with OAuth2PasswordBearer. "
                "Expired-token signing is covered by backend/tests/test_milestone3.py, "
                "because a Postman request cannot sign a token without the server secret. "
                "Detection may return status completed with reliable=false and an empty detections list. "
                "That is the honest YOLO result and is a passing assertion."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [
            {"key": "base_url", "value": "http://127.0.0.1:8000"},
            {"key": "inspector_email", "value": "inspector@infrascan.com"},
            {"key": "manager_email", "value": "manager@infrascan.com"},
            {"key": "demo_password", "value": ""},
            {"key": "sample_image", "value": ""},
            {"key": "access_token", "value": ""},
            {"key": "inspector_token", "value": ""},
            {"key": "manager_token", "value": ""},
            {"key": "inspector_user_id", "value": ""},
            {"key": "manager_user_id", "value": ""},
            {"key": "asset_code", "value": ""},
            {"key": "asset_id", "value": ""},
            {"key": "delete_asset_id", "value": ""},
            {"key": "inspection_id", "value": ""},
            {"key": "image_id", "value": ""},
            {"key": "existing_asset_id", "value": ""},
        ],
        "item": [
            {
                "name": "Health",
                "item": [
                    item(
                        "API health check",
                        "GET",
                        "/health",
                        description="Public liveness check.",
                        tests=status_test(200, """
const body = pm.response.json();
pm.test("health payload", function () {
  pm.expect(body.status).to.eql("ok");
  pm.expect(body.app).to.eql("InfraScan");
  pm.expect(body.version).to.be.a("string");
});
"""),
                    )
                ],
            },
            {
                "name": "Authentication",
                "item": [
                    item(
                        "Inspector login and JWT",
                        "POST",
                        "/auth/login",
                        description="OAuth2 password form. Saves the inspector token into collection variables.",
                        urlencoded=login_fields("{{inspector_email}}"),
                        tests=LOGIN_INSPECTOR,
                    ),
                    item(
                        "Invalid login",
                        "POST",
                        "/auth/login",
                        description="Unknown account. Uses a fake password, not a real one.",
                        urlencoded=[
                            {"key": "username", "value": "nobody@infrascan.com", "type": "text"},
                            {"key": "password", "value": "wrong-password", "type": "text"},
                        ],
                        tests=status_test(401, """
pm.test("login error is a message, not a token", function () {
  pm.expect(pm.response.json().detail).to.be.a("string");
  pm.expect(pm.response.json()).to.not.have.property("access_token");
});
"""),
                    ),
                    item(
                        "Manager login and JWT",
                        "POST",
                        "/auth/login",
                        urlencoded=login_fields("{{manager_email}}"),
                        tests=LOGIN_MANAGER,
                    ),
                    item(
                        "Authenticated profile",
                        "GET",
                        "/auth/me",
                        auth="inspector",
                        tests=status_test(200, """
const body = pm.response.json();
pm.test("profile matches the inspector", function () {
  pm.expect(body.email).to.eql(pm.collectionVariables.get("inspector_email") || pm.environment.get("inspector_email"));
  pm.expect(body.role.name).to.eql("Infrastructure Inspector");
  pm.expect(body.is_active).to.eql(true);
  pm.expect(body).to.not.have.property("password_hash");
});
"""),
                    ),
                    item(
                        "Missing token is rejected",
                        "GET",
                        "/auth/me",
                        description="No Authorization header.",
                        tests=status_test(401),
                    ),
                    item(
                        "Invalid token is rejected",
                        "GET",
                        "/auth/me",
                        auth="invalid",
                        tests=status_test(401, """
pm.test("invalid token detail", function () {
  pm.expect(pm.response.json().detail).to.eql("Could not validate credentials");
});
"""),
                    ),
                ],
            },
            {
                "name": "Authorization",
                "item": [
                    item(
                        "Inspector can list assets",
                        "GET",
                        "/assets/?page=1&size=10",
                        auth="inspector",
                        tests=status_test(200, """
const body = pm.response.json();
pm.test("asset list shape", function () {
  pm.expect(body.total).to.be.a("number");
  pm.expect(body.items).to.be.an("array");
});
const existing = body.items.find((row) => row.asset_code === "BRG-001");
if (existing) {
  pm.collectionVariables.set("existing_asset_id", String(existing.id));
  try { pm.environment.set("existing_asset_id", String(existing.id)); } catch (error) {}
}
"""),
                    ),
                    item(
                        "Inspector cannot create an asset",
                        "POST",
                        "/assets/",
                        auth="inspector",
                        raw='{"asset_code":"PM-DENY","name":"Denied","type":"Road"}',
                        tests=status_test(403),
                    ),
                    item(
                        "Inspector cannot list users",
                        "GET",
                        "/users/",
                        auth="inspector",
                        tests=status_test(403),
                    ),
                    item(
                        "Manager cannot list users",
                        "GET",
                        "/users/",
                        auth="manager",
                        tests=status_test(403),
                    ),
                ],
            },
            {
                "name": "Assets",
                "item": [
                    item(
                        "Manager creates an asset",
                        "POST",
                        "/assets/",
                        auth="manager",
                        prerequest="""
const code = "PM-" + Date.now();
pm.collectionVariables.set("asset_code", code);
try { pm.environment.set("asset_code", code); } catch (error) {}
""",
                        raw=json.dumps({
                            "asset_code": "{{asset_code}}",
                            "name": "Postman Milestone Asset",
                            "type": "Bridge",
                            "location_text": "API test site",
                            "latitude": 12.97,
                            "longitude": 77.59,
                            "construction_year": 2001,
                        }),
                        tests=SAVE_ASSET,
                    ),
                    item(
                        "Manager retrieves the asset",
                        "GET",
                        "/assets/{{asset_id}}",
                        auth="manager",
                        tests=status_test(200, """
pm.test("retrieved asset matches", function () {
  pm.expect(pm.response.json().asset_code).to.eql(pm.collectionVariables.get("asset_code"));
});
"""),
                    ),
                    item(
                        "Manager updates the asset",
                        "PUT",
                        "/assets/{{asset_id}}",
                        auth="manager",
                        raw='{"location_text":"API test site, updated"}',
                        tests=status_test(200, """
pm.test("location updated", function () {
  pm.expect(pm.response.json().location_text).to.eql("API test site, updated");
});
"""),
                    ),
                    item(
                        "Persistence re-read",
                        "GET",
                        "/assets/{{asset_id}}",
                        auth="inspector",
                        description="A later read still returns the updated location.",
                        tests=status_test(200, """
pm.test("updated location persisted", function () {
  pm.expect(pm.response.json().location_text).to.eql("API test site, updated");
});
"""),
                    ),
                    item(
                        "Manager creates a disposable asset",
                        "POST",
                        "/assets/",
                        auth="manager",
                        raw='{"asset_code":"PM-DEL-{{asset_code}}","name":"Disposable API Asset","type":"Road"}',
                        tests=status_test(201, """
pm.collectionVariables.set("delete_asset_id", String(pm.response.json().id));
try { pm.environment.set("delete_asset_id", String(pm.response.json().id)); } catch (error) {}
"""),
                    ),
                    item(
                        "Manager deletes the disposable asset",
                        "DELETE",
                        "/assets/{{delete_asset_id}}",
                        auth="manager",
                        tests=status_test(204),
                    ),
                    item(
                        "Deleted asset is gone",
                        "GET",
                        "/assets/{{delete_asset_id}}",
                        auth="manager",
                        tests=status_test(404),
                    ),
                ],
            },
            {
                "name": "Inspections and analysis",
                "item": [
                    item(
                        "Inspector creates an inspection",
                        "POST",
                        "/inspections/",
                        auth="inspector",
                        description="Uses the asset created above. The inspector must assign it to themselves.",
                        raw="""{
  "asset_id": {{asset_id}},
  "inspector_id": {{inspector_user_id}},
  "inspection_date": "2026-11-18",
  "notes": "Milestone 4 API inspection",
  "status": "pending"
}""",
                        tests=SAVE_INSPECTION,
                    ),
                    item(
                        "Inspector cannot assign another user",
                        "POST",
                        "/inspections/",
                        auth="inspector",
                        raw="""{
  "asset_id": {{asset_id}},
  "inspector_id": {{manager_user_id}},
  "inspection_date": "2026-11-18",
  "notes": "Should be rejected"
}""",
                        tests=status_test(403),
                    ),
                    item(
                        "Retrieve the inspection",
                        "GET",
                        "/inspections/{{inspection_id}}",
                        auth="inspector",
                        tests=status_test(200, """
pm.test("inspection id matches", function () {
  pm.expect(String(pm.response.json().id)).to.eql(String(pm.collectionVariables.get("inspection_id")));
});
"""),
                    ),
                    item(
                        "Inspection history for the asset",
                        "GET",
                        "/inspections/?asset_id={{asset_id}}",
                        auth="inspector",
                        tests=status_test(200, """
pm.test("history includes the new inspection", function () {
  const rows = pm.response.json();
  pm.expect(rows).to.be.an("array");
  const found = rows.some((row) => String(row.id) === String(pm.collectionVariables.get("inspection_id")));
  pm.expect(found).to.eql(true);
});
"""),
                    ),
                    item(
                        "Upload an inspection image",
                        "POST",
                        "/inspections/{{inspection_id}}/images",
                        auth="inspector",
                        description="Set sample_image to an absolute path of a local JPEG before running.",
                        formdata=[{"key": "files", "type": "file", "src": "{{sample_image}}"}],
                        tests=SAVE_IMAGE,
                    ),
                    item(
                        "List inspection images",
                        "GET",
                        "/inspections/{{inspection_id}}/images",
                        auth="inspector",
                        tests=status_test(200, """
pm.test("image list contains the upload", function () {
  const rows = pm.response.json();
  pm.expect(rows.some((row) => String(row.id) === String(pm.collectionVariables.get("image_id")))).to.eql(true);
});
"""),
                    ),
                    item(
                        "Run image analysis",
                        "POST",
                        "/images/{{image_id}}/analyze",
                        auth="inspector",
                        description="Validates honest model status. Does not require YOLO boxes.",
                        tests=ANALYSIS,
                    ),
                    item(
                        "Read saved analysis",
                        "GET",
                        "/images/{{image_id}}/analysis",
                        auth="inspector",
                        tests=ANALYSIS,
                    ),
                    item(
                        "Inspection analyses",
                        "GET",
                        "/inspections/{{inspection_id}}/analyses",
                        auth="inspector",
                        tests=status_test(200, """
pm.test("analysis history is an array", function () {
  pm.expect(pm.response.json()).to.be.an("array").that.is.not.empty;
});
"""),
                    ),
                    item(
                        "Model status",
                        "GET",
                        "/models/status",
                        auth="inspector",
                        tests=status_test(200, """
pm.test("model status names availability", function () {
  const body = pm.response.json();
  pm.expect(body.classifier).to.have.property("available");
  pm.expect(body.detection).to.have.property("available");
  pm.expect(body.segmentation).to.have.property("available");
});
"""),
                    ),
                    item(
                        "Dashboard stats",
                        "GET",
                        "/stats",
                        auth="inspector",
                        tests=status_test(200, """
pm.test("stats are numeric", function () {
  const body = pm.response.json();
  pm.expect(body.assets).to.be.a("number");
  pm.expect(body.inspections).to.be.a("number");
  pm.expect(body.images).to.be.a("number");
  pm.expect(body.analyses).to.be.a("number");
});
"""),
                    ),
                    item(
                        "Protected asset delete is blocked while inspections exist",
                        "DELETE",
                        "/assets/{{asset_id}}",
                        auth="manager",
                        tests=status_test(409),
                    ),
                ],
            },
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(collection, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
