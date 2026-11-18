"""Capture Milestone 3 UI screenshots and Milestone 4 report screenshots.

Requires the API on port 8000, Vite on port 5173, the API report HTML, and
Playwright Chromium. The demo password is read from INFRASCAN_DEMO_PASSWORD
and is not written into the page or the saved images.

This does not open the Postman desktop application.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "evidence" / "milestone_3"
API = ROOT / "evidence" / "milestone_4"
SAMPLE = ROOT / "docs" / "eda_outputs" / "samples" / "deepcrack" / "11120.jpg"
REPORT = API / "api_report.html"
BASE = "http://127.0.0.1:5173"
PASSWORD = os.environ.get("INFRASCAN_DEMO_PASSWORD", "")


def find_chrome() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
    matches = sorted(root.glob("chromium-*/chrome-win64/chrome.exe"))
    if not matches:
        raise SystemExit(f"Chromium not found under {root}")
    return matches[-1]


def sign_in(page, email: str) -> None:
    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.get_by_placeholder("name@organization.com").fill(email)
    page.locator("input[type='password']").fill(PASSWORD)
    page.get_by_role("button", name="Sign In").click()
    page.wait_for_url("**/dashboard")
    page.get_by_test_id("jwt-session").wait_for()


def shot(page, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path), full_page=True)
    print(f"Wrote {path}")


def capture_ui(page) -> None:
    if not SAMPLE.is_file():
        raise SystemExit(f"Sample image missing: {SAMPLE}")
    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.get_by_text("Password123").wait_for(state="hidden", timeout=2000)
    shot(page, UI / "01_login.png")

    sign_in(page, "inspector@infrascan.com")
    page.get_by_text("Inspector workspace").first.wait_for()
    page.get_by_test_id("jwt-session").get_by_text("bearer access token", exact=False).wait_for()
    shot(page, UI / "02_inspector_dashboard.png")

    page.get_by_role("link", name="Infrastructure Assets").click()
    page.wait_for_url("**/assets")
    page.get_by_text("BRG-001").wait_for()
    page.get_by_role("link", name="Register New Asset").wait_for(state="hidden")
    shot(page, UI / "03_inspector_assets.png")

    page.goto(f"{BASE}/assets/new", wait_until="networkidle")
    page.get_by_text("Access Denied").wait_for()
    shot(page, UI / "04_inspector_access_denied.png")

    page.goto(f"{BASE}/assets", wait_until="networkidle")
    page.locator("tr", has_text="BRG-001").get_by_role("link", name="Inspect").click()
    page.get_by_role("button", name="Schedule New Inspection").wait_for()
    shot(page, UI / "05_asset_inspections.png")

    page.get_by_role("button", name="Schedule New Inspection").click()
    page.get_by_placeholder("Focus areas:").fill("Milestone 3 evidence inspection")
    page.get_by_role("button", name="Create Inspection").click()
    page.get_by_text("Milestone 3 evidence inspection").wait_for()
    shot(page, UI / "06_inspection_created.png")

    page.locator("div.card", has_text="Milestone 3 evidence inspection").get_by_role(
        "link", name="Inspect Images & Upload"
    ).click()
    page.wait_for_url("**/inspections/**")
    page.locator("#file-upload").set_input_files(str(SAMPLE))
    page.get_by_text("Successfully uploaded").wait_for(timeout=30000)
    shot(page, UI / "07_image_upload.png")

    page.get_by_role("button", name="Run AI analysis").click()
    page.get_by_text("No reliable bounding boxes generated.").wait_for(timeout=180000)
    page.get_by_text("Label:").wait_for()
    page.get_by_text("Coverage:").wait_for()
    shot(page, UI / "08_analysis_results.png")

    page.goto(f"{BASE}/assets", wait_until="networkidle")
    page.locator("tr", has_text="BRG-001").get_by_role("link", name="Inspect").click()
    page.get_by_text("Milestone 3 evidence inspection").wait_for()
    shot(page, UI / "09_inspection_history.png")

    page.get_by_role("button", name="Sign Out").click()
    page.wait_for_url("**/login")
    page.goto(f"{BASE}/dashboard", wait_until="networkidle")
    page.wait_for_url("**/login")
    shot(page, UI / "10_logged_out.png")

    sign_in(page, "manager@infrascan.com")
    page.get_by_text("Manager workspace").first.wait_for()
    page.get_by_role("link", name="Register Asset").wait_for()
    shot(page, UI / "11_manager_dashboard.png")

    page.get_by_role("link", name="Register Asset").click()
    page.wait_for_url("**/assets/new")
    page.get_by_role("button", name="Save Asset").wait_for()
    shot(page, UI / "12_manager_asset_form.png")


def capture_report(page) -> None:
    if not REPORT.is_file():
        raise SystemExit(f"API report missing: {REPORT}")
    page.goto(REPORT.as_uri(), wait_until="networkidle")
    page.get_by_text("not a Postman desktop screenshot").wait_for()
    sections = {
        "01_collection_contents.png": "#collection",
        "02_health.png": "#health",
        "03_login_jwt_masked.png": "#login",
        "04_protected_endpoint.png": "#protected",
        "05_invalid_token.png": "#invalid",
        "06_role_authorization.png": "#authorization",
        "07_asset_api.png": "#assets",
        "08_inspection_api.png": "#inspections",
        "09_image_upload.png": "#upload",
        "10_image_analysis.png": "#analysis",
        "11_summary.png": "#summary",
    }
    for filename, selector in sections.items():
        target = API / filename
        page.locator(selector).screenshot(path=str(target))
        print(f"Wrote {target}")


def main() -> int:
    if not PASSWORD:
        print("INFRASCAN_DEMO_PASSWORD is not set.", file=sys.stderr)
        return 2
    chrome = find_chrome()
    UI.mkdir(parents=True, exist_ok=True)
    API.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(chrome), headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        capture_ui(page)
        capture_report(page)
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
