
from pathlib import Path
from io import BytesIO
import base64
import time

import numpy as np
from PIL import Image
from openvino import Core

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware

from database import initialize_database, get_connection
from auth import router as auth_router, get_current_user
from assets import router as assets_router
from inspections import router as inspections_router


# --------------------------------------------------
# APPLICATION INITIALIZATION
# --------------------------------------------------

app = FastAPI(
    title="InfraScan API",
    description="AI-powered infrastructure inspection and damage assessment API",
    version="1.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

initialize_database()


# --------------------------------------------------
# REGISTER API ROUTERS
# --------------------------------------------------

app.include_router(auth_router)
app.include_router(assets_router)
app.include_router(inspections_router)


# --------------------------------------------------
# LOAD OPENVINO MODEL ON INTEL GPU
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "openvino_model" / "unet_model.xml"

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"OpenVINO model not found: {MODEL_PATH}"
    )

core = Core()

available_devices = core.available_devices
print("Available OpenVINO devices:", available_devices)

if "GPU" not in available_devices:
    raise RuntimeError(
        "Intel GPU is not available to OpenVINO."
    )

unet_model = core.read_model(str(MODEL_PATH))

compiled_model = core.compile_model(
    unet_model,
    "GPU",
)

input_layer = compiled_model.input(0)
output_layer = compiled_model.output(0)

print(
    "InfraScan U-Net loaded on:",
    compiled_model.get_property("EXECUTION_DEVICES")
)


# --------------------------------------------------
# DAMAGE SEVERITY ASSESSMENT
# --------------------------------------------------

def assess_damage_severity(crack_percentage):

    if crack_percentage < 2:
        severity = "Low"
        description = "Small proportion of crack pixels detected."

    elif crack_percentage < 5:
        severity = "Moderate"
        description = "Moderate proportion of crack pixels detected."

    elif crack_percentage <= 10:
        severity = "High"
        description = "High proportion of crack pixels detected."

    else:
        severity = "Critical"
        description = "Very high proportion of crack pixels detected."

    return {
        "severity": severity,
        "severity_description": description,
        "assessment_note": (
            "Indicative image-based classification only. "
            "These thresholds are project-defined and do not "
            "represent engineering safety standards."
        ),
    }


# --------------------------------------------------
# CRACK LENGTH AND WIDTH ESTIMATION
# --------------------------------------------------

def estimate_crack_dimensions(mask):

    binary = (mask > 0).astype(np.uint8)

    changed = True

    while changed:

        changed = False

        for step in range(2):

            padded = np.pad(
                binary,
                1,
                mode="constant",
            )

            center = padded[1:-1, 1:-1]

            p2 = padded[:-2, 1:-1]
            p3 = padded[:-2, 2:]
            p4 = padded[1:-1, 2:]
            p5 = padded[2:, 2:]
            p6 = padded[2:, 1:-1]
            p7 = padded[2:, :-2]
            p8 = padded[1:-1, :-2]
            p9 = padded[:-2, :-2]

            neighbors = [
                p2, p3, p4, p5,
                p6, p7, p8, p9
            ]

            neighbor_count = sum(neighbors)

            transitions = np.zeros_like(binary)

            for i in range(8):
                transitions += (
                    (neighbors[i] == 0) &
                    (neighbors[(i + 1) % 8] == 1)
                )

            condition = (
                (center == 1) &
                (neighbor_count >= 2) &
                (neighbor_count <= 6) &
                (transitions == 1)
            )

            if step == 0:

                condition &= (p2 * p4 * p6 == 0)
                condition &= (p4 * p6 * p8 == 0)

            else:

                condition &= (p2 * p4 * p8 == 0)
                condition &= (p2 * p6 * p8 == 0)

            if np.any(condition):

                binary[condition] = 0
                changed = True

    # Count crack pixels and skeleton pixels

    crack_area_pixels = int(
        np.count_nonzero(mask)
    )

    skeleton_length_pixels = int(
        np.count_nonzero(binary)
    )

    if skeleton_length_pixels == 0:

        return {
            "crack_length_pixels": 0,
            "average_crack_width_pixels": 0.0,
        }

    # Estimate average width

    average_width = (
        crack_area_pixels / skeleton_length_pixels
    )

    return {
        "crack_length_pixels": skeleton_length_pixels,
        "average_crack_width_pixels": round(
            average_width,
            2,
        ),
    }


