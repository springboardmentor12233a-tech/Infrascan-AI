#!/usr/bin/env python3
"""
Phase 0 Diagnostic Script: Full Multi-Role Headless Browser Testing
Uses Playwright to log in as each of the 5 roles, visit every accessible screen,
record console errors/warnings, failed network requests (4xx/5xx), blank screens,
text overflow, and inspect Leaflet map state. Saves screenshots to docs/final/diagnosis_screens/.
"""

import json
import os
import sys
import time
from pathlib import Path

# Ensure Playwright browser path is set to D: drive
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = r"D:\ms-playwright"

from playwright.sync_api import sync_playwright

DOCS_DIR = Path(r"D:\Infosys springboards\docs\final")
SCREENSHOTS_DIR = DOCS_DIR / "diagnosis_screens"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://127.0.0.1:5173"
API_URL = "http://127.0.0.1:8000"

ROLES_PAGES = {
    "admin": [
        ("dashboard", "/dashboard"),
        ("map", "/map"),
        ("assets", "/assets"),
        ("inspections", "/inspections"),
        ("maintenance", "/maintenance"),
        ("comparisons", "/comparisons"),
        ("reports", "/reports"),
        ("models", "/models"),
        ("jobs", "/jobs"),
        ("notifications", "/notifications"),
        ("users", "/users"),
        ("audit_logs", "/audit-logs"),
        ("profile", "/profile"),
        ("about", "/about"),
        ("help", "/help"),
    ],
    "manager": [
        ("dashboard", "/dashboard"),
        ("map", "/map"),
        ("assets", "/assets"),
        ("inspections", "/inspections"),
        ("maintenance", "/maintenance"),
        ("comparisons", "/comparisons"),
        ("reports", "/reports"),
        ("notifications", "/notifications"),
        ("profile", "/profile"),
        ("about", "/about"),
        ("help", "/help"),
    ],
    "civil_engineer": [
        ("dashboard", "/dashboard"),
        ("map", "/map"),
        ("assets", "/assets"),
        ("inspections", "/inspections"),
        ("maintenance", "/maintenance"),
        ("comparisons", "/comparisons"),
        ("reports", "/reports"),
        ("notifications", "/notifications"),
        ("profile", "/profile"),
        ("about", "/about"),
        ("help", "/help"),
    ],
    "inspector": [
        ("dashboard", "/dashboard"),
        ("map", "/map"),
        ("assets", "/assets"),
        ("inspections", "/inspections"),
        ("notifications", "/notifications"),
        ("profile", "/profile"),
        ("about", "/about"),
        ("help", "/help"),
    ],
    "maintenance_engineer": [
        ("dashboard", "/dashboard"),
        ("map", "/map"),
        ("assets", "/assets"),
        ("inspections", "/inspections"),
        ("maintenance", "/maintenance"),
        ("notifications", "/notifications"),
        ("profile", "/profile"),
        ("about", "/about"),
        ("help", "/help"),
    ],
}

DEMO_CREDENTIALS = {
    "admin": ("admin@demo.infrascan.local", "DemoPassword2026!"),
    "manager": ("manager@demo.infrascan.local", "DemoPassword2026!"),
    "civil_engineer": ("engineer@demo.infrascan.local", "DemoPassword2026!"),
    "inspector": ("inspector@demo.infrascan.local", "DemoPassword2026!"),
    "maintenance_engineer": ("maintenance@demo.infrascan.local", "DemoPassword2026!"),
}


