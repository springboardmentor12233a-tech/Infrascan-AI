# Milestone 2: Technical Evaluation & Benchmark Report

**Project:** InfraScan — Intelligent Infrastructure Surface Defect Assessment  
**Evaluation Scope:** Classification, Object Detection, Semantic Segmentation, and Morphological Geometry  
**Status:** Complete Audit & Verification  
**Evaluation Date:** October 31, 2026  

---

## Executive Summary & Plan Target Alignment

The project plan defines the following performance targets:
1. **Classification Target**: Macro F1 $\ge 85\%$ (0.85) where the dataset allows.
2. **Object Detection Target**: $\text{mAP@50} \ge 85\%$ (0.85) and $\text{Recall} \ge 90\%$ (0.90).
3. **Semantic Segmentation Target**: $\text{Dice} \ge 85\%$ (0.85) and $\text{IoU} \ge 75\%$ (0.75).
4. **Inference Latency Target**: Under 3 seconds on the chosen GPU.

All figures presented below are drawn strictly from persisted evaluation artifacts (`test_metrics.json`, `test_predictions.csv`, `per_image_metrics.csv`, `run_card.json`, `speed_and_size.json`, `geometry_results.csv`, `geometry_summary.csv`). No numbers are estimated.

---

## C1. Defect Classification Benchmarks

Two classification models based on ResNet-50 backbones (pretrained on ImageNet) were trained and evaluated.

### 1. Plan Target: Macro F1
The project plan target for classification is **Macro F1 $\ge 85\%$ (0.85) where the dataset allows**.  
*Note on Validation Threshold Selection:* During validation tuning, a constraint rule of $\text{Recall} \ge 0.90$ was used to choose the operating decision threshold on the validation split; this thresholding rule was a calibration mechanism rather than an independent project plan target.

#### Macro F1 Computation from `test_predictions.csv`
Macro F1 is computed as the unweighted arithmetic mean of the positive class F1 (crack) and negative class F1 (no-crack):
$$\text{Macro F1} = \frac{\text{F1}_{\text{crack}} + \text{F1}_{\text{no-crack}}}{2}$$

1. **Concrete Crack Images (`concrete_crack_cls`)** ($N = 5,760$ test images):
   - Operating threshold: `0.4951`
   - Confusion Matrix: $\text{TP} = 2951, \quad \text{FP} = 1, \quad \text{TN} = 2807, \quad \text{FN} = 1$
   - Class 1 (Crack): $\text{Precision} = 0.9997$, $\text{Recall} = 0.9997$, $\text{F1} = 0.9997$ (0.999661)
   - Class 0 (No-Crack): $\text{Precision} = 0.9996$, $\text{Recall} = 0.9996$, $\text{F1} = 0.9996$ (0.999644)
   - **Macro F1**: **0.9997** (0.999653)
   - **Plan Target Status**: **REACHED** ($0.9997 \ge 0.85$).

2. **SDNET2018 (`sdnet2018`)** ($N = 8,802$ test images):
   - Operating threshold: `0.0100` (chosen on validation split to achieve validation recall $\ge 0.90$)
   - Confusion Matrix: $\text{TP} = 1168, \quad \text{FP} = 2429, \quad \text{TN} = 5118, \quad \text{FN} = 87$
   - Class 1 (Crack): $\text{Precision} = 0.3247$, $\text{Recall} = 0.9307$, $\text{F1} = 0.4815$ (0.481451)
   - Class 0 (No-Crack): $\text{Precision} = 0.9833$, $\text{Recall} = 0.6782$, $\text{F1} = 0.8027$ (0.802698)
   - **Macro F1**: **0.6421** (0.642074)
   - **Plan Target Status**: **NOT REACHED** ($0.6421 < 0.85$). Setting the threshold to $0.0100$ to maintain high recall ($0.9307$) resulted in 2,429 false positives, reducing precision to $0.3247$ and Macro F1 to $0.6421$.

---

