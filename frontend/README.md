InfraScan — AI-Powered Crack & Damage Assessment

1. Project Overview

InfraScan is a prototype application designed to support crack and damage assessment in civil infrastructure using image processing and a Convolutional Neural Network (CNN).

2. Objectives

- Upload infrastructure images for inspection.
- Perform basic image preprocessing.
- Predict possible crack or damage categories using a trained CNN.
- Store infrastructure assets and assessment results.
- Provide a web interface for viewing inspection information.

3. Technology Stack

- Frontend: React, TypeScript, Vite
- Backend: Python, FastAPI
- Database: SQLite with SQLAlchemy
- Image Processing: OpenCV, Pillow
- Machine Learning: PyTorch, CNN
- API Documentation: FastAPI Swagger UI

4. Dataset

Selected dataset: SDNET2018.

The project prototype used a small sample of 600 balanced deck images for initial model training and evaluation.

Initial model result: Approximately 50.83% validation accuracy after 3 epochs.

This is an experimental result from a limited sample. It does not establish reliable real-world crack detection performance.

5. Image Processing Workflow

1. Upload an image in JPG, JPEG, PNG, or WEBP format.
2. Validate the image and its file size.
3. Convert the image to grayscale.
4. Apply Gaussian blur.
5. Use Canny edge detection to identify image edges.
6. Resize the image to 64 × 64 pixels for CNN inference.
7. Store the assessment result in the database.

Note: Detected edges are not necessarily cracks. Model predictions and confidence scores are not validated engineering safety assessments.

6. Main Features

- User registration and login endpoints.
- Infrastructure asset creation and listing.
- Infrastructure image upload.
- Basic image preprocessing.
- Experimental CNN-based prediction.
- Database storage and retrieval of assessment results.

7. Run the Project

Backend

Open a terminal and run:

cd backend
.\venv311\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

Backend API: http://127.0.0.1:8000

API documentation: http://127.0.0.1:8000/docs

Frontend

Open a second terminal and run:

cd frontend
npm run dev

Frontend: http://localhost:5173

8. Database Tables

- "users" — user account information.
- "infrastructure_assets" — infrastructure asset details.
- "assessment_results" — image names, predicted categories, confidence scores, and timestamps.

9. Current Milestone 1 Progress

- [x] Frontend and backend initialized.
- [x] SDNET2018 selected and an initial dataset sample analyzed.
- [x] Infrastructure asset management implemented.
- [x] Image upload endpoint implemented.
- [x] Basic image preprocessing endpoint tested successfully.
- [x] Assessment results retrieved successfully through the API.
- [x] Experimental CNN prediction implemented.

Authentication enforcement, comprehensive dataset analysis, formal architecture documentation, and remaining acceptance checks should be verified before declaring Milestone 1 fully complete.

10. Limitations

InfraScan is an educational prototype. Its model requires more data, rigorous validation, and engineering review before any real infrastructure safety use.