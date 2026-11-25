# Explainable AI (XAI) for Structural Health Monitoring

> **MANDATORY CRITICAL DISCLAIMER**  
> **Attention maps show which image regions influenced the model's output. They do not prove that a defect is present or that the model is correct. AI result for engineer review, not a final structural safety verdict.**  
> Explainability heatmaps are diagnostic tools designed to inspect model behaviour, diagnose false alarms, and assist licensed civil engineers during structural triage. They do NOT replace physical inspections, destructive/non-destructive testing (NDT), or formal engineering certification.

---

## 1. Why Explainability is Needed in Civil Infrastructure

Deep neural networks excel at extracting visual defect patterns from high-resolution imagery, but their unconstrained black-box nature creates fundamental obstacles in high-stakes civil engineering:

1. **Human-in-the-Loop Verification and Triage**:
   A licensed civil engineer cannot rely on an ungrounded bounding box or binary mask when evaluating critical infrastructure like bridge piers, deck slabs, and retaining walls. Heatmaps reveal whether a model's prediction is anchored in genuine surface distress (e.g., crack fissure, spall cavity, exposed rebar) or spurious confounding artifacts (e.g., expansion joints, formwork seams, shadows, tire marks, oil stains, or electrical conduit).

2. **Legal Liability and Regulatory Compliance**:
   Infrastructure safety signoffs carry statutory and professional liability. Building codes and municipal infrastructure authorities (e.g., FHWA, AASHTO, IRC) require auditable inspection records. An opaque automated severity score without an interpretable causal trail cannot be admitted as evidence during regulatory audits or forensic failure investigations.

3. **Diagnosing Model Failure Modes**:
   When a model generates a false alarm or misses an existing structural defect, attention maps illuminate *why* the failure occurred. If the model focuses on wet asphalt instead of a longitudinal crack, inspection teams can flag the domain shift and feed targeted hard-negative samples back into the active learning loop.

---

## 2. Supported XAI Methods

InfraScan integrates four complementary explainability techniques across its semantic segmentation, road damage detection, bridge defect detection, and concrete crack classification pipelines:

### 2.1 Grad-CAM (Gradient-Weighted Class Activation Mapping)
*Reference: Selvaraju et al., "Grad-CAM: Visual Explanations from Deep Networks via Gradient-Based Localization", ICCV 2017.*

$$\alpha_k^c = \frac{1}{Z} \sum_{i} \sum_{j} \frac{\partial Y^c}{\partial A_{i,j}^k}, \quad L_{\text{Grad-CAM}}^c = \text{ReLU}\left(\sum_k \alpha_k^c A^k\right)$$

Grad-CAM computes the gradient of a target score $Y^c$ (such as the sum of crack logits inside a predicted segmentation mask) with respect to feature activation maps $A^k$ of a selected convolutional layer. Global average pooling of these gradients yields importance weights $\alpha_k^c$, capturing the relative significance of each channel. A rectified linear combination retains only features that positively influence the target class.  
- **Best For**: Coarse localization of semantic crack features and classification decisions.  
- **Failure Mode**: When multiple instances of defects coexist, gradients can average out, leading to uniform or under-emphasized activation on smaller defects.

### 2.2 Grad-CAM++ (Generalized Gradient-Weighted Class Activation Mapping)
*Reference: Chattopadhay et al., "Grad-CAM++: Generalized Gradient-Based Visual Explanations for Deep Convolutional Networks", WACV 2018.*

$$\alpha_k^c = \sum_{i} \sum_{j} w_{i,j}^{kc} \cdot \text{ReLU}\left(\frac{\partial Y^c}{\partial A_{i,j}^k}\right)$$

Grad-CAM++ extends Grad-CAM by taking a higher-order weighted average of positive partial derivatives via pixel-wise weighting coefficients $w_{i,j}^{kc}$. This formulation explicitly weights second- and third-order gradients, allowing the method to delineate multiple distinct occurrences of the same defect class and capture fine-grained defect substructures.  
- **Best For**: Dispersed cracking, multi-branch network cracks, and irregular spallation boundaries.  
- **Failure Mode**: Computationally heavier; higher sensitivity to local gradient noise.

### 2.3 Captum Saliency (Input Gradient Saliency)
*Reference: Simonyan et al., "Deep Inside Convolutional Networks: Visualising Image Classification Models and Saliency Maps", ICLR 2014.*

$$S(x) = \left\| \frac{\partial Y^c}{\partial x} \right\|_{\infty} \quad \text{or} \quad \max_{c \in \{R,G,B\}} \left| \frac{\partial Y^c}{\partial x_c} \right|$$

Saliency maps compute the first-order gradient of the target class score directly with respect to input image pixels $x$. By taking the maximum absolute gradient across color channels, it pinpoints input pixels whose perturbation maximally alters the model's confidence.  
- **Best For**: High-frequency edge inspection and micro-crack tracing at native pixel resolution.  
- **Failure Mode**: Highly susceptible to gradient saturation, high-frequency visual noise, and visual checkerboard patterns in deep networks.

