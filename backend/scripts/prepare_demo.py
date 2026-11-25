#!/usr/bin/env python3
"""
InfraScan Demo Environment Preparation Script
Prepares a clean, realistic, and predictable demonstration environment for evaluations
and live presentations.

Seeds:
1. 5 Role accounts (Inspector, Civil Engineer, Maintenance Engineer, Operations Manager, Administrator)
2. Chennai infrastructure assets with accurate GPS coordinates
3. Scheduled and completed inspections with photographic damage samples
4. Automated damage analyses with detections, crack measurements, and XAI heatmaps
5. Provisional severity assessments and maintenance work orders (P1-P4)
6. Historical baseline-vs-followup inspection comparison

All created demo records are tagged in the `demo_markers` table for easy identification
and clean uninstallation.
"""

from datetime import datetime, date, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from PIL import Image as PILImage, ImageDraw

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.models.user import User
from app.models.asset import InfrastructureAsset
from app.models.inspection import Inspection
from app.models.image import Image as ImageModel
from app.models.analysis import AnalysisRun, Detection, CrackMeasurement, ImageScale, ModelVersion
from app.models.severity import SeverityAssessment, InspectionSeverity
from app.models.maintenance import MaintenancePriority, MaintenanceTask
from app.models.comparison import InspectionComparison, ImageComparison
from app.models.demo import DemoMarker
from app.services.security import hash_password
from app.config import settings


def mark_demo(db, table_name: str, record_id: int):
    """Register record in demo_markers table."""
    try:
        marker = DemoMarker(table_name=table_name, record_id=record_id)
        db.add(marker)
        db.commit()
    except Exception:
        db.rollback()


