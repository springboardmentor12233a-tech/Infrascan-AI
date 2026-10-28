InfraScan — System Architecture

1. Overview

InfraScan is an AI-powered system designed to help assess cracks and damage in civil infrastructure using images.

2. Main Components

Frontend

- Technology: React and TypeScript
- Provides the user interface.
- Allows users to upload infrastructure images.
- Displays upload status and image information.

Backend

- Technology: Python and FastAPI
- Receives image uploads from the frontend.
- Validates image format and file size.
- Verifies image data and stores uploaded images.
- Will support image preprocessing and AI-based damage assessment.

Dataset

- Dataset: SDNET2018
- Contains 56,092 JPG images of cracked and non-cracked concrete surfaces.
- Used for exploring and developing the damage assessment model.

Database and Storage

- Planned database: stores user information, infrastructure assets, and assessment records.
- Image storage: stores uploaded infrastructure images.

3. System Workflow

1. The user opens the InfraScan frontend.
2. The user selects and uploads an infrastructure image.
3. The frontend sends the image to the FastAPI backend.
4. The backend validates the image and saves it.
5. Image preprocessing and AI-based damage assessment will be integrated.
6. The assessment results will be displayed on the frontend.

4. Current Implementation Status

- React frontend initialized.
- FastAPI backend initialized.
- Image upload endpoint implemented and tested.
- Basic image validation and storage implemented.
- SDNET2018 dataset downloaded and initial image counts analyzed.
- Database integration, authentication, infrastructure asset management, and AI prediction remain to be implemented or verified.

5. Future Improvements

- Implement authentication and role-based access.
- Add database integration.
- Implement infrastructure asset management.
- Develop the image preprocessing pipeline.
- Train and integrate an AI damage detection model.
- Display damage assessment results.