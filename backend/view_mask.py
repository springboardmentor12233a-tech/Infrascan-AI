import requests
import base64

url = "http://127.0.0.1:8000/predict"

image_path = "test_images/11125-1.jpg"

with open(image_path, "rb") as image:
    response = requests.post(
        url,
        files={"file": ("11125-1.jpg", image, "image/jpeg")}
    )

result = response.json()

print("Crack percentage:", result["crack_percentage"])

mask_data = base64.b64decode(result["mask"])

with open("predicted_crack_mask.png", "wb") as file:
    file.write(mask_data)

print("Predicted mask saved successfully!")