# InfraScan – AI-Powered Crack & Damage Assessment for Civil Infrastructure

## Project Overview

InfraScan is an AI-powered computer vision project focused on detecting and assessing cracks in civil infrastructure images. The project combines dataset analysis, data-quality validation, crack segmentation, and application development to build a foundation for automated infrastructure inspection.

## Problem Statement

Manual infrastructure inspection can be time-consuming and subjective. InfraScan explores how computer vision can assist by identifying crack regions from images and supporting more systematic infrastructure assessment.

## Project Objectives

- Analyze and validate infrastructure image datasets before model development.
- Identify potential data-quality issues and data leakage.
- Build a baseline AI model for crack detection and segmentation.
- Evaluate model performance using standard and pixel-level metrics.
- Develop a frontend and backend foundation for future deployment.

---

# Milestone 1: Dataset Analysis and Data Quality

Milestone 1 focused on understanding and validating the dataset before model training.

### Dataset

The project uses the SDNET2018 concrete crack dataset, containing images from:

- Deck
- Pavement
- Wall

The dataset contains both cracked and uncracked concrete surface images.

### Work Completed

- Exploratory Data Analysis (EDA)
- Image readability and dimension checks
- Class and surface distribution analysis
- Image-quality analysis
- Duplicate and near-duplicate analysis
- Data leakage checks across dataset splits
- Annotation issue identification

### Key Finding

The dataset was analyzed before model development to establish a reliable data foundation and identify potential quality or leakage issues that could affect model evaluation.

The latest Milestone 1 outputs are available in:

`results/milestone_1/`

---

# Milestone 2: Crack Segmentation Model and Evaluation

Milestone 2 focused on training and evaluating a baseline YOLO-based segmentation model.

Segmentation was used to identify the actual crack region at the pixel level rather than only predicting a bounding box.

### Official Test Results

| Metric | Result |
|---|---:|
| Box Precision | 84.54% |
| Box Recall | 70.27% |
| Box mAP@50 | 74.55% |
| Mask Precision | 84.25% |
| Mask Recall | 62.16% |
| Mask mAP@50 | 62.11% |
| Mask mAP@50–95 | 23.30% |

### Threshold Analysis

Multiple confidence thresholds were evaluated on 200 validation images.

Among the tested thresholds, **0.25** achieved the highest:

- Pixel IoU: **0.6162**
- Pixel Precision: **0.7132**

This threshold was selected as a reasonable operating point for the current baseline.

### Error and Data-Quality Analysis

In addition to aggregate metrics, numerical error analysis was performed.

One validation image was identified with an empty segmentation annotation while the model produced detections. The image was flagged for manual annotation review, and the original dataset was not modified.

The Milestone 2 evaluation results are available in:

`results/milestone_2/`

---

## Repository Structure

```text
Infrascan-AI/
│
├── README.md
│
├── notebooks/
│   ├── InfraScan_EDA.ipynb
│   └── 03_preprocessing_demo.ipynb
│
├── results/
│   ├── milestone_1/
│   │   ├── InfraScan_EDA_statistics.csv
│   │   ├── InfraScan_annotation_issues.csv
│   │   └── EDA_Plots/
│   │
│   └── milestone_2/
│       ├── full_test_metrics.json
│       ├── validation_threshold_comparison.csv
│       ├── validation_error_summary.csv
│       ├── annotation_review.csv
│       └── InfraScan_Milestone_2_Final_Report.txt
│
├── backend/
└── frontend/