### 2. Primary Metrics Summary
| Metric | Concrete Crack Images (`concrete_crack_cls`) | SDNET2018 (`sdnet2018`) |
| :--- | :---: | :---: |
| **Test Image Count ($N$)** | 5,760 | 8,802 |
| **Operating Threshold** | 0.4951 | 0.0100 |
| **Macro F1** | **0.9997** | **0.6421** |
| **Crack-Class F1** | 0.9997 [0.9991, 1.0000] | 0.4815 [0.4640, 0.4986] |
| **Crack-Class Recall** | 0.9997 [0.9990, 1.0000] | 0.9307 [0.9159, 0.9434] |
| **Crack-Class Precision** | 0.9997 [0.9990, 1.0000] | 0.3247 [0.3097, 0.3400] |
| **Accuracy** | 0.9997 | 0.7142 |
| **Balanced Accuracy** | 0.9997 | 0.8044 |
| **Specificity** | 0.9996 | 0.6782 |
| **AUC-ROC** | 1.0000 [1.0000, 1.0000] | 0.9342 [0.9246, 0.9423] |
| **Average Precision (PR-AUC)** | 1.0000 | 0.8419 |

---

### 3. SDNET2018 Per-Surface Breakdown (`metrics_by_group.csv`)
| Surface Code / Name | Total Images | Crack / No-Crack | Recall | Precision | F1-Score | Specificity | AUC-ROC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **D — Bridge Decks** | 2,268 | 290 / 1,978 | 0.9276 | 0.2325 | 0.3718 | 0.5511 | 0.9082 |
| **P — Pavements** | 3,510 | 367 / 3,143 | 0.8965 | 0.3194 | 0.4710 | 0.7770 | 0.9307 |
| **W — Walls** | 3,024 | 598 / 2,426 | 0.9532 | 0.4043 | 0.5677 | 0.6538 | 0.9486 |

---

### 4. Data Leakage & Training Checkpoint Verification
- **Perceptual Hash Audit (dHash $\le 2$ bits)**:
  - `concrete_crack_cls`: 931 / 5,760 near-duplicates (16.16%). Evaluating exclusively on the 4,829 non-duplicate test images yields $\text{Recall} = 0.9995$, $\text{Precision} = 0.9995$, $\text{F1} = 0.9995$.
  - `sdnet2018`: 7 / 8,802 near-duplicates (0.08%).
- **Best Epoch Verification**:
  - `concrete_crack_cls`: `model_card.json` reports `best_epoch: 0` as a default logging artifact; `history.csv` confirms best validation loss ($0.0008$) and best validation F1 ($0.9997$) occurred at **Epoch 13**.
  - `sdnet2018`: Minimum validation loss was reached at **Epoch 7** ($\text{val\_loss} = 0.4955$). After Epoch 7, training loss continued decreasing ($0.082 \to 0.015$) while validation loss rose to $0.7225$ by Epoch 14, indicating overfitting.

---

## C2. Road Damage Object Detection Benchmarks (RDD2022)

Two YOLO models were trained on RDD2022 (Japan + India): YOLOv8s and YOLO11s.  
- Training settings: 40 epochs, batch size 16, image resolution 640x640.
- Classes: D00 (longitudinal crack), D10 (transverse crack), D20 (alligator crack), D40 (pothole).
- **Test Split Status**: **Test split not evaluated yet** (no test evaluation file exists on disk; RDD2022 test split is unannotated).

### 1. Validation Split Performance Comparison
All metrics below are evaluated on the **validation split**:

| Model Architecture | Evaluated Split | Checkpoint Epoch | Validation Precision | Validation Recall | Validation mAP@50 | Validation mAP@50:95 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **YOLOv8s** | **Validation** | **Epoch 38 (Best mAP@50)** | **0.5211** | **0.4528** | **0.4554** | **0.2220** |
| YOLOv8s | Validation | Epoch 40 (Final) | 0.5505 | 0.4440 | 0.4545 | 0.2220 |
| **YOLO11s** | **Validation** | **Epoch 38 (Best mAP@50)** | **0.5534** | **0.4161** | **0.4437** | **0.2151** |
| YOLO11s | Validation | Epoch 40 (Final) | 0.5457 | 0.4197 | 0.4415 | 0.2159 |

