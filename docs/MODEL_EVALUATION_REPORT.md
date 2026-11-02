# Model evaluation report

All numbers below were printed by the training scripts on 2026-11-02 and saved under `models/reports/`. Nothing in this file was typed in by hand as a target score.

Device: CPU. Python 3.12.10. torch 2.15.0+cpu. ultralytics 8.4.198.

Do not compare F1, Dice, and mAP as if they were the same kind of score. Each metric belongs to a different task.

## SmallCNN — binary patch classification

| Item | Value |
|---|---|
| File | `models/weights/crack_cnn.pt` (gitignored; regenerate with the train script) |
| Report | `models/reports/classifier_metrics.json` |
| Dataset | DeepCrack local image-mask pairs |
| Split | Group-aware by source id, seed 42. Published train/test split was not used. `group_overlap` is empty. 48 train images, 12 val images. |
| Input | 64×64 RGB patches, ImageNet normalization |
| Labels | Crack if the patch crack fraction is at least 0.02. Non-crack only if the fraction is 0. |
| Samples | Up to 6 patches per class per image. Train patches 575 (crack rate 0.50). Val patches 144. |
| Architecture | Three conv-BN-ReLU-pool blocks, global average pool, linear layer to 2 classes |
| Optimisation | Adam, learning rate 0.001, batch 32, 8 epochs, cross-entropy, CPU |
| Selection | Highest validation F1. That was epoch 6. |

Official validation metrics (the checkpoint that was saved):

| Accuracy | Precision | Recall | F1 | Support |
|---:|---:|---:|---:|---:|
| 0.8194 | 0.7949 | 0.8611 | 0.8267 | 144 |

Confusion matrix, rows are truth and columns are prediction, order non-crack then crack:

|  | Pred non-crack | Pred crack |
|---|---:|---:|
| True non-crack | 56 | 16 |
| True crack | 10 | 62 |

Epoch log (validation F1): 0.7453, 0.7820, 0.8158, 0.7784, 0.8158, 0.8267, 0.7424, 0.7727.

Limitations: the score is on patches, not whole photos. Negative patches are background inside crack photographs. SDNET2018 and METU were not available. Only a capped image subset was used.

`evaluation_summary.json` also contains a seed-7 check (accuracy 0.875 on 32 patches). That file marks `"official": false`. Those groups can overlap images the network already saw. Quote the table above.

## U-Net — binary crack segmentation

| Item | Value |
|---|---|
| File | `models/weights/unet_deepcrack.pt` |
| Report | `models/reports/unet_metrics.json` |
| Dataset | DeepCrack image-mask pairs |
| Split | Same group rule, seed 42, `group_overlap` empty. 36 train images, 8 val images. |
| Input | 128×128. Image resized with `INTER_AREA`, mask with `INTER_NEAREST`. Horizontal flip is applied to both. |
| Loss | Binary cross-entropy with logits plus soft Dice |
| Architecture | Compact U-Net, 8 base channels, 3 encoder stages. Spatial size must be divisible by 8. |
| Optimisation | Adam, learning rate 0.001, batch 4, 6 epochs, CPU |
| Selection | Highest validation Dice. That was epoch 6. |

Official validation metrics on the resized 128×128 masks:

| Dice | IoU | Images |
|---:|---:|---:|
| 0.4316 | 0.3449 | 8 |

Epoch Dice: 0.3234, 0.3396, 0.3863, 0.4298, 0.4091, 0.4316.  
Epoch IoU: 0.2465, 0.2690, 0.2974, 0.3341, 0.3182, 0.3449.

A live run on `11120.jpg` produced a mask of 1,419 crack pixels (0.6793% of the image). The red overlay follows part of the crack and misses a large part of it. That agrees with a Dice near 0.43.

`evaluation_summary.json` records Dice 0.7435 and IoU 0.5932 on 6 images with seed 7. That sample is marked unofficial. Quote 0.4316 and 0.3449.

Empty predicted and empty target masks would score Dice 1.0 in `dice_iou`. The training validation images were not empty.

## YOLOv8n — bounding-box detection

| Item | Value |
|---|---|
| File | `models/weights/yolo_rdd.pt` |
| Report | `models/reports/yolo_metrics.json` |
| Dataset | RDD2022 Czech labeled training images only |
| Preparation | `scripts/ml/prepare_yolo.py` saw 2,829 XML files and 1,072 images with boxes. It copied 60 train and 20 val images into `datasets/processed/rdd2022_yolo` (gitignored). Unknown classes skipped: 0. |
| Class ids | 0 D00 longitudinal, 1 D10 transverse, 2 D20 alligator, 3 D40 pothole |
| Start weights | Official `yolov8n.pt` (COCO, 6.2 MB), then fine-tuned. Inference loads `yolo_rdd.pt` only. |
| Config | 5 epochs, image size 320, batch 8, workers 0, CPU, AdamW chosen by Ultralytics (lr 0.00125) |
| API threshold | 0.25 |

Saved validation metrics:

| Precision | Recall | mAP50 | mAP50-95 |
|---:|---:|---:|---:|
| 0.0006 | 0.1146 | 0.0004 | 0.0001 |

Per-class lines printed by Ultralytics on `best.pt` are in `docs/MILESTONE_2_COMPLETION_REPORT.md`. D10, D20, and D40 were all zero. D00 recall was 0.458 with precision 0.00226, which means the few D00 hits came with a very large number of false boxes at the validator’s low confidence.

Live inference at confidence 0.25 returned 0 boxes on both `11120.jpg` and `Czech_000261.jpg`.

This is a working training and inference pipeline with a weak model. It is not a detector you can trust in a field inspection.

## Which baseline to describe as the best

SmallCNN is the best of the three for a demonstration of learning. Its validation F1 is 0.8267 on a balanced patch set, and the confusion matrix shows both classes are recognised. State clearly that the negatives are background patches.

U-Net is a real segmentation baseline with modest overlap (Dice 0.4316). Show it on a close-up crack photo.

YOLOv8n is the right architecture for boxes, and this training run did not produce a usable detector. Say that directly.

## What the live street photo showed

`Czech_000261.jpg` was classified as crack with confidence 0.997, and the U-Net marked 35.1608% of the pixels as crack, including sky and roadway in the overlay. Those models never trained on dashboard road scenes. The number is a real model output and a poor description of the road.
