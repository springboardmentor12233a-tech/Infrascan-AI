
# InfraScan — AI-Powered Crack & Damage Assessment for Civil Infrastructure

## Project Overview

InfraScan is a prototype application designed to explore AI and computer vision techniques for identifying cracks and assessing damage in civil infrastructure images.

The project combines a React frontend, a FastAPI backend, dataset analysis, and a preliminary machine-learning classification baseline.

## Project Objectives

- Explore concrete crack datasets.
- Perform Exploratory Data Analysis (EDA).
- Prepare training, validation, and testing datasets.
- Develop a frontend and backend application.
- Establish a preliminary crack-classification baseline.
- Improve model performance in subsequent milestones.

## Project Structure

- `frontend/` — React and TypeScript frontend.
- `backend/` — FastAPI backend, database, and model-related files.
- `dataset/` — Dataset information, EDA scripts, and selected dataset splits.
- `docs/` — Project documentation.

## Dataset

The project uses SDNET2018, which contains 56,092 concrete surface images from bridge decks, walls, and pavements.

An 8,000-image subset has been prepared for preliminary model development:

| Split | Images |
|---|---:|
| Training | 5,598 |
| Validation | 1,196 |
| Testing | 1,206 |
| Total | 8,000 |

See `dataset/dataset-info.md` and `dataset/eda-summary.md` for details.

## Preliminary Model

- Feature extraction: Histogram of Oriented Gradients (HOG).
- Classifier: Support Vector Machine (SVM).
- Preliminary test accuracy: 35.07%.
- Classification scope: Six dataset classes.

The current result is a baseline for future experiments. The target accuracy of 99% has not yet been achieved.

## Application Features

- User registration and login.
- Image upload and basic image processing.
- Asset creation and retrieval.
- Dashboard and assessment-results interface.
- FastAPI endpoints for application functionality.

**Note:** AI prediction availability depends on the configured model and runtime environment. The current image-upload workflow provides basic image-processing information; a fully integrated, reliable AI prediction workflow remains future work.

## Current Status

- Dataset preparation and EDA documentation completed.
- Preliminary HOG + SVM baseline trained and evaluated.
- Frontend and backend application workflows tested.
- Further model development, integration testing, and documentation remain.

## Future Work

- Improve classification performance through additional experiments.
- Evaluate stronger classification models.
- Develop and evaluate crack detection and segmentation models.
- Integrate validated AI predictions into the application.
- Add further testing and improve reporting.

## Dataset Source

SDNET2018: https://digitalcommons.usu.edu/all_datasets/48/