### 2. Model Selection by Validation mAP@50:95
- `yolov8s_rdd2022` achieves a validation mAP@50:95 of **0.2220** (0.22204 at final epoch, 0.22196 at epoch 38).
- `yolo11s_rdd2022` achieves a validation mAP@50:95 of **0.2159** (0.21594 at final epoch, 0.21513 at epoch 38).
- **Winning Detector**: By the validation mAP@50:95 rule, **`yolov8s_rdd2022` is the final model**.
- **Plan Target Status**:
  - Target: $\text{mAP@50} \ge 85\%$ (0.85) and $\text{Recall} \ge 90\%$ (0.90).
  - Validation result: $\text{mAP@50} = 0.4554$, $\text{Recall} = 0.4528$.
  - Status: **NOT REACHED** on validation; test split not evaluated yet.
- *Data note:* Per-country test breakdowns and per-class test AP breakdowns were not evaluated because no test evaluation files exist.

---

## C3. Semantic Crack Segmentation Benchmarks

Semantic crack segmentation was trained on Crack500 and evaluated in-domain on Crack500 clean test split ($N = 1,087$) and externally on CFD ($N = 118$).

### 1. Winning Model Selection & Validation Reproducibility
- Winner: `unetplusplus_crack500` (ResNet-34 ImageNet encoder, optimal threshold `0.40`).
- Runner-up: `unet_crack500` (ResNet-34 ImageNet encoder, optimal threshold `0.25`).
- Validation Results (Crack500 validation split, 341 images):
  - U-Net++: Val Dice = **0.7482**, Val IoU = **0.6265**, Val Precision = **0.7698**, Val Recall = **0.7962**.
  - Standard U-Net: Val Dice = 0.7335, Val IoU = 0.6056, Val Precision = 0.7395, Val Recall = 0.7896.
- Local validation re-evaluation of `best.pth` produced local $\text{Dice} = 0.748205$ vs card value $0.7482$ ($\Delta = 0.000005$), confirming numerical reproducibility.

### 2. Byte-Identical Test Metrics Check
A SHA-256 cryptographic check was performed on the persisted test metrics files:
- `infrascan/ml/models/segmentation/unetplusplus_crack500/evaluation/crack500_test_metrics.json`
- `infrascan/ml/models/segmentation/unetplusplus_crack500/evaluation/crack500/crack500_test_metrics.json`
- **Result**: Both files are **byte-identical** with matching SHA-256 hash:  
  `003ae93521ad9a902d6af51b71aac8152fd05ef0a9483ae83877063ad567a7b8`.

---

### 3. In-Domain Test Evaluation: Crack500 ($N = 1,087$)
The clean test split comprises 1,087 images (37 crops were excluded during initial data cleaning due to `source_photo_split_overlap` where parent images overlapped with train/val).

| Metric | Crack500 Test Split ($N = 1,087$) | 95% Bootstrap Confidence Interval |
| :--- | :---: | :---: |
| **Operating Threshold** | 0.40 | — |
| **Mean Dice** | **0.6899** | **[0.6801, 0.7001]** |
| **Mean IoU** | **0.5481** | **[0.5382, 0.5586]** |
| **Precision** | 0.6933 | — |
| **Recall** | 0.7442 | — |
| **Pixel-Pooled Dice** | 0.7309 | — |
| **Pixel-Pooled IoU** | 0.5759 | — |
| **Boundary F1 (3px)** | 0.4523 | — |
| **Pixel Accuracy** | 0.9696 | — |
| **Specificity** | 0.9826 | — |

- **Plan Target Status**:
  - Target: $\text{Dice} \ge 85\%$ (0.85) and $\text{IoU} \ge 75\%$ (0.75).
  - Actual: $\text{Dice} = 0.6899$, $\text{IoU} = 0.5481$.
  - Status: **NOT REACHED**.
- **Data Leakage Check**: 0 shared parents, 0 exact duplicates ($d = 0$), 0 near-duplicates ($d \le 2$). Mean min Hamming distance is $17.80$ bits.

---

