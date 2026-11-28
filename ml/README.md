# InfraScan ML Module

Machine Learning workspace for dataset preprocessing, annotation cleaning, YOLO training, evaluation, and inference.

## Structure
- `annotation/` — `annotation_cleaner.py`
- `data_preprocessing/` — `dataset_preparation.py`, `verify_processed_counts.py`
- `training/` — `train_rdd2022.py` (YOLOv8n training & evaluation pipeline)
- `datasets/`, `evaluation/`, `inference/`, `models/`, `experiments/`, `configs/`, `tests/`

## Training Command (GPU recommended)
```powershell
python ml/training/train_rdd2022.py --src dataset_audit/processed_dataset --epochs 50 --imgsz 640 --batch 16
```
Exported weights should be placed at `backend/weights/rdd2022_yolo.pt` for live backend inference.

