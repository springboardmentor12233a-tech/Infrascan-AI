
import os
import xml.etree.ElementTree as ET

# Processed dataset location
BASE_PATH = (
    r"C:\Users\mitran\Downloads\InfraScan"
    r"\dataset_audit\processed_dataset"
)

COUNTRIES = [
    "China_Drone",
    "China_MotorBike",
    "United_States",
    "Czech",
    "Japan",
    "Norway",
    "India"
]

grand_total = 0

print("\n========== PROCESSED DATASET VERIFICATION ==========\n")

for country in COUNTRIES:

    annotation_dir = os.path.join(
        BASE_PATH,
        country,
        "train",
        "annotations",
        "xmls"
    )

    if not os.path.isdir(annotation_dir):
        print(f"{country}: Folder missing")
        continue

    country_total = 0
    xml_count = 0

    for filename in os.listdir(annotation_dir):

        if not filename.lower().endswith(".xml"):
            continue

        xml_path = os.path.join(annotation_dir, filename)

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            objects = root.findall("object")

            country_total += len(objects)
            xml_count += 1

        except ET.ParseError:
            print(f"Malformed XML: {xml_path}")

    grand_total += country_total

    print(f"{country}:")
    print(f"  XML files: {xml_count}")
    print(f"  Objects:   {country_total}")
    print()

print("=" * 45)
print(f"TOTAL PROCESSED OBJECTS: {grand_total}")
print("=" * 45)
