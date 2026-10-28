
# InfraScan Dataset Information

## Dataset Name
SDNET2018

## Purpose
To study concrete surface images and identify whether visible cracks are present.

## Image Categories
- Cracked concrete
- Non-cracked concrete

## Project Usage
The dataset is used for initial dataset exploration and analysis in Milestone 1. It also supports preliminary crack classification experiments.

## Analysis Plan
- Understand the dataset folder structure.
- Count the available images.
- Examine cracked and non-cracked categories.
- Check image dimensions and quality.
- Prepare training, validation, and testing splits.
- Establish a preliminary classification baseline.

## Source
https://digitalcommons.usu.edu/all_datasets/48/

## Download Status
- Dataset: SDNET2018
- Downloaded and extracted successfully.
- Images are present in D, W, and P folders.

## Exploratory Data Analysis (EDA)

### Dataset Image Count
- D folder: 13,520 images
- P folder: 24,534 images
- W folder: 18,138 images
- Total images: 56,092

### Initial Observation
The SDNET2018 dataset contains 56,092 images organized into three main folders: D, P, and W. The image counts were verified using a Python script.

### Subfolder Analysis
- The Python script successfully listed image counts for the subfolders inside D, P, and W.
- The dataset contains subfolders such as CD and UD.
- The dataset includes cracked and uncracked concrete images.

### Dataset Documentation Findings
- Full name: Structural Defects Network 2018 (SDNET2018)
- Total images: 56,092 JPG images
- Image categories: Cracked and non-cracked concrete surfaces
- Image sources: Bridge decks, walls, and pavements
- Class folders include CD, UD, CW, UW, CP, and UP.

## Selected Dataset Split

For preliminary model development, an 8,000-image subset was prepared from the original dataset.

| Split | Number of Images |
|---|---:|
| Training | 5,598 |
| Validation | 1,196 |
| Testing | 1,206 |
| Total | 8,000 |

### Class Folders
- D_CD
- D_UD
- P_CP
- P_UP
- W_CW
- W_UW

The selected split is stored in `dataset/split_data`.

## Preliminary Classification Baseline

- Model: Support Vector Machine (SVM)
- Feature extraction: Histogram of Oriented Gradients (HOG)
- Test accuracy: 35.07%
- Status: Preliminary six-class classification baseline

The baseline provides an initial performance reference for future model improvements. The project's 99% accuracy target has not yet been achieved.

## Image Quality and Limitations

- The existing EDA summary reports image dimensions of 256 × 256 pixels.
- The existing EDA summary reports zero unreadable images.
- The original dataset has an imbalanced class distribution.
- Further experiments are needed to improve classification performance and evaluate more advanced models.

## Related Documentation
- `dataset/eda-summary.md` — dataset exploration, class distribution, and split summary.
- `dataset/eda_analysis.py` — EDA analysis script.
