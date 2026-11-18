# Milestone 3 – Explainable AI (Grad-CAM)

## 1. Objective
To visualize the image regions that influence the ResNet18 crack classification model's predictions.

## 2. Model Details
- Model: ResNet18
- Checkpoint: m3_resnet18.pth
- Explainability technique: Grad-CAM
- Target layer: Final convolutional block (layer4)
- Input image size: 224 × 224

## 3. Experiment Result
- Test image: 7001-26.jpg
- Predicted class: D_CD
- Prediction confidence: 45.62%

## 4. Visualization
Generated a Grad-CAM heatmap and overlay to highlight image regions contributing to the model prediction.

Output: m3_resnet18_gradcam.png

## 5. Observation
The heatmap highlights a region near a visible surface defect. However, the activation is broad and the prediction confidence is relatively low. Further testing on multiple images is required.

## 6. Conclusion
Grad-CAM provides a visual explanation of the ResNet18 classification output. It helps inspect model attention but does not independently verify prediction correctness.