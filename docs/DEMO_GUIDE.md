# Demonstration guide

Use this sequence tomorrow. The servers must be started from `D:\Infrascan-AI`.

## Before you start

1. Python 3.12 virtualenv already exists at `backend\venv` on this machine. If you are on a new machine, install Python 3.12 and run `.\scripts\setup_ml_env.ps1`. PyTorch does not install on Python 3.14.
2. Frontend packages are already installed. If `frontend\node_modules` is missing, run `npm install` inside `frontend`.
3. Weight files must exist at:
   - `models\weights\crack_cnn.pt`
   - `models\weights\unet_deepcrack.pt`
   - `models\weights\yolo_rdd.pt`

   They are gitignored. On this PC they are already on disk. On a fresh clone, run the five training commands in `docs/MILESTONE_2_COMPLETION_REPORT.md`. Training took about 2.5 minutes on this CPU.

## One way to start

```powershell
Set-Location D:\Infrascan-AI
.\scripts\start_infrascan.ps1
```

That seeds the database, then opens two windows:

- API: http://127.0.0.1:8000/docs
- UI: http://127.0.0.1:5173

Or start them yourself:

```powershell
Set-Location D:\Infrascan-AI\backend
.\venv\Scripts\python.exe seed_data.py
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
Set-Location D:\Infrascan-AI\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Run uvicorn from `backend` so uploads land in `backend\uploads`.

## Accounts

Password for every seeded account: `Password123!`

| Role | Email |
|---|---|
| Inspector (use this one) | inspector@infrascan.com |
| Administrator | admin@infrascan.com |
| Infrastructure Manager | manager@infrascan.com |
| Civil Engineer | civil@infrascan.com |
| Maintenance Engineer | maintenance@infrascan.com |

Maintenance Engineer can sign in and will receive “Your role cannot run analysis.”

## Sample images

These files are local EDA copies. They are gitignored and already on this PC.

| Purpose | Path |
|---|---|
| Main demo (close-up crack) | `docs\eda_outputs\samples\deepcrack\11120.jpg` |
| Optional limit example (street) | `docs\eda_outputs\samples\rdd2022_czech\Czech_000261.jpg` |

## Click path

1. Open http://127.0.0.1:5173 and sign in as `inspector@infrascan.com`.
2. The dashboard shows asset, inspection, and image counts, plus whether each weight file is on disk. It does not invent a score.
3. Open Assets and choose **BRG-001 Golden Gate Overpass Viaduct** (or either of the other two).
4. Create an inspection. The date can be today. Notes can say “Milestone demonstration”.
5. Upload `11120.jpg`.
6. Click **Run AI analysis**.
7. The panel shows:
   - Quality: size, blur, brightness, contrast. This file returned status `ok`.
   - Classification: `crack`, confidence about 0.51, from a 4×4 grid of 64×64 patches.
   - Detection: status completed, and **no boxes**. The fine-tuned YOLOv8n did not pass confidence 0.25.
   - A red overlay and a black-and-white mask. The red pixels cover part of the crack.
   - Geometry in pixels, plus the sentence that these are not millimetres.
8. The dashboard count of analyzed images increases. The row is in SQLite table `image_analyses`.

An API-only replay of steps 5–8 is:

```powershell
Set-Location D:\Infrascan-AI
.\backend\venv\Scripts\python.exe scripts\smoke_api.py
```

On 2026-11-02 that script created inspection 1, uploaded both samples, and printed the metrics in the Milestone 2 report.

## What to say about each module

| Module | One sentence |
|---|---|
| Quality | Laplacian variance, mean brightness, and gray-level standard deviation. A blurry photo is flagged and still analyzed. |
| SmallCNN | Classifies 64×64 patches. The photo is crack if any patch scores at least 0.5. Validation F1 was 0.8267. |
| YOLOv8n | Fine-tuned for 5 epochs on 60 Czech road images. Validation mAP50 was 0.0004. Expect empty boxes. |
| U-Net | Predicts a 128×128 mask and scales it back. Validation Dice was 0.4316 and IoU was 0.3449. |
| Geometry | Area, skeleton length, and width from the distance transform, all in pixels. |

## If you also show the street photo

Say this before the overlay appears: the classifier and U-Net learned from close-up crack crops. On `Czech_000261.jpg` the API really returned label crack at confidence 0.997 and 35.16% coverage, and the overlay covers road and sky. That is a domain mismatch, not a successful road inspection. The detector still returned zero boxes.

## Tests you can mention

```powershell
Set-Location D:\Infrascan-AI\backend
.\venv\Scripts\python.exe -m pytest tests -q --tb=line
```

Result on 2026-11-02: 20 passed.

`GET http://127.0.0.1:8000/health` returned version 0.2.0.  
`GET http://127.0.0.1:5173/` returned HTTP 200.

The analysis screen was not clicked through an automated browser. The API calls that the screen makes were run by `scripts/smoke_api.py`.
