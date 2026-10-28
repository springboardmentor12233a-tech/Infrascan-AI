InfraScan — UI Wireframes

1. Purpose

The user interface will allow users to upload infrastructure images and manage damage assessment activities.

2. Main Pages

Page 1: Login and Registration

- Email and password fields
- Login and registration options
- Role-based access for authorized users

Page 2: Dashboard

- Overview of infrastructure assets
- Number of uploaded images
- Recent assessment records
- Navigation to other pages

Page 3: Infrastructure Asset Management

- Add a new infrastructure asset
- View saved assets
- Store asset name, type, location, and description

Page 4: Image Upload

- Select an image from the device
- Preview the selected image
- Upload the image to the backend
- Display upload status and validation messages

Page 5: Damage Assessment Results

- Display the uploaded image
- Show predicted defect category when AI prediction is available
- Display confidence score when available
- Show assessment history

3. Design Guidelines

- Use a clean white background.
- Use blue as the primary accent color.
- Keep navigation simple and consistent.
- Show clear success and error messages.
- Make pages usable on desktop and mobile screens.

4. Current Status

The initial React frontend includes a basic image upload interface with image preview and upload status messages.

The dashboard, authentication pages, asset management pages, and AI assessment results page are planned features and require implementation or verification.



5. Visual Layout Plan

Image Upload Page

- Header with InfraScan branding.
- Main heading and short description.
- Centered upload card with image selection, preview, and upload button.
- Assessment result message below the upload form.
- Footer note reminding users that engineering review is required.

Dashboard Page

- Header and navigation.
- Summary cards for infrastructure assets, uploaded images, and recent assessments.
- List of recent assessment records.

Login and Registration Page

- Centered form card.
- Email and password fields.
- Login and registration actions.

Infrastructure Asset Management Page

- Asset list or table.
- Button to add a new asset.
- Form fields for asset name, type, location, and description.

Damage Assessment Results Page

- Uploaded image preview.
- Predicted defect category and confidence score when available.
- Assessment date and history.

Note: The Image Upload page has an initial implementation. The other page layouts are planned and require implementation or verification.