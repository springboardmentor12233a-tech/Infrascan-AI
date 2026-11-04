# InfraScan – Milestone 2 Final Progress Report

## 1. Project Overview
InfraScan is an AI-powered crack and damage assessment project for civil infrastructure. Milestone 2 focuses on image preprocessing, crack detection, classification, segmentation, geometry extraction, and model evaluation.

## 2. Completed Implementation

### Image Quality and Preprocessing
- Assessed 118 images.
- Prepared 256 × 256 preprocessed images.
- Generated an image quality assessment CSV.

### Crack Detection
- Trained YOLOv8n for 30 epochs.
- Generated best and last model weights.
- Validation mAP@50: 72.96%.
- Test mAP@50: 81.70% on 10 test images.

### Crack Segmentation
- Prepared 118 image-mask pairs.
- Trained a U-Net model for 10 epochs.
- Generated 118 prediction masks.
- Validation IoU: 29.86%.
- Dice score: 45.99%.
- Pixel accuracy: 98.03%.

### Improved U-Net Evaluation
- Trained an improved U-Net using data augmentation and combined BCE + Dice loss.
- Generated 118 improved prediction masks.
- Validation IoU: 36.83%.
- Dice score: 53.83%.
- Pixel accuracy: 98.29%.
- Improved geometry results saved separately in `data/segmentation/crack_geometry_improved.csv`.
- Evaluation used the same 24-image validation split as the original U-Net, not an independent test set.

### Classification
- Evaluated HOG + LinearSVC baseline.
- Evaluated the CNN classifier.
- HOG + LinearSVC accuracy: 35.07%.
- CNN accuracy: 50.83%.
- Improved CNN accuracy: 72.72% on the 810-image validation split.
- Improved CNN macro precision: 75.75%, macro recall: 72.72%, and macro F1-score: 71.89%.
- This was the validation split used for model        selection, not an independent test set.


### Crack Geometry Extraction
- Extracted geometry measurements for 118 predicted masks.
- Generated crack area, approximate length, bounding-box dimensions, and coverage percentage.
- Saved results in Crack_Geometry_Results.csv.

## 3. Evaluation and Observations
- YOLOv8n demonstrated initial crack detection capability.
- CNN classification performance requires improvement.
- U-Net segmentation requires further optimization.
- Geometry measurements require additional validation against ground truth.

## 4. Current Limitations
- Evaluation datasets are relatively small.
- Classification models use different class configurations.
- Pixel-based geometry measurements do not represent physical dimensions.
- Segmentation performance requires improvement.
- Further integration and testing are required.

## 5. Milestone 2 Deliverables
- Image quality assessment.
- Image preprocessing.
- Baseline classification evaluation.
- YOLO crack detection.
- U-Net segmentation and prediction masks.
- Crack geometry extraction.
- Model evaluation metrics.
- Model comparison documentation.
-Improved U-Net evaluation and separate geometry results.
-Improved CNN evaluation.
- The available SDNET2018 labels distinguish cracked and uncracked deck, pavement, and wall surfaces; they do not provide separate crack-type labels, so crack-type classification was not evaluated.

## 6. Conclusion
The major Milestone 2 model implementations and initial evaluations have been carried out. Crack-type classification was not evaluated because the available labels do not provide separate crack types. Remaining work includes model validation, performance improvement, integration checks, and final verification against the project requirements.



### Improved CNN Evaluation
- Trained an improved CNN using a balanced dataset of 4,050 images.
- Best validation accuracy: 72.72%.
- Macro precision: 75.75%.
- Macro recall: 72.72%.
- Macro F1-score: 71.89%.
- Evaluation used the same 810-image validation split used for model selection, not an independent test set.