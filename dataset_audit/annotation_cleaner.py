
import os
import csv
import shutil
import xml.etree.ElementTree as ET

# ============================================================
# 1. CONFIGURATION
# ============================================================

DATASET_PATH = r"C:\Users\mitran\Downloads\InfraScan-DataSet\New folder\RDD2022"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

PROCESSED_PATH = os.path.join(
    SCRIPT_DIR, "processed_dataset"
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

# ============================================================
# 2. CREATE OUTPUT DIRECTORIES
# ============================================================

os.makedirs(PROCESSED_PATH, exist_ok=True)

cleaning_report = []

total_xml = 0
total_objects = 0
valid_objects = 0
removed_objects = 0
malformed_xml = 0

# ============================================================
# 3. BOUNDING BOX VALIDATION
# ============================================================

def validate_box(box, image_width, image_height):

    try:
        xmin = float(box.findtext("xmin"))
        ymin = float(box.findtext("ymin"))
        xmax = float(box.findtext("xmax"))
        ymax = float(box.findtext("ymax"))

    except (TypeError, ValueError):
        return False, "Missing or non-numeric coordinates"

    if image_width <= 0 or image_height <= 0:
        return False, "Invalid image dimensions"

    if xmax <= xmin:
        return False, "Zero or negative box width"

    if ymax <= ymin:
        return False, "Zero or negative box height"

    if (
        xmin < 0
        or ymin < 0
        or xmax > image_width
        or ymax > image_height
    ):
        return False, "Box outside image boundaries"

    return True, "Valid"


# ============================================================
# 4. PROCESS EACH COUNTRY
# ============================================================

print("\n========== ANNOTATION CLEANING ==========\n")

for country in COUNTRIES:

    source_dir = os.path.join(
        DATASET_PATH,
        country,
        "train",
        "annotations",
        "xmls"
    )

    output_dir = os.path.join(
        PROCESSED_PATH,
        country,
        "train",
        "annotations",
        "xmls"
    )

    os.makedirs(output_dir, exist_ok=True)

    if not os.path.isdir(source_dir):
        print(f"Skipping {country}: annotation directory missing")
        continue

    xml_files = [
        filename
        for filename in os.listdir(source_dir)
        if filename.lower().endswith(".xml")
    ]

    country_valid = 0
    country_removed = 0

    for xml_file in xml_files:

        total_xml += 1

        source_file = os.path.join(source_dir, xml_file)
        output_file = os.path.join(output_dir, xml_file)

        try:
            tree = ET.parse(source_file)
            root = tree.getroot()

            size = root.find("size")

            if size is None:
                raise ValueError("Image dimensions missing")

            try:
                image_width = int(size.findtext("width"))
                image_height = int(size.findtext("height"))
            except (TypeError, ValueError):
                raise ValueError("Invalid image dimensions")

            # Work on a snapshot because invalid objects
            # will be removed from the XML tree.

            for obj in list(root.findall("object")):

                total_objects += 1

                label = obj.findtext("name")
                box = obj.find("bndbox")

                if box is None:
                    is_valid = False
                    reason = "Bounding box missing"
                else:
                    is_valid, reason = validate_box(
                        box,
                        image_width,
                        image_height
                    )

                if is_valid:

                    valid_objects += 1
                    country_valid += 1

                else:

                    root.remove(obj)

                    removed_objects += 1
                    country_removed += 1

                    cleaning_report.append({
                        "country": country,
                        "xml_file": xml_file,
                        "class_label": label or "",
                        "action": "Object excluded",
                        "reason": reason
                    })

            # Save cleaned XML separately.
            tree.write(
                output_file,
                encoding="utf-8",
                xml_declaration=True
            )

        except (ET.ParseError, ValueError) as error:

            malformed_xml += 1

            cleaning_report.append({
                "country": country,
                "xml_file": xml_file,
                "class_label": "",
                "action": "File excluded",
                "reason": str(error)
            })

            print(f"Problem: {country}/{xml_file}: {error}")

    print(f"\n{country}")
    print("-" * 35)
    print(f"XML files processed: {len(xml_files)}")
    print(f"Valid objects:       {country_valid}")
    print(f"Removed objects:     {country_removed}")


# ============================================================
# 5. SAVE CLEANING REPORT
# ============================================================

REPORT_DIR = os.path.join(SCRIPT_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

report_path = os.path.join(
    REPORT_DIR,
    "annotation_cleaning_report.csv"
)

with open(
    report_path,
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:

    fieldnames = [
        "country",
        "xml_file",
        "class_label",
        "action",
        "reason"
    ]

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(cleaning_report)


# ============================================================
# 6. FINAL SUMMARY
# ============================================================

print("\n========== CLEANING SUMMARY ==========")

print(f"XML files processed: {total_xml}")
print(f"Original objects:    {total_objects}")
print(f"Valid objects kept:  {valid_objects}")
print(f"Invalid objects removed: {removed_objects}")
print(f"Files excluded:      {malformed_xml}")

print(f"\nCleaned dataset: {PROCESSED_PATH}")
print(f"Cleaning report: {report_path}")

print("\n========== CLEANING COMPLETE ==========")
