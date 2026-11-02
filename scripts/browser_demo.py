"""Drive the live InfraScan UI and save screenshots.

Requires the API on port 8000, Vite on port 5173, and Playwright with Chromium.
This machine uses the system Python Playwright install and the cached browser:

    python scripts/browser_demo.py
"""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "demo_screenshots"
SAMPLE = ROOT / "docs" / "eda_outputs" / "samples" / "deepcrack" / "11120.jpg"
CHROME = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright" / "chromium-1234" / "chrome-win64" / "chrome.exe"
BASE = "http://127.0.0.1:5173"


def main() -> None:
    if not SAMPLE.is_file():
        raise SystemExit(f"Sample image missing: {SAMPLE}")
    if not CHROME.is_file():
        raise SystemExit(f"Chromium not found: {CHROME}")
    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(CHROME), headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{BASE}/login", wait_until="networkidle")
        page.screenshot(path=str(OUT / "01_login.png"), full_page=True)

        page.get_by_placeholder("name@organization.com").fill("inspector@infrascan.com")
        page.locator("input[type='password']").fill("Password123!")
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_url("**/dashboard")
        page.get_by_text("Milestone 2 model status").wait_for()
        page.screenshot(path=str(OUT / "02_dashboard.png"), full_page=True)

        page.get_by_role("link", name="View All Assets").click()
        page.wait_for_url("**/assets")
        page.get_by_text("BRG-001").wait_for()
        page.screenshot(path=str(OUT / "03_assets.png"), full_page=True)

        page.locator("tr", has_text="BRG-001").get_by_role("link", name="Inspect").click()
        page.get_by_role("button", name="Schedule New Inspection").wait_for()
        page.screenshot(path=str(OUT / "04_asset_history.png"), full_page=True)

        page.get_by_role("button", name="Schedule New Inspection").click()
        page.get_by_placeholder("Focus areas:").fill("Browser demonstration inspection")
        page.get_by_role("button", name="Create Inspection").click()
        page.get_by_text("Browser demonstration inspection").wait_for()
        page.screenshot(path=str(OUT / "05_inspection_created.png"), full_page=True)

        page.get_by_role("link", name="Inspect Images & Upload").first.click()
        page.wait_for_url("**/inspections/**")
        page.locator("#file-upload").set_input_files(str(SAMPLE))
        page.get_by_text("Successfully uploaded").wait_for(timeout=30000)
        page.screenshot(path=str(OUT / "06_uploaded.png"), full_page=True)

        page.get_by_role("button", name="Run AI analysis").click()
        page.get_by_text("No reliable bounding boxes generated.").wait_for(timeout=120000)
        page.get_by_text("Label:").wait_for()
        page.get_by_text("Coverage:").wait_for()
        page.screenshot(path=str(OUT / "07_analysis.png"), full_page=True)
        browser.close()
    print(f"Screenshots written to {OUT}")


if __name__ == "__main__":
    main()
