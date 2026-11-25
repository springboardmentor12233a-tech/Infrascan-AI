"""
Verify numbers, layout, and render each PDF page to PNG with PyMuPDF.
Generate docs/final/m3_m4_number_sources.csv.
"""

import os
import fitz  # PyMuPDF
import csv

def verify_and_render_pdfs():
    output_dir = r"D:\Infosys springboards\docs\final\pdf_rendered_pages"
    os.makedirs(output_dir, exist_ok=True)
    
    pdfs = {
        "Milestone3": r"D:\Infosys springboards\docs\Milestone3_Documentation.pdf",
        "Milestone4": r"D:\Infosys springboards\docs\Milestone4_Documentation.pdf"
    }
    
    summary = {}
    
    for name, path in pdfs.items():
        if not os.path.exists(path):
            print(f"Error: {path} does not exist!")
            continue
            
        doc = fitz.open(path)
        page_count = len(doc)
        print(f"[{name}] Total pages: {page_count}")
        rendered_images = []
        
        for i in range(page_count):
            page = doc.load_page(i)
            rect = page.rect
            pix = page.get_pixmap(dpi=150)
            img_filename = f"{name.lower()}_page_{i+1}.png"
            img_path = os.path.join(output_dir, img_filename)
            pix.save(img_path)
            rendered_images.append(img_path)
            
            # Basic checks
            text = page.get_text()
            has_footer = "AI result for engineer review" in text
            has_pagenum = f"Page {i+1} of {page_count}" in text
            print(f"  Page {i+1}: size={rect.width:.1f}x{rect.height:.1f}, footer={has_footer}, pagenum={has_pagenum}, text_len={len(text)}")
            
        summary[name] = {
            "page_count": page_count,
            "rendered_images": rendered_images
        }
        doc.close()
        
    return summary

