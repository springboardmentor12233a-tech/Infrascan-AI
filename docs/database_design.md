InfraScan — Database Schema

1. Overview

The InfraScan database will store user information, infrastructure assets, uploaded image details, and damage assessment results.

2. Database Tables

Table 1: Users

Stores information about registered users.

Column| Data Type| Description
user_id| INTEGER| Primary key
name| VARCHAR(100)| User's full name
email| VARCHAR(150)| User's email address
password_hash| VARCHAR(255)| Hashed password
role| VARCHAR(50)| User role
created_at| DATETIME| Account creation time

Table 2: InfrastructureAssets

Stores information about infrastructure being inspected.

Column| Data Type| Description
asset_id| INTEGER| Primary key
asset_name| VARCHAR(150)| Name of the asset
asset_type| VARCHAR(100)| Type of infrastructure
location| VARCHAR(255)| Asset location
description| TEXT| Additional details
created_by| INTEGER| Foreign key referencing Users
created_at| DATETIME| Record creation time

Table 3: AssessmentRecords

Stores image assessment and AI prediction results.

Column| Data Type| Description
assessment_id| INTEGER| Primary key
asset_id| INTEGER| Foreign key referencing InfrastructureAssets
user_id| INTEGER| Foreign key referencing Users
image_path| VARCHAR(255)| Stored image path
predicted_class| VARCHAR(50)| Predicted damage class
confidence_score| FLOAT| Model confidence score
assessment_date| DATETIME| Date of assessment
notes| TEXT| Additional assessment notes

3. Table Relationships

- One user can register multiple infrastructure assets.
- One infrastructure asset can have multiple assessment records.
- One user can create multiple assessment records.
- Each assessment record belongs to one infrastructure asset and one user.

4. Current Status

This is the proposed database design for InfraScan. Database integration and table creation are pending.