### 4. External Generalization Test: CFD ($N = 118$)
Evaluated directly on the 118 images of CFD using threshold $0.40$:

| Metric | CFD External Test ($N = 118$) | 95% Bootstrap Confidence Interval |
| :--- | :---: | :---: |
| **Mean Dice** | **0.4533** | **[0.4187, 0.4873]** |
| **Mean IoU** | **0.3109** | **[0.2839, 0.3384]** |
| **Precision** | 0.4390 | — |
| **Recall** | 0.7024 | — |
| **Pixel-Pooled Dice** | 0.4214 | — |
| **Pixel-Pooled IoU** | 0.2669 | — |
| **Boundary F1 (3px)** | 0.5906 | — |
| **Pixel Accuracy** | 0.9663 | — |
| **Specificity** | 0.9764 | — |

---

### 5. CFD vs. Crack500 Gap & Width Effect Analysis
- **Observed Gap**: Mean Dice is **0.4533** on CFD versus **0.6899** on Crack500.
- **Crack Width Comparison**: CFD true-mask mean crack width is **4.38 px** (min 2.08 px, max 40.76 px), whereas Crack500 true-mask mean crack width is **18.96 px** (min 3.75 px, max 73.02 px).
- **CFD Thickness Groups (from `cfd_per_image_metrics.csv` & `summary.md`)**:
  - **Thin**: width range $[2.08, 3.06\,\text{px}]$ ($N = 40$), mean width $2.76\,\text{px}$, mean Dice = **0.3472**, mean IoU = **0.2223**.
  - **Medium**: width range $[3.07, 3.85\,\text{px}]$ ($N = 39$), mean width $3.41\,\text{px}$, mean Dice = **0.4727**, mean IoU = **0.3232**.
  - **Thick**: width range $[3.89, 40.76\,\text{px}]$ ($N = 39$), mean width $6.96\,\text{px}$, mean Dice = **0.5428**, mean IoU = **0.3896**.
- **Comparison with Crack500 Images in the CFD Width Range**:
  - *Thin range $[2.08, 3.06\,\text{px}]$*: Crack500 has **0 images** (the minimum crack width in Crack500 test is $3.75\,\text{px}$). Direct comparison cannot be done for this range.
  - *Medium range $[3.07, 3.85\,\text{px}]$*: Crack500 has only **1 image** (mean width $3.75\,\text{px}$, Dice $0.4059$, IoU $0.2546$). A statistical comparison cannot be done with $N = 1$.
  - *Thick range $[3.89, 40.76\,\text{px}]$*: Crack500 has 1,039 images in this range, but their mean width is $17.61\,\text{px}$ (Dice $0.6865$, IoU $0.5438$), compared to CFD's mean width of $6.96\,\text{px}$ (Dice $0.5428$, IoU $0.3896$).
  - *Narrow overlapping width band $[3.89, 10.0\,\text{px}]$*:
    - Crack500 ($N = 191$, mean width $7.93\,\text{px}$): mean Dice is **0.6163**, mean IoU is **0.4633**.
    - CFD ($N = 35$, mean width $4.93\,\text{px}$): mean Dice is **0.5654**, mean IoU is **0.4084**.
- **Conclusion**: Performance falls with decreasing crack width in both datasets (in Crack500: thick 0.7308 $\to$ medium 0.7095 $\to$ thin 0.6296; in CFD: thick 0.5428 $\to$ medium 0.4727 $\to$ thin 0.3472). Other potential causes of the performance gap were not tested.

---

### 6. Computational Footprint & Latency
- **Model Checkpoint Size**: `99.66 MB`
- **Total Parameters**: `26,078,609` (all trainable)
- **Host CPU Inference Latency (from `speed_and_size.json`)**:
  - Mean latency: **1,349.14 ms / image** (1.35 seconds per 384x384 crop)
  - Median latency: `1,331.18 ms`
  - 95th percentile latency: `1,510.49 ms`
  - Throughput: `0.74 images / sec`
- **GPU Latency Status**: Training `run_card.json` records hardware device name `Tesla T4`, but inference latency on GPU was not measured or persisted in test evaluation files.

