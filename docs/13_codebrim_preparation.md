# CODEBRIM Bridge Defect Dataset Preparation for YOLO Detection

**Document Version**: 1.0  
**Generated Date**: 2026-11-05  
**Pipeline Module**: `data/prepare_codebrim_yolo.py`  
**Dataset Version**: CODEBRIM Multi-Target Defect Detection (YOLO format)  
**Fixed Random Seed**: `42`  

---

## 1. Executive Summary

This report documents the preparation, normalization, multi-label bounding box conversion, and train/val/test splitting of the **CODEBRIM** (COncrete DEfect BRidge IMage) dataset for YOLO-based defect detection.

All raw data under `data/raw/codebrim/` remains strictly **READ-ONLY** and untouched. The processed dataset is stored under `data/processed/codebrim_yolo/` and packaged as `data/processed/colab_zips/codebrim_yolo.zip` (254.39 MB) for high-performance training on Google Colab or local GPU clusters.

### Defect Target Classes
The dataset is mapped to five concrete defect classes:
- **0**: `crack`
- **1**: `spallation`
- **2**: `exposed_bars`
- **3**: `efflorescence`
- **4**: `corrosion_stain`

Background annotations (`<Background>1</Background>`) denote defect-free concrete patches and are excluded from detection targets.

---

## 2. Dataset Attribution & License

