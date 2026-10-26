# RDD2022 Czech subset

Official parent archive (CC BY 4.0):
https://figshare.com/articles/dataset/RDD2022_-_The_multi-national_Road_Damage_Dataset_released_through_CRDDC_2022/21431547

`Czech.zip` (257,118,242 bytes) is the stored member `RDD2022/Czech.zip` inside FigShare file 38030910. The CRDDC S3 country URL remains AccessDenied.

Local layout after extraction:

```text
extracted/Czech/train/images/        2829 JPEG
extracted/Czech/train/annotations/xmls/  2829 Pascal VOC XML
extracted/Czech/test/images/         709 JPEG (no public boxes)
```

Re-run EDA:

```powershell
python scripts/eda_infrascan.py --dataset rdd2022_czech
```