---

## C4. Quantitative Crack Geometry Extraction

The geometry pipeline extracts skeleton step length, caliper width via Euclidean Distance Transform (EDT), orientation via PCA, and topological invariants.

### 1. Synthetic Validation Table across Width Modes
Evaluated across balanced straight lines (widths 2 to 10 px), 8x super-sampled rotated polygons ($0^\circ$ to $75^\circ$), and the concentric circular arc:

| Shape / Primitive | True Width (px) | Derivation | `edt2` Mean Err | `edt2` MAE | `edt2_minus1` Mean Err | `edt2_minus1` MAE | Better Mode |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **Horizontal_W2** | 2.0 | Discrete row span (2 px) | +0.000 | 0.000 | -1.000 | 1.000 | **`edt2`** |
| **Horizontal_W3** | 3.0 | Discrete row span (3 px) | +0.960 | 0.960 | -0.040 | 0.040 | **`edt2_minus1`** |
| **Horizontal_W4** | 4.0 | Discrete row span (4 px) | +0.000 | 0.000 | -1.000 | 1.000 | **`edt2`** |
| **Horizontal_W5** | 5.0 | Discrete row span (5 px) | +0.959 | 0.959 | -0.041 | 0.041 | **`edt2_minus1`** |
| **Horizontal_W6** | 6.0 | Discrete row span (6 px) | -0.021 | 0.021 | -1.021 | 1.021 | **`edt2`** |
| **Horizontal_W7** | 7.0 | Discrete row span (7 px) | +0.938 | 0.938 | -0.062 | 0.062 | **`edt2_minus1`** |
| **Horizontal_W8** | 8.0 | Discrete row span (8 px) | -0.021 | 0.021 | -1.021 | 1.021 | **`edt2`** |
| **Horizontal_W9** | 9.0 | Discrete row span (9 px) | +0.936 | 0.936 | -0.064 | 0.064 | **`edt2_minus1`** |
| **Horizontal_W10** | 10.0 | Discrete row span (10 px) | -0.022 | 0.022 | -1.022 | 1.022 | **`edt2`** |
| **Rotated_00deg** | 5.0 | 8x polygon, INTER_AREA | +0.979 | 0.979 | -0.021 | 0.021 | **`edt2_minus1`** |
| **Rotated_15deg** | 5.0 | 8x polygon, INTER_AREA | +0.129 | 0.129 | -0.871 | 0.871 | **`edt2`** |
| **Rotated_30deg** | 5.0 | 8x polygon, INTER_AREA | +0.172 | 0.172 | -0.828 | 0.828 | **`edt2`** |
| **Rotated_45deg** | 5.0 | 8x polygon, INTER_AREA | +0.657 | 0.657 | -0.343 | 0.343 | **`edt2_minus1`** |
| **Rotated_60deg** | 5.0 | 8x polygon, INTER_AREA | +0.247 | 0.247 | -0.753 | 0.753 | **`edt2`** |
| **Rotated_75deg** | 5.0 | 8x polygon, INTER_AREA | +0.105 | 0.105 | -0.895 | 0.895 | **`edt2`** |
| **Concentric_Arc** | 5.0 | 8x concentric circles | +0.336 | 0.336 | -0.664 | 0.664 | **`edt2`** |
| **Crack500 (All 1,087)** | 19.01 | Crack500 GT mask mean | +0.795 | 4.741 | +0.811 | 4.726 | — (offset cancels) |

- **Summary of Width Modes**:
  - Even straight lines [W2..W10]: `edt2` MAE = **0.013 px**; `edt2_minus1` MAE = **1.013 px**.
  - Odd straight lines [W3..W9]: `edt2` MAE = **0.948 px**; `edt2_minus1` MAE = **0.052 px**.
  - 50/50 balance: `edt2` MAE = **0.480 px** vs `edt2_minus1` MAE = **0.532 px**.
  - Rotated polygons and curve: `edt2` MAE = **0.375 px** vs `edt2_minus1` MAE = **0.625 px**.
  - Real Crack500 data: MAE is virtually identical (**4.741 px** vs **4.726 px**) due to offset cancellation.
  - `edt2` is preserved as canonical default.

