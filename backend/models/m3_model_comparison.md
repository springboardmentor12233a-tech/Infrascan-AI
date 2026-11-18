
# InfraScan - Milestone 3 Model Comparison

## 1. Objective

To compare traditional machine learning and deep learning approaches for six-class infrastructure damage classification.

The evaluated models include HOG + Linear SVM, Custom CNN, ResNet18, and Lightweight Vision Transformer (ViT).

## 2. Dataset

- Total images: 8,000
- Training images: 5,598
- Validation images: 1,196
- Test images: 1,206
- Number of classes: 6

### Damage Classes

- D_CD
- D_UD
- P_CP
- P_UP
- W_CW
- W_UW

## 3. Model Performance Comparison

| Model | Test Accuracy | Macro F1 |
|---|---:|---:|
| HOG + Linear SVM | 35.07% | 0.3508 |
| Six-Class CNN | 48.18% | 0.4018 |
| ResNet18 | 67.00% | 0.6700 |
| Lightweight ViT | 59.12% | 0.5900 |

## 4. ResNet18 Class-wise Results

| Class | Precision | Recall | F1-score |
|---|---:|---:|---:|
| D_CD | 0.65 | 0.58 | 0.61 |
| D_UD | 0.61 | 0.65 | 0.63 |
| P_CP | 0.77 | 0.67 | 0.72 |
| P_UP | 0.67 | 0.76 | 0.71 |
| W_CW | 0.68 | 0.67 | 0.67 |
| W_UW | 0.67 | 0.71 | 0.69 |

## 5. Vision Transformer Configuration

- Architecture: Lightweight Vision Transformer
- Training approach: From scratch
- Pretrained weights: Not used
- Image size: 64 x 64
- Patch size: 8 x 8
- Embedding dimension: 128
- Transformer blocks: 4
- Attention heads: 4
- Epochs: 15
- Device: CPU
- Best validation accuracy: 56.10%

## 6. ViT Class-wise Results

| Class | Precision | Recall | F1-score |
|---|---:|---:|---:|
| D_CD | 0.5692 | 0.7164 | 0.6344 |
| D_UD | 0.5040 | 0.6219 | 0.5568 |
| P_CP | 0.6978 | 0.6318 | 0.6632 |
| P_UP | 0.7033 | 0.6368 | 0.6684 |
| W_CW | 0.5714 | 0.4577 | 0.5083 |
| W_UW | 0.5389 | 0.4826 | 0.5092 |

## 7. ViT Evaluation Metrics

- Test accuracy: 59.12%
- Macro precision: 59.74%
- Macro recall: 59.12%
- Macro F1-score: 59.00%
- Test images: 1,206

## 8. Conclusion

ResNet18 achieved the highest recorded test accuracy of approximately 67% and macro F1-score of approximately 0.67 among the evaluated models.

The Lightweight Vision Transformer achieved 59.12% test accuracy and 0.59 macro F1-score.

The results demonstrate that the ResNet18 model performed better than the evaluated ViT model on this dataset and experimental setup.

Further improvements in model architecture, training strategy, and dataset quality may improve classification performance.

These models are experimental prototypes and require further validation before real-world infrastructure safety applications.