def create_synthetic_demo_image(filepath: Path, draw_crack: bool = True):
    """Create a realistic demo image (640x480) with synthetic crack or clean concrete."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    img = PILImage.new("RGB", (640, 480), color=(180, 182, 185))
    draw = ImageDraw.Draw(img)

    import random
    rng = random.Random(42)
    for _ in range(5000):
        x = rng.randint(0, 639)
        y = rng.randint(0, 479)
        shade = rng.randint(150, 210)
        draw.point((x, y), fill=(shade, shade, shade))

    if draw_crack:
        points = [(120, 80), (180, 140), (230, 190), (290, 240), (340, 310), (410, 390)]
        for i in range(len(points) - 1):
            draw.line([points[i], points[i+1]], fill=(40, 40, 45), width=3)
        draw.line([(290, 240), (330, 220), (380, 215)], fill=(50, 50, 55), width=2)

    img.save(filepath, format="JPEG", quality=90)


def prepare_demo():
    print("=" * 70)
    print(" InfraScan Live Demo Environment Provisioner")
    print("=" * 70)

    db = SessionLocal()
    try:
        # 1. Demo Users
        print("[1/6] Seeding 5 role-based demonstration accounts...")
        demo_users = [
            ("inspector@demo.infrascan.local", "Priya Sharma", "inspector"),
            ("engineer@demo.infrascan.local", "Dr. Rajesh Kumar, PE", "civil_engineer"),
            ("maintenance@demo.infrascan.local", "Suresh Menon", "maintenance_engineer"),
            ("manager@demo.infrascan.local", "Ananya Deshmukh", "manager"),
            ("admin@demo.infrascan.local", "Chief Systems Admin", "admin"),
        ]

        user_objects = {}
        for email, name, role in demo_users:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    password_hash=hash_password("DemoPassword2026!"),
                    full_name=name,
                    role=role,
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                mark_demo(db, "users", user.user_id)
            user_objects[role] = user
        print("      [+] Accounts active for all 5 roles. Default password: DemoPassword2026!")

        # 2. Demo Assets
        print("[2/6] Provisioning critical civil infrastructure assets...")
        assets_data = [
            {
                "name": "Kathipara Flyover Span C-4",
                "asset_type": "bridge",
                "importance_level": "high",
                "material_type": "concrete",
                "latitude": 13.0067,
                "longitude": 80.2025,
                "construction_year": 2008,
                "responsible_department": "National Highways Authority",
                "inspection_frequency_days": 90,
                "district": "Chennai",
                "address": "Kathipara Junction, Guindy, Chennai",
            },
            {
                "name": "NH-48 Corridor Km 42+500",
                "asset_type": "road",
                "importance_level": "high",
                "material_type": "asphalt",
                "latitude": 12.9810,
                "longitude": 80.1245,
                "construction_year": 2014,
                "responsible_department": "State Highways Dept",
                "inspection_frequency_days": 180,
                "district": "Sriperumbudur",
                "address": "NH-48 Corridor, Chennai Outer",
            },
            {
                "name": "Metro Viaduct Pillar P-112",
                "asset_type": "bridge",
                "importance_level": "high",
                "material_type": "concrete",
                "latitude": 13.0418,
                "longitude": 80.2341,
                "construction_year": 2019,
                "responsible_department": "Chennai Metro Rail Ltd",
                "inspection_frequency_days": 120,
                "district": "Chennai",
                "address": "Anna Salai, Teynampet, Chennai",
            },
        ]

        asset_objects = []
        for a_data in assets_data:
            existing = db.query(InfrastructureAsset).filter(InfrastructureAsset.name == a_data["name"]).first()
            if not existing:
                asset = InfrastructureAsset(**a_data, created_by=user_objects["manager"].user_id)
                db.add(asset)
                db.commit()
                db.refresh(asset)
                mark_demo(db, "infrastructure_assets", asset.asset_id)
                asset_objects.append(asset)
            else:
                asset_objects.append(existing)
        print(f"      [+] {len(asset_objects)} assets ready in GIS database.")

        # 3. Demo Inspections
        print("[3/6] Scheduling field inspections...")
        primary_asset = asset_objects[0]
        today = date.today()

        # Baseline Inspection (90 days ago)
        base_insp = db.query(Inspection).filter(
            Inspection.asset_id == primary_asset.asset_id,
            Inspection.inspection_date == today - timedelta(days=90),
        ).first()
        if not base_insp:
            base_insp = Inspection(
                asset_id=primary_asset.asset_id,
                inspector_id=user_objects["inspector"].user_id,
                inspection_date=today - timedelta(days=90),
                status="completed",
            )
            db.add(base_insp)
            db.commit()
            db.refresh(base_insp)
            mark_demo(db, "inspections", base_insp.inspection_id)

        # Recent Inspection (Today)
        recent_insp = db.query(Inspection).filter(
            Inspection.asset_id == primary_asset.asset_id,
            Inspection.inspection_date == today,
        ).first()
        if not recent_insp:
            recent_insp = Inspection(
                asset_id=primary_asset.asset_id,
                inspector_id=user_objects["inspector"].user_id,
                inspection_date=today,
                status="completed",
            )
            db.add(recent_insp)
            db.commit()
            db.refresh(recent_insp)
            mark_demo(db, "inspections", recent_insp.inspection_id)

        # Clean Asset Inspection (Pillar P-112)
        clean_asset = asset_objects[2]
        clean_insp = db.query(Inspection).filter(
            Inspection.asset_id == clean_asset.asset_id,
            Inspection.inspection_date == today,
        ).first()
        if not clean_insp:
            clean_insp = Inspection(
                asset_id=clean_asset.asset_id,
                inspector_id=user_objects["inspector"].user_id,
                inspection_date=today,
                status="completed",
            )
            db.add(clean_insp)
            db.commit()
            db.refresh(clean_insp)
            mark_demo(db, "inspections", clean_insp.inspection_id)

        # 4. Images & Synthetic Damage
        print("[4/6] Creating demo inspection imagery...")
        upload_dir = settings.upload_path

        # Baseline Image
        base_img_path = upload_dir / str(base_insp.inspection_id) / "kathipara_span_c4_baseline.jpg"
        if not base_img_path.exists():
            create_synthetic_demo_image(base_img_path, draw_crack=True)

        base_img = db.query(ImageModel).filter(ImageModel.inspection_id == base_insp.inspection_id).first()
        if not base_img:
            base_img = ImageModel(
                inspection_id=base_insp.inspection_id,
                uploaded_by=user_objects["inspector"].user_id,
                file_path=str(base_img_path.relative_to(settings.storage_path.resolve())),
                original_filename="kathipara_span_c4_baseline.jpg",
                file_hash=hashlib.sha256(base_img_path.read_bytes()).hexdigest(),
                width_px=640,
                height_px=480,
                file_size_bytes=base_img_path.stat().st_size,
                source="camera",
                gps_latitude=13.0067,
                gps_longitude=80.2025,
                captured_at=datetime.now(timezone.utc) - timedelta(days=90),
                blur_score=142.5,
                brightness_score=178.0,
                quality_status="passed",
                quality_notes="Optimal lighting, sharp focus",
            )
            db.add(base_img)
            db.commit()
            db.refresh(base_img)
            mark_demo(db, "images", base_img.image_id)

        # Recent Image with Longitudinal Crack
        rec_img_path = upload_dir / str(recent_insp.inspection_id) / "kathipara_span_c4_recent.jpg"
        if not rec_img_path.exists():
            create_synthetic_demo_image(rec_img_path, draw_crack=True)

        rec_img = db.query(ImageModel).filter(ImageModel.inspection_id == recent_insp.inspection_id).first()
        if not rec_img:
            rec_img = ImageModel(
                inspection_id=recent_insp.inspection_id,
                uploaded_by=user_objects["inspector"].user_id,
                file_path=str(rec_img_path.relative_to(settings.storage_path.resolve())),
                original_filename="kathipara_span_c4_recent.jpg",
                file_hash=hashlib.sha256(rec_img_path.read_bytes()).hexdigest(),
                width_px=640,
                height_px=480,
                file_size_bytes=rec_img_path.stat().st_size,
                source="camera",
                gps_latitude=13.0067,
                gps_longitude=80.2025,
                captured_at=datetime.now(timezone.utc),
                blur_score=156.2,
                brightness_score=181.4,
                quality_status="passed",
                quality_notes="Optimal lighting",
            )
            db.add(rec_img)
            db.commit()
            db.refresh(rec_img)
            mark_demo(db, "images", rec_img.image_id)

        # Clean Image (No damage)
        clean_img_path = upload_dir / str(clean_insp.inspection_id) / "pillar_p112_clean.jpg"
        if not clean_img_path.exists():
            create_synthetic_demo_image(clean_img_path, draw_crack=False)

        clean_img = db.query(ImageModel).filter(ImageModel.inspection_id == clean_insp.inspection_id).first()
        if not clean_img:
            clean_img = ImageModel(
                inspection_id=clean_insp.inspection_id,
                uploaded_by=user_objects["inspector"].user_id,
                file_path=str(clean_img_path.relative_to(settings.storage_path.resolve())),
                original_filename="pillar_p112_clean.jpg",
                file_hash=hashlib.sha256(clean_img_path.read_bytes()).hexdigest(),
                width_px=640,
                height_px=480,
                file_size_bytes=clean_img_path.stat().st_size,
                source="camera",
                gps_latitude=13.0418,
                gps_longitude=80.2341,
                captured_at=datetime.now(timezone.utc),
                blur_score=165.0,
                brightness_score=175.0,
                quality_status="passed",
                quality_notes="Pristine condition",
            )
            db.add(clean_img)
            db.commit()
            db.refresh(clean_img)
            mark_demo(db, "images", clean_img.image_id)

        # Scale calibration on Recent Image (1 px = 0.5 mm -> mm_per_pixel = 0.5)
        scale = db.query(ImageScale).filter(ImageScale.image_id == rec_img.image_id).first()
        if not scale:
            scale = ImageScale(
                image_id=rec_img.image_id,
                method="reference_object",
                mm_per_pixel=0.5,
                reference_mm=50.0,
                reference_px=100.0,
                point1_x=10.0,
                point1_y=10.0,
                point2_x=110.0,
                point2_y=10.0,
                camera_perpendicular=True,
                uncertainty_percent=4.2,
                is_current=True,
                set_by=user_objects["civil_engineer"].user_id,
            )
            db.add(scale)
            db.commit()
            db.refresh(scale)
            mark_demo(db, "image_scales", scale.scale_id)

        # 5. Analysis Run, Detections, Measurements & Severity
        print("[5/6] Registering deep learning analysis run & geometric measurements...")
        arun = db.query(AnalysisRun).filter(AnalysisRun.image_id == rec_img.image_id).first()
        if not arun:
            arun = AnalysisRun(
                image_id=rec_img.image_id,
                status="done",
                started_at=datetime.now(timezone.utc) - timedelta(seconds=2),
                finished_at=datetime.now(timezone.utc),
                seconds=0.184,
                image_scale_note="Calibrated with 50mm reference marker (0.50 mm/px +/- 4.2%)",
            )
            db.add(arun)
            db.commit()
            db.refresh(arun)
            mark_demo(db, "analysis_runs", arun.run_id)

            # Detections
            det1 = Detection(
                run_id=arun.run_id,
                model_id="yolov8s_rdd2022",
                damage_type="D00",
                damage_label="Longitudinal Crack",
                confidence=0.884,
                x_min=110.0,
                y_min=75.0,
                x_max=425.0,
                y_max=405.0,
            )
            db.add(det1)
            db.commit()

            # Crack Measurement
            meas = CrackMeasurement(
                run_id=arun.run_id,
                mask_path="storage/masks/demo_kathipara_mask.png",
                threshold=0.40,
                crack_pixels=1240,
                length_px=380.5,
                avg_width_px=3.2,
                max_width_px=6.4,
                p95_width_px=5.8,
                area_px=1240,
                density_percent=0.40,
                orientation_deg=48.5,
                num_components=1,
                num_branch_points=1,
                num_end_points=3,
                mm_per_pixel=0.5,
                length_mm=190.25,
                avg_width_mm=1.60,
                max_width_mm=3.20,
                width_mode="edt2",
                scale_id=scale.scale_id,
                length_mm_uncertainty=7.99,
                width_mm_uncertainty=0.13,
                measurement_note="Measured with calibrated reference marker",
            )
            db.add(meas)
            db.commit()

            # Severity Assessment (Critical)
            sev = SeverityAssessment(
                run_id=arun.run_id,
                image_id=rec_img.image_id,
                severity_level="critical",
                score=88.5,
                priority_suggestion="P1",
                factors_json=json.dumps({
                    "max_width_mm": 3.20,
                    "crack_length_mm": 190.25,
                    "asset_importance": "high",
                    "damage_classes": ["D00 - Longitudinal Crack"],
                    "rules_triggered": ["R-WIDTH-CRITICAL-3MM", "R-ASSET-HIGH-IMPORTANCE"],
                }),
                warnings_json=json.dumps(["Crack width exceeds 2.0 mm structural threshold"]),
                rules_version="2026.1",
                rules_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                review_status="confirmed",
                reviewed_by=user_objects["civil_engineer"].user_id,
                reviewed_at=datetime.now(timezone.utc),
                final_severity="critical",
                final_priority="P1",
                review_comment="Confirmed during visual walk-through; epoxy injection required.",
                is_superseded=False,
            )
            db.add(sev)
            db.commit()

            # Inspection Severity Rollup
            insp_sev = InspectionSeverity(
                inspection_id=recent_insp.inspection_id,
                worst_severity="critical",
                worst_score=88.5,
                images_assessed=1,
                images_pending_review=0,
                summary_json=json.dumps({"critical": 1, "high": 0, "medium": 0, "low": 0}),
            )
            db.add(insp_sev)
            db.commit()

        # Clean Analysis Run (No damage detected)
        clean_arun = db.query(AnalysisRun).filter(AnalysisRun.image_id == clean_img.image_id).first()
        if not clean_arun:
            clean_arun = AnalysisRun(
                image_id=clean_img.image_id,
                status="done",
                started_at=datetime.now(timezone.utc) - timedelta(seconds=1),
                finished_at=datetime.now(timezone.utc),
                seconds=0.112,
                image_scale_note="No scale calibrated",
            )
            db.add(clean_arun)
            db.commit()
            mark_demo(db, "analysis_runs", clean_arun.run_id)

        # 6. Maintenance Work Order & Historical Comparison
        print("[6/6] Generating maintenance work orders & historical image progression...")
        prio = db.query(MaintenancePriority).filter(MaintenancePriority.asset_id == primary_asset.asset_id).first()
        if not prio:
            prio = MaintenancePriority(
                asset_id=primary_asset.asset_id,
                inspection_id=recent_insp.inspection_id,
                suggested_priority="P1",
                final_priority="P1",
                provisional=False,
                factors_json=json.dumps({"worst_severity": "critical", "importance": "high"}),
                status="confirmed",
                reviewed_by=user_objects["civil_engineer"].user_id,
                reviewed_at=datetime.now(timezone.utc),
                review_comment="Prioritized for immediate structural repair",
            )
            db.add(prio)
            db.commit()
            db.refresh(prio)
            mark_demo(db, "maintenance_priorities", prio.priority_id)

        task = db.query(MaintenanceTask).filter(MaintenanceTask.asset_id == primary_asset.asset_id).first()
        if not task:
            task = MaintenanceTask(
                asset_id=primary_asset.asset_id,
                inspection_id=recent_insp.inspection_id,
                priority_id=prio.priority_id,
                title="Epoxy Pressure Grouting — Span C-4 Longitudinal Crack",
                description="Perform epoxy pressure injection and structural polyurethane sealing on 3.2mm crack.",
                task_type="repair",
                priority="P1",
                status="open",
                assigned_to=user_objects["maintenance_engineer"].user_id,
                created_by=user_objects["civil_engineer"].user_id,
                due_date=today + timedelta(days=7),
            )
            db.add(task)
            db.commit()
            mark_demo(db, "maintenance_tasks", task.task_id)

        # Historical Comparison between Baseline and Recent Inspection
        insp_comp = db.query(InspectionComparison).filter(
            InspectionComparison.asset_id == primary_asset.asset_id,
            InspectionComparison.prev_inspection_id == base_insp.inspection_id,
            InspectionComparison.curr_inspection_id == recent_insp.inspection_id,
        ).first()
        if not insp_comp:
            insp_comp = InspectionComparison(
                asset_id=primary_asset.asset_id,
                prev_inspection_id=base_insp.inspection_id,
                curr_inspection_id=recent_insp.inspection_id,
                created_by=user_objects["civil_engineer"].user_id,
                summary_json=json.dumps({
                    "crack_growth_detected": True,
                    "max_width_delta_mm": 0.8,
                    "status": "active_deterioration",
                }),
            )
            db.add(insp_comp)
            db.commit()
            db.refresh(insp_comp)
            mark_demo(db, "inspection_comparisons", insp_comp.comparison_id)

            img_comp = ImageComparison(
                comparison_id=insp_comp.comparison_id,
                prev_image_id=base_img.image_id,
                curr_image_id=rec_img.image_id,
                status="ok",
                inliers=245,
                inlier_ratio=0.82,
                reprojection_rmse=1.24,
                overlap_share=0.91,
                metrics_json=json.dumps({
                    "crack_pixels_delta": 310,
                    "growth_percentage": 24.5,
                }),
            )
            db.add(img_comp)
            db.commit()
            mark_demo(db, "image_comparisons", img_comp.id)

        print("=" * 70)
        print(" Demo Environment Ready!")
        print("=" * 70)
        print(" Logins (Password: DemoPassword2026!):")
        print("  - Inspector:            inspector@demo.infrascan.local")
        print("  - Civil Engineer:       engineer@demo.infrascan.local")
        print("  - Maintenance Engineer: maintenance@demo.infrascan.local")
        print("  - Operations Manager:   manager@demo.infrascan.local")
        print("  - System Administrator: admin@demo.infrascan.local")
        print("=" * 70)
        return 0
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Demo provisioning failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(prepare_demo())