---

### 2. Crack500 Test Evaluation on All 1,087 Images & Empty Masks Analysis
- **Audit Counts**: 1,087 manifest test images, 1,087 mask files found, 1,087 masks measured, 0 missing/failed.
- **Empty Masks Analysis**:
  - **Ground Truth vs Predicted**: In the test split, **all 1,087 ground truth masks contain cracks** (`has_crack = True` for 100% of images). The 17 empty masks are **predicted masks** where no crack component $\ge 20\,\text{px}$ was detected (16 produced 0 pixels, and 1 produced $< 20\,\text{px}$). For these 17 images, ground-truth cracks have a mean length of $283.34\,\text{px}$ and mean width of $17.26\,\text{px}$.
  - **Statistical Treatment**: `measure_crack` returns `length_px = 0.0` and `avg_width_px = 0.0` for empty masks. In the error calculations ($\text{pred} - \text{gt}$), these contribute a length error of $-L_{\text{gt}}$ and width error of $-W_{\text{gt}}$.

#### Geometry Error Metrics
| Evaluation Population | Metric | GT Mean | Predicted Mean | Mean Error (Signed) | Mean Absolute Error (MAE) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **All 1,087 Images** | Crack Length ($L_{\text{px}}$) | 732.85 px | 693.79 px | -39.06 px | **140.32 px** |
| | Transverse Width ($\bar{W}_{\text{px}}$) | 19.01 px | 19.80 px | +0.80 px | **4.74 px** |
| **Excluding 17 Empty Predictions ($N = 1,070$)** | Crack Length ($L_{\text{px}}$) | 739.99 px | 704.81 px | -35.18 px | **138.04 px** |
| | Transverse Width ($\bar{W}_{\text{px}}$) | 19.03 px | 20.11 px | +1.08 px | **4.54 px** |

- **Uncertainty Statements**:
  - Across all 1,087 images: *width uncertainty is about +-1 px from the method plus the model's per-image error (mean absolute error 4.7 px on Crack500 test).*
  - Across the 1,070 cracked predictions: *width uncertainty is about +-1 px from the method plus the model's per-image error (mean absolute error 4.5 px on Crack500 test non-empty predictions).*

#### Empirical Distribution Summary ($N = 1,070$ Cracked Predictions)
| Metric | Mean | Median (p50) | 95th Percentile (p95) |
| :--- | :---: | :---: | :---: |
| **Skeleton Length ($L_{\text{px}}$)** | 704.81 px | 676.66 px | 1322.84 px |
| **Mean Transverse Width ($\bar{W}_{\text{px}}$)** | 20.11 px | 18.80 px | 34.83 px |
| **Maximum Caliper Width ($W_{\max, \text{px}}$)** | 40.95 px | 38.73 px | 70.00 px |
| **95th Percentile Width ($W_{95, \text{px}}$)** | 34.42 px | 32.25 px | 61.90 px |
| **Crack Area ($A_{\text{px}}$)** | 13,516.25 px | 11,912.00 px | 29,692.00 px |
| **Surface Density (%)** | 5.87% | 5.17% | 12.89% |
| **Principal Orientation ($\theta_{\text{deg}}$)** | 90.14° | 89.55° | 178.01° |
| **Connected Components ($N_{\text{comp}}$)** | 1.98 | 1.00 | 5.00 |
| **Bifurcation Branch Points ($N_{\text{branch}}$)** | 10.68 | 7.00 | 30.55 |
| **Terminal Endpoints ($N_{\text{end}}$)** | 7.03 | 6.00 | 16.00 |

---

## C5. Milestone 2 Target vs. Actual Evaluation Matrix

The table below contrasts each performance target from the project plan against the actual results:

