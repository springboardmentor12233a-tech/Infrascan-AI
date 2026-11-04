# InfraScan – AI-Powered Crack & Damage Assessment for Civil Infrastructure

## Project Overview

InfraScan aims to use Artificial Intelligence and Computer Vision to identify cracks and damage in civil infrastructure from images.

## Project Objectives

* Explore suitable datasets for crack and damage detection.
* Perform Exploratory Data Analysis (EDA) on selected datasets.
* Develop a frontend and backend for the application.
* Investigate AI-based approaches for crack detection and damage assessment.

## Project Structure

* `frontend/` – React + TypeScript + Vite frontend application
* `backend/` – FastAPI backend application with authentication and asset management
* `ml/` – Machine learning pipelines (classification, detection, segmentation, crack geometry)
* `notebooks/` – EDA, training, and evaluation Jupyter notebooks
* `docs/` – Project reports, evaluation documentation, and result figures

## Current Status

Milestone 1 and Milestone 2 implementations completed.

---

## Milestone 1 Implementation

This repository includes a FastAPI backend, a React/TypeScript frontend, and
preprocessing demonstration notebooks. The backend includes authentication,
role-based access control, infrastructure assets, inspection workflows, and
audit logging.

### Run locally

- Backend: install `backend/requirements.txt`, configure required settings
  locally without committing credentials, then run
  `uvicorn app.main:app --reload` from `backend/`.
- Frontend: run `npm install` and `npm run dev` from `frontend/`.

Keep credentials and local `.env` files out of Git. Virtual environments,
dependency directories, caches, generated output, and raw datasets are ignored.

---

## Milestone 2 Implementation

Milestone 2 delivers the core AI and computer vision models for automated infrastructure defect assessment, encompassing classification, detection, segmentation, and quantitative crack geometry characterization.

### 1. Dataset Research & Exploratory Data Analysis (EDA)
- **Notebooks**:
  - `notebooks/01_dataset_structure.ipynb`: Directory hierarchies, image formats, annotations, and split sanity.
  - `notebooks/02_eda.ipynb`: Pixel intensities, resolution distributions, aspect ratios, and color distributions.
  - `notebooks/03_class_distribution.ipynb`: Class balance analysis across concrete, asphalt, and bridge datasets.
  - `notebooks/04_dataset_cleaning.ipynb`: Near-duplicate detection via perceptual hashing, corrupted file handling, and leakage-free splitting.
- **Documentation**: `docs/08_dataset_cleaning.md`.

### 2. Crack Classification (ResNet-50)
- **Pipelines**: `ml/classification/train_classifier.py`, `ml/classification/evaluate_classifier.py`, `ml/classification/config.py`.
- **Notebooks**: `notebooks/05_train_resnet50_colab.ipynb`, `notebooks/06_evaluate_classifiers_colab.ipynb`.
- **Results**:
  - `concrete_crack_cls`: Test Macro F1 = **0.9997** (Crack F1: 0.9997, Uncracked F1: 0.9996). Target $\ge 0.85$ reached.
  - `sdnet2018`: Test Macro F1 = **0.6421** (Crack F1: 0.4815, Uncracked F1: 0.8027). Substructure generalization challenged by surface shadows and aggregate voids.

### 3. Road Distress Detection (YOLOv8s & YOLO11s)
- **Pipelines**: `ml/detection/train_yolo.py`, `ml/detection/evaluate_yolo.py`, `ml/detection/config.py`.
- **Notebooks**: `notebooks/07_train_yolo_colab.ipynb`, `notebooks/07_train_yolo_kaggle.ipynb`, `notebooks/08_evaluate_yolo_colab.ipynb`, `notebooks/08_evaluate_yolo_kaggle.ipynb`.
- **Results**:
  - Model selection rule based on Validation mAP@50:95: YOLOv8s (**0.2220**) vs YOLO11s (**0.2159**).
  - Chosen model: **YOLOv8s** (Val mAP@50: 0.4285, Val Recall: 0.4437). Test split unassessed.

### 4. Semantic Segmentation (U-Net & U-Net++ ResNet-34)
- **Notebooks**: `notebooks/09_train_seg_kaggle.ipynb`, `notebooks/10_eval_seg_kaggle.ipynb`, `notebooks/11_evaluate_seg_test.ipynb`.
- **Pipelines & Evaluation**: `ml/segmentation/evaluate_seg_test.py`, `ml/segmentation/run_remaining_steps.py`.
- **Results**:
  - Chosen model: **U-Net++ (ResNet-34)** with threshold 0.40 (Validation Dice: 0.7482).
  - CRACK500 Test Split (1,087 images): Mean Dice = **0.6899** [0.6801, 0.7001], Mean IoU = **0.5481** [0.5382, 0.5586].
  - CFD Zero-Shot Generalization (118 images): Mean Dice = **0.4533** [0.4187, 0.4873], Mean IoU = **0.3109** [0.2839, 0.3384].
  - Speed benchmark: Host CPU latency = **1,349 ms / image** (384×640 input resolution).

### 5. Crack Geometry Measurement
- **Algorithms**: `ml/geometry/crack_geometry.py`, `ml/geometry/validate_geometry.py`, `ml/geometry/run_geometry.py`.
- **Capabilities**:
  - Medial axis skeletonization (`skimage.morphology.skeletonize`).
  - Graph-based path step length integration with $1.0$ and $\sqrt{2}$ diagonal neighbor weighting.
  - Perpendicular crack width estimation using Euclidean Distance Transform (EDT) ($2 \times \text{EDT}$).
  - Validation across synthetic shapes (rectangles, rotated polygons, arcs) confirming $\pm 1.0\text{ px}$ uncertainty.
  - Crack500 test set evaluation across 1,087 images (Length MAE: 140.32 px, Width MAE: 4.74 px).

### 6. Documentation & Milestone 2 Evaluation Report
- Comprehensive formal report: `docs/12_model_evaluation_report.md` and `docs/12_model_evaluation_report.pdf`.
- Full data traceability audit: `docs/12_number_sources.csv`.
- Evaluation visual figures & diagnostic panels: `docs/figures/`.
