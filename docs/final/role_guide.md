# InfraScan Multi-Role Operational Guide (`role_guide.md`)

> **Core Honesty Principle**: Every screen, report, and notification displaying AI results carries the mandatory disclaimer:
> *"AI result for engineer review, not a final structural safety verdict."*
> Whenever no damage is detected by the AI models:
> *"No damage detected by the AI. This is not evidence that there is no damage."*

---

## 1. Role Governance & Architectural Overview

InfraScan is structured around five distinct roles operating collaboratively across real-time Server-Sent Events (SSE) and strict Role-Based Access Control (RBAC):

1. **System Administrator (`admin`)**
2. **Operations Manager (`manager`)**
3. **Civil Structural Engineer (`civil_engineer`)**
4. **Field Inspector (`inspector`)**
5. **Maintenance Technician (`maintenance_engineer`)**

---

## 2. Detailed Role Specifications

### 2.1 System Administrator (`admin`)
- **Primary Mission**: Ensure platform availability, enforce access governance, audit security trails, and monitor asynchronous AI pipelines.
- **Allowed Pages & Screens**:
  - `/dashboard`: High-level operational hub with "Needs your attention" alerts for failed jobs and system alerts.
  - `/users`: User lifecycle governance (create users, reassign roles, toggle active status, force password resets, revoke sessions). Changes propagate live to affected client sessions within 3 seconds.
  - `/audit-logs`: Full chronological audit log of all database mutations.
  - `/models`: AI model registry displaying YOLOv8s RDD2022, U-Net++ Crack500, and RT-DETR CodeBRIM configurations, hashes, and validation dice scores.
  - `/jobs`: Asynchronous worker queue monitor with `SKIP LOCKED` concurrency, status filters, cancel actions, and retry triggers.
- **Strict Role Boundaries (What they CANNOT do)**:
  - Cannot deactivate or demote the last remaining active administrator (enforced by backend validation).
  - Cannot approve civil structural verifications (reserved strictly for qualified civil engineers).

---

### 2.2 Operations Manager (`manager`)
- **Primary Mission**: Portfolio infrastructure asset management, geographic oversight, and inspection dispatch.
- **Allowed Pages & Screens**:
  - `/dashboard`: Operational metrics, overdue inspections counter, unassigned defect alerts.
  - `/assets`: Create and edit infrastructure assets (dams, bridges, tunnels, roads, retaining walls) with latitude, longitude, and district metadata.
  - `/map`: GIS map with severity-colored markers, clustering, district filters, and regional summary tables.
  - `/inspections`: Schedule inspections and assign them to specific field inspectors.
  - `/reports`: View and download generated inspection reports across the portfolio.
  - `/maintenance`: Track repair work order execution and portfolio maintenance velocity.
- **Strict Role Boundaries (What they CANNOT do)**:
  - Cannot upload inspection imagery (field responsibility).
  - Cannot modify AI severity ratings or certify structural damage.

---

### 2.3 Civil Structural Engineer (`civil_engineer`)
- **Primary Mission**: Authoritative review of provisional AI outputs, severity certification, priority setting, and maintenance verification.
- **Allowed Pages & Screens**:
  - `/dashboard`: Actionable "Needs your attention" review queue displaying pending severity assessments, unconfirmed priorities, and completed tasks awaiting verification.
  - `/inspections/:id`: Inspect high-resolution damage photos, YOLO defect bounding boxes, U-Net++ segmentation masks, and Grad-CAM/Grad-CAM++ attention heatmaps.
  - Multi-layer Severity Review: Confirm provisional AI assessment or correct it (comment required for correction) to set final severity.
  - Maintenance Task Dispatch: Confirm or override suggested maintenance priorities (P1-P4) and create maintenance repair tasks assigned to maintenance engineers.
  - `/maintenance`: Verify completed maintenance tasks with inspection notes, or reopen for revision.
  - `/comparisons`: Pairwise historical comparison between consecutive inspection intervals to measure crack progression and geometric change.
  - `/reports`: Generate official versioned inspection reports (PDF, CSV, Excel, JSON). Reports remain marked `DRAFT` while any assessment remains unreviewed.
- **Strict Role Boundaries (What they CANNOT do)**:
  - Cannot access administrative user management or revoke other users' sessions.

---

### 2.4 Field Inspector (`inspector`)
- **Primary Mission**: Execution of assigned field inspections and high-fidelity image capture.
- **Allowed Pages & Screens**:
  - `/dashboard`: "Needs your attention" feed showing assigned inspections awaiting upload, quality warnings, and failed analyses.
  - `/inspections`: Scoped strictly to inspections assigned to their own user ID.
  - `/upload`: Multi-file upload queue with image preview, manual rotation, and EXIF GPS parsing.
  - Automatic Analysis: With `AUTO_ANALYZE=true`, valid images automatically queue background inference and display stage progress (preprocessing -> detection -> segmentation -> measurement -> severity).
  - Inspection Completion: Mark inspection as `completed` when photo collection is finished, immediately dispatching notifications to civil engineers.
- **Strict Role Boundaries (What they CANNOT do)**:
  - Cannot view or upload photos to inspections assigned to other inspectors.
  - Cannot review, confirm, or override severity assessments.
  - Cannot create infrastructure assets or maintenance tasks.

---

### 2.5 Maintenance Technician (`maintenance_engineer`)
- **Primary Mission**: Physical repair execution of certified civil maintenance work orders.
- **Allowed Pages & Screens**:
  - `/dashboard`: "Needs your attention" feed showing open and overdue maintenance tasks assigned to them.
  - `/maintenance`: "My Tasks" view filtered to their assigned work orders (P1 Critical through P4 Routine).
  - Work Order Execution: Transition task status from `assigned` to `in_progress` upon initiating repair work.
  - Work Order Completion: Transition task to `completed` and submit resolution notes detailing epoxy sealing, mortar patching, materials, and field observations.
- **Strict Role Boundaries (What they CANNOT do)**:
  - Cannot verify their own completed tasks (mandatory civil engineer verification gate).
  - Cannot reassign tasks to other technicians or modify engineering priorities.

---

## 3. Real-Time Inter-Role Effects Matrix

| Triggering Action | Actor Role | Real-Time Live Effect | Target Audience |
|---|---|---|---|
| Schedule Inspection | Manager | In-app notification & inspection appears in list | Assigned Inspector |
| Complete Inspection | Inspector | In-app notification: *"qualified engineering review required"* | Civil Engineers |
| Confirm Severity | Civil Engineer | Map marker recolored & provisional flag cleared | Manager, Admin, Engineers |
| Create Maintenance Task | Civil Engineer | In-app notification: *"New Maintenance Task Assigned"* | Assigned Maintenance Engineer |
| Complete Maintenance Task | Maintenance Eng | In-app notification: *"Verification Required"* | Civil Engineers |
| Verify Maintenance Task | Civil Engineer | Task marked `verified`, asset history updated | Manager, Maintenance Eng |
| Generate Report | Civil Engineer | `report.ready` notification with download links | Requester & Managers |
| Reassign / Revoke User | Admin | Instant permission refresh or session logout | Affected User Browser |