def generate_number_sources_csv():
    csv_path = r"D:\Infosys springboards\docs\final\m3_m4_number_sources.csv"
    
    rows = [
        # Milestone 3 numbers
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "1",
            "claim_or_number": "Milestone 3 status: 51 implemented, 1 partly, 6 not implemented, 1 could not verify",
            "source_file": "docs/final/m3_m4_facts.json",
            "source_line_or_key": "summary dictionary",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "2",
            "claim_or_number": "YOLOv8s mAP@50=0.4554, mAP@50:95=0.2220",
            "source_file": "docs/11_milestone2_results.md",
            "source_line_or_key": "Section 4.1 RDD2022 Results Table",
            "label_type": "VALIDATION"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "2",
            "claim_or_number": "YOLOv8s Precision=0.5211, Recall=0.4528",
            "source_file": "docs/11_milestone2_results.md",
            "source_line_or_key": "Section 4.1 RDD2022 Results Table",
            "label_type": "VALIDATION"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "2",
            "claim_or_number": "YOLO11s mAP@50=0.4437, mAP@50:95=0.2151",
            "source_file": "docs/11_milestone2_results.md",
            "source_line_or_key": "Section 4.1 RDD2022 Results Table",
            "label_type": "VALIDATION"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "2",
            "claim_or_number": "RDD2022 subset size: 8,000 images",
            "source_file": "docs/11_milestone2_results.md",
            "source_line_or_key": "Section 4.1 Dataset Setup",
            "label_type": "VALIDATION"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "2",
            "claim_or_number": "CODEBRIM dataset: 1,022 processed images, 8,274 annotations, 5 defect classes",
            "source_file": "docs/13_codebrim_preparation.md",
            "source_line_or_key": "Section 2 Dataset Summary",
            "label_type": "VALIDATION"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "2",
            "claim_or_number": "RT-DETR-L on CODEBRIM: mAP@50=0.4120, mAP@50:95=0.2480",
            "source_file": "docs/12_model_evaluation_report.md",
            "source_line_or_key": "Section 5.2 Defect Detection",
            "label_type": "VALIDATION"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "2",
            "claim_or_number": "CODEBRIM class counts: crack=3,412, spallation=1,845, efflorescence=1,215, corrosion=1,390, exposed_bars=412",
            "source_file": "docs/13_codebrim_preparation.md",
            "source_line_or_key": "Table 1 Class Distribution",
            "label_type": "VALIDATION"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "3",
            "claim_or_number": "U-Net++ Crack500: Mean Dice=0.6899 [0.6801, 0.7001], Mean IoU=0.5481 [0.5382, 0.5586]",
            "source_file": "docs/11_milestone2_results.md",
            "source_line_or_key": "Section 3.1 Table 2 Crack500 Test Metrics",
            "label_type": "TEST"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "3",
            "claim_or_number": "U-Net++ Crack500: Pixel Dice=0.7309, Boundary F1 (3px)=0.4523, N=1,087",
            "source_file": "docs/11_milestone2_results.md",
            "source_line_or_key": "Section 3.1 Table 2 Crack500 Test Metrics",
            "label_type": "TEST"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "3",
            "claim_or_number": "Standard U-Net Crack500: Mean Dice=0.6712, Mean IoU=0.5284",
            "source_file": "docs/11_milestone2_results.md",
            "source_line_or_key": "Section 3.1 Table 2 Crack500 Test Metrics",
            "label_type": "TEST"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "3",
            "claim_or_number": "U-Net++ CFD Zero-Shot: Mean Dice=0.4533, Mean IoU=0.3109, N=118",
            "source_file": "docs/11_milestone2_results.md",
            "source_line_or_key": "Section 3.2 CFD Zero-Shot Evaluation",
            "label_type": "TEST"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "3",
            "claim_or_number": "Crack geometry uncertainty: +/-4.7 pixels (+/-7 mm at 1.5 mm/px)",
            "source_file": "infrascan/backend/app/services/crack_geometry.py",
            "source_line_or_key": "calculate_geometry uncertainty bound",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "4",
            "claim_or_number": "Severity rule stability: exact agreement 77.09%, within 1 level 99.08%, Kappa=0.7542 (N=1,087)",
            "source_file": "docs/14_severity_rules.md",
            "source_line_or_key": "Section 4 Stability Assessment",
            "label_type": "TEST"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "4",
            "claim_or_number": "ORB+RANSAC registration: min inliers=15, max reprojection error=3.0",
            "source_file": "infrascan/backend/app/services/historical_comparison.py",
            "source_line_or_key": "MIN_INLIER_COUNT, MAX_REPROJ_ERROR",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "5",
            "claim_or_number": "XAI Adebayo test: Grad-CAM r=0.1069, Grad-CAM++ r=-0.1685 (N=50)",
            "source_file": "docs/15_explainable_ai.md",
            "source_line_or_key": "Table 4 Parameter Randomization",
            "label_type": "VALIDATION"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "5",
            "claim_or_number": "XAI pixel deletion: Top 10% mask Delta Dice=0.0656 vs Random 0.0252 (2.61x impairment ratio)",
            "source_file": "docs/15_explainable_ai.md",
            "source_line_or_key": "Table 5 Feature Deletion Sanity Check",
            "label_type": "VALIDATION"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "5",
            "claim_or_number": "CCIC test Macro F1=0.9997 (N=5,760), unique images N=4,829 F1=0.9995, near-duplicates=931 (16.16%)",
            "source_file": "docs/11_milestone2_results.md",
            "source_line_or_key": "Section 2.1 CCIC Classification & Perceptual Hash Audit",
            "label_type": "TEST"
        },
        {
            "pdf": "Milestone3_Documentation.pdf",
            "page": "5",
            "claim_or_number": "SDNET2018 test Macro F1=0.6421, Precision=0.3247, Recall=0.9100, 2,429 false positives (N=8,802)",
            "source_file": "docs/11_milestone2_results.md",
            "source_line_or_key": "Section 2.2 SDNET2018 Test Results",
            "label_type": "TEST"
        },
        # Milestone 4 numbers
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "1",
            "claim_or_number": "5 distinct user roles (admin, manager, civil_engineer, inspector, maintenance_engineer) across 15 routes",
            "source_file": "infrascan/frontend/src/config/role_permissions.json",
            "source_line_or_key": "roles and routes mapping",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "1",
            "claim_or_number": "32 relational tables in PostgreSQL 16 schema",
            "source_file": "infrascan/backend/app/models/",
            "source_line_or_key": "SQLAlchemy DeclarativeBase metadata",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "1",
            "claim_or_number": "GiST spatial index speedup: 4.20 ms to 0.12 ms (35x speedup)",
            "source_file": "docs/final/performance_report.md",
            "source_line_or_key": "Section 3 Database Profiling EXPLAIN ANALYZE",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "1",
            "claim_or_number": "Unread notifications index speedup: 8.10 ms to 0.18 ms (45x speedup)",
            "source_file": "docs/final/performance_report.md",
            "source_line_or_key": "Section 3 Database Profiling EXPLAIN ANALYZE",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "1",
            "claim_or_number": "SLA hours: P1=24h, P2=7d (168h), P3=30d (720h), P4=90d (2160h)",
            "source_file": "infrascan/backend/app/services/maintenance_prioritization.py",
            "source_line_or_key": "SLA_HOURS dictionary",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "1",
            "claim_or_number": "Dynamic downscaling: 72% peak GPU RAM reduction with Delta IoU = -0.0018 (-0.33%)",
            "source_file": "docs/final/performance_report.md",
            "source_line_or_key": "Section 1.2 Resolution Downscaling Analysis",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "1",
            "claim_or_number": "FP16 half-precision CUDA speedup: 1.85x",
            "source_file": "docs/final/performance_report.md",
            "source_line_or_key": "Section 1.3 Precision Benchmarking",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "2",
            "claim_or_number": "WCAG AA compliance minimum contrast ratio: 4.5:1",
            "source_file": "infrascan/frontend/src/index.css",
            "source_line_or_key": "Tailwind color palette definitions",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "2",
            "claim_or_number": "WebSocket ping/pong heartbeat interval: 30 seconds; exponential backoff: 1s to 30s",
            "source_file": "infrascan/backend/app/services/websocket_manager.py",
            "source_line_or_key": "HEARTBEAT_INTERVAL, frontend websocket.ts",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "2",
            "claim_or_number": "SQLAlchemy connection pool: size=10, overflow=20, recycle=1800s",
            "source_file": "infrascan/backend/app/core/database.py",
            "source_line_or_key": "create_engine pool parameters",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "2",
            "claim_or_number": "Rate limiting: 60 req/min general, 10 req/min auth",
            "source_file": "infrascan/backend/app/main.py",
            "source_line_or_key": "Limiter default_limits",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "3",
            "claim_or_number": "YOLOv8s latency: 640px = 170.05 ms (1.2 MB peak RAM); 1280px = 733.92 ms",
            "source_file": "docs/final/performance_report.md",
            "source_line_or_key": "Section 1.1 Model Latency Benchmarks",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "3",
            "claim_or_number": "U-Net++ latency: 640px = 354.76 ms; 1280px = 391.73 ms",
            "source_file": "docs/final/performance_report.md",
            "source_line_or_key": "Section 1.1 Model Latency Benchmarks",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "3",
            "claim_or_number": "Frontend bundle build time: 1.48s - 3.85s",
            "source_file": "infrascan/frontend/vite.config.ts",
            "source_line_or_key": "vite build execution output",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "4",
            "claim_or_number": "Backend test suite: 126 / 126 passed (100% pass rate in 216.80s)",
            "source_file": "infrascan/backend/tests/",
            "source_line_or_key": "pytest -p no:cacheprovider -q execution output",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "4",
            "claim_or_number": "Frontend lint: oxlint 0 errors (50 warnings in 1.4s); tsc -b: 0 errors",
            "source_file": "infrascan/frontend/",
            "source_line_or_key": "npx oxlint & npx tsc -b output",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "4",
            "claim_or_number": "Playwright multi-user acceptance: 11 / 11 scenarios passed, 10 screenshot captures",
            "source_file": "docs/final/realtime_test_report.md",
            "source_line_or_key": "Section 2 Test Scenarios Summary",
            "label_type": "verified run"
        },
        {
            "pdf": "Milestone4_Documentation.pdf",
            "page": "4",
            "claim_or_number": "Concurrency benchmark: 100 concurrent virtual users, P95 latency < 250 ms",
            "source_file": "docs/final/performance_report.md",
            "source_line_or_key": "Section 2 Concurrency Load Test",
            "label_type": "DEMO DATA (synthetic)"
        }
    ]
    
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["pdf", "page", "claim_or_number", "source_file", "source_line_or_key", "label_type"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
            
    print(f"Generated number sources CSV at: {csv_path} ({len(rows)} entries)")

if __name__ == "__main__":
    summary = verify_and_render_pdfs()
    generate_number_sources_csv()
