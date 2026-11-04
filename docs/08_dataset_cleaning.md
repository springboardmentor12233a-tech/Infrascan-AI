# InfraScan Dataset Cleaning, Splitting & Label Conversion Report

**Generated Date**: 2026-10-25  
**Pipeline Module**: `infrascan/ml/data_prep.py`  
**Notebook Verification**: `data/notebooks/04_dataset_cleaning.ipynb`  
**Fixed Random Seed**: `42`  

---

## 1. Executive Summary

This report documents the rigorous data cleaning, deduplication, group splitting, and label conversion executed for the **InfraScan** crack detection project. All raw data (`data/raw/`) remains strictly **READ-ONLY** and untouched. Standardized manifests, reports, and converted YOLO detection datasets are generated under `data/processed/`.

All source files under `data/raw/` were treated as read-only. Cleaning exclusions and skipped annotation
items are recorded in `data/processed/reports/cleaning_report.csv`. Integrity assertions were run after
conversion, including hash disjointness across splits, manifest path checks, and YOLO label bounds.

---

## 2. Dataset Sizes: Before vs After Cleaning

| Dataset | Candidates before cleaning | Kept | Excluded |
|---|---:|---:|---:|
| SDNET2018 (classification) | 56,092 | 56,079 | 13 |
| concrete_crack_cls (classification) | 40,000 | 38,402 | 1,598 |
| RDD2022 (object detection) | 38,385 | 38,384 | 1 |
| CRACK500 (segmentation) | 3,368 | 3,288 | 80 |
| CFD (external test) | 118 | 118 | 0 |

---

## 3. Exclusion Audit by Reason (`cleaning_report.csv`)

A total of **12398 exclusion and annotation audit records** were logged. The breakdown by dataset and reason:

```
reason              duplicate_hash  invalid_box  source_photo_split_overlap  unsupported_class
dataset                                                                                       
concrete_crack_cls            1598            0                           0                  0
crack500                         0            0                          80                  0
rdd2022                          1            1                           0              10705
sdnet2018                       13            0                           0                  0
```

Duplicate images, unreadable inputs, missing labels, mismatched image-mask sizes, and invalid annotation
items are never deleted from raw storage; affected entries are excluded or skipped only in processed outputs.

---

## 4. Dataset Splits & Class Distributions (`split_summary.csv`)

           dataset                          task split            class_name  count  total_in_split imbalance_ratio
         sdnet2018                classification  test               cracked   1255            8802          6.01:1
         sdnet2018                classification  test             uncracked   7547            8802          6.01:1
         sdnet2018                classification train               cracked   5996           38495          5.42:1
         sdnet2018                classification train             uncracked  32499           38495          5.42:1
         sdnet2018                classification   val               cracked   1230            8782          6.14:1
         sdnet2018                classification   val             uncracked   7552            8782          6.14:1
concrete_crack_cls                classification  test               cracked   2952            5760          1.05:1
concrete_crack_cls                classification  test             uncracked   2808            5760          1.05:1
concrete_crack_cls                classification train               cracked  13779           26881          1.05:1
concrete_crack_cls                classification train             uncracked  13102           26881          1.05:1
concrete_crack_cls                classification   val               cracked   2953            5761          1.05:1
concrete_crack_cls                classification   val             uncracked   2808            5761          1.05:1
           rdd2022      object_detection (boxes) train                   D00  18160           38534          3.92:1
           rdd2022      object_detection (boxes) train                   D10   8300           38534          3.92:1
           rdd2022      object_detection (boxes) train                   D20   7444           38534          3.92:1
           rdd2022      object_detection (boxes) train                   D40   4630           38534          3.92:1
           rdd2022     object_detection (images) train background (no crack)  10236           26869               -
           rdd2022      object_detection (boxes)   val                   D00   3855            8105          4.26:1
           rdd2022      object_detection (boxes)   val                   D10   1818            8105          4.26:1
           rdd2022      object_detection (boxes)   val                   D20   1527            8105          4.26:1
           rdd2022      object_detection (boxes)   val                   D40    905            8105          4.26:1
           rdd2022     object_detection (images)   val background (no crack)   2227            5759               -
           rdd2022      object_detection (boxes)  test                   D00   3998            8363          3.96:1
           rdd2022      object_detection (boxes)  test                   D10   1711            8363          3.96:1
           rdd2022      object_detection (boxes)  test                   D20   1645            8363          3.96:1
           rdd2022      object_detection (boxes)  test                   D40   1009            8363          3.96:1
           rdd2022     object_detection (images)  test background (no crack)   2155            5756               -
          crack500 segmentation (images by mask)  test     images_with_crack   1087            1087           inf:1
          crack500 segmentation (images by mask)  test  images_without_crack      0            1087           inf:1
          crack500 segmentation (images by mask) train     images_with_crack   1860            1860           inf:1
          crack500 segmentation (images by mask) train  images_without_crack      0            1860           inf:1
          crack500 segmentation (images by mask)   val     images_with_crack    341             341           inf:1
          crack500 segmentation (images by mask)   val  images_without_crack      0             341           inf:1
               cfd segmentation (images by mask)  test     images_with_crack    118             118           inf:1
               cfd segmentation (images by mask)  test  images_without_crack      0             118           inf:1

---

## 5. Documented Limitations & Recommendations

1. **Possible crop leakage**: `concrete_crack_cls` is split randomly by class because source-photo identifiers are unavailable; related crops may cross splits.
2. **RDD2022 country coverage**: 7 labeled country folders are available (China_Drone, China_MotorBike, Czech, India, Japan, Norway, United_States). Countries contribute to each split, so this split does not measure generalization to unseen countries.
3. **CRACK500 source partitions**: only the official `traincrop`, `valcrop`, and `testcrop` image-mask pairs are used; surviving rows keep their official train/val/test assignment. Full-size folders and `fphb_testresult` outputs are excluded. 80 crop images from 6 source photos spanning official partitions were excluded to prevent source-photo leakage.
4. **Official split proportions**: CRACK500's official crop partition sizes are preserved and therefore are not forced to a 70/15/15 ratio.
5. **Segmentation domain**: CRACK500 and CFD are road-surface data; results may not generalize to concrete walls, bridges, or other non-road structures.
