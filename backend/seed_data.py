import sys, os
import os
import cv2
import numpy as np
from datetime import datetime, timedelta
from database import SessionLocal, engine, Base
from models import Asset, Inspection, InspectionResult
from services.geometry import extract_crack_geometry
from services.severity import assess_damage_severity
from services.priority import determine_maintenance_priority
from services.gradcam import generate_gradcam_visualization

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(Asset).count() > 0:
        print("Database already contains assets. Skipping seed.")
        db.close()
        return

    print("Seeding initial infrastructure assets and demo inspections...")

    # Real-world styled infrastructure assets with valid GPS coordinates
    assets = [
        Asset(
            name="Yamuna Expressway Flyover P14",
            type="Bridge",
            location_name="Noida-Greater Noida Expwy, Sector 128",
            latitude=28.5355,
            longitude=77.3910,
            construction_year=2012,
            material_type="Prestressed Concrete Box Girder",
            responsible_dept="National Highways Division"
        ),
        Asset(
            name="Old Yamuna Rail-cum-Road Bridge Pier 7",
            type="Bridge",
            location_name="Kashmere Gate, Delhi",
            latitude=28.6675,
            longitude=77.2433,
            construction_year=1866,
            material_type="Masonry & Reinforced Concrete Substructure",
            responsible_dept="Northern Railway Infrastructure"
        ),
        Asset(
            name="NH-48 Gurugram Elevated Corridor Pier 102",
            type="Road",
            location_name="Cyber City, Gurugram",
            latitude=28.4986,
            longitude=77.0878,
            construction_year=2019,
            material_type="Reinforced Concrete Pier",
            responsible_dept="NHAI Maintenance Wing"
        ),
        Asset(
            name="Pragati Maidan Tunnel Portal South",
            type="Tunnel",
            location_name="Ring Road, New Delhi",
            latitude=28.6180,
            longitude=77.2450,
            construction_year=2022,
            material_type="Shotcrete & Precast Concrete Lining",
            responsible_dept="Delhi PWD Civil Dept"
        ),
        Asset(
            name="SMASH Lab Structural Concrete Wall",
            type="Wall",
            location_name="SMASH Testing Laboratory",
            latitude=41.7431,
            longitude=-111.8139,
            construction_year=2018,
            material_type="Portland Cement Concrete (SDNET Benchmark)",
            responsible_dept="Structural Health Lab"
        )
    ]

    for a in assets:
        db.add(a)
    db.commit()

    # Generate synthetic benchmark demonstration images with real crack patterns
    base_storage = os.environ.get(
    "INFRASCAN_STORAGE_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
    upload_dir = os.path.join(base_storage, "uploads")
    results_dir = os.path.join(base_storage, "results")
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    demo_scenarios = [
        {
            "asset_idx": 0,
            "name": "demo_pier14_longitudinal_crack.jpg",
            "has_crack": True,
            "pattern": "longitudinal",
            "date": datetime.utcnow() - timedelta(days=45),
            "notes": "Longitudinal flexural crack observed along lower soffit."
        },
        {
            "asset_idx": 0,
            "name": "demo_pier14_followup_expanded.jpg",
            "has_crack": True,
            "pattern": "expanded_longitudinal",
            "date": datetime.utcnow() - timedelta(days=3),
            "notes": "Follow-up monitoring: apparent widening and crack extension detected."
        },
        {
            "asset_idx": 1,
            "name": "demo_yamuna_pier_severe_alligator.jpg",
            "has_crack": True,
            "pattern": "alligator",
            "date": datetime.utcnow() - timedelta(days=12),
            "notes": "High moisture zone with multi-directional alligator cracking and spalling risk."
        },
        {
            "asset_idx": 2,
            "name": "demo_corridor_pier_sound.jpg",
            "has_crack": False,
            "pattern": "sound",
            "date": datetime.utcnow() - timedelta(days=20),
            "notes": "Routine inspection: surface in sound state with no visible fractures."
        },
        {
            "asset_idx": 3,
            "name": "demo_tunnel_lining_hairline.jpg",
            "has_crack": True,
            "pattern": "hairline",
            "date": datetime.utcnow() - timedelta(days=8),
            "notes": "Minor transverse hairline shrinkage crack on crown lining."
        }
    ]

    for s in demo_scenarios:
        # Create 512x512 concrete texture image
        np.random.seed(42 + len(s["name"]))
        img = np.random.normal(160, 15, (512, 512)).astype(np.uint8)
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        # Add concrete aggregate variations
        for _ in range(80):
            pt = (np.random.randint(0, 512), np.random.randint(0, 512))
            cv2.circle(img, pt, np.random.randint(1, 4), (120, 120, 120), -1)

        mask = np.zeros((512, 512), dtype=np.uint8)

        if s["pattern"] == "longitudinal":
            pts = np.array([[80, 100], [180, 220], [300, 310], [420, 440]], np.int32)
            cv2.polylines(img, [pts], False, (40, 40, 40), 4)
            cv2.polylines(mask, [pts], False, 255, 6)
        elif s["pattern"] == "expanded_longitudinal":
            pts = np.array([[60, 80], [170, 210], [310, 320], [450, 480]], np.int32)
            branch = np.array([[170, 210], [240, 180], [320, 190]], np.int32)
            cv2.polylines(img, [pts], False, (25, 25, 25), 7)
            cv2.polylines(img, [branch], False, (30, 30, 30), 4)
            cv2.polylines(mask, [pts], False, 255, 9)
            cv2.polylines(mask, [branch], False, 255, 6)
        elif s["pattern"] == "alligator":
            for _ in range(12):
                p1 = (np.random.randint(100, 400), np.random.randint(100, 400))
                p2 = (p1[0] + np.random.randint(-60, 60), p1[1] + np.random.randint(-60, 60))
                cv2.line(img, p1, p2, (35, 35, 35), 3)
                cv2.line(mask, p1, p2, 255, 5)
        elif s["pattern"] == "hairline":
            pts = np.array([[200, 50], [220, 250], [210, 450]], np.int32)
            cv2.polylines(img, [pts], False, (80, 80, 80), 1)
            cv2.polylines(mask, [pts], False, 255, 2)

        # Save image
        img_path = os.path.join(upload_dir, s["name"])
        cv2.imwrite(img_path, img)

        # Mask and overlay
        mask_path = os.path.join(results_dir, f"mask_{s['name']}.png")
        overlay_path = os.path.join(results_dir, f"overlay_{s['name']}.png")
        cv2.imwrite(mask_path, mask)

        overlay = img.copy()
        crack_px = mask > 127
        overlay[crack_px] = (overlay[crack_px].astype(float) * 0.35 + np.array([0, 0, 255], dtype=float) * 0.65).astype(np.uint8)
        cv2.imwrite(overlay_path, overlay)

        # Grad-CAM
        gradcam_path = os.path.join(results_dir, f"gradcam_{s['name']}.png")
        generate_gradcam_visualization(img, s["has_crack"], mask, gradcam_path)

        # Geometry & Severity
        geom = extract_crack_geometry(mask)
        sev = assess_damage_severity(s["has_crack"], geom, defect_count=1 if s["has_crack"] else 0)
        target_asset = assets[s["asset_idx"]]
        prio = determine_maintenance_priority(sev, target_asset.type)

        insp = Inspection(
            asset_id=target_asset.id,
            image_filename=s["name"],
            original_image_path=img_path,
            timestamp=s["date"],
            inspector_name="Senior Civil Inspector",
            notes=s["notes"],
            latitude=target_asset.latitude,
            longitude=target_asset.longitude,
            location_source="asset_default"
        )
        db.add(insp)
        db.commit()
        db.refresh(insp)

        res = InspectionResult(
            inspection_id=insp.id,
            crack_detected=s["has_crack"],
            crack_probability=0.998 if s["has_crack"] else 0.005,
            surface_type="Reinforced Concrete",
            defect_count=1 if s["has_crack"] else 0,
            detections_json="[]",
            mask_image_path=mask_path,
            overlay_image_path=overlay_path,
            crack_area_px=geom["crack_area_px"],
            crack_area_ratio=geom["crack_area_ratio"],
            skeleton_length_px=geom["skeleton_length_px"],
            mean_width_px=geom["mean_width_px"],
            max_width_px=geom["max_width_px"],
            crack_density=geom["crack_density"],
            orientation_angle=geom["orientation_angle"],
            num_branches=geom["num_branches"],
            num_components=geom["num_components"],
            severity_level=sev["severity_level"],
            severity_score=sev["severity_score"],
            severity_reasons_json=str(sev["severity_reasons"]).replace("'", '"'),
            urgent_review_required=sev["urgent_review_required"],
            priority_level=prio["priority_level"],
            priority_score=prio["priority_score"],
            priority_rationale=prio["priority_rationale"],
            recommended_action=prio["recommended_action"],
            brightness_mean=float(np.mean(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))),
            contrast_std=float(np.std(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))),
            blur_score=1500.0,
            image_width=512,
            image_height=512,
            gradcam_image_path=gradcam_path,
            model_status_json='{"demo_mode": false, "notes": "Benchmark demonstration sample"}'
        )
        db.add(res)
        db.commit()

    print("Database seeding completed successfully.")
    db.close()

if __name__ == "__main__":
    seed_database()
