
import os
import csv
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

# ============================================================
# 1. CONFIGURATION
# ============================================================

DATASET_PATH = r"C:\Users\mitran\Downloads\InfraScan-DataSet\New folder\RDD2022"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(SCRIPT_DIR, "reports")

os.makedirs(REPORT_DIR, exist_ok=True)

COUNTRIES = [
    "China_Drone",
    "China_MotorBike",
    "United_States",
    "Czech",
    "Japan",
    "Norway",
    "India"
]

# Initial four-class investigation baseline.
# Other labels are recorded, NOT discarded.
EXPECTED_LABELS = {"D00", "D10", "D20", "D40"}

# ============================================================
# 2. GLOBAL STATISTICS
# ============================================================

total_xml = 0
annotated_xml = 0
empty_xml = 0
invalid_xml = 0
missing_images = 0
total_boxes = 0

class_counts = Counter()
country_stats = []

unusual_labels = []
invalid_files = []
empty_files = []
missing_image_files = []
invalid_boxes = []

# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================

def save_csv(filename, headers, rows):

    filepath = os.path.join(REPORT_DIR, filename)

    with open(filepath, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Report saved: {filepath}")


# ============================================================
# 4. DATASET AUDIT
# ============================================================

print("\n========== RDD2022 DATASET AUDIT ==========\n")

for country in COUNTRIES:

    annotation_dir = os.path.join(
        DATASET_PATH,
        country,
        "train",
        "annotations",
        "xmls"
    )

    image_dir = os.path.join(
        DATASET_PATH,
        country,
        "train",
        "images"
    )

    if not os.path.isdir(annotation_dir):
        print(f"{country}: Annotation folder not found")
        continue

    if not os.path.isdir(image_dir):
        print(f"{country}: Image folder not found")
        continue

    xml_files = [
        filename
        for filename in os.listdir(annotation_dir)
        if filename.lower().endswith(".xml")
    ]

    image_files = set(os.listdir(image_dir))

    country_annotated = 0
    country_empty = 0
    country_boxes = 0
    country_missing = 0
    country_invalid = 0

    for xml_file in xml_files:

        total_xml += 1

        xml_path = os.path.join(annotation_dir, xml_file)

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            filename = root.findtext("filename")

            # --------------------------------------------
            # IMAGE MATCHING
            # --------------------------------------------

            if not filename or filename not in image_files:

                country_missing += 1
                missing_images += 1

                missing_image_files.append({
                    "country": country,
                    "xml_file": xml_file,
                    "image_filename": filename or ""
                })

            # --------------------------------------------
            # OBJECT DETECTION ANNOTATIONS
            # --------------------------------------------

            objects = root.findall("object")

            if not objects:

                country_empty += 1
                empty_xml += 1

                empty_files.append({
                    "country": country,
                    "xml_file": xml_file,
                    "image_filename": filename or ""
                })

                continue

            country_annotated += 1
            annotated_xml += 1

            for obj in objects:

                label = obj.findtext("name")
                box = obj.find("bndbox")

                # ----------------------------------------
                # MISSING LABEL OR BOUNDING BOX
                # ----------------------------------------

                if not label or box is None:

                    country_invalid += 1
                    invalid_xml += 1

                    invalid_files.append({
                        "country": country,
                        "xml_file": xml_file,
                        "issue": "Missing label or bounding box"
                    })

                    continue

                # ----------------------------------------
                # UNUSUAL LABEL DETECTION
                # ----------------------------------------

                if label not in EXPECTED_LABELS:

                    unusual_labels.append({
                        "country": country,
                        "label": label,
                        "xml_file": xml_file
                    })

                # ----------------------------------------
                # BOUNDING BOX VALIDATION
                # ----------------------------------------

                try:

                    xmin = float(box.findtext("xmin"))
                    ymin = float(box.findtext("ymin"))
                    xmax = float(box.findtext("xmax"))
                    ymax = float(box.findtext("ymax"))

                    size = root.find("size")

                    if size is None:
                        raise ValueError("Image dimensions missing")

                    image_width = int(size.findtext("width"))
                    image_height = int(size.findtext("height"))

                    if image_width <= 0 or image_height <= 0:
                        raise ValueError("Invalid image dimensions")

                    if xmax <= xmin or ymax <= ymin:
                        raise ValueError("Invalid bounding box dimensions")

                    if (
                        xmin < 0
                        or ymin < 0
                        or xmax > image_width
                        or ymax > image_height
                    ):
                        raise ValueError("Bounding box outside image boundaries")

                    class_counts[label] += 1
                    country_boxes += 1
                    total_boxes += 1

                except (TypeError, ValueError) as error:

                    country_invalid += 1
                    invalid_xml += 1

                    invalid_boxes.append({
                        "country": country,
                        "xml_file": xml_file,
                        "label": label,
                        "issue": str(error)
                    })

        except ET.ParseError as error:

            country_invalid += 1
            invalid_xml += 1

            invalid_files.append({
                "country": country,
                "xml_file": xml_file,
                "issue": f"Malformed XML: {error}"
            })

    # --------------------------------------------
    # COUNTRY SUMMARY
    # --------------------------------------------

    country_stats.append({
        "country": country,
        "total_xml": len(xml_files),
        "annotated_xml": country_annotated,
        "empty_xml": country_empty,
        "bounding_boxes": country_boxes,
        "missing_images": country_missing,
        "invalid_annotations": country_invalid
    })

    print(f"\n{country}")
    print("-" * 40)
    print(f"Total XML files:       {len(xml_files)}")
    print(f"Annotated XML files:   {country_annotated}")
    print(f"Empty XML files:       {country_empty}")
    print(f"Bounding boxes:        {country_boxes}")
    print(f"Missing images:        {country_missing}")
    print(f"Invalid annotations:   {country_invalid}")


# ============================================================
# 5. OVERALL SUMMARY
# ============================================================

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


# ============================================================
# 6. GENERATE CSV REPORTS
# ============================================================

print("\n========== GENERATING REPORTS ==========")

save_csv(
    "country_summary.csv",
    [
        "country",
        "total_xml",
        "annotated_xml",
        "empty_xml",
        "bounding_boxes",
        "missing_images",
        "invalid_annotations"
    ],
    country_stats
)

class_rows = [
    {"class_label": label, "bounding_boxes": count}
    for label, count in sorted(class_counts.items())
]

save_csv(
    "class_distribution.csv",
    ["class_label", "bounding_boxes"],
    class_rows
)

save_csv(
    "unusual_labels.csv",
    ["country", "label", "xml_file"],
    unusual_labels
)

save_csv(
    "empty_annotations.csv",
    ["country", "xml_file", "image_filename"],
    empty_files
)

save_csv(
    "invalid_annotations.csv",
    ["country", "xml_file", "issue"],
    invalid_files
)

save_csv(
    "invalid_bounding_boxes.csv",
    ["country", "xml_file", "label", "issue"],
    invalid_boxes
)

save_csv(
    "missing_images.csv",
    ["country", "xml_file", "image_filename"],
    missing_image_files
)


# ============================================================
# 7. FINAL STATUS
# ============================================================

print("\n========== AUDIT COMPLETE ==========")

print(f"Reports directory: {REPORT_DIR}")

print(f"Unusual label entries: {len(unusual_labels)}")
print(f"Empty XML files: {len(empty_files)}")
print(f"Invalid XML entries: {len(invalid_files)}")
print(f"Invalid bounding boxes: {len(invalid_boxes)}")
print(f"Missing image references: {len(missing_image_files)}")

print("\nReview the generated CSV reports before dataset cleaning.")
