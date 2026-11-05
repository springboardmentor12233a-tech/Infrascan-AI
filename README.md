# InfraScan – AI-Powered Crack & Damage Assessment for Civil Infrastructure

## Project Overview

InfraScan aims to use Artificial Intelligence and Computer Vision to identify cracks and damage in civil infrastructure from images.

## Project Objectives

* Explore suitable datasets for crack and damage detection.
* Perform Exploratory Data Analysis (EDA) on selected datasets.
* Develop a frontend and backend for the application.
* Investigate AI-based approaches for crack detection and damage assessment.

## Project Structure

* `frontend/` – Frontend application
* `backend/` – Backend application and AI processing
* `datasets/` – Dataset information and documentation
* `docs/` – Project documentation

## Current Status

Milestone 2 AI development and evaluation are complete for the verified
classification, detection, segmentation, and crack-measurement workflows.

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

## Milestone 2 Implementation

Milestone 2 adds the AI model development and evaluation workflows:

- **CNN crack classification:** trained on 40,000 concrete images
  (32,000 training and 8,000 validation images). Validation accuracy is
  `0.996875`, with F1-score `0.9968762`.
- **YOLO road-damage detection:** detects `Crack`, `Pothole`, and
  `Surface Erosion` using bounding boxes. The verified model achieved
  precision `0.597`, recall `0.551`, mAP50 `0.586`, and mAP50-95 `0.273`.
- **U-Net crack segmentation:** trained and evaluated using 118 verified
  CrackForest image-mask pairs (94 training and 24 validation pairs).
  Verified IoU is `0.4054` and Dice is `0.5769`.
- **Crack geometry measurement:** reports cleaned crack area, skeleton-based
  length, average width, and maximum width in pixels.
- **FastAPI integration:** the existing YOLO model can be run through the
  authenticated image-analysis endpoint and displayed in the frontend.

Milestone 2 models are decision-support tools, not certified structural safety
assessments. The YOLO model is trained for road-damage imagery and may
misclassify unusual or building-related cracks. An experimental fine-tuned
checkpoint exists separately, but it has not replaced the verified production
checkpoint because further representative road-crack annotations are needed.

Detailed results and limitations are documented in
[`reports/milestone_2_report.md`](../reports/milestone_2_report.md).
