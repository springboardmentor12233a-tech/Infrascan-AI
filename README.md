# InfraScan – AI-Powered Crack & Damage Assessment for Civil Infrastructure

## Project Overview

InfraScan explores how computer vision can help identify visible cracks in concrete images. This repository contains the project web application and model experiments. It is a student research prototype, not a structural-safety assessment.

## Project Objectives

- Explore crack-image datasets and their label limitations.
- Prepare data and evaluate crack classification, detection, and segmentation.
- Develop a frontend and backend for organizing inspection images.
- Record model results, limitations, and next steps clearly.

## Project Structure

- frontend/ – Frontend application
- backend/ – Backend application and AI processing
- notebooks/ – Data preparation and model experiments
- datasets/ – Dataset information and documentation, when added
- docs/ – Project documentation, when added

## Current Status

Milestone 1 dataset preparation and the initial application foundation are complete. Milestone 2 baseline classification, detection, segmentation, and a controlled preprocessing-fault diagnosis have been run. The results below apply only to the named datasets and test splits.

## Milestone 1: Dataset and Project Foundation

- Selected a balanced 10,000-image Concrete Crack Images for Classification (CCIC) subset: 5,000 cracked and 5,000 uncracked image crops.
- Recorded selected files in a manifest and prepared 7,000 training, 1,500 validation, and 1,500 test images.
- Planned and started the image-upload workflow using a React frontend and FastAPI backend.
- CCIC has image-level cracked/uncracked labels only; it does not include crack boxes, pixel masks, or physical scale measurements.

## Milestone 2: Initial Model Experiments

- The CCIC classifier achieved 97.4% accuracy on its 1,500-image test split (1,461 correct predictions).
- Detection and segmentation used the separate annotated Crack-Seg dataset (4,029 images), because CCIC does not include crack-location annotations.
- YOLO test results: box mAP50 0.777; mask mAP50 0.657.
- U-Net test results: pixel Dice 0.726; IoU 0.570.
- A controlled polygon-coordinate conversion fault was diagnosed and corrected. This was a demonstration fault, not a naturally occurring model failure.
- Classification, detection, and segmentation scores measure different tasks and should not be compared as if they were the same metric.

## Next Steps

- Add verified Colab figures and notebook outputs to the project documentation.
- Confirm with the mentor whether the CCIC plus Crack-Seg dataset approach satisfies the requested dataset size.
- Evaluate the models on independent concrete images and document false positives or missed cracks.
- Keep future progress notes dated and include the evidence, result, and next task.

## Run Locally

- Backend: install dependencies from backend/requirements.txt, configure local settings without committing credentials, then run uvicorn app.main:app --reload from backend/.
- Frontend: run npm install and npm run dev from frontend/.

Do not commit credentials, local .env files, or large raw dataset archives.
