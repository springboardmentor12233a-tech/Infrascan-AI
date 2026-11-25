"""
Safely sync Milestone 3 and Milestone 4 files to infrascan-ai-mentor repo.
Strictly excludes .env, credentials, venv, node_modules, caches, and datasets.
"""

import os
import shutil
from pathlib import Path

SRC_INFRASCAN = Path(r"D:\Infosys springboards\infrascan")
SRC_DOCS = Path(r"D:\Infosys springboards\docs")
DEST_REPO = Path(r"D:\Infosys springboards\infrascan-ai-mentor")

EXCLUDE_PATTERNS = [
    ".env",
    "venv",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".coverage",
    "demo_accounts.local.txt",
    "storage",
    "uploads",
    "data/raw",
    "data/processed",
    ".git"
]

def is_excluded(rel_path_str):
    p = rel_path_str.replace("\\", "/").lower()
    for ex in EXCLUDE_PATTERNS:
        if ex in p.split("/"):
            return True
        if p.endswith(ex):
            return True
    if p.endswith(".local.txt") or p.endswith(".env"):
        return True
    return False

def copy_file_safe(src_file, dest_file):
    if is_excluded(str(src_file)):
        print(f"  [SKIPPED EXCLUDED] {src_file}")
        return False
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_file, dest_file)
    return True

def sync_milestone_3():
    print("=== Copying Milestone 3 Files ===")
    count = 0
    # 1. M3 AI & Geometry Services, Routers, Config, Tests
    m3_backend_files = [
        "app/ai/geometry.py",
        "app/ai/explain.py",
        "app/services/severity_service.py",
        "app/services/explain_service.py",
        "app/routers/severity.py",
        "app/routers/explanations.py",
        "app/routers/comparisons.py",
        "app/config/severity_rules.json",
        "tests/test_scale_and_remeasure.py",
        "tests/test_explain.py",
        "tests/test_severity.py",
    ]
    for rel in m3_backend_files:
        src = SRC_INFRASCAN / "backend" / rel
        dst = DEST_REPO / "backend" / rel
        if src.exists():
            if copy_file_safe(src, dst):
                count += 1
                
    # 2. M3 Docs & Reports
    m3_docs_files = [
        "13_codebrim_preparation.md",
        "14_severity_rules.md",
        "15_explainable_ai.md",
        "Milestone3_Documentation.pdf",
        "final/m3_m4_facts.md",
        "final/m3_m4_facts.json",
        "final/m3_m4_number_sources.csv",
    ]
    for rel in m3_docs_files:
        src = SRC_DOCS / rel
        dst = DEST_REPO / "docs" / rel
        if src.exists():
            if copy_file_safe(src, dst):
                count += 1
                
    print(f"Milestone 3 files copied: {count}")
    return count

def sync_milestone_4():
    print("=== Copying Milestone 4 Files ===")
    count = 0
    
    # 1. M4 Backend Full Architecture
    for root, dirs, files in os.walk(SRC_INFRASCAN / "backend"):
        dirs[:] = [d for d in dirs if not is_excluded(d)]
        for f in files:
            src_f = Path(root) / f
            rel = src_f.relative_to(SRC_INFRASCAN / "backend")
            dst_f = DEST_REPO / "backend" / rel
            if not is_excluded(str(rel)):
                copy_file_safe(src_f, dst_f)
                count += 1

    # 2. M4 Frontend Code & Config
    for root, dirs, files in os.walk(SRC_INFRASCAN / "frontend"):
        dirs[:] = [d for d in dirs if not is_excluded(d)]
        for f in files:
            src_f = Path(root) / f
            rel = src_f.relative_to(SRC_INFRASCAN / "frontend")
            dst_f = DEST_REPO / "frontend" / rel
            if not is_excluded(str(rel)):
                copy_file_safe(src_f, dst_f)
                count += 1

    # 3. M4 Deploy & Scripts
    for folder in ["deploy", "scripts"]:
        for root, dirs, files in os.walk(SRC_INFRASCAN / folder):
            dirs[:] = [d for d in dirs if not is_excluded(d)]
            for f in files:
                src_f = Path(root) / f
                rel = src_f.relative_to(SRC_INFRASCAN)
                dst_f = DEST_REPO / rel
                if not is_excluded(str(rel)):
                    copy_file_safe(src_f, dst_f)
                    count += 1
                    
    # 4. M4 Docs & Reports
    m4_docs_files = [
        "Milestone4_Documentation.pdf",
        "final/presentation_speech_m3_m4.md",
        "final/performance_report.md",
        "final/realtime_test_report.md",
        "final/realtime_progress.md",
        "final/final_report.md",
        "final/role_guide.md",
        "final/realtime_design.md",
        "final/user_quickstart.md",
        "final/known_issues.md",
    ]
    for rel in m4_docs_files:
        src = SRC_DOCS / rel
        dst = DEST_REPO / "docs" / rel
        if src.exists():
            if copy_file_safe(src, dst):
                count += 1
                
    # Screens in docs/final/
    for sub in ["screenshots", "realtime_screens", "diagnosis_screens"]:
        src_sub = SRC_DOCS / "final" / sub
        if src_sub.exists():
            for f in src_sub.glob("*.*"):
                dst_f = DEST_REPO / "docs" / "final" / sub / f.name
                if copy_file_safe(f, dst_f):
                    count += 1

    print(f"Milestone 4 files copied: {count}")
    return count

if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "all"
    if action == "m3":
        sync_milestone_3()
    elif action == "m4":
        sync_milestone_4()
    else:
        sync_milestone_3()
        sync_milestone_4()
