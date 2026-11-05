# InfraScan – System Architecture

## 1. Project Overview

InfraScan is an AI-powered infrastructure assessment system designed to identify and analyze cracks and damage in infrastructure images, including roads, bridges, and buildings.

The system aims to assist infrastructure inspection by using image processing and deep learning techniques.

## 2. System Architecture

The system follows a client-server architecture consisting of the following components:

### A. Frontend – React.js

* Provides the user interface.
* Allows users to select infrastructure images.
* Displays image previews.
* Sends images to the backend through REST APIs.
* Displays upload status and responses.

### B. Backend – FastAPI

* Handles frontend requests.
* Provides REST API endpoints.
* Validates uploaded image files.
* Checks file extensions and image formats.
* Limits uploaded image size to 10 MB.
* Stores uploaded images.
* Will coordinate image preprocessing and AI model predictions.

### C. Database – PostgreSQL (Planned)

The database will manage:

* User information.
* Infrastructure asset details.
* Uploaded image metadata.
* Crack detection results.
* Inspection records.

### D. AI and Image Processing Module (Planned)

This module will perform:

* Image quality assessment.
* Image preprocessing.
* Crack classification.
* Crack detection.
* Crack segmentation.
* Crack geometry analysis.

## 3. System Workflow

1. User opens the InfraScan web application.
2. User selects an infrastructure image.
3. React displays an image preview.
4. The frontend sends the image to the FastAPI backend.
5. The backend validates the uploaded image.
6. The valid image is stored on the server.
7. The image processing module will prepare the image for AI analysis.
8. AI models will analyze the image and identify potential cracks or damage.
9. Analysis results will be stored in the database.
10. Results will be displayed to the user through the frontend.

## 4. Technologies Used

| Component                  | Technology                |
| -------------------------- | ------------------------- |
| Frontend                   | React.js, JavaScript, CSS |
| Backend                    | Python, FastAPI           |
| API Communication          | REST API                  |
| Image Handling             | Pillow                    |
| Database (Planned)         | PostgreSQL                |
| AI/ML (Planned)            | PyTorch / TensorFlow      |
| Image Processing (Planned) | OpenCV                    |
| Development Tools          | VS Code, Git, GitHub      |

## 5. Current Implementation Status

* React frontend initialized.
* FastAPI backend initialized.
* Frontend-backend communication configured using CORS.
* Image selection and preview implemented.
* Image upload API implemented and tested.
* Image format and file size validation implemented.
* PostgreSQL integration and AI model development are pending.

## 6. Conclusion

The initial InfraScan architecture establishes communication between the React frontend and FastAPI backend. The current implementation supports infrastructure image uploads and validation. The architecture is designed to accommodate future database integration, image preprocessing, and AI-powered crack assessment.