### 2.4 EigenCAM (Class-Agnostic Principal Feature Visualization)
*Reference: Muhammad & Yeasin, "Eigen-CAM: Class-Activation Map using Principal Components", IJCNN 2020.*

$$A = \sum_k A^k, \quad \mathbf{V}_1 = \text{SVD}(A), \quad L_{\text{Eigen-CAM}} = \text{Projection}(A, \mathbf{V}_1)$$

EigenCAM visualizes the principal components of feature activations by applying 2D Singular Value Decomposition (SVD) directly to the convolutional feature maps. It computes the first principal component without requiring backward gradient computation or class scores, making it inherently robust to gradient vanishing, label switching, or complex multi-head outputs.  
- **Best For**: Real-time explainability on single-stage detectors (YOLOv8s, RT-DETR-L) and multi-class bridge defect detection.  
- **Failure Mode**: Class-agnostic; highlights the most visually salient object in the feature map regardless of whether it is the defect of interest.

---

## 3. Model Architectures & Target Layer Selection

The target layer must be the deepest convolutional layer preceding classification heads, global pooling, or decoding bottlenecks. Deep layers encode rich high-level semantic abstractions while still preserving vital 2D spatial coordinate topology:

| Model Task | Architecture | Target Layer Module | Layer Description | Spatial Downsampling |
| :--- | :--- | :--- | :--- | :--- |
| **Crack Segmentation** | U-Net++ (ResNet-34) | `model.encoder.layer4[-1]` | Final `BasicBlock` of ResNet-34 encoder | 32× downsampling |
| **Road Damage Detection** | YOLOv8s (`DetectionModel`) | `model.model.model[21]` | Final `C2f` convolutional block before `Detect` head | 32× downsampling |
| **Bridge Defect Detection**| RT-DETR-L (`RTDETRDetectionModel`)| `model.model.model[27]` | Final `RepC3` block before transformer decoder | 32× downsampling |
| **Crack Classification** | ResNet-50 (`torchvision`) | `model.layer4[-1]` | Final `Bottleneck` block before average pooling | 32× downsampling |

### Justification:
- **Spatial Resolution**: Selecting shallower layers (e.g. `layer1` or `layer2`) yields fine spatial resolution but lacks semantic specificity, highlighting every trivial high-contrast texture or pebble.
- **Semantic Richness**: Selecting the final convolutional stage (`layer4[-1]`) ensures that activations correspond to learned defect concepts (e.g., interconnected fissures, spall perimeter) rather than generic image gradients.
- **Head Independence**: In object detectors (YOLOv8 and RT-DETR), explaining layers inside the anchor-free detection heads produces multi-scale tensor mismatches. Pointing to the final backbone/neck fusion stage (`model[21]` and `model[27]`) reliably captures pre-detection spatial attention.

---

## 4. Reading and Interpreting Attention Heatmaps

### Color Scale & Normalization
InfraScan normalizes all attention maps per-image into $[0.0, 1.0]$ using min-max scaling:

$$H_{\text{norm}}(i, j) = \frac{H(i, j) - \min(H)}{\max(H) - \min(H) + 10^{-7}}$$

The normalized map is mapped to the standard **JET** pseudo-color palette and alpha-blended ($\alpha = 0.50$) with the original BGR inspection photo:

```
[0.0: Blue / Cyan] ---------> [0.5: Green / Yellow] ---------> [1.0: Deep Red]
 Low / Zero Influence             Moderate Activation              Maximum Attention
```

### What High Attention Means:
- **Causal Influence**: The model's internal feature activations in the red/yellow regions exerted the greatest mathematical pull on the predicted output (crack probability or bounding box confidence).
- **Spatial Alignment**: Indicates whether the neural network detected the defect using the actual physical distress structure or if it was misled by contextual background cues.

### What High Attention DOES NOT Mean:
1. **NOT Proof of a Defect**: High attention on an area does not prove a defect exists in reality; it only demonstrates that the model *believed* that region supported its prediction.
2. **NOT a Boundary Delineation**: Because the target layer has 32× spatial downsampling, red regions are diffuse blobs and must never be interpreted as precise millimeter crack widths or physical excavation cutlines.
3. **NOT Severity or Depth**: A bright red activation on a hairline surface crack merely reflects high detection confidence, not structural depth, structural hazard, or high physical severity.

---

## 5. Empirical Sanity Checks (Validation Split Protocol)

Following the rigorous sanity check methodology established by Adebayo et al. (*Sanity Checks for Saliency Maps*, NeurIPS 2018), we subjected our segmentation explainability pipeline to two empirical tests across 50 randomly sampled images from the **Crack500 VALIDATION split** (never touching the test split):

