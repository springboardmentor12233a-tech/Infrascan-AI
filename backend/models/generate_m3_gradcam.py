from pathlib import Path

import torch
import torch.nn.functional as F
import numpy as np
import matplotlib.pyplot as plt

from PIL import Image
from torchvision import models, transforms
from torchvision.models import ResNet18_Weights

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "backend" / "models" / "m3_resnet18.pth"
DATA_DIR = ROOT / "dataset" / "split_data" / "test"
OUTPUT_DIR = ROOT / "backend" / "models"

DEVICE = torch.device("cpu")

checkpoint = torch.load(
    MODEL_PATH, map_location=DEVICE, weights_only=True
)

classes = checkpoint["classes"]
image_size = checkpoint["image_size"]

model = models.resnet18(weights=None)
model.fc = torch.nn.Linear(model.fc.in_features, len(classes))
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()

transform = transforms.Compose([
    transforms.Resize((image_size, image_size)),
    transforms.ToTensor(),
    transforms.Normalize(
        [0.485, 0.456, 0.406],
        [0.229, 0.224, 0.225]
    )
])

image_files = sorted(
    p for p in DATA_DIR.rglob("*")
    if p.suffix.lower() in [".jpg", ".jpeg", ".png"]
)

if not image_files:
    raise FileNotFoundError(f"No test images found in {DATA_DIR}")

image_path = image_files[0]

original = Image.open(image_path).convert("RGB").resize(
    (image_size, image_size)
)

input_tensor = transform(original).unsqueeze(0)

activations = None
gradients = None

def forward_hook(module, inputs, output):
    global activations
    activations = output
    output.retain_grad()

handle = model.layer4[-1].register_forward_hook(forward_hook)

model.zero_grad()

outputs = model(input_tensor)
predicted_index = outputs.argmax(dim=1).item()
confidence = torch.softmax(outputs, dim=1)[0, predicted_index].item()

outputs[0, predicted_index].backward()

gradients = activations.grad

weights = gradients.mean(dim=(2, 3), keepdim=True)

cam = (weights * activations).sum(dim=1, keepdim=True)
cam = F.relu(cam)

cam = F.interpolate(
    cam,
    size=(image_size, image_size),
    mode="bilinear",
    align_corners=False
)

cam = cam.squeeze().detach().numpy()

cam = cam - cam.min()
cam = cam / (cam.max() + 1e-8)

handle.remove()

original_array = np.asarray(original)

plt.figure(figsize=(12, 5))

plt.subplot(1, 3, 1)
plt.imshow(original_array)
plt.title("Original Image")
plt.axis("off")

plt.subplot(1, 3, 2)
plt.imshow(cam, cmap="jet")
plt.title("Grad-CAM Heatmap")
plt.axis("off")

plt.subplot(1, 3, 3)
plt.imshow(original_array)
plt.imshow(cam, cmap="jet", alpha=0.45)
plt.title("Grad-CAM Overlay")
plt.axis("off")

plt.suptitle(
    f"Predicted: {classes[predicted_index]} "
    f"({confidence * 100:.2f}%)"
)

plt.tight_layout()

output_path = OUTPUT_DIR / "m3_resnet18_gradcam.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight")
plt.close()

print("Image:", image_path.name)
print("Predicted class:", classes[predicted_index])
print(f"Confidence: {confidence * 100:.2f}%")
print("Grad-CAM saved:", output_path)
