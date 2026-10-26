# InfraScan datasets

This folder stores **local copies** of public crack and damage datasets used for research and EDA. Large images and archives are gitignored. Do not commit them.

Hands-on EDA in this pass used only files that were actually downloaded and verified. Research covering 15 public datasets lives in [`docs/InfraScan_Dataset_Research.xlsx`](../docs/InfraScan_Dataset_Research.xlsx) and [`docs/InfraScan_EDA_Report.md`](../docs/InfraScan_EDA_Report.md).

## Layout

```text
datasets/
  README.md                 this file
  manifests/                download records (JSON)
  raw/                      original downloads, untouched
    cfd/                    CrackForest Dataset (git clone)
    deepcrack/              DeepCrack zip + extracted/
    sdnet2018/              placeholder until Cloudflare is passed
    rdd2022_czech/          Czech.zip from official FigShare stored member + extracted/
  processed/                derived patches, resized copies, converted labels
```

Keep originals in `raw/` and write any converted masks, patches, or splits under `processed/`.

## What was downloaded in this pass

| Dataset | Local path | Status |
|---|---|---|
| CrackForest (CFD) | `datasets/raw/cfd` | Verified git clone from the official repository |
| DeepCrack (Liu et al.) | `datasets/raw/deepcrack` | Verified official `DeepCrack.zip` (SHA-256 `ec3fc2bee3b71c2cc3c74739cbc51c97b77f78193d08ce3dda0e16d7d41bf585`) |
| SDNET2018 | `datasets/raw/sdnet2018` | **Not downloaded.** Digital Commons is behind a Cloudflare JavaScript challenge. |
| RDD2022 Czech | `datasets/raw/rdd2022_czech` | Verified official FigShare stored member `RDD2022/Czech.zip` (257,118,242 bytes, SHA-256 `081c963a53cd2122e5fb62c7050c0c0e80efb3c71bf05f13fa26cfbec15e5d9e`). CRDDC S3 country URL is still AccessDenied. |

Exact file counts are in `manifests/download_manifest.json` and the EDA report.

## Download instructions

Run from the repository root after installing [`requirements-eda.txt`](../requirements-eda.txt).

```powershell
python -m pip install -r requirements-eda.txt
python scripts/download_datasets.py --list
python scripts/download_datasets.py --dataset cfd
python scripts/download_datasets.py --dataset deepcrack
python scripts/download_datasets.py --dataset rdd2022_czech
```

### CFD (official GitHub)

```powershell
git clone --depth 1 https://github.com/cuilimeng/CrackForest-dataset.git datasets/raw/cfd
```

License: non-commercial research only. Cite Shi et al., IEEE T-ITS 2016.

### DeepCrack (official GitHub zip)

```powershell
curl.exe -L -o datasets/raw/deepcrack/DeepCrack.zip https://github.com/yhlleo/DeepCrack/raw/master/dataset/DeepCrack.zip
```

Extract to `datasets/raw/deepcrack/extracted`. License: non-commercial research and educational use. Cite Liu et al., Neurocomputing 2019.

### SDNET2018 (manual step)

1. Open [https://digitalcommons.usu.edu/all_datasets/48/](https://digitalcommons.usu.edu/all_datasets/48/).
2. Complete the Cloudflare check in a browser.
3. Download `SDNET2018.zip` (listed as 515,903 kB).
4. Save it as `datasets/raw/sdnet2018/SDNET2018.zip` and extract to `datasets/raw/sdnet2018/extracted`.
5. Re-run EDA: `python scripts/eda_infrascan.py --dataset sdnet2018`

License: CC BY 4.0. Cite Dorafshan, Thomas, Maguire, Data in Brief 2018. The 56,092 files are 256×256 **patches** from 230 original photographs.

### RDD2022 Czech (official FigShare stored member)

The CRDDC S3 country ZIP remains `AccessDenied`. The official FigShare file `RDD2022_released_through_CRDDC2022.zip` (13,264,172,619 bytes, CC BY 4.0) stores each country as an uncompressed nested zip. `scripts/download_datasets.py` range-downloads only `RDD2022/Czech.zip` (257,118,242 bytes).

```powershell
python scripts/download_datasets.py --dataset rdd2022_czech
python scripts/eda_infrascan.py --dataset rdd2022_czech
```

Cite Arya et al., Geoscience Data Journal 2024. The CRDDC label map is `datasets/manifests/rdd_label_map.pbtxt`.

## Licenses and citations

| Dataset | License (verified) | Citation |
|---|---|---|
| SDNET2018 | CC BY 4.0 | Maguire, Dorafshan, Thomas (2018). https://doi.org/10.15142/T3TD19 |
| METU classification / segmentation | CC BY 4.0 | Özgenel, Mendeley Data |
| RDD2022 | CC BY 4.0 on FigShare | Arya et al. (2024), https://doi.org/10.6084/m9.figshare.21431547 |
| CFD | Non-commercial research | Shi et al. (2016), IEEE T-ITS |
| DeepCrack (Liu) | Non-commercial research and education | Liu et al. (2019), Neurocomputing |
| SUT-Crack | CC BY 4.0 | Sabouri and Sepidbar (2023), Data in Brief |
| CODEBRIM | Non-commercial / educational | Mundt et al. (2019), CVPR; Zenodo 10.5281/zenodo.2620293 |
| CCSS-DATA | CC BY-SA 4.0 | Shokri et al. (2022), Remote Sensing |
| CRACK500 | Not clearly stated | Yang et al. (2019), IEEE T-ITS |

CFD and DeepCrack are suitable for this academic project. They are not a commercial-product license.

## Rerun EDA

```powershell
python scripts/eda_infrascan.py --help
python scripts/eda_infrascan.py --dataset all
python scripts/eda_infrascan.py --dataset cfd
python scripts/eda_infrascan.py --dataset deepcrack --skip-perceptual
```

Outputs go to `docs/eda_outputs/` (CSV, plots, sample images, JSON).

## Git reminder

`.gitignore` excludes `datasets/raw/**`, `datasets/processed/**`, archive files (`*.zip`, `*.rar`, `*.7z`), the nested CrackForest clone `datasets/raw/cfd/`, and copied EDA sample JPEGs under `docs/eda_outputs/samples/`. Do not `git add` that nested clone (it has its own `.git` and would become a gitlink). Plots and CSV/JSON summaries under `docs/eda_outputs/` are small generated outputs, not the training set.
