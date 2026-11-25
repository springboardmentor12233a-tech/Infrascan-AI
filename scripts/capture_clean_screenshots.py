import time
import os
from pathlib import Path

# Set Playwright browser path to D: drive
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = r"D:\ms-playwright"

from playwright.sync_api import sync_playwright

def capture_screenshots():
    out_dir = r"D:\Infosys springboards\docs\final\screenshots"
    os.makedirs(out_dir, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        
        # 1. Login
        print("Navigating to login...")
        page.goto("http://127.0.0.1:5173/login")
        page.wait_for_selector("input[type='email']", timeout=10000)
        page.fill("input[type='email']", "admin@infrascan.com")
        page.fill("input[type='password']", "Admin123!")
        page.click("button[type='submit']")
        
        # 2. Wait for dashboard
        page.wait_for_url("**/dashboard", timeout=10000)
        time.sleep(2.0)  # Wait for charts/metrics to fetch
        
        dash_path = os.path.join(out_dir, "01_dashboard.png")
        page.screenshot(path=dash_path)
        print(f"Captured dashboard: {dash_path} ({os.path.getsize(dash_path)} bytes)")
        
        # 3. Map
        page.goto("http://127.0.0.1:5173/map")
        time.sleep(2.5)  # Wait for leaflet map and markers
        map_path = os.path.join(out_dir, "02_map.png")
        page.screenshot(path=map_path)
        print(f"Captured map: {map_path} ({os.path.getsize(map_path)} bytes)")
        
        # 4. Inspections
        page.goto("http://127.0.0.1:5173/inspections")
        time.sleep(2.0)
        insp_path = os.path.join(out_dir, "05_inspections.png")
        page.screenshot(path=insp_path)
        print(f"Captured inspections: {insp_path} ({os.path.getsize(insp_path)} bytes)")
        
        browser.close()
        print("Done capturing clean screenshots.")

if __name__ == "__main__":
    capture_screenshots()
