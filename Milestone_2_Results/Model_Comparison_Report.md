# InfraScan – Model Comparison Report

## 1\. Objective

Evaluate the baseline classification, CNN classification, YOLO crack detection, and U-Net segmentation approaches.

## 2\. Model Evaluation Results

|Model|Task|Evaluation Metric|Result|
|-|-|-|-:|
|HOG + LinearSVC|6-class classification|Accuracy|35.07%|
|CNN|2-class classification|Accuracy|50.83%|
|YOLOv8n|Crack detection|Validation mAP@50|72.96%|
|YOLOv8n|Crack detection|Test mAP@50|81.70%|
|U-Net|Crack segmentation|IoU|29.86%|
|U-Net|Crack segmentation|Dice|45.99%|
|U-Net|Crack segmentation|Pixel Accuracy|98.03%|

## 3\. Additional Metrics

### HOG + LinearSVC

* Macro Precision: 35.19%
* Macro Recall: 35.07%
* Macro F1-score: 35.08%

### CNN

* Precision: 64.76%
* Recall: 54.97%
* F1-score: 43.59%

### YOLOv8n

* Validation Precision: 62.96%
* Validation Recall: 80.95%
* Validation mAP@50–95: 30.56%

### U-Net

* Validation images: 24
* Prediction masks generated: 118

## 4\. Observations

* YOLOv8n completed 30 training epochs and generated evaluation plots and confusion matrices.
* CNN classification requires improvement, particularly for the UD class.
* U-Net successfully generated prediction masks, but segmentation quality requires improvement.
* Crack geometry measurements were extracted for 118 predicted masks.
- Improved U-Net generated prediction masks for 118 images.
- Improved U-Net geometry measurements were saved separately in `data/segmentation/crack_geometry_improved.csv`.
- The improved U-Net evaluation used the same 24-image validation split as the original U-Net; these results are not from an independent test set.

## 5\. Limitations

* Classification models use different class configurations and cannot be directly compared.
* YOLO test evaluation used only 10 images.
* U-Net evaluation used 24 validation images.
* Geometry measurements are pixel-based approximations and require further validation.
* Physical crack dimensions cannot be established without image calibration.

## 6\. Conclusion

The initial InfraScan model implementations and evaluations have been completed. Further model optimization, validation, and integration are required to improve reliability and overall system performance.



\## 7. Improved U-Net Evaluation



An improved U-Net training experiment was conducted using data augmentation and combined BCE + Dice loss.



\### Original vs Improved U-Net



| Metric | Original U-Net | Improved U-Net |

|---|---:|---:|

| IoU | 29.86% | 36.83% |

| Dice Score | 45.99% | 53.83% |

| Pixel Accuracy | 98.03% | 98.29% |



\### Observations

\- IoU improved by 6.97 percentage points.

\- Dice score improved by 7.84 percentage points.

\- Pixel accuracy improved by 0.26 percentage points.

\- The improved model performed better on all three evaluated metrics.



Improved model: `unet\_crack\_improved.pth`



Evaluation was performed on the same 24-image validation split.

## 8. Improved CNN Evaluation

- Improved CNN validation accuracy: 72.72%.
- Macro precision: 75.75%.
- Macro recall: 72.72%.
- Macro F1-score: 71.89%.
- Evaluation used the 810-image validation split used for model selection, not an independent test set.