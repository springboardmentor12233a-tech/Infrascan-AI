#!/usr/bin/env python3
"""Build docs/InfraScan_Dataset_Research.xlsx from verified research notes."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "InfraScan_Dataset_Research.xlsx"

HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
WRAP = Alignment(wrap_text=True, vertical="top")
THIN = Border(
    left=Side(style="thin", color="D9D9D9"),
    right=Side(style="thin", color="D9D9D9"),
    top=Side(style="thin", color="D9D9D9"),
    bottom=Side(style="thin", color="D9D9D9"),
)
ALT = PatternFill("solid", fgColor="F2F7FB")
REC_FILL = {
    "Primary": PatternFill("solid", fgColor="C6EFCE"),
    "Complementary": PatternFill("solid", fgColor="FFF2CC"),
    "Do not download now": PatternFill("solid", fgColor="FCE4D6"),
    "Blocked / limited access": PatternFill("solid", fgColor="F8CBAD"),
}

COLUMNS = [
    "dataset_name",
    "original_image_count",
    "derived_patch_count",
    "official_url",
    "purpose_ai_task",
    "defect_categories",
    "annotation_types",
    "license",
    "limitations",
    "verification_source",
    "access_status",
    "infrascan_recommendation",
    "notes_on_uncertainty",
]


ROWS = [
    {
        "dataset_name": "SDNET2018",
        "original_image_count": "230 original photographs (54 bridge decks, 72 walls, 104 pavements)",
        "derived_patch_count": "56,092 patches of 256x256 px (8,484 cracked / 47,608 non-cracked). Deck 13,620 (2,025/11,595); Wall 18,138 (3,851/14,287); Pavement 24,334 (2,608/21,726).",
        "official_url": "https://digitalcommons.usu.edu/all_datasets/48/",
        "purpose_ai_task": "Binary crack vs non-crack classification on concrete decks, walls, and pavements",
        "defect_categories": "Crack present / crack absent. Crack widths 0.06-25 mm.",
        "annotation_types": "Image-level labels encoded in folders (CD/UD, CW/UW, CP/UP). No boxes or masks.",
        "license": "CC BY 4.0 (Data in Brief article and Digital Commons record)",
        "limitations": "Patches are not independent photographs. Strong class imbalance. Hairline cracks and clutter (shadows, holes, scaling) make labels noisy for some patches. No localization.",
        "verification_source": "Dorafshan, Thomas, Maguire, Data in Brief 21 (2018) 1664-1668, Table 1; USU Digital Commons DOI 10.15142/T3TD19",
        "access_status": "Research completed. Download blocked: Cloudflare JavaScript challenge. EDA pending. Manual browser download required.",
        "infrascan_recommendation": "Primary",
        "notes_on_uncertainty": "None for published counts. Local file counts must still be verified after extraction.",
    },
    {
        "dataset_name": "Concrete Crack Images for Classification (METU / Özgenel)",
        "original_image_count": "458 high-resolution photographs (4032x3024) from METU campus buildings",
        "derived_patch_count": "40,000 patches of 227x227 px; 20,000 positive and 20,000 negative. Authors state no rotation/flip augmentation.",
        "official_url": "https://data.mendeley.com/datasets/5y9wdsg2zt/2",
        "purpose_ai_task": "Binary concrete crack classification",
        "defect_categories": "Positive (crack) / Negative (no crack)",
        "annotation_types": "Image-level class folders. No boxes or masks in this release.",
        "license": "CC BY 4.0",
        "limitations": "Patches come from 458 originals, so random splits leak. Building-facade concrete, not roads. Overlaps conceptually with SDNET2018.",
        "verification_source": "Mendeley Data DOI 10.17632/5y9wdsg2zt.2; Özgenel and Gönenç Sorguç, ISARC 2018",
        "access_status": "Public 230 MB RAR on Mendeley",
        "infrascan_recommendation": "Complementary",
        "notes_on_uncertainty": "Patch extraction grid is described as Zhang et al. 2016 method; exact overlap between adjacent patches is not restated on the landing page.",
    },
    {
        "dataset_name": "Concrete Crack Segmentation Dataset (Özgenel)",
        "original_image_count": "458 high-resolution images with alpha maps",
        "derived_patch_count": "Not a patch dataset. Source of the 40,000 classification patches above.",
        "official_url": "https://data.mendeley.com/datasets/jwsn7tfbrp/1",
        "purpose_ai_task": "Binary semantic segmentation of concrete cracks",
        "defect_categories": "Crack / background",
        "annotation_types": "Pixel-wise BW alpha maps",
        "license": "CC BY 4.0",
        "limitations": "Building surfaces at METU only. Large files (~681-711 MB). Binary crack only, no spalling/rebar.",
        "verification_source": "Mendeley Data DOI 10.17632/jwsn7tfbrp.1",
        "access_status": "Public RAR on Mendeley",
        "infrascan_recommendation": "Complementary",
        "notes_on_uncertainty": "File size is reported as 681 MB 'Download All' and 711 MB for the listed RAR; use the Mendeley file list at download time.",
    },
    {
        "dataset_name": "RDD2022",
        "original_image_count": "47,420 road images from Japan, India, Czech Republic, Norway, United States, and China. FigShare/data article. Country training/test table on the CRDDC site is approximate (India 9,000+1,000; Japan 10,000+1,000; Czech 2,000+1,000; Norway 9,000+1,000; US 5,000+1,000; China 3,500+1,000). The data article reports Japan 13,133; India 9,665; Czech 3,538; Norway 10,201; US 6,005; China_M 2,477; China_D 2,401.",
        "derived_patch_count": "Not a patch dataset. More than 55,000 damage instances (FigShare).",
        "official_url": "https://github.com/sekilab/RoadDamageDetector",
        "purpose_ai_task": "Multi-class road damage object detection",
        "defect_categories": "CRDDC'2022 scoring classes: D00 longitudinal crack, D10 transverse crack, D20 alligator crack, D40 pothole. XML files may contain additional historical labels.",
        "annotation_types": "Pascal VOC XML bounding boxes for the train set. Test images have no public boxes.",
        "license": "FigShare record is CC BY 4.0. GitHub repository LICENSE is MIT and applies to the software. Cite Arya et al. RDD2022.",
        "limitations": "Road-only. Full archive is 12.36 GB. Country appearance differs, so Czech-only is not a global detector. Test labels are withheld. Many train XMLs have zero objects.",
        "verification_source": "Arya et al. RDD2022 data article; FigShare 10.6084/m9.figshare.21431547 file 38030910; local extraction of stored member RDD2022/Czech.zip",
        "access_status": "Research completed. Downloaded and verified: Czech subset from official FigShare zip via HTTP Range (257,118,242 bytes). CRDDC S3 country URL remains AccessDenied. EDA completed on local Czech files.",
        "infrascan_recommendation": "Primary",
        "notes_on_uncertainty": "Full 47,420-image corpus was not downloaded. Czech local count 3,538 matches the data article.",
    },
    {
        "dataset_name": "CrackForest Dataset (CFD)",
        "original_image_count": "118 urban road images, 480x320 px",
        "derived_patch_count": "None in the official release",
        "official_url": "https://github.com/cuilimeng/CrackForest-dataset",
        "purpose_ai_task": "Road crack segmentation / contour detection",
        "defect_categories": "Road surface cracks",
        "annotation_types": "MATLAB groundTruth .mat files plus a seg/ directory in the official repo",
        "license": "Non-commercial research only (README)",
        "limitations": "Small. Urban asphalt, not structural concrete. MATLAB labels need conversion for PyTorch/TF. Non-commercial restriction.",
        "verification_source": "Official GitHub README; Shi et al., IEEE T-ITS 2016",
        "access_status": "Research completed. Downloaded and verified from official GitHub. EDA completed.",
        "infrascan_recommendation": "Primary",
        "notes_on_uncertainty": "Official clone contains 155 JPEGs: 118 annotated (001-118) plus 37 unlabeled extras.",
    },
    {
        "dataset_name": "CRACK500",
        "original_image_count": "500 pavement photographs taken by phone on Temple University campus. Paper/repo descriptions: size around 2000x1500 (also reported around 2560x1440).",
        "derived_patch_count": "Each image cropped into 16 non-overlapping regions; regions with more than 1,000 crack pixels kept. Resulting split commonly cited: 1,896 train / 348 val / 1,124 test patches.",
        "official_url": "https://github.com/fyangneil/pavement-crack-detection",
        "purpose_ai_task": "Pavement crack segmentation",
        "defect_categories": "Crack / background",
        "annotation_types": "Pixel-wise masks",
        "license": "Not clearly stated on the GitHub README. Do not assume CC BY.",
        "limitations": "Official files sit on Google Drive / OneDrive / Baidu Yun. Road/pavement, not building concrete. Patching from 500 originals creates leakage if splits ignore the parent image. Some later papers report 447-499 usable originals after cleanup.",
        "verification_source": "Yang et al., Feature Pyramid and Hierarchical Boosting Network, IEEE T-ITS 2019 / arXiv 1901.06340; fyangneil GitHub",
        "access_status": "Manual: follow Google Drive / OneDrive links on the official GitHub README",
        "infrascan_recommendation": "Do not download now",
        "notes_on_uncertainty": "License is unverified. Original-count 500 vs later cleaned 447/499 is dataset-version dependent.",
    },
    {
        "dataset_name": "CrackTree260",
        "original_image_count": "260 road pavement images (expansion of CrackTree200/206). Typical size 800x600, some papers note 600-720 x 800-960.",
        "derived_patch_count": "Zou et al. describe augmentation to 35,100 sub-images of 512x512 for training in their DeepCrack paper. Those crops are derived, not extra photographs.",
        "official_url": "https://github.com/qinnzou/DeepCrack",
        "purpose_ai_task": "Pavement crack segmentation (often used as training set in Zou et al.)",
        "defect_categories": "Crack centerline / crack pixels",
        "annotation_types": "Pixel-wise crack maps (thin/centerline style)",
        "license": "Not clearly posted as a standard CC license on the landing page. Treat as research use until the OneDrive terms are read.",
        "limitations": "Hosted on OneDrive links from qinnzou/DeepCrack. Asphalt under relatively homogeneous lighting.",
        "verification_source": "Zou et al. DeepCrack paper dataset section; qinnzou/DeepCrack README",
        "access_status": "OneDrive links on https://github.com/qinnzou/DeepCrack (may require Microsoft login)",
        "infrascan_recommendation": "Blocked / limited access",
        "notes_on_uncertainty": "CrackTree200 vs 206 vs 260 naming is inconsistent across papers; 260 is the Zou 2018/2019 expansion.",
    },
    {
        "dataset_name": "DeepCrack (Liu et al. / yhlleo)",
        "original_image_count": "537 RGB images, 544x384 px. Split: 300 train / 237 test. Paper footnote: GitHub yhlleo/DeepCrack.",
        "derived_patch_count": "None in the official zip",
        "official_url": "https://github.com/yhlleo/DeepCrack",
        "purpose_ai_task": "Pixel-wise crack segmentation across mixed scenes/materials",
        "defect_categories": "Crack / background. Crack widths cited as 1-180 px in later surveys.",
        "annotation_types": "Manually annotated binary maps (train_lab / test_lab)",
        "license": "Non-commercial research and educational use. Authors claim copyright on part of the originals and all maps.",
        "limitations": "GitHub issue reports 10 overlapping train/test images, which would make unique count 527 if confirmed. Mixed internet and real-world sources. Non-commercial.",
        "verification_source": "Liu et al., Neurocomputing 338 (2019) 139-153; official README",
        "access_status": "Research completed. Downloaded and verified official DeepCrack.zip. EDA completed.",
        "infrascan_recommendation": "Primary",
        "notes_on_uncertainty": "Train/test overlap is reported by a GitHub issue, not by the paper. Verify after extraction.",
    },
    {
        "dataset_name": "EdmCrack600",
        "original_image_count": "600 pavement images from Edmonton, Canada",
        "derived_patch_count": "None stated on the official README",
        "official_url": "https://github.com/mqp2259/EdmCrack600",
        "purpose_ai_task": "Pixel-level pavement crack detection",
        "defect_categories": "Pavement cracks",
        "annotation_types": "Pixel-level annotations",
        "license": "Academic use; commercial use is not allowed (README)",
        "limitations": "Google Drive download. Road-only. Non-commercial.",
        "verification_source": "Official GitHub README; Mei, Gül, Azim, Automation in Construction 2020",
        "access_status": "Google Drive file linked from GitHub (login/virus-scan interstitial likely)",
        "infrascan_recommendation": "Do not download now",
        "notes_on_uncertainty": "Image resolution is not stated on the README.",
    },
    {
        "dataset_name": "SUT-Crack",
        "original_image_count": "130 high-resolution asphalt images (3024x4032) captured at a fixed 672 mm height, with geotags",
        "derived_patch_count": "25,563 classification patches of 200x200 (with crack / without crack)",
        "official_url": "https://data.mendeley.com/datasets/gsbmknrhkv/6",
        "purpose_ai_task": "Classification, detection, and segmentation of pavement cracks",
        "defect_categories": "Pavement cracks (oil stains, shadows, lighting variation included)",
        "annotation_types": "PNG ground-truth masks, Pascal VOC XML boxes, crack-length TXT",
        "license": "CC BY 4.0",
        "limitations": "Asphalt pavement, not structural concrete. 988 MB. 130 originals only for dense labels.",
        "verification_source": "Sabouri and Sepidbar, Data in Brief 51 (2023) 109642; Mendeley DOI 10.17632/gsbmknrhkv.6",
        "access_status": "Public ZIP ~985-988 MB on Mendeley",
        "infrascan_recommendation": "Complementary",
        "notes_on_uncertainty": "Classification patch count is 25,563 in the paper body.",
    },
    {
        "dataset_name": "Aigle-RN (AEL / Chambon)",
        "original_image_count": "38 images is the figure commonly cited for Aigle-RN. The broader AEL collection (Aigle-RN + ESAR + LCMS) is reported as 58 annotated images in later surveys. An older IRIT page described five acquisition systems and 269 pavement images with 68 annotated.",
        "derived_patch_count": "None verified",
        "official_url": "https://www.irit.fr/~Sylvie.Chambon/Crack_Detection_Database.html",
        "purpose_ai_task": "Pavement crack segmentation",
        "defect_categories": "Asphalt cracks",
        "annotation_types": "Pixel-wise crack annotations (AEL papers)",
        "license": "Not verified; original IRIT page is currently 404",
        "limitations": "Official IRIT URL returned 404 during this research. Tiny and pavement-only.",
        "verification_source": "Amhaz et al. 2014/2016; SUT-Crack comparison table (38 images, 991x462 or 311x462); IRIT page 404 on 2026-10-19",
        "access_status": "Official page not reachable. Do not use unofficial mirrors.",
        "infrascan_recommendation": "Blocked / limited access",
        "notes_on_uncertainty": "38 vs 58 vs 68 depends on whether Aigle-RN alone or AEL is counted. Marked uncertain until a live official host is found.",
    },
    {
        "dataset_name": "CRKWH100",
        "original_image_count": "100 road pavement images, 512x512, line-array camera, 1 mm GSD, visible light",
        "derived_patch_count": "None",
        "official_url": "https://github.com/qinnzou/DeepCrack",
        "purpose_ai_task": "Pavement crack segmentation (often a test set in Zou et al.)",
        "defect_categories": "Asphalt cracks",
        "annotation_types": "Pixel-wise maps (centerline-like)",
        "license": "Not a standard CC statement on the README. OneDrive terms apply.",
        "limitations": "OneDrive download. Thin cracks, homogeneous pavement.",
        "verification_source": "qinnzou/DeepCrack README; Zou et al. DeepCrack paper",
        "access_status": "OneDrive link; may require Microsoft login",
        "infrascan_recommendation": "Blocked / limited access",
        "notes_on_uncertainty": "None for the 100-image count from the authors' README.",
    },
    {
        "dataset_name": "CrackLS315",
        "original_image_count": "315 road pavement images, 512x512, line-array camera under laser illumination, 1 mm GSD",
        "derived_patch_count": "None",
        "official_url": "https://github.com/qinnzou/DeepCrack",
        "purpose_ai_task": "Pavement crack segmentation (laser-illuminated test set)",
        "defect_categories": "Asphalt cracks",
        "annotation_types": "Pixel-wise maps",
        "license": "Not a standard CC statement on the README. OneDrive terms apply.",
        "limitations": "Laser appearance differs from phone/DSLR photos used in InfraScan. OneDrive access.",
        "verification_source": "qinnzou/DeepCrack README; Zou et al. DeepCrack paper",
        "access_status": "OneDrive link; may require Microsoft login",
        "infrascan_recommendation": "Blocked / limited access",
        "notes_on_uncertainty": "None for the 315-image count from the authors' README.",
    },
    {
        "dataset_name": "CCSS-DATA",
        "original_image_count": "670 RGB images of concrete sidewalks (University of Calgary) with matching masks. Camera mix: Canon EOS M5 308, Xiaomi Mi A1 124, ZED left 155, Samsung Galaxy S7 83. Images resized to ~2K for annotation.",
        "derived_patch_count": "Paper experiments also use 512x512 patches and optional traditional augmentation; those are derived.",
        "official_url": "https://www.kaggle.com/datasets/parniashokri/ccssdata",
        "purpose_ai_task": "Semantic segmentation of concrete sidewalk cracks",
        "defect_categories": "Crack / background. Seasonal snow, rain, grass, clutter.",
        "annotation_types": "Pixel-wise semantic masks",
        "license": "CC BY-SA 4.0 (Kaggle card)",
        "limitations": "Kaggle download requires a Kaggle account. ~1.3 GB. Sidewalks, not bridges. Share-alike license.",
        "verification_source": "Shokri, Shahbazi, Nielsen, Remote Sens. 2022, 14, 5793; Kaggle dataset card",
        "access_status": "Public on Kaggle; account + API token required",
        "infrascan_recommendation": "Complementary",
        "notes_on_uncertainty": "Kaggle may host multiple versions (originalSize vs benchmarkingDatasets). Use originalSize-noExternalData for the 670-image set.",
    },
    {
        "dataset_name": "CODEBRIM",
        "original_image_count": "1,590 high-resolution images from 30 bridges",
        "derived_patch_count": "Crops from 5,354 annotated defect boxes plus 2,506 background boxes. Classification ZIPs are 7.9-12.2 GB.",
        "official_url": "https://zenodo.org/records/2620293",
        "purpose_ai_task": "Multi-target multi-class concrete defect classification and detection",
        "defect_categories": "Crack, spallation, efflorescence, exposed bars, corrosion stain, background. Multi-label boxes.",
        "annotation_types": "Bounding boxes with multi-hot defect tags in XML; cropped classification splits also provided",
        "license": "Non-commercial and educational use (Zenodo license.md / authors' GitHub)",
        "limitations": "Original-image ZIP is 8.3 GB. Non-commercial. No pixel masks in the original release (SegCODEBRIM is a later 420-image subset).",
        "verification_source": "Mundt et al., CVPR 2019; Zenodo 10.5281/zenodo.2620293",
        "access_status": "Public on Zenodo but too large for this EDA pass",
        "infrascan_recommendation": "Complementary",
        "notes_on_uncertainty": "Dataset-ninja reports 567 images without annotations; confirm against the original XML set before training.",
    },
]


REC_ROWS = [
    [
        "Role",
        "Dataset",
        "Task for InfraScan",
        "Why selected or deferred",
        "Download for this EDA?",
    ],
    [
        "Primary classification",
        "SDNET2018",
        "Crack vs no-crack classifier on concrete decks, walls, pavements",
        "Official CC BY 4.0, published class table, matches civil-infrastructure surfaces. Use original-image grouping if a train/val split is created.",
        "Yes — official Digital Commons ZIP",
    ],
    [
        "Primary detection",
        "RDD2022 Czech subset",
        "YOLOv8-style road damage detection (D00/D10/D20/D40)",
        "Czech subset taken from the official FigShare stored zip (257 MB) after S3 AccessDenied. VOC boxes for D00/D10/D20/D40. Expand country coverage later.",
        "Yes — downloaded and EDA completed",
    ],
    [
        "Primary segmentation",
        "DeepCrack (Liu / yhlleo) + CFD",
        "U-Net / pixel-wise crack masks",
        "Both have official GitHub files. DeepCrack covers mixed scenes at 537 images; CFD is a small 118-image road benchmark. Both are non-commercial.",
        "Yes — official GitHub",
    ],
    [
        "Next segmentation (license-friendly)",
        "Özgenel Concrete Crack Segmentation",
        "Concrete building crack masks under CC BY 4.0",
        "458 originals with alpha maps. Better license than DeepCrack/CFD if the product later needs broader reuse.",
        "Not in this pass (681 MB; DeepCrack already covers the task)",
    ],
    [
        "Next multi-defect concrete",
        "CODEBRIM",
        "Spalling, exposed bars, corrosion, efflorescence in addition to cracks",
        "Closest public match to 'other visible defects' on bridges. 8.3 GB original ZIP deferred.",
        "No — size / later milestone",
    ],
    [
        "Deferred",
        "CRACK500, SUT-Crack, CCSS-DATA, METU classification patches",
        "Extra pavement/sidewalk coverage",
        "CRACK500 needs Drive login and has an unclear license. SUT-Crack and CCSS-DATA are credible CC datasets but overlap with CFD/RDD/DeepCrack for an initial EDA.",
        "No",
    ],
    [
        "Not used",
        "CrackTree260, CRKWH100, CrackLS315, EdmCrack600, Aigle-RN",
        "Mostly pavement segmentation",
        "OneDrive/Drive/404 hosts. Do not use unofficial mirrors.",
        "No",
    ],
]


def style_header(ws, ncols: int) -> None:
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(ncols)}1"
    for col in range(1, ncols + 1):
        cell = ws.cell(1, col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        cell.border = THIN
    ws.row_dimensions[1].height = 32
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def apply_wrap(ws, nrows: int, ncols: int, widths: dict[int, float]) -> None:
    for r in range(2, nrows + 1):
        ws.row_dimensions[r].height = 92
        for c in range(1, ncols + 1):
            cell = ws.cell(r, c)
            cell.alignment = WRAP
            cell.border = THIN
            cell.font = Font(name="Calibri", size=10)
            if r % 2 == 0:
                if not cell.fill or cell.fill.fgColor is None or cell.fill.fgColor.rgb in {"00000000", None}:
                    cell.fill = ALT
    for idx, width in widths.items():
        ws.column_dimensions[get_column_letter(idx)].width = width


def add_hyperlink(cell, url: str) -> None:
    cell.hyperlink = url
    cell.value = url
    cell.font = Font(name="Calibri", size=10, color="0563C1", underline="single")


def build() -> Path:
    wb = Workbook()

    ws = wb.active
    ws.title = "Dataset_Comparison"
    for col, name in enumerate(COLUMNS, start=1):
        ws.cell(1, col, name.replace("_", " ").title())
    for r, row in enumerate(ROWS, start=2):
        for c, key in enumerate(COLUMNS, start=1):
            ws.cell(r, c, row[key])
        add_hyperlink(ws.cell(r, 4), row["official_url"])
        rec = row["infrascan_recommendation"]
        if rec in REC_FILL:
            ws.cell(r, 12).fill = REC_FILL[rec]
    style_header(ws, len(COLUMNS))
    apply_wrap(
        ws,
        1 + len(ROWS),
        len(COLUMNS),
        {
            1: 28,
            2: 36,
            3: 32,
            4: 42,
            5: 28,
            6: 28,
            7: 28,
            8: 24,
            9: 36,
            10: 32,
            11: 28,
            12: 22,
            13: 32,
        },
    )
    ws.oddHeader.left.text = "InfraScan dataset research"
    ws.oddFooter.left.text = "Verified from official sources. Uncertain items are labelled."

    rec = wb.create_sheet("Recommendations")
    rec["A1"] = "InfraScan final dataset recommendations"
    rec["A1"].font = Font(bold=True, size=16, color="1F4E79", name="Calibri")
    rec.merge_cells("A1:E1")
    rec["A2"] = (
        "InfraScan needs classification, detection, and segmentation of visible cracks "
        "and other surface damage on concrete structures and roads. This sheet records "
        "the complementary set chosen after checking task fit, annotations, license, "
        "and download practicality. Counts below are from publications/landing pages; "
        "hands-on EDA counts live in docs/InfraScan_EDA_Report.md."
    )
    rec["A2"].alignment = WRAP
    rec.merge_cells("A2:E2")
    rec.row_dimensions[2].height = 64

    start = 4
    for c, val in enumerate(REC_ROWS[0], start=1):
        rec.cell(start, c, val)
    style_header(rec, 5)
    rec.freeze_panes = "A5"
    for r, row in enumerate(REC_ROWS[1:], start=start + 1):
        for c, val in enumerate(row, start=1):
            cell = rec.cell(r, c, val)
            cell.alignment = WRAP
            cell.border = THIN
        rec.row_dimensions[r].height = 70
    rec.column_dimensions["A"].width = 28
    rec.column_dimensions["B"].width = 36
    rec.column_dimensions["C"].width = 36
    rec.column_dimensions["D"].width = 55
    rec.column_dimensions["E"].width = 32

    rec["A13"] = "Requirements still unsupported by the selected EDA set"
    rec["A13"].font = Font(bold=True, size=12, color="1F4E79")
    rec.merge_cells("A13:E13")
    gaps = [
        "Pixel masks on bridge-scale concrete with overlapping defects (need SegCODEBRIM or a custom mask set).",
        "Multi-class structural defects beyond cracks (spalling, exposed bars, corrosion, efflorescence) — CODEBRIM has boxes but was not downloaded.",
        "Severity / crack-width labels in millimetres (SDNET reports a width range in the paper, not per-image widths).",
        "Licenses that clearly allow commercial productization of CFD and DeepCrack (both non-commercial).",
        "A documented original-image identifier for SDNET patches, required to block leakage.",
        "RDD2022 coverage outside Czech roads, and RDD test-set labels (withheld).",
        "Aigle-RN / CrackTree260 / CRKWH100 / CrackLS315 until official hosts work without login walls.",
    ]
    for i, gap in enumerate(gaps, start=14):
        rec.cell(i, 1, f"{i - 13}. {gap}")
        rec.merge_cells(start_row=i, start_column=1, end_row=i, end_column=5)
        rec.cell(i, 1).alignment = WRAP
        rec.row_dimensions[i].height = 32

    rec["A22"] = "Citations for the primary set"
    rec["A22"].font = Font(bold=True, size=12, color="1F4E79")
    rec.merge_cells("A22:E22")
    cites = [
        "Dorafshan S., Thomas R.J., Maguire M. (2018). SDNET2018. Data in Brief 21:1664-1668. https://doi.org/10.1016/j.dib.2018.11.015  Dataset: https://doi.org/10.15142/T3TD19",
        "Arya D. et al. (2024). RDD2022: A multi-national image dataset for automatic road damage detection. Geoscience Data Journal. FigShare: https://doi.org/10.6084/m9.figshare.21431547",
        "Shi Y. et al. (2016). Automatic road crack detection using random structured forests. IEEE T-ITS 17(12). https://github.com/cuilimeng/CrackForest-dataset",
        "Liu Y. et al. (2019). DeepCrack. Neurocomputing 338:139-153. https://github.com/yhlleo/DeepCrack",
    ]
    for i, cite in enumerate(cites, start=23):
        rec.cell(i, 1, cite)
        rec.merge_cells(start_row=i, start_column=1, end_row=i, end_column=5)
        rec.cell(i, 1).alignment = WRAP
        rec.row_dimensions[i].height = 36

    src = wb.create_sheet("Sources_and_Method")
    src["A1"] = "Verification method"
    src["A1"].font = Font(bold=True, size=14, color="1F4E79")
    src.merge_cells("A1:B1")
    method = [
        ("Cutoff date", "2026-10-19"),
        ("Rule", "Counts, licenses, and URLs come from official repos, data papers, or institutional landing pages. Unofficial Kaggle re-uploads were not treated as authority."),
        ("Rule", "Patches are never counted as original photographs."),
        ("Rule", "If a host required login, CAPTCHA, or a dead page, the next manual step is recorded instead of using a mirror."),
        ("SDNET2018", "https://digitalcommons.usu.edu/all_datasets/48/ and Data in Brief Table 1"),
        ("METU classification", "https://data.mendeley.com/datasets/5y9wdsg2zt/2"),
        ("METU segmentation", "https://data.mendeley.com/datasets/jwsn7tfbrp/1"),
        ("RDD2022 GitHub", "https://github.com/sekilab/RoadDamageDetector"),
        ("RDD2022 FigShare", "https://figshare.com/articles/dataset/RDD2022_-_The_multi-national_Road_Damage_Dataset_released_through_CRDDC_2022/21431547"),
        ("RDD2022 Czech ZIP", "https://bigdatacup.s3.ap-northeast-1.amazonaws.com/2022/CRDDC2022/RDD2022/Country_Specific_Data_CRDDC2022/RDD2022_Czech.zip"),
        ("CFD", "https://github.com/cuilimeng/CrackForest-dataset"),
        ("CRACK500", "https://github.com/fyangneil/pavement-crack-detection"),
        ("DeepCrack Liu", "https://github.com/yhlleo/DeepCrack"),
        ("EdmCrack600", "https://github.com/mqp2259/EdmCrack600"),
        ("SUT-Crack", "https://doi.org/10.17632/gsbmknrhkv.6"),
        ("Aigle-RN", "https://www.irit.fr/~Sylvie.Chambon/Crack_Detection_Database.html (404 on research date)"),
        ("CrackTree260 / CRKWH100 / CrackLS315", "https://github.com/qinnzou/DeepCrack"),
        ("CCSS-DATA", "https://www.mdpi.com/2072-4292/14/22/5793 and https://www.kaggle.com/datasets/parniashokri/ccssdata"),
        ("CODEBRIM", "https://zenodo.org/records/2620293"),
    ]
    src.cell(2, 1, "Item")
    src.cell(2, 2, "Value")
    style_header(src, 2)
    for i, (k, v) in enumerate(method, start=3):
        src.cell(i, 1, k).alignment = WRAP
        cell = src.cell(i, 2, v)
        cell.alignment = WRAP
        cell.border = THIN
        if str(v).startswith("http"):
            add_hyperlink(cell, v)
        src.row_dimensions[i].height = 36
    src.column_dimensions["A"].width = 36
    src.column_dimensions["B"].width = 100

    local = wb.create_sheet("Local_Download_Status", 1)
    local["A1"] = "Local download and EDA status"
    local["A1"].font = Font(bold=True, size=14, color="1F4E79", name="Calibri")
    local.merge_cells("A1:F1")
    local["A2"] = (
        "This sheet records what was actually fetched and counted on disk during the "
        "2026-10-19 EDA pass. Publication counts remain on Dataset_Comparison. "
        "Re-run scripts/eda_infrascan.py after completing blocked downloads."
    )
    local["A2"].alignment = WRAP
    local.merge_cells("A2:F2")
    local.row_dimensions[2].height = 48
    local_header = [
        "Dataset",
        "Local path",
        "Download status",
        "Verified local counts",
        "EDA executed",
        "Blocker / next step",
    ]
    for col, name in enumerate(local_header, start=1):
        local.cell(4, col, name)
    style_header(local, 6)
    local.freeze_panes = "A5"
    local_rows = [
        [
            "CrackForest (CFD)",
            "datasets/raw/cfd",
            "downloaded_verified",
            "155 JPEG (118 annotated 001-118 + 37 unlabeled extras); 118 .seg; 118 .mat; 0 unreadable",
            "Yes",
            "Use the 118 annotated images only",
        ],
        [
            "DeepCrack (Liu)",
            "datasets/raw/deepcrack",
            "downloaded_verified",
            "ZIP 67,708,808 bytes; 300 train + 237 test RGB/mask pairs; 10 train/test filename overlaps",
            "Yes",
            "Rebuild splits before training",
        ],
        [
            "SDNET2018",
            "datasets/raw/sdnet2018",
            "blocked_cloudflare",
            "0 images",
            "No",
            "Open https://digitalcommons.usu.edu/all_datasets/48/ in a browser and download SDNET2018.zip",
        ],
        [
            "RDD2022 Czech",
            "datasets/raw/rdd2022_czech",
            "downloaded_verified",
            "Czech.zip 257,118,242 bytes SHA-256 081c963a53cd2122e5fb62c7050c0c0e80efb3c71bf05f13fa26cfbec15e5d9e; 3,538 JPEG 600x600; train 2,829 with VOC XML; test 709 unlabeled; 1,745 boxes",
            "Yes",
            "S3 country URL still AccessDenied. Full FigShare dump was not downloaded. Expand to other countries from the same official zip if needed.",
        ],
    ]
    for r, row in enumerate(local_rows, start=5):
        for c, val in enumerate(row, start=1):
            cell = local.cell(r, c, val)
            cell.alignment = WRAP
            cell.border = THIN
        local.row_dimensions[r].height = 64
        url = None
        if "digitalcommons" in row[-1]:
            url = "https://digitalcommons.usu.edu/all_datasets/48/"
        if "figshare.com" in row[-1]:
            url = "https://figshare.com/articles/dataset/RDD2022_-_The_multi-national_Road_Damage_Dataset_released_through_CRDDC_2022/21431547"
        if url:
            add_hyperlink(local.cell(r, 6), url)
            local.cell(r, 6).value = row[-1]
            local.cell(r, 6).alignment = WRAP
    local.column_dimensions["A"].width = 22
    local.column_dimensions["B"].width = 28
    local.column_dimensions["C"].width = 24
    local.column_dimensions["D"].width = 55
    local.column_dimensions["E"].width = 16
    local.column_dimensions["F"].width = 55

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}")
