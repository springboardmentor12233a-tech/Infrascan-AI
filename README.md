# InfraScan – AI-Powered Crack & Damage Assessment for Civil Infrastructure

## Project Overview

InfraScan explores how computer vision can help identify visible cracks in concrete images. This is a student research prototype, not a structural-safety assessment.

## Project Structure

- frontend/ – React and TypeScript application
- backend/ – FastAPI application and AI-related modules
- notebooks/ – Preprocessing demonstration, comparison image, and [executed Milestone 2 detection and segmentation notebook](notebooks/InfraScan_Milestone_2_Detection_Segmentation.ipynb)
- datasets/ and docs/ – Add dataset notes and project documentation here as they are prepared

## Current Status (4 November 2026)

Milestone 1 dataset preparation and the initial web-application code are in the repository. The executed Milestone 2 detection and segmentation notebook, including its outputs, has now been added under notebooks/. Selected report figures and end-to-end application verification are still pending.

## Milestone 1: Dataset and Project Foundation

- Selected a balanced 10,000-image Concrete Crack Images for Classification (CCIC) subset: 5,000 cracked and 5,000 uncracked image crops.
- Recorded the selected files in a manifest and prepared 7,000 training, 1,500 validation, and 1,500 test images.
- CCIC has image-level cracked/uncracked labels only; it does not include crack boxes, pixel masks, or physical scale measurements.

## Frontend and Backend Code

### Backend

The backend is a FastAPI application. The repository contains modules and routes for authentication, users, infrastructure assets, uploaded images, and inspections. It also has separate folders for AI modules, database models, schemas, services, scripts, and tests. The presence of test files does not by itself mean the tests have passed; test status should be recorded after running them.

### Frontend

The frontend is a React and TypeScript application. Its page files include the home page, dashboard, login and registration, profile and users, assets and asset details, inspections and inspection details, and image upload. These files show the screens implemented in code. The complete frontend-to-backend flow still needs to be run and checked before calling it fully verified.

## Milestone 2: Initial Model Experiments

- The CCIC classifier achieved 97.4% accuracy on its 1,500-image test split (1,461 correct predictions).
- Detection and segmentation used the separate annotated Crack-Seg dataset (4,029 images), because CCIC does not include crack-location annotations.
- YOLO test results: box mAP50 0.777; mask mAP50 0.657.
- U-Net test results: pixel Dice 0.726; IoU 0.570.
- A controlled polygon-coordinate conversion fault was diagnosed and corrected. This was a demonstration fault, not a naturally occurring model failure.
- Classification, detection, and segmentation metrics measure different tasks and should not be compared as if they were the same score.

## Remaining Work

- Run the backend and frontend locally and verify the full flow: sign in, create an asset, upload an image, and view the inspection record. Record any errors and fixes.
- Run the backend tests and record the actual pass/fail result.
- Check and document whether trained model inference is connected to the application upload flow. Do not describe this as complete until it has been tested.
- Add selected Milestone 2 result figures to notebooks/ or docs/; the executed [Colab notebook](notebooks/InfraScan_Milestone_2_Detection_Segmentation.ipynb) and its outputs are committed.
- Confirm with the mentor whether the CCIC plus Crack-Seg dataset approach satisfies the requested dataset size.
- Test on independent concrete images if available and record false positives or missed cracks.

## Run Locally

- Backend: install dependencies from backend/requirements.txt, configure local settings without committing credentials, then run uvicorn app.main:app --reload from backend/.
- Frontend: run npm install and npm run dev from frontend/.

For each later update, add the date, what changed, evidence or result, and the next task. Do not commit credentials, local .env files, or large raw dataset archives.
