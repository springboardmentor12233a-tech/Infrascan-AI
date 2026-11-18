# InfraScan – Milestone 3 U-Net Evaluation

## Evaluation Objective
To evaluate the improved U-Net model for concrete crack segmentation.

## Evaluation Dataset
- Validation images: 24
- Model: Improved U-Net
- Threshold: 0.5

## Evaluation Metrics

| Metric | Result |
|---|---:|
| IoU | 36.83% |
| Dice Score | 53.83% |
| Pixel Accuracy | 98.29% |

## Conclusion
The improved U-Net achieved 98.29% pixel accuracy, 36.83% IoU and 53.83% Dice score on the validation dataset.

Pixel accuracy is high, but IoU and Dice indicate that crack-region overlap still needs improvement. Further segmentation validation is required before using the extracted measurements for reliable damage severity assessment.