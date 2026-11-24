"""
Classifier Inference Service.

Loads the trained SDNET2018 MobileNetV2 classification model, runs inference,
and computes honest probability-based confidence scores.
"""

from pathlib import Path
from typing import Dict, Optional
import numpy as np
import keras

from .preprocessing import preprocess_classification

DEFAULT_CLASSIFIER_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "classification" / "best_classifier.keras"


class ClassifierService:
    """Singleton service for crack classification."""

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or DEFAULT_CLASSIFIER_PATH
        self.model: Optional[keras.Model] = None

    def is_loaded(self) -> bool:
        return self.model is not None

    def load_model(self):
        """Loads model weights into memory if not already initialized."""
        if self.model is None:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Classification model weights not found at: {self.model_path}")
            print(f"[ClassifierService] Loading model from {self.model_path} ...")
            self.model = keras.models.load_model(str(self.model_path))
            print("[ClassifierService] Classification model loaded successfully.")

    def predict(self, image_bgr: np.ndarray) -> Dict:
        """
        Executes binary crack classification on an image.

        Args:
            image_bgr: Decoded image in BGR format.

        Returns:
            Dict containing label, confidence, raw crack probability, status, and message.
        """
        if self.model is None:
            self.load_model()

        tensor = preprocess_classification(image_bgr)
        raw_prob = float(self.model.predict(tensor, verbose=0)[0][0])

        is_cracked = raw_prob >= 0.5
        label = "Cracked" if is_cracked else "Uncracked"
        confidence = raw_prob if is_cracked else (1.0 - raw_prob)

        message = (
            f"Crack-like regions detected with {confidence * 100:.2f}% confidence. "
            "Further inspection by a qualified civil engineering professional is recommended."
            if is_cracked
            else f"No crack-like surface patterns detected with {confidence * 100:.2f}% confidence."
        )

        return {
            "label": label,
            "confidence": round(confidence, 4),
            "crack_probability": round(raw_prob, 4),
            "status": "success",
            "message": message
        }


# Global singleton instance
classifier_service = ClassifierService()

