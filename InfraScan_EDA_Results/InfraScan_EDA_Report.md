# InfraScan — Exploratory Data Analysis Report

## 1. Dataset Overview
- Dataset: SDNET2018
- Total images: 56,092
- Image format: JPEG
- Image dimensions: 256 x 256
- Color mode: RGB
- Readable images: 56,092
- Corrupt/unreadable images: 0

## 2. Class Distribution
| Class | Images | Percentage |
|---|---:|---:|
| Cracked | 8,484 | 15.13% |
| Uncracked | 47,608 | 84.87% |

The dataset is imbalanced, with approximately 5.61 uncracked images
for every cracked image.

## 3. Surface Distribution
| Surface | Cracked | Uncracked | Total |
|---|---:|---:|---:|
| Deck | 2,025 | 11,595 | 13,620 |
| Pavement | 2,608 | 21,726 | 24,334 |
| Wall | 3,851 | 14,287 | 18,138 |

## 4. Exact Duplicate Analysis
SHA-256 analysis identified 13 exact duplicate groups and 13 extra
duplicate files. Two groups have conflicting binary labels:
- D/CD/7039-112.jpg and D/UD/7039-112_2.jpg
- W/CW/7074-105.jpg and W/UW/7074-105_2.jpg

These pairs require review. No files or labels were automatically changed.

## 5. Image Quality Analysis
Brightness, grayscale contrast and Laplacian variance were calculated
for all 56,092 images.

Overall summary:
- Mean brightness: 162.56
- Median brightness: 166.56
- Mean contrast: 14.98
- Median contrast: 10.95
- Mean Laplacian variance: 248.32
- Median Laplacian variance: 79.82

Very low brightness, contrast or Laplacian variance can indicate images
that deserve inspection. These metrics alone do not prove an image is
bad or blurry.

## 6. Class-wise Quality
Cracked:
- Mean brightness: 167.45
- Median brightness: 171.45
- Mean contrast: 14.86
- Median contrast: 10.93
- Mean Laplacian variance: 230.25
- Median Laplacian variance: 81.05

Uncracked:
- Mean brightness: 161.69
- Median brightness: 165.65
- Mean contrast: 15.00
- Median contrast: 10.96
- Mean Laplacian variance: 251.54
- Median Laplacian variance: 79.43

## 7. Surface-wise Median Quality
| Surface | Brightness | Contrast | Laplacian Variance |
|---|---:|---:|---:|
| Deck | 177.62 | 7.49 | 47.23 |
| Pavement | 155.54 | 21.67 | 367.88 |
| Wall | 168.51 | 7.73 | 34.86 |

Surface-wise differences may reflect different textures and image
characteristics; they should not automatically be interpreted as defects.

## 8. Perceptual Hash Analysis
- Candidate pairs with Hamming distance <= 5: 300
- Pairs with identical perceptual hashes: 18
- Candidate pairs with different binary labels: 122

These are similarity candidates, not 300 confirmed duplicate pairs.
Different labels do not by themselves prove incorrect annotations.
Visual verification and duplicate-group analysis are still required.

## 9. Limitations and Next Steps
1. Review exact duplicates and conflicting labels.
2. Verify near-duplicate candidates before making data changes.
3. Prevent duplicate or related images from crossing dataset splits.
4. Use a stratified, leakage-aware train/validation/test split.
5. Establish a baseline image classifier.
6. Evaluate precision, recall, F1-score, confusion matrix and PR-AUC,
   alongside accuracy, because the classes are imbalanced.

This report records the current EDA findings. It does not claim that
near-duplicate candidates have all been manually verified.