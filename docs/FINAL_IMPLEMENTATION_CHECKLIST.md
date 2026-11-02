# Final implementation checklist

Checked on 2026-11-02 after commit `98b82f7`, on branch `feature/milestone-1-2-demo`.
The live database is SQLite at `backend/infrascan.db`. Docker is not installed on this PC, so PostgreSQL was not started.

Pytest, run from `backend` with `.\venv\Scripts\python.exe -m pytest tests -q --tb=short`:

`23 passed, 29 warnings in 11.51s`

The warnings are deprecations in Starlette, FastAPI `on_event`, the `regex` query parameter, and `python-jose`. No test failed.

Browser script `scripts/browser_demo.py` signed in as the inspector, opened BRG-001, created an inspection, uploaded `docs/eda_outputs/samples/deepcrack/11120.jpg`, and opened the analysis panel. Screenshots are in `docs/demo_screenshots/`.

| Requirement | Class | Evidence |
|---|---|---|
| Login | Completed and tested | Screenshot `01_login.png`. Pytest `test_register_and_login` and `test_invalid_login_is_rejected` (401). |
| Dashboard | Completed and tested | `02_dashboard.png` shows 3 assets and weight files found. Counts are live from `GET /stats`. |
| Asset list | Completed and tested | `03_assets.png`. Pytest asset CRUD. |
| Add/edit asset | Implemented and tested for a manager in pytest. Not clicked in the browser | `frontend/src/pages/AssetForm.tsx`. Inspectors do not see the edit control. |
| Create inspection | Completed and tested | Browser created “Browser demonstration inspection” on BRG-001. `05_inspection_created.png`. |
| Image upload | Completed and tested | `06_uploaded.png`. Pytest rejects a bad type, a tiny image, a duplicate, and a blurry image. |
| Analysis trigger | Completed and tested | Button calls `POST /images/{id}/analyze`. Panel in `07_analysis.png`. |
| Image quality | Completed and tested | Panel shows 544×384, blur 2579.71, brightness 153.3, contrast 33.69, flags none. |
| Classification | Completed and tested | Label crack, confidence 0.512. Validation F1 0.8267 is in `models/reports/classifier_metrics.json`. |
| Detection | Partially implemented | Pipeline ran. Validation mAP50 is 0.0004, so the UI says no reliable boxes were generated. `07_analysis.png`. |
| Segmentation mask and overlay | Completed and tested | Overlay and mask are visible. Dice 0.4316 and IoU 0.3449 are the validation scores, not a score for this one photo. |
| Geometry | Completed and tested | Area 1419 px, length 348 px, mean width 4.479 px, bbox 467×249, coverage 0.6793%. Unit is pixels. |
| Inspection history | Completed and tested | Asset page lists inspections and links to each one. The new inspection appeared before upload. |
| Wireframes | Completed as design artifacts | `docs/wireframes/index.html`. They are not the running app. |
| PostgreSQL | Blocked | `docker` is not installed. SQLite is the database that was used. |
| SDNET2018 and METU | Blocked | No images on disk. |
| Google sign-in | Not implemented | Endpoint still returns 501. |

YOLO label check, not a new training run: `Czech_000031.xml` box D20 (273, 442, 343, 488) on a 600×600 image becomes the file line `2 0.513333 0.775000 0.116667 0.076667` in `datasets/processed/rdd2022_yolo/labels/train/Czech_000031.txt`. The conversion matches. The low mAP is from the 5-epoch, 60-image CPU fine-tune.
