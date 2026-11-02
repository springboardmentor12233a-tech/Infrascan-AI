# Known limitations

Read this before the presentation. These are limits of the system that was actually run.

## Models

- SmallCNN validation F1 is 0.8267 on 144 DeepCrack patches. Negative patches are background inside crack photos. They are not intact-concrete photos from SDNET2018 or METU. Those two datasets are not on disk.
- The published DeepCrack train/test split was not used. Ten stems `11289-*` appear on both sides of that split. The training split groups by source id. `group_overlap` in both reports is empty.
- U-Net validation Dice is 0.4316 and IoU is 0.3449 on 8 images at 128×128. The overlay on `11120.jpg` covers only part of the visible crack.
- On the street photo `Czech_000261.jpg`, the same U-Net marked 35.1608% of pixels as crack, including sky and road. That output is saved and visible. It is a poor result because the network never trained on dashboard photos.
- YOLOv8n was fine-tuned from COCO `yolov8n.pt` for 5 epochs on 60 labeled Czech images (20 validation images). Saved metrics: precision 0.0006, recall 0.1146, mAP50 0.0004, mAP50-95 0.0001. One converted label, `Czech_000031.txt`, was checked against its XML and the numbers match, so the miss is not a broken coordinate conversion. The API withholds boxes when saved mAP50 is below 0.05 and tells the user that no reliable boxes were generated. The confidence threshold stays 0.25.
- Czech test images (709) have no public XML, so they were excluded from training and from mAP.
- `evaluation_summary.json` contains an extra seed-7 sample with higher classifier and Dice numbers. Those entries are marked `"official": false`. Quote `classifier_metrics.json`, `unet_metrics.json`, and `yolo_metrics.json`.

## Measurements and product scope

- Geometry is in pixels. There is no camera calibration and no millimetre conversion.
- Quality scores are heuristics (Laplacian variance, mean brightness, gray standard deviation). They do not certify that a photo is fit for a structural decision.
- AI output is decision support. It is not a safety rating.
- Analysis runs when the user clicks **Run AI analysis**. Upload alone does not call the models.
- Google sign-in still returns HTTP 501.
- PostgreSQL is described in Docker Compose and was not started in this session. The running app uses SQLite at `backend\infrascan.db`.
- File storage is the local `backend\uploads` folder. There is no S3 adapter in this build.
- Headless Chromium on 2026-11-02 clicked login, assets, inspection create, upload, and analysis. A second pass signed in as the manager, created and edited `DEMO-RW-04`, then reopened the saved inspection. Screenshots are in `docs/demo_screenshots/`. Docker is not installed, so PostgreSQL was not started. The demonstration database is SQLite.

## Environment

- Train and serve the models with Python 3.12. Python 3.14 has no PyTorch wheel.
- This PC could not download large wheels from `files.pythonhosted.org`. `scripts/setup_ml_env.ps1` uses the Aliyun PyPI mirror and the official PyTorch CPU index.
- Installing Ultralytics upgraded NumPy to 2.5.4 and httpx to 0.28.1, and added OpenCV 5. Pytest still passed. `backend/requirements.txt` still pins the older versions for a clean API install.
- Weight files (`*.pt`, `*.pth`), `models/runs/`, raw datasets, `backend/infrascan.db`, and `backend/uploads/*` are gitignored. A fresh clone has the code and the metric JSON, and needs the datasets plus a training run before analysis can leave the `unavailable` status.

## Datasets that were researched and not downloaded

The research notes cover 15 candidate datasets. The local EDA, and every model in this milestone, use only CFD, DeepCrack, and the RDD2022 Czech subset. Do not say that all 15 were downloaded.