# --------------------------------------------------
# HOME ENDPOINT
# --------------------------------------------------

@app.get("/")
def home():

    return {
        "message": "InfraScan backend is running!",
        "status": "success",
    }


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "message": "InfraScan API is operational",
        "inference_device": "Intel GPU",
    }


# --------------------------------------------------
# CRACK DETECTION, SEGMENTATION AND SEVERITY
# --------------------------------------------------

@app.post("/predict")
async def predict_crack(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):

    try:

        start_time = time.time()

        if not file.filename:

            raise HTTPException(
                status_code=400,
                detail="Please upload an image file",
            )

        image_data = await file.read()

        if not image_data:

            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty",
            )

        try:

            image = Image.open(
                BytesIO(image_data)
            ).convert("RGB")

        except Exception:

            raise HTTPException(
                status_code=400,
                detail="Invalid image file",
            )

        # Resize image for model input

        image = image.resize((256, 256))

        image_array = (
            np.array(image, dtype=np.float32) / 255.0
        )

        image_array = np.expand_dims(
            image_array,
            axis=0,
        )

        preprocessing_time = time.time()

        # OpenVINO GPU prediction

        prediction = compiled_model(
            {input_layer: image_array}
        )[output_layer]

        prediction = np.asarray(prediction)[0]

        inference_time = time.time()

        # --------------------------------------------------
        # GENERATE PREDICTION PROBABILITY HEATMAP
        # --------------------------------------------------

        probability_map = np.clip(
            prediction[:, :, 0],
            0.0,
            1.0,
        )

        heatmap = np.zeros(
            (256, 256, 3),
            dtype=np.uint8,
        )

        heatmap[:, :, 0] = (
            probability_map * 255
        ).astype(np.uint8)

        heatmap[:, :, 2] = (
            (1.0 - probability_map) * 255
        ).astype(np.uint8)

        heatmap[:, :, 1] = (
            (1.0 - np.abs(probability_map - 0.5) * 2) * 255
        ).astype(np.uint8)

        heatmap_buffer = BytesIO()

        Image.fromarray(heatmap).save(
            heatmap_buffer,
            format="PNG",
        )

        confidence_heatmap_base64 = base64.b64encode(
            heatmap_buffer.getvalue()
        ).decode("utf-8")

        # Generate binary crack mask

        mask = (
            prediction[:, :, 0] > 0.5
        ).astype(np.uint8) * 255

        # Convert mask into Base64 PNG

        buffer = BytesIO()

        Image.fromarray(mask).save(
            buffer,
            format="PNG",
        )

        mask_base64 = base64.b64encode(
            buffer.getvalue()
        ).decode("utf-8")

        # --------------------------------------------------
        # CREATE RED CRACK DETECTION OVERLAY
        # --------------------------------------------------

        red_layer = Image.new(
            "RGB",
            image.size,
            (255, 0, 0),
        )

        alpha_mask = Image.fromarray(mask).point(
            lambda value: int(value * 0.45)
        )

        overlay_image = Image.composite(
            red_layer,
            image.convert("RGB"),
            alpha_mask,
        )

        overlay_buffer = BytesIO()

        overlay_image.save(
            overlay_buffer,
            format="PNG",
        )

        overlay_base64 = base64.b64encode(
            overlay_buffer.getvalue()
        ).decode("utf-8")

        # --------------------------------------------------
        # CALCULATE CRACK PERCENTAGE
        # --------------------------------------------------

        crack_percentage = float(
            np.mean(mask > 0) * 100
        )

        # --------------------------------------------------
        # ASSESS DAMAGE SEVERITY
        # --------------------------------------------------

        severity_result = assess_damage_severity(
            crack_percentage
        )

        # --------------------------------------------------
        # ESTIMATE CRACK LENGTH AND WIDTH
        # --------------------------------------------------

        dimension_result = estimate_crack_dimensions(
            mask
        )

        # --------------------------------------------------
        # SAVE ANALYSIS RESULT IN DATABASE
        # --------------------------------------------------

        connection = get_connection()

        try:

            connection.execute(
                """
                INSERT INTO analysis_history
                (filename, crack_percentage, analyzed_by)
                VALUES (?, ?, ?)
                """,
                (
                    file.filename,
                    round(crack_percentage, 2),
                    current_user["id"],
                ),
            )

            connection.commit()

        finally:

            connection.close()

        # --------------------------------------------------
        # CALCULATE EXECUTION TIME
        # --------------------------------------------------

        total_time = time.time() - start_time

        print(
            f"Preprocessing: "
            f"{preprocessing_time - start_time:.2f} seconds"
        )

        print(
            f"GPU inference: "
            f"{inference_time - preprocessing_time:.2f} seconds"
        )

        print(
            f"Total: {total_time:.2f} seconds"
        )

        # --------------------------------------------------
        # RETURN PREDICTION RESULTS
        # --------------------------------------------------

        return {

            "filename": file.filename,

            "crack_percentage": round(
                crack_percentage,
                2,
            ),

            "severity": severity_result["severity"],

            "severity_description": severity_result[
                "severity_description"
            ],

            "assessment_note": severity_result[
                "assessment_note"
            ],

            "crack_length_pixels": dimension_result[
                "crack_length_pixels"
            ],

            "average_crack_width_pixels": dimension_result[
                "average_crack_width_pixels"
            ],

            "mask": mask_base64,

            "overlay": overlay_base64,

            "confidence_heatmap": confidence_heatmap_base64,

            "message": (
                "Crack prediction and severity assessment "
                "completed successfully"
            ),
        }

    except HTTPException:

        raise

    except Exception as error:

        print(f"Prediction error: {error}")

        raise HTTPException(
            status_code=500,
            detail="An error occurred during crack prediction",
        )


