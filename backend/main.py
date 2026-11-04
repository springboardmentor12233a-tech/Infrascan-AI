
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from tensorflow.keras.models import load_model
import tensorflow as tf
import numpy as np
from PIL import Image
from io import BytesIO
import base64
import time

app = FastAPI(title="InfraScan API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "InfraScan_UNet_Improved_BCE_Dice.keras"
)

model = load_model(str(MODEL_PATH), compile=False)
print("InfraScan U-Net model loaded successfully!")

# Use direct model inference instead of model.predict()
@tf.function(reduce_retracing=True)
def run_inference(image_tensor):
    return model(image_tensor, training=False)


@app.get("/")
def home():
    return {
        "message": "InfraScan backend is running!",
        "status": "success"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/predict")
async def predict_crack(file: UploadFile = File(...)):
    try:
        start_time = time.time()

        image_data = await file.read()
        image = Image.open(BytesIO(image_data)).convert("RGB")
        image = image.resize((256, 256))

        image_array = np.array(image, dtype=np.float32) / 255.0
        image_array = np.expand_dims(image_array, axis=0)

        input_tensor = tf.convert_to_tensor(image_array)

        preprocessing_time = time.time()

        prediction = run_inference(input_tensor).numpy()[0]
        inference_time = time.time()

        mask = (prediction[:, :, 0] > 0.5).astype(np.uint8) * 255

        buffer = BytesIO()
        Image.fromarray(mask).save(buffer, format="PNG")

        mask_base64 = base64.b64encode(
            buffer.getvalue()
        ).decode("utf-8")

        crack_percentage = float(np.mean(mask > 0) * 100)

        total_time = time.time() - start_time

        print(f"Preprocessing: {preprocessing_time - start_time:.2f} seconds")
        print(f"Inference: {inference_time - preprocessing_time:.2f} seconds")
        print(f"Total: {total_time:.2f} seconds")

        return {
            "filename": file.filename,
            "crack_percentage": round(crack_percentage, 2),
            "mask": mask_base64,
            "message": "Crack prediction completed successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
