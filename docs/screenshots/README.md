# InfraScan Application Screenshots Index

This directory contains genuine, high-resolution visual evidence captured directly from the live running InfraScan platform (FastAPI backend + Vite/React frontend + SQLite database) in November 2026.

All screenshots depict actual system pages, real database entities, and live AI computer-vision analysis outputs without mocks or synthetic placeholders. Sensitive credentials and secrets are excluded.

---

## Screenshot Inventory & Descriptions

| Filename | Platform View | Role / Access | Key Features & Functional Evidence |
|---|---|:---:|---|
| **`01_login_page.png`** | Authentication Portal | Public | Dual-role authentication form with username/password inputs, branded layout, and link to inspector registration. |
| **`02_registration_page.png`** | Inspector Registration | Public | Multi-field user registration form (`username`, `email`, `full_name`, `password`). Intercepts client-side role privilege escalation. |
| **`03_user_dashboard.png`** | User Dashboard | Registered User | Inspector workspace displaying personal inspection metrics (`Total Inspections`, `Cracked Surfaces`, `Critical Reviews`), account badge, and recent activity table. |
| **`04_new_inspection_form.png`** | Inspection Upload | Registered User | Multipart file upload interface with asset selection, custom inspector notes, geolocation binding, and drag-and-drop concrete photo input. |
| **`05_inspection_history.png`** | User Inspection History | Registered User | User-isolated table of historical civil inspections showing thumbnail previews, asset names, timestamps, defect status, area metrics, and detail links. |
| **`06_inspection_detail_overview.png`** | Inspection Detail Suite | User / Admin | Comprehensive inspection analysis suite (Inspection #41) showing severity badge, priority level, metadata, and interactive multi-model visualization pane. |
| **`07_crack_geometry_severity.png`** | Geometry & Severity Engine | User / Admin | Quantitative crack geometry extraction metrics (`crack_area_px`, `skeleton_length_px`, `mean_width_px`, `orientation_angle`, topology) and deterministic severity scoring card. |
| **`08_gradcam_overlay.png`** | Explainable AI (Grad-CAM) | User / Admin | Class activation saliency heatmap indicating high-activation concrete regions utilized by convolutional feature extractors for damage localization. |
| **`09_model_comparison.png`** | Model Evaluation & Benchmarks| Administrator | Academic model comparison matrix detailing architectures (CNN Classifier, YOLO11 Object Detector, U-Net Segmentor), historical training metrics, and local deployment provenance. |
| **`10_admin_dashboard.png`** | Admin System Overview | Administrator | Executive platform overview aggregating system-wide metrics: 15 total registered users, 46 total inspections, cracked surface ratios, and system health status. |
| **`11_admin_user_management.png`** | User Lifecycle Registry | Administrator | Administrative user management table with search filters, role badges (`admin` vs `user`), active/inactive status pills, and interactive deactivation/reactivation toggles. |
| **`12_admin_system_inspections.png`**| System-Wide Inspections | Administrator | Cross-tenant administrative oversight table showing all inspections conducted across all registered user accounts with filtering and direct report access. |
| **`13_assets_inventory.png`** | Infrastructure Assets | User / Admin | Civil asset registry (bridges, tunnels, retaining walls, highway piers) with GPS coordinates, structural types, and inspection count tracking. |
| **`14_geospatial_map.png`** | Geospatial Damage Map | User / Admin | Interactive OpenStreetMap/Leaflet geospatial visualization plotting asset markers, localized damage clusters, and structural coordinates. |
| **`15_hairline_defect_assessment.png`**| Hairline Defect Assessment| User / Admin | Detailed inspection view for hairline fracture defect (#45, score 80.0/100, Severe Damage) exhibiting narrow aperture (3.3px) with dense multi-trajectory branching (829 branches). |
| **`16_pdf_report.png`** | Formal Engineering PDF Export| Authenticated | Rendered first page of generated binary PDF inspection report (`ReportLab 3.0+`) displaying project metadata, defect metrics, embedded photo overlays, and legal structural disclaimer. |
| **`17_csv_report_preview.png`** | Structured CSV Data Export | Authenticated | Rendered structured view of the 41-line CSV inspection data export, encapsulating all tabular metadata, crack geometry, severity score, and recommended engineering action plan. |

---

## Verification & Authenticity Notice
- **Backend Host**: `http://127.0.0.1:8000` (FastAPI 2.0.0)
- **Frontend Host**: `http://127.0.0.1:5173` (React 18 + Vite SPA)
- **Capture Method**: Automated headless browser automation via Playwright / Microsoft Edge with authenticated session states and clean viewport rendering (1440x900).
