InfraScan — Exploratory Data Analysis (EDA)

1. Dataset Overview

- Dataset: SDNET2018
- Total images: 56,092
- Image dimensions: 256 × 256 pixels
- Unreadable images: 0

2. Class Distribution

Class| Number of Images
Cracked Deck| 2,025
Uncracked Deck| 11,595
Cracked Pavement| 2,608
Uncracked Pavement| 21,726
Cracked Wall| 3,851
Uncracked Wall| 14,287
Total| 56,092

3. Cracked vs. Uncracked Distribution

- Cracked images: 8,484 (15.12%)
- Uncracked images: 47,608 (84.88%)

The dataset has a noticeable class imbalance, with uncracked images substantially outnumbering cracked images.

4. Image Quality Analysis

All 56,092 images were checked. The analysis reported zero unreadable images, and all images were reported at 256 × 256 pixels.

5. Visual Analysis

Random sample images were displayed, and a bar chart was created to visualize the six-class distribution.

6. Conclusion

The initial EDA of SDNET2018 is complete. The dataset contains six classes representing cracked and uncracked deck, pavement, and wall surfaces. The class distribution is imbalanced, which should be considered when preparing and evaluating a classification model.

Next step: Review dataset preparation and create appropriate training, validation, and test splits when required by the project workflow.
7. Selected 8,000-Image Dataset Split

The selected dataset contains 8,000 images across six classes.

| Split | Number of Images |
|---|---:|
| Training | 5,598 |
| Validation | 1,196 |
| Testing | 1,206 |
| Total | 8,000 |

Class folders:
- D_CD
- D_UD
- P_CP
- P_UP
- W_CW
- W_UW

The split is used for preliminary model development and evaluation.
The HOG + SVM baseline achieved 35.07% test accuracy.
This is a preliminary result, not the target accuracy of 99%.
