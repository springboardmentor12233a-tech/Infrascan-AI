# Milestone 2 completion report

Branch: `feature/milestone-1-2-demo`  
Date of the runs below: 2026-11-02  
Environment: Python 3.12.10 virtualenv at `backend\venv`, torch 2.15.0+cpu, torchvision 0.29.2+cpu, ultralytics 8.4.198, OpenCV 5.0.0. CPU only (Intel Core i7-5600U). Host Python 3.14 cannot install PyTorch.

Official scores are the training-validation numbers in `models/reports/`. A later seed-7 sample is stored in `evaluation_summary.json` with `"official": false`. Quote the training numbers.

## Requirement tracking

| Requirement | Status | Evidence |
|---|---|---|
| Image quality report | Implemented and tested | `backend/app/ml/quality.py`. Pytest covers blur, invalid bytes, and contrast. Live images `11120.jpg` and `Czech_000261.jpg` both returned status `ok`. |
| Binary crack classifier | Implemented and tested | `scripts/ml/train_classifier.py` wrote `models/weights/crack_cnn.pt` and `models/reports/classifier_metrics.json`. |
| YOLO conversion, config, train, inference | Implemented and tested | `prepare_yolo.py` wrote 60 train and 20 val images. `train_yolo.py` fine-tuned YOLOv8n for 5 epochs. Inference ran. The score is near zero. See limitations. |
| U-Net segmentation | Implemented and tested | `scripts/ml/train_unet.py` wrote `models/weights/unet_deepcrack.pt`. Dice 0.4316 and IoU 0.3449 on 8 validation images. |
| Geometry from a mask | Implemented and tested | Pytest on a synthetic line. Live DeepCrack analysis returned area 1419 px and coverage 0.6793%. |
| Model comparison report | Implemented and tested | `docs/MODEL_EVALUATION_REPORT.md` uses the JSON files from these runs. |
| API and UI integration | Implemented. API tested. Browser click-through not tested | `POST /images/{id}/analyze` saved two rows. Overlay and mask GET returned HTTP 200. Vite served the frontend. No browser tool was available to click the button. |

## Training commands

Run from `D:\Infrascan-AI` with `backend\venv\Scripts\python.exe`:

```powershell
.\backend\venv\Scripts\python.exe scripts\ml\train_classifier.py
.\backend\venv\Scripts\python.exe scripts\ml\train_unet.py
.\backend\venv\Scripts\python.exe scripts\ml\prepare_yolo.py
.\backend\venv\Scripts\python.exe scripts\ml\train_yolo.py
.\backend\venv\Scripts\python.exe scripts\ml\evaluate_models.py
```

All five exited 0 in one chained run (about 147 seconds).

## Official validation metrics

SmallCNN, DeepCrack patches, best checkpoint by validation F1 (epoch 6 of 8):

| Metric | Value |
|---|---|
| Accuracy | 0.8194 |
| Precision | 0.7949 |
| Recall | 0.8611 |
| F1 | 0.8267 |
| Support | 144 patches |
| Confusion matrix | TN 56, FP 16, FN 10, TP 62 |

U-Net, DeepCrack, best checkpoint by validation Dice (epoch 6 of 6), 128×128 masks:

| Metric | Value |
|---|---|
| Dice | 0.4316 |
| IoU | 0.3449 |
| Images | 8 |

YOLOv8n fine-tune, RDD2022 Czech labeled subset, 60 train / 20 val, 5 epochs, image size 320, CPU. Numbers saved in `models/reports/yolo_metrics.json`:

| Metric | Value |
|---|---|
| Precision | 0.0006 |
| Recall | 0.1146 |
| mAP50 | 0.0004 |
| mAP50-95 | 0.0001 |

Ultralytics also printed this class table while validating `best.pt` (20 images, 33 instances):

| Class | Images | Instances | Precision | Recall | mAP50 | mAP50-95 |
|---|---:|---:|---:|---:|---:|---:|
| all | 20 | 33 | 0.000566 | 0.115 | 0.000442 | 0.000111 |
| D00 | 17 | 24 | 0.00226 | 0.458 | 0.00177 | 0.000442 |
| D10 | 5 | 5 | 0 | 0 | 0 | 0 |
| D20 | 2 | 2 | 0 | 0 | 0 | 0 |
| D40 | 2 | 2 | 0 | 0 | 0 | 0 |

The API uses confidence 0.25. On both live sample images the detector returned zero boxes. That matches a model whose precision at the validation operating point is about 0.0006.

## Live analysis evidence

`scripts/smoke_api.py` against `http://127.0.0.1:8000` after `seed_data.py`:

| File | Quality | Class | Confidence | Boxes | Crack pixels | Coverage |
|---|---|---|---:|---:|---:|---:|
| `docs/eda_outputs/samples/deepcrack/11120.jpg` | ok | crack | 0.512 | 0 | 1419 | 0.6793% |
| `docs/eda_outputs/samples/rdd2022_czech/Czech_000261.jpg` | ok | crack | 0.997 | 0 | 126579 | 35.1608% |

Overlay and mask responses were HTTP 200 for both. Dashboard stats after the run: 3 assets, 1 inspection, 2 images, 2 analyses. All three weight files were reported available.

The close-up overlay paints part of the visible crack and misses much of it. The street photo overlay paints large areas of road and sky. The U-Net was trained on DeepCrack close-ups, so that street result is a domain-shift failure. Use `11120.jpg` in the demonstration and describe the street result as a known limit.

## Environment notes

`ultralytics` upgraded NumPy from the pinned 1.26.4 to 2.5.4 and httpx from 0.27.0 to 0.28.1, and installed `opencv-python` 5.0.0.93 beside `opencv-python-headless` 4.9.0.80. Imports and the 20 pytest tests passed with those versions. `backend/requirements.txt` pins were left unchanged.

`files.pythonhosted.org` timed out on this machine. The working install used `https://mirrors.aliyun.com/pypi/simple/` plus the PyTorch CPU index. `scripts/setup_ml_env.ps1` now uses that mirror.

## Still incomplete or blocked

- The detector is trained and callable, and it is not accurate enough to show reliable boxes.
- Training used capped subsets so it could finish on CPU.
- SDNET2018 and METU are still missing, so classifier negatives are background patches.
- Czech test images have no public XML, so they were excluded from mAP.
- Pixel geometry is not millimetres.
- The React analysis button was not clicked in a browser.
