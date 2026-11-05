# InfraScan Milestone 2 ML Workbench

This directory contains the reproducible model-development utilities for Milestone 2:

- image quality assessment and preprocessing;
- a baseline crack/no-crack classifier trained on the included dataset;
- annotation-gated YOLO detection and U-Net segmentation entry points;
- crack geometry extraction and segmentation metrics;
- JSON evaluation reports for comparing trained models.

The included `datasets/concrete_cracks/extracted/` dataset has image-level
`Negative` and `Positive` labels only. It does **not** contain bounding-box or
pixel-mask annotations. The detection and segmentation commands therefore
require an explicitly annotated dataset and fail with an actionable message
instead of generating fabricated labels.

## Setup

From the project root:

```powershell
python -m pip install -r ml\requirements-ml.txt
```

YOLO and U-Net training additionally require the optional packages listed in
`requirements-ml-optional.txt`.

## Baseline classifier

```powershell
python -m ml.quality_report --data-root datasets\concrete_cracks\extracted --output ml\artifacts\quality-report.json
python -m ml.train_classifier --data-root datasets\concrete_cracks\extracted --output-dir ml\artifacts\classifier
```

Use `--limit-per-class` for a quick local run. The command writes a pickle
model and `evaluation.json`; these are local experiment outputs, not production
AI predictions.

## Detection and segmentation

```powershell
python -m ml.train_detection --dataset-yaml path\to\data.yaml --output-dir ml\artifacts\detection
python -m ml.train_segmentation --images path\to\images --masks path\to\masks --output-dir ml\artifacts\segmentation
```

Both commands validate that annotations exist before importing or training a
model. This preserves the distinction between the current classification
dataset and the later annotated datasets required by Milestone 2.
