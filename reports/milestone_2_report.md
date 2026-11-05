# InfraScan Milestone 2 Evaluation Report

## 1. Scope

Milestone 2 evaluates three separate AI tasks for infrastructure damage
assessment:

1. Binary crack classification.
2. Road damage object detection.
3. Pixel-level crack segmentation.

The metrics are task-specific and must not be treated as directly equivalent.
Classification evaluates image-level labels, detection evaluates bounding
boxes, and segmentation evaluates pixel-level masks.

## 2. Dataset and model scope

### CNN crack classification

- Dataset: 40,000 concrete crack images.
- Positive images: 20,000.
- Negative images: 20,000.
- Training images: 32,000.
- Validation images: 8,000.
- Task: classify each image as crack or no crack.

### YOLO road damage detection

- Classes: Crack, Pothole, Surface Erosion.
- Task: locate and classify road damage using bounding boxes.
- Model:
  [best.pt](../runs/road_damage/yolo11n_initial/weights/best.pt)

### U-Net crack segmentation

- Dataset: 118 verified CrackForest image-mask pairs.
- Training pairs: 94.
- Validation pairs: 24.
- Task: identify crack pixels using binary segmentation masks.
- Model:
  [best_unet_crack_segmentation.keras](../runs/segmentation/best_unet_crack_segmentation.keras)

The CrackForest masks use background as `0` and crack regions as `255`.
Original source images and annotations were preserved.

## 3. Model-wise evaluation

### 3.1 CNN classification

The following are validation-set results from the 8,000-image validation
split:

| Metric | Result |
|---|---:|
| Accuracy | 0.996875 |
| Precision | 0.9965026 |
| Recall | 0.99725 |
| F1-score | 0.9968762 |

Confusion matrix, with rows representing actual classes and columns
representing predicted classes:

```text
[[3986, 14],
 [11, 3989]]
```

These results indicate strong validation performance for the binary
classification task. They do not establish performance on every possible
camera, lighting, surface, or infrastructure condition.

### 3.2 YOLO road damage detection

The existing trained YOLO model was evaluated without retraining or
overwriting it:

| Metric | Result |
|---|---:|
| Precision | 0.597 |
| Recall | 0.551 |
| mAP@50 | 0.586 |
| mAP@50-95 | 0.273 |

The model detects three road-damage classes:

- Crack
- Pothole
- Surface Erosion

Detection metrics measure bounding-box localization and class prediction.
They are not directly comparable with CNN accuracy or U-Net IoU.

### 3.3 U-Net crack segmentation

| Metric | Result |
|---|---:|
| IoU | 0.4054 |
| Dice coefficient | 0.5769 |
| Pixel precision | 0.6929 |
| Pixel recall | 0.4942 |

The U-Net provides meaningful but imperfect crack localization. The recall
shows that some ground-truth crack pixels remain missed, so the model should
not be treated as a complete crack boundary extractor.

## 4. Crack geometry measurements

Geometry was measured for test image `084.jpg` using the predicted binary
mask and the measurement pipeline.

| Measurement | Result |
|---|---:|
| Raw predicted foreground pixels | 5,437 |
| Cleaned crack area | 5,412 pixels |
| Skeleton pixels | 1,106 |
| Connected components | 3 |
| Main crack length | 1,845.53 pixels |
| Main crack average width | 6.30 pixels |
| Main crack maximum width | 14.39 pixels |
| Pixels removed by morphological opening | 25 |

The 25-pixel difference is caused by morphological opening used to remove
small noise before connected-component and geometry analysis.

All geometry values are image-pixel measurements. No millimetre or centimetre
values are reported because no valid camera calibration or reference scale
was supplied.

## 5. Comparison and interpretation

| Model | Task | Primary metrics | Result |
|---|---|---|---|
| CNN | Image classification | Accuracy, precision, recall, F1 | Strong validation classification performance |
| YOLO11n | Road damage detection | Precision, recall, mAP@50, mAP@50-95 | Moderate bounding-box detection performance |
| U-Net | Crack segmentation | IoU, Dice, pixel precision, pixel recall | Useful but imperfect pixel localization |

The models serve different stages of the workflow. The CNN determines
whether an image contains a crack, YOLO identifies and classifies road
damage regions, and U-Net estimates crack pixels for more detailed analysis.
Their scores should be interpreted within their own evaluation protocols.

## 6. Limitations

- CNN results are validation-set results and may not represent unseen
  infrastructure, cameras, lighting, or environmental conditions.
- The U-Net uses only 118 verified image-mask pairs, which limits
  generalization.
- U-Net crack localization is imperfect, particularly for thin, faint,
  branching, or visually ambiguous cracks.
- Crack geometry depends on the quality of the predicted mask and therefore
  inherits segmentation errors.
- Geometry is reported only in pixels. Physical crack length or width cannot
  be inferred without camera calibration or a known reference scale.
- Dataset-specific bias, annotation variation, class imbalance, and domain
  shift may affect real-world performance.
- The models have not been established as regulatory, forensic, or
  safety-certified systems.

## 7. Future improvements

- Expand and diversify segmentation data for buildings, bridges, roads, and
  tunnels.
- Improve patch sampling and validation coverage for thin and low-contrast
  cracks.
- Tune confidence thresholds using a separate validation protocol.
- Add calibrated camera or reference-object measurements for physical units.
- Evaluate on independent field images from different devices and conditions.
- Add uncertainty estimates, human review workflows, and failure-case
  monitoring.
- Improve detection and segmentation models with additional labeled data and
  targeted augmentation.

## 8. Conclusion

Milestone 2 provides working evaluation results for crack classification,
road-damage detection, crack segmentation, and pixel-based crack geometry.
The CNN shows strong validation-set classification performance, YOLO provides
moderate road-damage detection performance, and U-Net provides useful but
imperfect crack localization for downstream analysis.

These AI models are decision-support tools, not certified structural safety
assessments. Results must be reviewed by qualified infrastructure
inspectors or civil engineers, especially before maintenance, safety, or
engineering decisions are made.
