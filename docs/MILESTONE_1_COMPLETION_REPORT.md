# Milestone 1 completion report

Branch: `feature/milestone-1-2-demo`  
Base commit: `2ddfa4a` — Complete InfraScan dataset research and initial EDA.  
Checked on 2026-11-02 against the files in this working tree and `docs/eda_outputs/eda_machine_summary.md`.

Status words used below:

| Status | Meaning |
|---|---|
| Implemented and tested | Code ran and produced the result named here |
| Implemented but not tested | Code is present; this session did not execute that path |
| Partially implemented | A real slice works; the full requirement does not |
| Not implemented | Absent, or only a stub |
| Blocked | An external file, service, or download is missing |

## Requirement tracking

| Requirement | Status | Evidence |
|---|---|---|
| Dataset research and EDA preserved | Implemented and tested | Existing `docs/InfraScan_EDA_Report.md` and `docs/eda_outputs/` were not rewritten. Counts below match `eda_machine_summary.md`. |
| CFD facts | Implemented and tested | 155 JPEG, 118 matched `.seg`/`.mat`, 37 unlabeled extras, 0 unreadable, mean crack fraction 0.02287 |
| DeepCrack facts | Implemented and tested | 537 pairs (300 train / 237 test), 0 unreadable, mean crack fraction 0.03537. Filename overlap on stems `11289-1` through `11289-10`. |
| RDD2022 Czech facts | Implemented and tested | 3,538 JPEG, 2,829 XML, 1,745 boxes (D00 988, D10 399, D20 161, D40 197), 0 XML errors, 709 images without XML |
| Fifteen candidate datasets researched | Implemented and tested | Listed in the dataset research workbook. Only CFD, DeepCrack, and RDD Czech were downloaded and passed through EDA. |
| SDNET2018 and METU downloads | Blocked | `datasets/raw/sdnet2018` is a README. METU images were not on disk. |
| Dataset loaders, mask checks, VOC and CFD parsers | Implemented and tested | `backend/app/ml/datasets.py`. Pytest covers grouping, VOC conversion, and the CFD parser when files exist. Training loaded 537 DeepCrack pairs. YOLO prep read 2,829 XML files. |
| Leakage-aware splits | Implemented and tested | Classifier and U-Net reports show `group_overlap: []`. Published DeepCrack split was not used for training. |
| FastAPI app, routers, Pydantic models | Implemented and tested | `GET /health` returned version `0.2.0`. Pytest: 20 passed. |
| SQLite database | Implemented and tested | `sqlite:///./infrascan.db` from `backend/`. Seed created 5 users and assets BRG-001, TUN-002, DAM-003. New table `image_analyses`. |
| PostgreSQL | Implemented but not tested | Docker Compose file already in the repo. This session did not start Postgres. |
| JWT login and five-role access control | Implemented and tested | Pytest covers login and a 403 for an inspector calling `/users`. Live smoke logged in as `inspector@infrascan.com`. Maintenance Engineer receives 403 on analyze (pytest). |
| Assets, inspections, image upload, local storage | Implemented and tested | Pytest covers asset CRUD, bad file type, tiny images, blur, and duplicate MD5. Live smoke uploaded two real JPEGs. |
| Audit log calls | Implemented and tested | `log_action` runs on register, login, and analyze. A dedicated audit-table assertion was not added. |
| Reusable preprocess (validate, letterbox, normalize, tensor, optional denoise, gray/RGB) | Implemented and tested | `backend/app/ml/preprocess.py` and wrappers in `backend/app/services/preprocessing.py`. Pytest covers letterbox, paired resize, and a grayscale tensor. |
| React login, dashboard, assets, inspections, upload, analysis panel | Implemented. API tested. Browser click-through not tested | Vite returned HTTP 200 on `http://127.0.0.1:5173/`. The same endpoints the pages call were exercised by `scripts/smoke_api.py`. No browser automation tool was available. |
| Google OAuth | Not implemented | Existing endpoint still returns 501. |

## Dataset findings used in this milestone

These numbers were read from `docs/eda_outputs/eda_machine_summary.md` on 2026-11-02. They match the known audit.

- CFD: 155 JPEG images, 118 annotation-matched `.seg` and `.mat` sets, 37 extra images without annotations, 0 unreadable, mean crack fraction 0.022865838983050852.
- DeepCrack: 537 image-mask pairs, 300 training and 237 testing, 0 unreadable, mean crack fraction 0.035369435754189944. The published split shares source stems `11289-*`. Training scripts group by source id and keep `group_overlap` empty.
- RDD2022 Czech: 3,538 JPEG images, 2,829 XML files, 1,745 boxes, 0 XML parse errors. Class counts: D00 988, D10 399, D20 161, D40 197.

## What this session added to Milestone 1

The login, asset, inspection, upload, CLAHE preview, and role checks were already in the repository. This session kept that code and added:

- Aspect-preserving resize and a shared tensor preprocess used by the models.
- Richer quality fields (contrast, overexposure, flags) in the analysis payload. The upload endpoint still stores the original blur / brightness / quality status so the Milestone 1 tests stay valid.
- Live dashboard counts from `GET /stats`.
- Persisted analysis rows in `image_analyses`.

## Commands that were run

```powershell
Set-Location D:\Infrascan-AI\backend
.\venv\Scripts\python.exe -m pytest tests -q --tb=line
```

Result: `20 passed` in 7.85s. Warnings only (FastAPI `regex` query, `on_event`, `datetime.utcnow` inside python-jose).

```powershell
Set-Location D:\Infrascan-AI\backend
.\venv\Scripts\python.exe seed_data.py
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`GET /health` returned `{"status":"ok","app":"InfraScan","version":"0.2.0",...}`.

## Still incomplete

- PostgreSQL was not started.
- The React screens were not clicked in a browser.
- Google sign-in remains a stub.
- SDNET2018 and METU remain unavailable, so non-crack examples are background patches inside crack photos.