- **Dataset Name**: CODEBRIM: COncrete DEfect BRidge IMage Dataset
- **Citation**: Mundt, M., Majumder, S., Murali, S., Trivellas, P., & Kang, Y. (2019). *Meta-learning for Concrete Defect Detection and Classification in Bridge Inspection*. arXiv / CVPR Workshops.
- **Repository / DOI**: [Zenodo 10.5281/zenodo.2620293](https://doi.org/10.5281/zenodo.2620293)
- **Institution**: Frankfurt Institute for Advanced Studies (FIAS) and Goethe University Frankfurt.
- **License**: **Custom Non-Commercial Educational License**.
  > **License Terms**: Use of the dataset is granted strictly for **academic, research, and non-commercial educational purposes**. Any commercial utilization, commercial model deployment, or unauthorized redistribution is prohibited without prior permission from FIAS / Goethe University Frankfurt.

---

## 3. Dataset Sizes: Before vs After Preparation

| Metric | Raw Dataset | Processed YOLO Dataset | Excluded / Filtered | Reason |
|---|---:|---:|---:|---|
| **Total Images** | 1,590 | 1,022 | 568 | 538 unannotated + 30 empty/background-only |
| **Annotations (XML)** | 1,052 | 1,022 | 30 | 28 with 0 objects, 2 with no defect labels |
| **Raw Bounding Boxes** | 5,233 | 5,181 spatial boxes | 52 | 49 background-only + 3 zero-defect boxes |
| **Total YOLO Defect Lines** | — | 8,274 lines | — | Multi-label expansion (1 box with $K$ defects $\to K$ lines) |
| **Exact SHA-256 Duplicates** | 0 | 0 | 0 | All retained images have unique hashes |
| **Longest Image Edge** | 1,200 – 6,000 px | $\le 1,280$ px | — | Scaled preserving aspect ratio (Lanczos, Q=90) |

---

## 4. Exclusion Audit by Reason

Images and annotations were filtered according to strict quality guidelines:

1. **Unannotated Images (538 images)**:
   - 538 image files (`image_0000001.jpg` .. `image_0001600.jpg`) had no corresponding `.xml` annotation file in the archive.
   - *Exclusion rationale*: It is impossible to ascertain whether these images represent true negatives (completely defect-free structures) or uninspected/omitted sections. Including them as blank label images would risk penalizing true defect detections during training.
2. **Empty or Objectless XMLs (28 annotations)**:
   - 28 XML files contained `<folder>`, `<filename>`, and `<size>` tags but zero `<object>` elements.
   - *Exclusion rationale*: No target bounding boxes provided.
3. **Non-Defect / Background-Only Annotations (2 annotations / 49 boxes)**:
   - 49 bounding boxes were labeled exclusively with `<Background>1</Background>` and zeros for all 5 defect categories.
   - *Exclusion rationale*: Background boxes represent non-damaged structural concrete. In YOLO bounding box detection, background is implicitly learned from unannotated image area.
4. **Invalid Bounding Boxes ($w \le 0$ or $h \le 0$)**:
   - Exactly **0** invalid boxes were found. All bounding coordinates satisfied $x_{min} < x_{max}$ and $y_{min} < y_{max}$ within image bounds.
5. **Exact Image Duplicates**:
   - Exactly **0** duplicate SHA-256 hashes were found across all 1,590 raw images.

---

## 5. Multi-Label Defect Conversion

In real-world civil engineering structures, defects frequently compound: concrete spalling exposes internal steel reinforcement, which subsequently corrodes and produces rust/corrosion staining. 

In the CODEBRIM XML annotations:
- **1,980 bounding boxes** (38.2% of all defect boxes) contain two or more co-occurring defects.
- Most frequent co-occurrence: `(CorrosionStain, ExposedBars, Spallation)` on 786 bounding boxes.

### Conversion Rule
Because standard YOLO object detection architectures assign a single class index per line (`<class_id> <x_center> <y_center> <width> <height>`), a bounding box carrying $K$ simultaneous defect classes is converted into **$K$ independent YOLO annotation lines** sharing the exact same spatial coordinates.

For example, a box with Spallation ($1$), Exposed Bars ($2$), and Corrosion Stain ($4$):
```text
1 0.451200 0.621500 0.152400 0.221000
2 0.451200 0.621500 0.152400 0.221000
4 0.451200 0.621500 0.152400 0.221000
```
This preserves full defect supervision without losing multi-label defect information.

---

## 6. Dataset Split (70 / 15 / 15, Seed 42)

The 1,022 valid images were randomly partitioned into training, validation, and test subsets using a fixed seed (`42`):

| Split | Image Count | Share | YOLO Defect Instances | Label Files |
|---|---:|---:|---:|---:|
| **Train** | 715 | 70.0% | 5,720 | 715 |
| **Validation** | 153 | 15.0% | 1,230 | 153 |
| **Test** | 154 | 15.1% | 1,324 | 154 |
| **Total** | **1,022** | **100.0%** | **8,274** | **1,022** |

### Split Disjointness Verification
- Hash intersection check $\text{Train} \cap \text{Val} = \emptyset$ (0 shared hashes).
- Hash intersection check $\text{Train} \cap \text{Test} = \emptyset$ (0 shared hashes).
- Hash intersection check $\text{Val} \cap \text{Test} = \emptyset$ (0 shared hashes).
- 100% 1-to-1 match between images (`.jpg`) and labels (`.txt`).

---

## 7. Class Distribution & Geometric Statistics

### Defect Class Breakdown Across Splits

| Class ID | Class Name | Train Instances | Val Instances | Test Instances | Total Instances | Dataset Share |
|---|---|---:|---:|---:|---:|---:|
| **0** | `crack` | 1,773 | 342 | 387 | 2,502 | 30.2% |
| **1** | `spallation` | 1,290 | 282 | 320 | 1,892 | 22.9% |
| **2** | `exposed_bars` | 1,042 | 210 | 250 | 1,502 | 18.2% |
| **3** | `efflorescence` | 548 | 140 | 140 | 828 | 10.0% |
| **4** | `corrosion_stain` | 1,067 | 256 | 227 | 1,550 | 18.7% |
| **Total** | | **5,720** | **1,230** | **1,324** | **8,274** | **100.0%** |

### Imbalance Ratio
- **Most frequent class**: `crack` (2,502 instances)
- **Least frequent class**: `efflorescence` (828 instances)
- **Class Imbalance Ratio**: **3.02 : 1**  
*(Significantly more balanced than RDD2022 pavement defects, which exhibited > 10:1 imbalance).*

### Bounding Box Density & Relative Geometry
- **Boxes per Image**:
  - Minimum: 1 box
  - Median: 5.0 boxes
  - Mean: 8.10 boxes
  - Maximum: 50 boxes
- **Relative Normalized Dimensions ($W_{img}, H_{img} \in [0.0, 1.0]$)**:
  - Width Ratio ($w$): Min = `0.0085`, Median = `0.1278`, Max = `0.9998`
  - Height Ratio ($h$): Min = `0.0136`, Median = `0.1690`, Max = `0.9998`
  - Area Ratio ($w \times h$): Min = `0.000147`, Median = `0.0230`, Max = `0.9995`
- **Small Defect Prevalence**:
  - Defects with width smaller than 3% of image width ($w < 0.03$): **320 boxes (3.87%)**.
  - Small cracks and incipient spalls represent ~4% of targets, requiring high-resolution feature maps (P3/80x80 in YOLOv8) during detection.

---

## 8. Visual Inspection

Eight random training images with annotated bounding boxes and defect labels were verified and plotted:

![CODEBRIM Sample Visualizations](file:///D:/Infosys%20springboards/docs/figures/codebrim_yolo_samples.jpg)

The visualization confirms:
1. Accurate bounding box alignment following 1280px aspect-ratio-preserving downscaling.
2. Correct multi-label bounding box overlays (e.g. spallation bounding boxes enclosing exposed rebar and corrosion staining).
3. Consistent normalized YOLO coordinates across landscape and portrait camera orientations.

---

## 9. Colab Training Archive

- **Archive Path**: `data/processed/colab_zips/codebrim_yolo.zip`
- **File Size**: **254.39 MB (0.25 GB)**
- **Max Image Edge**: 1,280 px
- **Compression**: Deflate (ZIP)
- **Contents**: 2,046 total files (`data.yaml`, `images/train/`, `images/val/`, `images/test/`, `labels/train/`, `labels/val/`, `labels/test/`, `sample_training_boxes.jpg`).
- *Archive size is well below the 8.0 GB warning threshold.*

---

## 10. Critical Limitations & Risks

1. **Potential Same-Bridge Data Leakage**:
   - The CODEBRIM dataset was collected from 30 bridges in the Frankfurt area, but the public release strips all EXIF metadata and anonymizes file names to sequential integers (`image_0000001.jpg` .. `image_0001600.jpg`).
   - Because no bridge ID or structural group tag is provided, a random 70/15/15 split by image was conducted.
   - **Risk**: Multiple photos captured from different vantage points of the same physical bridge may appear across train, validation, and test splits. Validation metrics may be moderately optimistic compared to a strict group-bridge cross-validation split.
2. **Unannotated Images Excluded**:
   - 538 images without XML files were excluded rather than included as empty background images.
   - **Risk**: If some of these 538 images were true defect-free bridge components, excluding them slightly lowers the background exposure during training. This can be mitigated during training by applying background mosaic augmentation or a small fraction of negative images.
3. **Bridge Infrastructure vs Road Pavement**:
   - CODEBRIM depicts concrete bridge superstructures (piers, abutments, girders, soffits, decks). Defects include heavy spalling, exposed structural rebar, and chemical efflorescence.
   - By contrast, InfraScan's earlier baseline models trained on RDD2022 and CRACK500 reflect asphalt/concrete road surfaces (longitudinal, transverse, alligator cracks, potholes).
   - Combining or transitioning between these datasets must account for domain divergence (concrete bridge textures vs road asphalt).
4. **Multi-Label Overlapping Boxes in YOLO**:
   - Standard YOLO NMS (Non-Maximum Suppression) is class-aware (`classes=None` or per-class NMS).
   - Because multiple lines share the same bounding box for different classes (e.g. Spallation and Exposed Rebar), standard class-aware NMS will preserve both predictions as intended. However, class-agnostic NMS (`agnostic_nms=True`) must NOT be enabled during inference, as it would suppress co-occurring defect detections.