| Task / Domain | Target Metric | Plan Target | Actual Result Achieved | Target Status | Evidence & Persistent Files |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Classification (CCIC)** | Macro F1 | $\ge 85\%$ (0.85) | **0.9997** | **REACHED** | Computed from `test_predictions.csv` ($\text{F1}_{\text{crack}} = 0.9997, \text{F1}_{\text{no-crack}} = 0.9996$). |
| **Classification (SDNET)** | Macro F1 | $\ge 85\%$ (0.85) where dataset allows | **0.6421** | **NOT REACHED** | Computed from `test_predictions.csv` ($\text{F1}_{\text{crack}} = 0.4815, \text{F1}_{\text{no-crack}} = 0.8027$). Threshold $0.0100$ caused 2,429 false positives. |
| **Object Detection (RDD2022)** | mAP@50 | $\ge 85\%$ (0.85) | **0.4554** (val v8s)<br>0.4437 (val 11s) | **NOT REACHED** | Best validation mAP@50 is 0.4554. Test split not evaluated yet. |
| **Object Detection (RDD2022)** | Recall | $\ge 90\%$ (0.90) | **0.4528** (val v8s)<br>0.4161 (val 11s) | **NOT REACHED** | Best validation recall is 0.4528. Test split not evaluated yet. |
| **Segmentation (Crack500)** | Mean Dice | $\ge 85\%$ (0.85) | **0.6899** | **NOT REACHED** | Persisted in `crack500_test_metrics.json` ($N = 1,087$ test images). |
| **Segmentation (Crack500)** | Mean IoU | $\ge 75\%$ (0.75) | **0.5481** | **NOT REACHED** | Persisted in `crack500_test_metrics.json` ($N = 1,087$ test images). |
| **Inference Latency** | Latency per image | $< 3.0$ seconds on chosen GPU | **1.35 s** (host CPU) | **REACHED on CPU** | Persisted in `speed_and_size.json` ($1,349.14\,\text{ms}$ on CPU). GPU inference latency not recorded in test files. |
| **Geometry Extraction** | Unit Test Verification | 100% Passing | **6 / 6 Passed** | **REACHED** | Pytest test suite executed cleanly in 8.35s. |

---

## C6. Practical Technical Discussion

### 1. Classification
- On SDNET2018, enforcing the validation rule of $\text{Recall} \ge 0.90$ drove the operating threshold to $0.0100$, producing 2,429 false positives and reducing crack precision to $0.3247$ and Macro F1 to $0.6421$.
- Concrete Crack Images (`concrete_crack_cls`) contains 16.16% near-duplicate pairs (dHash $\le 2$). Excluding them yields an F1 of $0.9995$.

### 2. Detection
- Detection models achieved validation mAP@50 of $0.4554$ (YOLOv8s) and $0.4437$ (YOLO11s), and validation recall of $0.4528$ and $0.4161$.
- The test split has not been evaluated yet. Per-country test breakdowns and per-class test AP breakdowns were not evaluated because no test evaluation files exist.
- YOLOv8s is selected as the final detection model based on higher validation mAP@50:95 ($0.2220$ vs $0.2159$).

### 3. Segmentation
- Mean Dice was $0.6899$ on Crack500 test and $0.4533$ on CFD test.
- Mean crack width is $18.96\,\text{px}$ in Crack500 versus $4.38\,\text{px}$ in CFD.
- Segmentation performance decreases with decreasing crack width in both datasets (Crack500: $0.7308 \to 0.7095 \to 0.6296$; CFD: $0.5428 \to 0.4727 \to 0.3472$). Other causes were not tested.

### 4. Geometry
- 17 of 1,087 test images produced empty predicted masks after filtering, whereas all 1,087 ground truth masks contain cracks.
- Length MAE across all 1,087 images is $140.32\,\text{px}$ ($-39.06\,\text{px}$ signed mean error); excluding the 17 empty predictions, length MAE is $138.04\,\text{px}$ ($-35.18\,\text{px}$ signed mean error).
- Width MAE across all 1,087 images is $4.74\,\text{px}$ ($+0.80\,\text{px}$ signed mean error); excluding the 17 empty predictions, width MAE is $4.54\,\text{px}$ ($+1.08\,\text{px}$ signed mean error).
- Converting pixel measurements to physical units requires a known optical scale factor ($\text{mm/pixel}$); otherwise, all metric fields evaluate to `None`.
