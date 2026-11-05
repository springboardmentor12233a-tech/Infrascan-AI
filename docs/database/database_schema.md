# InfraScan – Database Schema Design

## 1. Introduction

The InfraScan database is designed to store user information, infrastructure asset details, inspection records, uploaded images, AI-generated damage results and maintenance activities.

PostgreSQL is selected as the planned relational database.

## 2. Database Tables

### 2.1 Users

Stores information about people using the platform.

| Field         | Description                          |
| ------------- | ------------------------------------ |
| user_id       | Primary key                          |
| full_name     | User's name                          |
| email         | Unique email address                 |
| password_hash | Hashed password                      |
| role          | Administrator, Inspector or Engineer |
| created_at    | Account creation date                |

### 2.2 Infrastructure_Assets

Stores registered infrastructure information.

| Field      | Description                   |
| ---------- | ----------------------------- |
| asset_id   | Primary key                   |
| asset_name | Infrastructure name           |
| asset_type | Road, Bridge or Building      |
| location   | Asset location                |
| material   | Construction material         |
| created_by | User who registered the asset |
| created_at | Registration date             |

### 2.3 Inspections

Stores inspection details for each infrastructure asset.

| Field           | Description                                   |
| --------------- | --------------------------------------------- |
| inspection_id   | Primary key                                   |
| asset_id        | Foreign key referencing Infrastructure_Assets |
| inspector_id    | Foreign key referencing Users                 |
| inspection_date | Date of inspection                            |
| status          | Pending, In Progress or Completed             |
| remarks         | Inspection notes                              |

### 2.4 Uploaded_Images

Stores information about images submitted for inspection.

| Field             | Description                         |
| ----------------- | ----------------------------------- |
| image_id          | Primary key                         |
| inspection_id     | Foreign key referencing Inspections |
| image_path        | Stored image location               |
| original_filename | Uploaded filename                   |
| upload_date       | Upload timestamp                    |

### 2.5 Model_Versions

Stores information about AI models used by the platform.

| Field      | Description                               |
| ---------- | ----------------------------------------- |
| model_id   | Primary key                               |
| model_name | Model name                                |
| model_type | Classification, Detection or Segmentation |
| version    | Model version                             |
| created_at | Registration date                         |

### 2.6 Damage_Assessments

Stores AI-generated inspection analysis results.

| Field            | Description                             |
| ---------------- | --------------------------------------- |
| assessment_id    | Primary key                             |
| image_id         | Foreign key referencing Uploaded_Images |
| model_id         | Foreign key referencing Model_Versions  |
| damage_type      | Identified damage category              |
| severity         | Estimated severity                      |
| confidence_score | Model confidence                        |
| assessment_date  | Analysis timestamp                      |

### 2.7 Maintenance_Tasks

Stores maintenance activities associated with inspection findings.

| Field         | Description                                   |
| ------------- | --------------------------------------------- |
| task_id       | Primary key                                   |
| asset_id      | Foreign key referencing Infrastructure_Assets |
| inspection_id | Foreign key referencing Inspections           |
| description   | Maintenance task description                  |
| priority      | Low, Medium, High or Critical                 |
| status        | Pending, In Progress or Completed             |
| due_date      | Target completion date                        |

## 3. Entity Relationships

1. One user can register multiple infrastructure assets.
2. One infrastructure asset can have multiple inspections.
3. One user can perform multiple inspections.
4. One inspection can contain multiple uploaded images.
5. One image can have multiple damage assessment records.
6. One AI model can be used for multiple assessments.
7. One infrastructure asset can have multiple maintenance tasks.

## 4. Database Design Summary

The database follows a relational structure using primary keys and foreign keys to maintain data consistency.

The schema is designed to support future project modules such as AI model management, inspection history, damage analytics, report generation and maintenance prioritization.

## 5. Current Implementation Status

This document represents the planned database schema for InfraScan. PostgreSQL database creation and application integration are separate implementation tasks and will be completed later.
