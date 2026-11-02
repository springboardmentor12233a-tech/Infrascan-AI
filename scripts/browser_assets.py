"""Open the manager asset form and the saved inspection history.

Requires the API on port 8000, Vite on port 5173, and the system Playwright
Chromium used by scripts/browser_demo.py. Does not delete the created asset.
"""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "demo_screenshots"
CHROME = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright" / "chromium-1234" / "chrome-win64" / "chrome.exe"
BASE = "http://127.0.0.1:5173"
CODE = "DEMO-RW-04"
NAME = "Faculty Demo Retaining Wall"
LOCATION = "Campus demonstration site, north wall"


def sign_in(page, email: str) -> None:
    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.get_by_placeholder("name@organization.com").fill(email)
    page.locator("input[type='password']").fill("Password123!")
    page.get_by_role("button", name="Sign In").click()
    page.wait_for_url("**/dashboard")


def main() -> None:
    if not CHROME.is_file():
        raise SystemExit(f"Chromium not found: {CHROME}")
    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(CHROME), headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        sign_in(page, "manager@infrascan.com")
        page.get_by_role("link", name="View All Assets").click()
        page.wait_for_url("**/assets")
        page.get_by_role("link", name="Register New Asset").click()
        page.wait_for_url("**/assets/new")
        page.locator("input[name='asset_code']").fill(CODE)
        page.locator("input[name='name']").fill(NAME)
        page.locator("select[name='type']").select_option("Retaining Wall")
        page.locator("input[name='construction_year']").fill("1998")
        page.locator("input[name='location_text']").fill("Campus demonstration site")
        page.get_by_role("button", name="Save Asset").click()
        page.wait_for_url("**/assets")
        page.get_by_text(CODE).wait_for()
        page.screenshot(path=str(OUT / "08_asset_created.png"), full_page=True)

        page.locator("tr", has_text=CODE).locator("a[href$='/edit']").click()
        page.wait_for_url("**/edit")
        page.locator("input[name='name']").wait_for()
        page.locator("input[name='location_text']").fill(LOCATION)
        page.get_by_role("button", name="Save Asset").click()
        page.wait_for_url("**/assets")
        page.get_by_text(LOCATION).wait_for()
        page.screenshot(path=str(OUT / "09_asset_edited.png"), full_page=True)

        page.get_by_role("button", name="Sign Out").click()
        page.wait_for_url("**/login")
        sign_in(page, "inspector@infrascan.com")
        page.goto(f"{BASE}/assets", wait_until="networkidle")
        page.locator("tr", has_text="BRG-001").get_by_role("link", name="Inspect").click()
        page.get_by_text("Browser demonstration inspection").wait_for()
        page.screenshot(path=str(OUT / "10_inspection_history.png"), full_page=True)
        page.locator("div", has_text="Browser demonstration inspection").get_by_role(
            "link", name="Inspect Images & Upload"
        ).click()
        page.wait_for_url("**/inspections/**")
        page.get_by_text("11120.jpg").wait_for(timeout=30000)
        page.screenshot(path=str(OUT / "11_saved_inspection.png"), full_page=True)
        browser.close()
    print(f"Screenshots written to {OUT}")


if __name__ == "__main__":
    main()
