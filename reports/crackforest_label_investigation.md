# CrackForest Label Investigation

## Scope

This investigation examined the 22 MATLAB annotations that contain labels `3`
and/or `4`. The existing preparation script, original dataset files, and
already-generated processed masks were not modified.

The inspected source is:

- `datasets/crack_segmentation/README.md`
- `datasets/crack_segmentation/groundTruth/*.mat`
- `datasets/crack_segmentation/seg/*.seg`
- Matching images in `datasets/crack_segmentation/image/`

The upstream dataset repository was also checked:
<https://github.com/cuilimeng/CrackForest-dataset>.

## Documentation findings

The repository README describes CrackForest as an **annotated road crack image
database** and states that it is available for non-commercial research. It
does not define labels `1`, `2`, `3`, or `4` as separate semantic classes.
It also does not say that labels `3` or `4` are boundaries or background.

Therefore, the README alone is insufficient to map the extra values. The raw
annotation format provides the additional evidence below.

## `.seg` format findings

Each `.seg` file has this structure:

```text
width 480
height 320
segments N
gray 1
invert 0
flipflop 0
format ascii cr
data
<region_id> <row> <start_column> <end_column>
```

The first value on each data row is a region identifier. The rows describe
horizontal runs of pixels, not polygon boundaries. The separate `Boundaries`
array in the MATLAB file is therefore the boundary representation; the
region IDs in `.seg` are not boundary values.

The `segments` header agrees with the number of region IDs in every inspected
file. For example:

- `040.seg`: `segments 3`, region IDs `0`, `1`, `2`
- `084.seg`: `segments 4`, region IDs `0`, `1`, `2`, `3`
- `102.seg`: `segments 4`, region IDs `0`, `1`, `2`, `3`

## MATLAB-to-SEG comparison

All 118 available `.mat`/`.seg` pairs were parsed and compared. The result
was exact for every pair:

```text
groundTruth.Segmentation == parsed_SEG_region_ids + 1
```

There were **zero mismatches**.

This explains the apparent extra MATLAB values:

| MATLAB `Segmentation` value | `.seg` region ID | Verified interpretation |
|---:|---:|---|
| 1 | 0 | Background region |
| 2 | 1 | First annotated foreground crack region |
| 3 | 2 | Additional annotated foreground crack region |
| 4 | 3 | Additional annotated foreground crack region |

These are region/segment IDs, not four damage classes. The number of
foreground regions varies by image. Among the 118 annotated pairs:

- 96 contain MATLAB values `{1, 2}`
- 17 contain `{1, 2, 3}`
- 5 contain `{1, 2, 3, 4}`

## Representative examples

### `040`

Evidence files: `groundTruth/040.mat`, `seg/040.seg`, `image/040.jpg`.

- `.seg` header: `segments 3`
- MATLAB values: `{1, 2, 3}`
- Pixel counts:
  - label `1`: 151,269
  - label `2`: 2,326
  - label `3`: 5
- The five label-3 pixels are a small additional annotated region near the
  main crack area.
- The `.seg` file represents these pixels with region ID `2`; it does not
  represent them as a boundary-only value.

### `054`

Evidence files: `groundTruth/054.mat`, `seg/054.seg`, `image/054.jpg`.

- `.seg` header: `segments 3`
- MATLAB values: `{1, 2, 3}`
- Pixel counts:
  - label `1`: 150,161
  - label `2`: 3,267
  - label `3`: 172
- Label `3` is a separate small foreground region near the right side of the
  annotated crack. It is encoded as region ID `2` in `.seg`.

### `084`

Evidence files: `groundTruth/084.mat`, `seg/084.seg`, `image/084.jpg`.

- `.seg` header: `segments 4`
- MATLAB values: `{1, 2, 3, 4}`
- Pixel counts:
  - label `1`: 146,435
  - label `2`: 3,359
  - label `3`: 3,506
  - label `4`: 300
- The image visibly contains multiple connected crack paths. The additional
  labels occupy crack-shaped regions:
  - label `2`: lower/horizontal crack region
  - label `3`: central crossing crack region
  - label `4`: upper vertical crack region
- The `.seg` file uses region IDs `1`, `2`, and `3` for these three foreground
  regions. The `Boundaries` array is stored separately.

### `102`

Evidence files: `groundTruth/102.mat`, `seg/102.seg`, `image/102.jpg`.

- `.seg` header: `segments 4`
- MATLAB values: `{1, 2, 3, 4}`
- The three non-background regions form the main crack and its branches.
- Exact raster comparison again gives MATLAB values equal to `.seg` values
  plus one.

### `107`

Evidence files: `groundTruth/107.mat`, `seg/107.seg`, `image/107.jpg`.

- `.seg` header: `segments 4`
- MATLAB values: `{1, 2, 3, 4}`
- Labels `2`, `3`, and `4` are three foreground annotated regions.
- The MATLAB and `.seg` rasters match exactly under the one-based offset.

## Meaning of the labels

The evidence supports the following interpretation:

1. MATLAB label `1` is background. This is the one-based representation of
   `.seg` region ID `0`.
2. MATLAB label `2` is a crack foreground region. It is the one-based
   representation of `.seg` region ID `1`.
3. MATLAB label `3` is an additional crack foreground region, not a separate
   damage class and not a boundary value.
4. MATLAB label `4` is another additional crack foreground region, not a
   separate damage class and not a boundary value.

The dataset does not provide evidence that labels `3` and `4` represent
background. Their `.seg` rows assign them explicit filled regions, while
boundaries are provided separately in `groundTruth.Boundaries`.

## Recommendation

The 22 annotations **can safely be included in binary U-Net training** once
the preparation logic is deliberately updated to use this verified rule:

```text
MATLAB label 1 -> binary background 0
MATLAB labels 2, 3, 4 -> binary crack 255
```

This is not an assumption based on pixel frequency. It follows from:

1. The exact MATLAB/`.seg` raster correspondence across all 118 pairs.
2. The `.seg` `segments` header and region-ID encoding.
3. The separate `Boundaries` field.
4. The crack-region appearance and locations in representative images.

The current preparation script was intentionally not changed in this
investigation. The 22 files remain excluded from the existing processed
outputs until the mapping rule is reviewed and explicitly applied.

The 37 original images without corresponding `.mat` annotations remain
unusable for supervised segmentation training unless genuine masks are
obtained for them.

## Sources

- Local dataset documentation: `datasets/crack_segmentation/README.md`
- Local raw annotations: `datasets/crack_segmentation/groundTruth/*.mat`
- Local run-length region annotations: `datasets/crack_segmentation/seg/*.seg`
- Local source images: `datasets/crack_segmentation/image/*.jpg`
- Upstream dataset repository: <https://github.com/cuilimeng/CrackForest-dataset>
- Upstream README: <https://raw.githubusercontent.com/cuilimeng/CrackForest-dataset/master/README.md>
- Upstream representative annotation:
  <https://raw.githubusercontent.com/cuilimeng/CrackForest-dataset/master/seg/084.seg>
