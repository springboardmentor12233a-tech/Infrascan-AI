# InfraScan EDA Report

**Date:** 2026-10-19
**Repository:** [springboardmentor12233a-tech/Infrascan-AI](https://github.com/springboardmentor12233a-tech/Infrascan-AI)
**Working branch:** `dataset-research-eda` (from `siri/infrascan`)
**Workbook:** [`InfraScan_Dataset_Research.xlsx`](InfraScan_Dataset_Research.xlsx)

This report records **verified** research and **hands-on** analysis. Publication counts are cited from official pages. Local file counts come from scripts run on files that exist under `datasets/raw/`. Missing downloads are marked pending.

Existing teammate work was left in place: `infrascan.ipynb` on `siri/infrascan` and `InfraScan_Initial_Setup.ipynb` on `feature/shreya-eda-analysis`.

## 1. Project requirements vs data

| Need | Dataset | Research | Downloaded and verified | EDA | Notes |
|---|---|---|---|---|---|
| Concrete crack **classification** | SDNET2018 | Yes | **No** | Pending | Cloudflare browser step required |
| Road damage **detection** | RDD2022 Czech | Yes | **Yes** | **Yes** | Official FigShare stored member, CC BY 4.0 |
| Crack **segmentation** | DeepCrack + CFD | Yes | **Yes** | **Yes** | Non-commercial licenses |
| Other defects (spall, rebar, corrosion) | CODEBRIM | Yes | No | Pending | 8.3 GB original ZIP not fetched |

## 2. Datasets researched (15)

Verified from official repositories, data papers, or institutional landing pages. Full comparison with clickable URLs: Excel sheet `Dataset_Comparison`. Status values below match `Local_Download_Status`.

| Dataset | Original photographs | Derived patches | Task | License | Status |
|---|---|---|---|---|---|
| SDNET2018 | 230 | 56,092 of 256×256 | Classification | CC BY 4.0 | Research complete; download **blocked** (Cloudflare); EDA pending |
| METU Concrete Crack Images | 458 | 40,000 of 227×227 | Classification | CC BY 4.0 | Research complete; Mendeley download not scriptable |
| Özgenel Concrete Crack Segmentation | 458 | — | Segmentation | CC BY 4.0 | Research complete; not downloaded this pass |
| RDD2022 | 47,420 | — | Detection | CC BY 4.0 (FigShare) | Czech subset **downloaded, verified, EDA completed** |
| CFD | 118 annotated (+ 37 extra in repo) | — | Segmentation | Non-commercial | **Downloaded, verified, EDA completed** |
| CRACK500 | 500 | 1,896 / 348 / 1,124 crops | Segmentation | Unclear | Research complete; Drive wall |
| CrackTree260 | 260 | 35,100 of 512×512 in Zou recipe | Segmentation | Unclear | OneDrive |
| DeepCrack (Liu) | 537 | — | Segmentation | Non-commercial | **Downloaded, verified, EDA completed** |
| EdmCrack600 | 600 | — | Segmentation | Academic, no commercial | Google Drive |
| SUT-Crack | 130 | 25,563 of 200×200 | Class / det / seg | CC BY 4.0 | Mendeley ~988 MB, not downloaded |
| Aigle-RN | 38 commonly cited | — | Segmentation | Unverified | Official IRIT page 404 |
| CRKWH100 | 100 | — | Segmentation | Unclear | OneDrive |
| CrackLS315 | 315 | — | Segmentation | Unclear | OneDrive |
| CCSS-DATA | 670 | 512×512 experiment patches | Segmentation | CC BY-SA 4.0 | Kaggle account |
| CODEBRIM | 1,590 | Crops from 5,354 defect boxes | Multi-label detection | Non-commercial | Zenodo 8.3 GB, not downloaded |

Patches are never counted as independent original photographs.

## 3. Download status

Disk free before this continuation: **361.84 GB** on D:. FigShare RDD2022 parent archive is 13,264,172,619 bytes (~12.36 GB) and HTTP 200 with `application/zip`. The 12.36 GB file was **not** downloaded whole. It is a stored zip of seven country archives. Only `RDD2022/Czech.zip` (257,118,242 bytes) was range-fetched from the official FigShare object.

| Dataset | Source used | Result | Verified local files |
|---|---|---|---|
| CFD | `git clone --depth 1 https://github.com/cuilimeng/CrackForest-dataset.git` | Success | 155 JPEG, 118 `.seg`, 118 `.mat` |
| DeepCrack | `https://github.com/yhlleo/DeepCrack/raw/master/dataset/DeepCrack.zip` | Success | ZIP 67,708,808 bytes, SHA-256 `ec3fc2bee3b71c2cc3c74739cbc51c97b77f78193d08ce3dda0e16d7d41bf585`. 300+237 RGB and 300+237 masks. |
| RDD2022 Czech | FigShare file 38030910 stored member `RDD2022/Czech.zip` | Success | ZIP 257,118,242 bytes, SHA-256 `081c963a53cd2122e5fb62c7050c0c0e80efb3c71bf05f13fa26cfbec15e5d9e`. 3,538 JPEG, 2,829 XML. |
| SDNET2018 | Digital Commons | **Blocked** | Cloudflare challenge. No archive on disk. |
| METU classification | Mendeley S3 cache | **Blocked** | AccessDenied / JS download wall. |

CRDDC S3 `RDD2022_Czech.zip` is still HTTP 403 AccessDenied. Manifest: [`datasets/manifests/download_manifest.json`](../datasets/manifests/download_manifest.json).

## 4. EDA actually executed

```powershell
python scripts/eda_infrascan.py --help
python scripts/eda_infrascan.py --list
python scripts/eda_infrascan.py --dataset all
```

`--list` after the empty-folder fix reports only datasets with images or annotations: `cfd`, `deepcrack`, `rdd2022_czech`.

Checks on those three:

- File and image-format counts
- Dimensions and color modes (Pillow `load()`)
- Unreadable / corrupt images
- Exact MD5 duplicates
- Perceptual hashes (`imagehash.phash`, first 2,000 images)
- Folder structure
- Dataset-specific parsers (Berkeley `.seg`; DeepCrack masks; Pascal VOC XML)
- Image–label matching
- Class / crack-pixel / box imbalance
- Train/test filename overlap
- Plots, CSV inventories, sample images

SDNET2018 was not analysed. No SDNET class counts were invented.

## 5. Numerical findings (from local files)

### 5.1 CrackForest Dataset (CFD)

| Item | Value |
|---|---|
| JPEG files | 155 |
| Annotated `001.jpg`–`118.jpg` | 118 |
| Extra unlabeled JPEGs | 37 (`201`–`208`, `301`–`329`) |
| `.seg` / `.mat` | 118 / 118 |
| Image–`.seg` matches | 118 / 118 |
| Unreadable | 0 |
| MD5 duplicate groups | 0 |
| pHash duplicate groups | 0 |
| Size | 153 × 480×320; 2 extras (`328.jpg`, `329.jpg`) 320×480 |
| Color | RGB JPEG |
| Mean / median crack fraction | 0.02287 / 0.01353 |
| Min / max crack fraction | 0.00352 / 0.35286 |
| Empty masks | 0 |

Plots: `docs/eda_outputs/plots/cfd_*.png`. Samples: `docs/eda_outputs/samples/cfd/`.

### 5.2 DeepCrack (Liu et al.)

| Item | Value |
|---|---|
| RGB JPEGs / PNG masks | 537 / 537 |
| Train / test pairs | 300 / 237, all stems matched |
| Unreadable | 0 |
| MD5 duplicate groups | 0 |
| pHash duplicate groups | 1 (`test_img/11216.jpg`, `train_img/11158.jpg`) |
| Size | 980 files 544×384; 94 files 384×544 |
| Mean / median crack fraction | 0.03537 / 0.02802 |
| Train/test **filename** overlap | 10 stems `11289-1` … `11289-10` (not byte-identical) |

**Filename overlap investigation (files on disk, not a re-run of full EDA):** The 10 shared stems `11289-1` through `11289-10` exist in both `train_img` and `test_img`. Test also has `11289-11`. Paired files are **not** the same bytes: MD5 hashes differ; pHash Hamming distances are 30-40; grayscale NCC is near 0 (range about -0.04 to 0.05). Pixel mean absolute difference is about 18-31 (max 182-230). Train and test JPEG quantization tables differ. Visual inspection of `11289-1` shows the **same crack** with a different crop offset (the crack sits lower in the train crop and higher in the test crop). Corresponding `train_lab` / `test_lab` masks also differ. This is **source-image leakage**: crops from the same original (`11289-*`) appear in both splits. It is not a copy of identical files.

The pHash pair `test_img/11216.jpg` vs `train_img/11158.jpg` is a near-duplicate under different names: pHash Hamming 0, NCC 0.964, mean absolute pixel difference 2.93.

Leakage has **not** been eliminated. For future model evaluation, split by original crack / source-image id (the `11289` prefix and similar groups), not by filename uniqueness alone. Plots: `docs/eda_outputs/plots/deepcrack_*.png`.

### 5.3 RDD2022 Czech

Source: official FigShare stored member extracted to `datasets/raw/rdd2022_czech/extracted`.

| Item | Value |
|---|---|
| JPEG files | 3,538 (matches Arya et al. Czech total) |
| Train images | 2,829 |
| Test images | 709 |
| VOC XML | 2,829 (train only); 0 parse errors |
| Image–XML stem matches | 2,829 |
| Images without XML | 709 (the test set; labels withheld) |
| Unreadable | 0 |
| Size / color | All 600×600 RGB JPEG |
| MD5 duplicate groups | 0 |
| pHash duplicate groups | 3 (one pair crosses train/test: `Czech_002609.jpg` test vs `Czech_001046.jpg` train) |
| Box classes | D00 988, D10 399, D20 161, D40 197 (1,745 boxes total; matches the data-article Czech train-label count) |
| Train XML with zero objects | 1,757 of 2,829 |
| Train XML with ≥1 object | 1,072 |
| Max objects in one XML | 8 |
| Mean objects per XML | 0.617 |
| Mean box area | 5,689 px² |
| Extra classes beyond D00/D10/D20/D40 | none in this subset |

D00 dominates. D20 is the rarest CRDDC class. More than half of the train XMLs are negatives (no damage box). Test images have no public boxes, so they cannot be used for supervised evaluation without the withheld labels.

Plots: `docs/eda_outputs/plots/rdd2022_czech_box_classes.png`, `rdd2022_czech_objects_per_image.png`, size/filesize plots. Samples: `docs/eda_outputs/samples/rdd2022_czech/`.

### 5.4 SDNET2018

Hands-on EDA is **pending**. Published Table 1 (not local): 8,484 cracked / 47,608 non-cracked patches from 230 originals.

## 6. Annotation analysis

- **CFD:** Berkeley `.seg` run-length maps; segment 0 is background. MATLAB `.mat` files were counted, not opened.
- **DeepCrack:** single-channel PNG masks; no empty masks in the 537 files.
- **RDD2022 Czech:** Pascal VOC XML. Classes are only D00, D10, D20, D40. 1,757 empty annotation files are valid negatives, not parse failures.

## 7. Quality, leakage, and limitations

- No unreadable images in the three downloaded sets.
- Segmentation crack pixels are rare (~2–4%). Detection boxes are sparse (mean 0.62 per train XML).
- CFD extras 201–329 are unlabeled.
- DeepCrack train/test share 10 filenames (`11289-1` … `11289-10`) that are shifted crops of the same crack, plus one pHash near-duplicate under different names (`11216.jpg` / `11158.jpg`). Group-aware splits are still required.
- RDD Czech has one pHash pair across train/test.
- CFD and DeepCrack are **non-commercial**. RDD2022 Czech is **CC BY 4.0**.
- No downloaded set covers spalling, exposed bars, or corrosion.
- No concrete **classification** images are on disk until SDNET2018 is fetched in a browser.

## 8. Final selection

1. **SDNET2018** — still the primary classification set (CC BY 4.0). Manual Cloudflare download remains.
2. **RDD2022 Czech** — primary detection set, on disk, CC BY 4.0.
3. **DeepCrack + CFD** — segmentation, on disk, non-commercial.

**Still unsupported:** multi-class structural defects other than cracks; per-image millimetre widths; commercial-friendly segmentation licenses; SDNET original-image IDs; RDD countries other than Czech; RDD test boxes.

## 9. Remaining work

1. Browser-download SDNET2018.zip (see manual steps below).
2. Convert CFD `.seg` to PNG under `datasets/processed/`.
3. Rebuild DeepCrack splits with a **group-aware** split by original source image (for example keep all `11289-*` crops in one side). Dropping only the 10 shared filenames is not enough; `11289-11` is test-only but belongs to the same source. Do not claim leakage is gone until that regrouping is done and checked.
4. Decide whether empty RDD train XMLs stay as negatives.
5. Optionally range-fetch India/Japan/US from the same FigShare zip if more detection diversity is needed.
6. Keep large archives out of git.

### SDNET2018 manual steps

1. Open https://digitalcommons.usu.edu/all_datasets/48/ in a browser.
2. Complete the Cloudflare “Just a moment…” check. Do not script around it.
3. Download `SDNET2018.zip` (listed as 515,903 kB).
4. Save to `datasets/raw/sdnet2018/SDNET2018.zip` and extract to `datasets/raw/sdnet2018/extracted`.
5. Run `python scripts/eda_infrascan.py --dataset sdnet2018`.

## 10. How to rerun

```powershell
python -m pip install -r requirements-eda.txt
python scripts/download_datasets.py --list
python scripts/download_datasets.py --dataset all
python scripts/eda_infrascan.py --help
python scripts/eda_infrascan.py --list
python scripts/eda_infrascan.py --dataset all
python scripts/build_dataset_research_xlsx.py
```

Outputs: `docs/eda_outputs/csv/`, `docs/eda_outputs/plots/`, `docs/eda_outputs/samples/`, `docs/eda_outputs/eda_results.json`.
