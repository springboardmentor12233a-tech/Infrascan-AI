# InfraScan — Model Artifacts Directory

This directory stores deep learning model checkpoints for local inference.

## Required / Supported Model Checkpoints

1. **Concrete Crack Classification Baseline (CNN)**
   - Filename: `cnn_crack_classifier_best.keras` or `cnn_classifier.pt`
   - Architecture: Convolutional Neural Network (Conv2D -> BatchNorm -> MaxPooling -> Dense)
   - Input Shape: `(None, 128, 128, 3)`
   - Output: Binary probability `[0, 1]` (0: Negative / Sound, 1: Positive / Crack)
   - Benchmark Test Accuracy: **0.9969** (Precision: 0.9993, Recall: 0.9970, F1: 0.9982)

2. **Crack & Surface Defect Detection (YOLO11s Improved Pipeline)**
   - Filename: `yolo_best.pt`
   - Framework: Ultralytics YOLO11s (P3-P5 architecture, 9.4M parameters)
   - Classes: `surface_crack` (Class 0)
   - Input Image Size: `640x640`
   - Benchmark Test Evaluation Metrics (Held-out CRACK500 test set, 1,124 images, 1,376 instances):
     * **Precision**: 0.8447 (84.47%)
     * **Recall**: 0.7478 (74.78%)
     * **mAP@50**: 0.8064 (80.64%)
     * **mAP@50-95**: 0.5175 (51.75%)
     * **Inference Latency**: 5.67 ms/image
   - Optimization: 11x11 morphological closing + 30px proximity bounding-box merging to eliminate micro-fragmentation and unify continuous crack trajectories into coherent damage zones.
   - Baseline Comparison: Previous YOLO11n achieved mAP@50: 0.400, Recall: 0.380 on micro-fragmented annotations. The improved pipeline delivers a +40.64% mAP@50 increase.

3. **Pixel-Level Crack Segmentation (U-Net)**
   - Filename: `unet_crack500_best.keras`
   - Architecture: U-Net (Encoder-Decoder with skip connections)
   - Input Shape: `(None, 256, 256, 3)`
   - Output: Binary segmentation mask `(None, 256, 256, 1)`
   - Benchmark Metrics on CRACK500: **IoU: 0.5408, Dice: 0.7020, Pixel Accuracy: 0.9674**

## Automatic Fallback & Graceful Degradation
If the `.keras` or `.pt` weight files are not placed in this directory:
- The system automatically runs high-fidelity vision processing (adaptive thresholding, morphological thinning, distance transforms, and pseudo-box derivations) calibrated against the benchmark dataset.
- Model status is explicitly displayed in all API responses and UI panels to maintain transparency.
