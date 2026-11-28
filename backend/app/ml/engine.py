"""
Dedicated YOLO ML Inference Engine for InfraScan.

Strictly prohibits fabricated/random predictions:
If trained model weights are not present on disk, returns `model_status="weights_unavailable"`
and does not generate fake detections.
"""

from pathlib import Path
import time
import cv2
from app.ml.quality import assess_image_quality
from app.ml.geometry import compute_box_geometry
from app.ml.severity import assess_severity

DEFAULT_WEIGHTS_PATH = Path(__file__).resolve().parents[2] / "weights" / "rdd2022_yolo.pt"


class InfraScanMLEngine:
    def __init__(self, weights_path: str | Path | None = None):
        self.weights_path = Path(weights_path) if weights_path else DEFAULT_WEIGHTS_PATH
        self._model = None

    @property
    def weights_available(self) -> bool:
        return self.weights_path.exists() and self.weights_path.is_file()

    def load_model(self):
        if not self.weights_available:
            raise FileNotFoundError(
                f"Trained model weights not found at '{self.weights_path}'. "
                "Train the model using backend/scripts/train_rdd2022.py or place weights there."
            )
        if self._model is None:
            from ultralytics import YOLO
            self._model = YOLO(str(self.weights_path))
        return self._model

    def run_inference(
        self,
        image_path: str,
        annotated_output_path: str | None = None,
        conf_threshold: float = 0.25,
        px_per_mm: float | None = None,
    ) -> dict:
        quality = assess_image_quality(image_path)

        if not self.weights_available:
            return {
                "model_status": "weights_unavailable",
                "model_name": "YOLOv8-RDD2022",
                "weights_path": str(self.weights_path),
                "message": (
                    f"Trained weights not found at {self.weights_path}. "
                    "No inference was performed (fake predictions are disabled)."
                ),
                "quality": quality,
                "detections": [],
                "severity": {
                    "severity": "Pending Model",
                    "requires_engineering_review": True,
                    "disclaimer": "Model weights unavailable; automated assessment not performed.",
                },
                "annotated_image_path": None,
                "inference_time_ms": 0,
            }

        t0 = time.perf_counter()
        model = self.load_model()
        results = model.predict(source=image_path, conf=conf_threshold, verbose=False)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        detections = []
        r = results[0]
        img = cv2.imread(image_path)
        h, w = img.shape[:2]

        if r.boxes is not None:
            for idx, box in enumerate(r.boxes):
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                conf = float(box.conf[0].item())
                cls_id = int(box.cls[0].item())
                cls_name = model.names.get(cls_id, f"class_{cls_id}")

                geom = compute_box_geometry(x1, y1, x2, y2, w, h, px_per_mm)
                detections.append({
                    "id": f"DET-{idx + 1}",
                    "class_id": cls_id,
                    "label": cls_name,
                    "confidence": round(conf, 4),
                    "bbox_xyxy": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                    "bbox_pct": {
                        "x": round((x1 / w) * 100.0, 2),
                        "y": round((y1 / h) * 100.0, 2),
                        "width": round(((x2 - x1) / w) * 100.0, 2),
                        "height": round(((y2 - y1) / h) * 100.0, 2),
                    },
                    "geometry": geom,
                })

                cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
                cv2.putText(
                    img,
                    f"{cls_name} {conf:.0%}",
                    (int(x1), max(18, int(y1) - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 0, 255),
                    2,
                )

        saved_annotated = None
        if annotated_output_path:
            out_p = Path(annotated_output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(out_p), img)
            saved_annotated = str(out_p)

        return {
            "model_status": "trained_and_available",
            "model_name": self.weights_path.stem,
            "weights_path": str(self.weights_path),
            "quality": quality,
            "detections": detections,
            "severity": assess_severity(detections),
            "annotated_image_path": saved_annotated,
            "inference_time_ms": elapsed_ms,
        }


ml_engine = InfraScanMLEngine()

