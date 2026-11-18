# Milestone 3 – U-Net Segmentation Experiments

## 1. Objective
Compare two segmentation dataset configurations to evaluate their effect on crack segmentation performance.

## 2. Experimental Configurations

### Experiment A – Label 2 Only
- Training images: 94
- Validation images: 24
- Validation IoU: 36.83%
- Validation Dice: 53.83%
- Checkpoint: m3_unet_label2_only.pth

### Experiment B – Label 2 + Label 4
- Training images: 94
- Validation images: 24
- Validation IoU: 34.62%
- Validation Dice: 51.43%
- Checkpoint: m3_unet_label2_plus4.pth

## 3. Comparison

Experiment A achieved higher validation IoU and Dice scores than Experiment B.

Adding label 4 did not improve the reported validation metrics.

## 4. Preliminary Conclusion

Label 2 Only is the better-performing configuration based on the current validation results.

Visual inspection and further validation are required before selecting the final segmentation configuration.

## 5. Limitations
- The segmentation dataset contains only 118 images.
- Results are based on a small validation set of 24 images.
- Each experiment was evaluated against its own ground-truth masks.
- Therefore, the metrics are not a perfectly controlled comparison of predictions against identical targets.
- Physical crack measurements require image calibration.

## 6. Generated Artifacts
- m3_unet_label2_only.pth
- m3_unet_label2_plus4.pth
- m3_unet_experiment_results.json
- m3_unet_ab_visual_comparison.png