def run_diagnostics():
    print("=" * 70)
    print(" STARTING PHASE 0 HEADLESS BROWSER DIAGNOSIS")
    print(f" Target Frontend: {BASE_URL}")
    print(f" Target Backend:  {API_URL}")
    print("=" * 70)

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for role, (email, password) in DEMO_CREDENTIALS.items():
            print(f"\n---> Testing Role: {role.upper()} ({email})")
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()

            console_logs = []
            network_failures = []
            tile_requests = 0

            # Attach event listeners
            def on_console(msg):
                if msg.type in ["error", "warning"]:
                    console_logs.append({"type": msg.type, "text": msg.text, "location": msg.location})

            def on_response(response):
                nonlocal tile_requests
                url = response.url
                status = response.status
                if "tile.openstreetmap.org" in url or "tile" in url:
                    tile_requests += 1
                if status >= 400:
                    network_failures.append({"status": status, "url": url, "method": response.request.method})

            page.on("console", on_console)
            page.on("response", on_response)

            # 1. Login
            page.goto(f"{BASE_URL}/login")
            page.wait_for_selector('input[type="email"]', timeout=10000)
            page.fill('input[type="email"]', email)
            page.fill('input[type="password"]', password)
            page.click('button[type="submit"]')

            # Wait for navigation to dashboard
            try:
                page.wait_for_url("**/dashboard", timeout=8000)
                print(f"  [+] Login successful for {role}")
            except Exception as e:
                print(f"  [!] Login redirect failed for {role}: {e}")
                # Save screenshot of failure
                fail_screen = SCREENSHOTS_DIR / f"{role}_login_fail.png"
                page.screenshot(path=str(fail_screen))
                results.append({"role": role, "page": "login", "error": "Login failed", "screenshot": str(fail_screen)})
                context.close()
                continue

            # 2. Iterate pages
            for page_name, path in ROLES_PAGES[role]:
                print(f"    Testing page: {path} ({page_name})...")
                # Clear previous page logs
                console_logs.clear()
                network_failures.clear()
                tile_requests = 0

                full_url = f"{BASE_URL}{path}"
                try:
                    page.goto(full_url, timeout=12000)
                    page.wait_for_load_state("domcontentloaded", timeout=6000)
                    time.sleep(1.5)  # Allow charts/maps to render
                except Exception as e:
                    print(f"      [!] Page load warning on {path}: {e}")

                # Check blank screen
                body_text = page.inner_text("body").strip()
                is_blank = len(body_text) < 10

                # Check horizontal overflow
                has_overflow = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")

                # Leaflet map state check (if on /map)
                map_diag = None
                if page_name == "map":
                    map_diag = page.evaluate("""() => {
                        const mapElem = document.querySelector('#map') || document.querySelector('.leaflet-container');
                        if (!mapElem) return { found: false };
                        const height = mapElem.offsetHeight;
                        const stylesheetLoaded = Array.from(document.styleSheets).some(s => {
                            try { return s.href && s.href.includes('leaflet'); } catch (e) { return false; }
                        }) || !!document.querySelector('link[href*="leaflet"]');
                        const markers = document.querySelectorAll('.leaflet-marker-icon').length;
                        return {
                            found: true,
                            height: height,
                            taller_than_300: height >= 300,
                            stylesheet_loaded: stylesheetLoaded,
                            marker_count: markers
                        };
                    }""")
                    map_diag["tile_requests"] = tile_requests

                # Capture screenshot
                screen_path = SCREENSHOTS_DIR / f"{role}_{page_name}.png"
                page.screenshot(path=str(screen_path), full_page=True)

                res_item = {
                    "role": role,
                    "page_name": page_name,
                    "path": path,
                    "is_blank": is_blank,
                    "has_overflow": has_overflow,
                    "console_errors": [c for c in console_logs if c["type"] == "error"],
                    "console_warnings": [c for c in console_logs if c["type"] == "warning"],
                    "failed_requests": network_failures[:],
                    "map_diagnostics": map_diag,
                    "screenshot": str(screen_path),
                }
                results.append(res_item)

                status_str = "OK"
                if is_blank:
                    status_str = "BLANK"
                elif res_item["console_errors"]:
                    err_texts = [c["text"][:60] for c in res_item["console_errors"]]
                    status_str = f"ERRORS ({len(res_item['console_errors'])}): {err_texts}"
                print(f"      Result: {status_str} | Overflow: {has_overflow} | Failures: {len(network_failures)}")
                if map_diag:
                    print(f"      Map: height={map_diag.get('height')}px, markers={map_diag.get('marker_count')}, tiles={tile_requests}, css={map_diag.get('stylesheet_loaded')}")

            context.close()

        browser.close()

    # Save summary report
    out_json = DOCS_DIR / "diagnosis_report.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Diagnosis report saved to {out_json}")
    return results


if __name__ == "__main__":
    run_diagnostics()
