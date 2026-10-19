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

Initial project structure created. Dataset research and EDA are the next steps.

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
