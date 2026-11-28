
import os
import xml.etree.ElementTree as ET
from collections import Counter

DATASET_PATH = r"C:\Users\mitran\Downloads\InfraScan-DataSet\RDD2022\RDD2022"

countries = [
    "China_Drone",
    "China_MotorBike",
    "United_States",
    "Czech",
    "Japan",
    "Norway",
    "India"
]

total_xml = 0
annotated_xml = 0
empty_xml = 0
invalid_xml = 0
missing_images = 0
total_boxes = 0

class_counts = Counter()

print("\n========== RDD2022 DATASET AUDIT ==========\n")

for country in countries:

    annotation_dir = os.path.join(
        DATASET_PATH, country, "train", "annotations", "xmls"
    )

    image_dir = os.path.join(
        DATASET_PATH, country, "train", "images"
    )

    if not os.path.isdir(annotation_dir):
        print(f"{country}: Annotation folder not found")
        continue

    xml_files = [
        f for f in os.listdir(annotation_dir)
        if f.lower().endswith(".xml")
    ]

    country_annotated = 0
    country_empty = 0
    country_boxes = 0
    country_missing = 0
    country_invalid = 0

    image_files = set(os.listdir(image_dir)) if os.path.isdir(image_dir) else set()

    for xml_file in xml_files:

        total_xml += 1
        xml_path = os.path.join(annotation_dir, xml_file)

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            filename = root.findtext("filename")

            if not filename or filename not in image_files:
                country_missing += 1
                missing_images += 1

            objects = root.findall("object")

            if not objects:
                country_empty += 1
                empty_xml += 1
                continue

            country_annotated += 1
            annotated_xml += 1

            for obj in objects:

                label = obj.findtext("name")
                box = obj.find("bndbox")

                if not label or box is None:
                    country_invalid += 1
                    invalid_xml += 1
                    continue

                try:
                    xmin = float(box.findtext("xmin"))
                    ymin = float(box.findtext("ymin"))
                    xmax = float(box.findtext("xmax"))
                    ymax = float(box.findtext("ymax"))

                    if xmax <= xmin or ymax <= ymin:
                        raise ValueError("Invalid box dimensions")

                    class_counts[label] += 1
                    country_boxes += 1
                    total_boxes += 1

                except (TypeError, ValueError):
                    country_invalid += 1
                    invalid_xml += 1

        except ET.ParseError:
            country_invalid += 1
            invalid_xml += 1

    print(f"\n{country}")
    print("-" * 35)
    print(f"Total XML files:       {len(xml_files)}")
    print(f"Annotated XML files:   {country_annotated}")
    print(f"Empty XML files:       {country_empty}")
    print(f"Bounding boxes:        {country_boxes}")
    print(f"Missing images:        {country_missing}")
    print(f"Invalid annotations:   {country_invalid}")

print("\n========== OVERALL SUMMARY ==========")
print(f"Total XML files:       {total_xml}")
print(f"Annotated XML files:   {annotated_xml}")
print(f"Empty XML files:       {empty_xml}")
print(f"Total bounding boxes:  {total_boxes}")
print(f"Missing images:        {missing_images}")
print(f"Invalid annotations:   {invalid_xml}")

print("\n========== CLASS DISTRIBUTION ==========")

for label, count in sorted(class_counts.items()):
    print(f"{label}: {count}")

print("\n========== AUDIT COMPLETE ==========")