### 5.1 Model Parameter Randomisation Test
- **Hypothesis**: If an XAI method faithfully reflects learned representations, scrambling model weights must cause the heatmap to decorrelate or collapse. If the heatmap remains unchanged after weight scrambling, the method is merely acting as an edge detector insensitive to model parameters.
- **Protocol**: Weights of the deepest encoder stage (`layer4`), decoder subnets, and segmentation head were re-initialized using random Gaussian weights (Kaiming normal). Heatmaps generated by the randomized model were compared against the trained baseline via Spearman rank correlation ($r$).
- **Empirical Results**:
  - **Grad-CAM Mean Spearman $r$**: **0.1069** (95% CI: $[0.0514, 0.1625]$)
  - **Grad-CAM++ Mean Spearman $r$**: **-0.1685** (95% CI: $[-0.2501, -0.0917]$)
  - **Outcome**: **PASS**. The rank correlation collapses to near zero (or inverts) upon weight randomization, confirming that the attention maps depend directly on learned structural representations rather than low-level image contrast.

### 5.2 Feature Deletion Test
- **Hypothesis**: If highlighted attention regions are functionally critical to the model's inference, deleting them must degrade model performance significantly more than deleting an equivalent number of random pixels.
- **Protocol**: For each validation image, the top 10% highest attention pixels were masked out (replaced by the image mean color). In parallel, an identical count of randomly distributed pixels was masked out. We measured the resulting drop in predicted crack area ($\Delta \text{Area}$) and Sørensen-Dice coefficient ($\Delta \text{Dice}$) against ground truth.
- **Empirical Results**:
  - **Intact Image Mean Dice**: **0.7387**
  - **Top 10% Attention Deletion $\Delta \text{Dice}$**: **0.0656** drop (95% CI: $[0.0370, 0.0994]$)
  - **10% Random Deletion $\Delta \text{Dice}$**: **0.0252** drop (95% CI: $[0.0086, 0.0476]$)
  - **Impairment Ratio**: Deleting the top 10% attended pixels degraded segmentation performance **2.61× more severely** than random deletion.
  - **Outcome**: **PASS**. Attended regions are functionally consequential to model predictions.

---

## 6. Known Limitations & Failure Modes

1. **Coarse Spatial Resolution (32× Downsampling)**:
   Feature maps at `layer4[-1]` of ResNet-34 have spatial dimensions $H/32 \times W/32$. For an input of $384 \times 640$, the CAM resolution is only $12 \times 20$ grid cells. Resizing this back to full resolution causes diffuse, smooth heatmaps that cannot trace millimeter-thin crack tips.
2. **Empty Predicted Mask Fallback**:
   When the segmentation model predicts no crack pixels above threshold ($0.40$), standard Grad-CAM has no target. InfraScan employs a deterministic fallback explaining the top 1% highest probability pixels, flagging an explicit warning: `"Predicted crack mask was empty; explained top 1% most probable pixels."`
3. **Multi-Object Blending in Single-Stage Detectors**:
   EigenCAM projects the primary eigenvector across the entire feature volume. If an image contains both road potholes and lane markings, the heatmap may blend attention across both structures rather than isolating an individual bounding box.
4. **Absence of Negative Evidence**:
   CAM methods show where the model found evidence for a class; they do not explain *why* the model decided something was *not* a crack (absence of activation does not imply certainty of sound concrete).
5. **CPU Inference Latency**:
   On standard multi-core CPU hardware (without dedicated GPU acceleration), computing backpropagation gradients introduces observable latency:
   - Segmentation Grad-CAM (U-Net++): **~8.2 to 12.5 seconds**
   - Object Detection EigenCAM (YOLOv8s): **~0.81 seconds**
   - Object Detection EigenCAM (RT-DETR-L): **~1.87 seconds**
   - Crack Classifier Grad-CAM (ResNet-50): **~1.95 seconds**

---

## 7. Engineer Review Workflow & Governance

Every visual attention heatmap displayed in the InfraScan UI or exported to inspection reports is governed by strict review rules:

1. **5-Pane Switchable Analysis Interface**:
   Engineers can toggle between:
   - **Original Image**: Raw visual evidence without overlays.
   - **Detections**: Bounding boxes, defect class, and confidence.
   - **Segmentation Mask**: Pixel-level binary distress masks and geometric metrics.
   - **AI Attention Map**: Grad-CAM / EigenCAM heatmap with interactive opacity control and method comparison.
   - **Damage Assessment**: Advisory severity score breakdown (Factors A through F).

2. **Side-by-Side Comparison**:
   Enables engineers to compare two distinct explanation methods (e.g. Grad-CAM vs. Grad-CAM++) side-by-side with quantitative Spearman rank correlation ($r$) and top 10% spatial overlap (IoU) metrics.

3. **Permanent Warning Banner**:
   The following notice is permanently rendered below every attention map:
   > *"Attention maps show which image regions influenced the model's output. They do not prove that a defect is present or that the model is correct. AI result for engineer review, not a final structural safety verdict."*