# --------------------------------------------------
# ANALYSIS HISTORY
# --------------------------------------------------

@app.get("/analysis-history")
def get_analysis_history(
    current_user: dict = Depends(get_current_user),
):

    connection = get_connection()

    try:

        if current_user["role"] == "Admin":

            rows = connection.execute(
                """
                SELECT
                    id,
                    filename,
                    crack_percentage,
                    analyzed_by,
                    analyzed_at
                FROM analysis_history
                ORDER BY analyzed_at DESC
                """
            ).fetchall()

        else:

            rows = connection.execute(
                """
                SELECT
                    id,
                    filename,
                    crack_percentage,
                    analyzed_by,
                    analyzed_at
                FROM analysis_history
                WHERE analyzed_by = ?
                ORDER BY analyzed_at DESC
                """,
                (current_user["id"],),
            ).fetchall()

        return {
            "total": len(rows),
            "records": [dict(row) for row in rows],
        }

    finally:

        connection.close()

# --------------------------------------------------
# DELETE ANALYSIS HISTORY RECORD
# --------------------------------------------------

@app.delete("/analysis-history/{record_id}")
def delete_analysis_record(
    record_id: int,
    current_user: dict = Depends(get_current_user),
):
    # Only Admin can delete analysis reports
    if current_user["role"] != "Admin":
        raise HTTPException(
            status_code=403,
            detail="Only Admin can delete analysis reports."
        )

    connection = get_connection()

    try:
        cursor = connection.execute(
            "DELETE FROM analysis_history WHERE id = ?",
            (record_id,)
        )

        connection.commit()

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Analysis report not found."
            )

        return {
            "message": "Analysis report deleted successfully.",
            "deleted_id": record_id
        }

    finally:
        connection.close()

