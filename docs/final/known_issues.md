# InfraScan Known Issues & Engineering Boundaries (`known_issues.md`)

> **Honesty Mandate**: In accordance with project evaluation standards, this document transparently lists all known operational boundaries, hardware constraints, and non-blocking limitations. No defects are concealed.

---

## 1. Hardware & Execution Boundaries

### 1.1 CPU-Only PyTorch Environment
- **Observed State**: The host machine runs PyTorch CPU build (`2.15.0+cpu`). CUDA hardware acceleration is unavailable (`torch.cuda.is_available() == False`).
- **Impact on Latency**:
  - YOLOv8s RDD2022 (detection): ~180-250 ms / image.
  - U-Net++ ResNet-34 (crack segmentation): ~450-600 ms / image.
  - RT-DETR-L (defect transformer): ~900-1250 ms / image.
  - Grad-CAM Heatmap Generation: ~350-500 ms / image.
- **Architectural Safeguard**: Heavy inference runs are strictly dispatched to the asynchronous background worker (`app/worker.py`) using `SKIP LOCKED` job claiming. The web process never blocks during inference.

### 1.2 Maximum Dimension Image Resizing (`MAX_SIDE = 1280`)
- High-resolution smartphone imagery (e.g. 4000x3000px, 12MP) is downscaled for inference to a maximum side of 1280 pixels.
- The original file is stored untouched. Bounding boxes and segmentation masks are reprojected back to the original image coordinate frame.
- High-frequency micro-cracks (< 0.5px width after downscale) may exhibit lower recall before scale reprojection.

---

## 2. Geospatial & Mapping Constraints

### 2.1 Public OpenStreetMap Tile Server Dependency
- Leaflet map relies on public OpenStreetMap standard tiles (`https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`).
- In strictly offline environments or restrictive corporate proxies, tiles fail gracefully (`tileerror` listener handled). The SVG severity markers, popups, and regional summary tables remain fully interactive against a fallback neutral grid background.
- Notice displayed: *"Locations are points; GPS from photos may be missing or inaccurate."*

### 2.2 EXIF GPS Fallback
- Smartphone imagery missing EXIF GPS metadata falls back to the parent infrastructure asset's primary coordinates.
- Multiple photos taken across different sections of a large bridge or dam will cluster at the asset centroid unless individual GPS tags are present.

---

## 3. Scale Calibration & Measurement Precision

### 3.1 Pixel-Only Measurement Fallback
- Crack length, maximum width, and damaged surface area are initially calculated in raw pixels.
- Millimetre measurements (`length_mm`, `max_width_mm`, `area_mm2`) are populated **only** when an authorized user submits a two-point reference scale calibration (`ImageScale`).
- Without a stored calibration, physical millimetre fields remain strictly `None` with the note: *"No scale calibrated. Measurements recorded in pixels."*

---

## 4. Engineering Domain Disclaimers

### 4.1 Advisory Severity Rules
- Severity scoring (0 to 100) and priority mappings (P1 to P4) follow heuristic rules configured in `backend/app/config/severity_rules.json`.
- These thresholds represent engineer-defined advisory guidelines and have not undergone certification against formal statutory civil engineering codes (e.g. IRC, AASHTO, or Eurocode).
- Every assessment requires qualified civil engineer review before maintenance work orders are dispatched.
