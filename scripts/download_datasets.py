#!/usr/bin/env python3
"""Download official InfraScan EDA subsets, extract them, and write a manifest.

Skips archives that are already present and valid. Rejects HTML/XML error pages.
RDD2022 Czech is taken from the official FigShare zip via HTTP Range (stored member).
SDNET2018 is recorded as blocked (Cloudflare); this script does not bypass that check.

Examples:
  python scripts/download_datasets.py --list
  python scripts/download_datasets.py --dataset cfd
  python scripts/download_datasets.py --dataset rdd2022_czech
  python scripts/download_datasets.py --dataset all
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "datasets" / "raw"
MANIFEST_DIR = ROOT / "datasets" / "manifests"
MANIFEST_PATH = MANIFEST_DIR / "download_manifest.json"
USER_AGENT = "InfraScan-DatasetResearch/1.0 (academic; +https://github.com/springboardmentor12233a-tech/Infrascan-AI)"

# Official FigShare article 21431547, file 38030910.
FIGSHARE_RDD_URL = "https://ndownloader.figshare.com/files/38030910"
FIGSHARE_RDD_BYTES = 13264172619

DATASETS: dict[str, dict[str, Any]] = {
    "cfd": {
        "name": "CrackForest Dataset (CFD)",
        "method": "git",
        "url": "https://github.com/cuilimeng/CrackForest-dataset.git",
        "dest": RAW_DIR / "cfd",
        "expected_mb": 8,
        "notes": "Official GitHub repository with images, MATLAB ground truth, and seg maps. Non-commercial research only.",
    },
    "deepcrack": {
        "name": "DeepCrack",
        "method": "http_zip",
        "url": "https://github.com/yhlleo/DeepCrack/raw/master/dataset/DeepCrack.zip",
        "dest": RAW_DIR / "deepcrack",
        "archive_name": "DeepCrack.zip",
        "expected_mb": 65,
        "notes": "Official dataset zip from yhlleo/DeepCrack. Non-commercial research and educational use.",
    },
    "rdd2022_czech": {
        "name": "RDD2022 Czech subset",
        "method": "figshare_stored_member",
        "url": FIGSHARE_RDD_URL,
        "dest": RAW_DIR / "rdd2022_czech",
        "archive_name": "Czech.zip",
        "member_name": "RDD2022/Czech.zip",
        "expected_mb": 246,
        "expected_bytes": 257118242,
        "notes": "Official CRDDC'2022 Czech archive stored inside FigShare RDD2022_released_through_CRDDC2022.zip (CC BY 4.0).",
    },
    "sdnet2018": {
        "name": "SDNET2018",
        "method": "blocked_cloudflare",
        "url": "https://digitalcommons.usu.edu/all_datasets/48/",
        "dest": RAW_DIR / "sdnet2018",
        "archive_name": "SDNET2018.zip",
        "expected_mb": 504,
        "notes": "Official Digital Commons ZIP is behind a Cloudflare JavaScript challenge. Do not bypass it.",
    },
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def disk_free_gb(path: Path) -> float:
    return shutil.disk_usage(path).free / (1024 ** 3)


def sha256_file(path: Path, chunk: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def count_images(path: Path) -> int:
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
    skip = {".git"}
    return sum(
        1
        for p in path.rglob("*")
        if p.is_file() and p.suffix.lower() in exts and not any(part in skip for part in p.parts)
    )


def looks_like_error_page(path: Path) -> str | None:
    if not path.exists() or path.stat().st_size == 0:
        return "empty file"
    head = path.read_bytes()[:256]
    if head.startswith(b"<!DOCTYPE") or head.startswith(b"<html") or b"Just a moment" in head:
        return "HTML challenge or error page"
    if head.startswith(b"<?xml") and b"AccessDenied" in head:
        return "XML AccessDenied"
    if path.stat().st_size < 1024 * 50 and b"<Error>" in head:
        return "XML error page"
    return None


def curl_download(url: str, dest: Path, extra_headers: list[str] | None = None) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "curl.exe",
        "-L",
        "--retry",
        "8",
        "--retry-all-errors",
        "--retry-delay",
        "3",
        "-C",
        "-",
        "-A",
        USER_AGENT,
        "--fail",
        "-o",
        str(dest),
        url,
    ]
    if extra_headers:
        for header in extra_headers:
            cmd.extend(["-H", header])
    print(" ".join(cmd[:-1]), url)
    completed = subprocess.run(cmd)
    return completed.returncode


def http_get_bytes(url: str, start: int, end: int) -> bytes:
    req = Request(
        url,
        headers={"User-Agent": USER_AGENT, "Range": f"bytes={start}-{end}"},
    )
    with urlopen(req, timeout=60) as response:
        return response.read()


def figshare_member_offsets(url: str, member_name: str) -> tuple[int, int, int]:
    """Return (payload_start, payload_end, payload_size) for a stored zip member."""
    tail = http_get_bytes(url, FIGSHARE_RDD_BYTES - 4096, FIGSHARE_RDD_BYTES - 1)
    idx = tail.rfind(b"PK\x06\x06")
    if idx < 0:
        raise RuntimeError("ZIP64 EOCD not found in FigShare archive tail")
    rec = tail[idx:]
    _n_this, _n_total, cd_size, cd_off = struct.unpack_from("<QQQQ", rec, 24)
    cd = http_get_bytes(url, cd_off, cd_off + cd_size - 1)
    pos = 0
    while pos + 46 <= len(cd):
        if cd[pos : pos + 4] != b"PK\x01\x02":
            break
        (
            _ver_made,
            _ver_need,
            _flags,
            method,
            _time,
            _date,
            _crc,
            comp,
            uncomp,
            namelen,
            extra_len,
            comm_len,
            _disk,
            _int_attr,
            _ext_attr,
            local_off,
        ) = struct.unpack_from("<HHHHHHIIIHHHHHII", cd, pos + 4)
        name = cd[pos + 46 : pos + 46 + namelen].decode("utf-8", "replace")
        extra = cd[pos + 46 + namelen : pos + 46 + namelen + extra_len]
        abs_off = local_off
        if local_off == 0xFFFFFFFF or comp == 0xFFFFFFFF or uncomp == 0xFFFFFFFF:
            epos = 0
            dpos_used = {"uncomp": uncomp == 0xFFFFFFFF, "comp": comp == 0xFFFFFFFF, "off": local_off == 0xFFFFFFFF}
            dpos = 0
            while epos + 4 <= len(extra):
                eid, esize = struct.unpack_from("<HH", extra, epos)
                data = extra[epos + 4 : epos + 4 + esize]
                dpos = 0
                if uncomp == 0xFFFFFFFF and dpos + 8 <= len(data):
                    uncomp = struct.unpack_from("<Q", data, dpos)[0]
                    dpos += 8
                if comp == 0xFFFFFFFF and dpos + 8 <= len(data):
                    comp = struct.unpack_from("<Q", data, dpos)[0]
                    dpos += 8
                if local_off == 0xFFFFFFFF and dpos + 8 <= len(data):
                    abs_off = struct.unpack_from("<Q", data, dpos)[0]
                    dpos += 8
                epos += 4 + esize
                _ = (eid, dpos_used)
        if name == member_name:
            if method != 0:
                raise RuntimeError(f"{member_name} is compressed (method {method}); range extract requires stored members")
            local = http_get_bytes(url, abs_off, abs_off + 29)
            (
                _sig,
                _ver,
                _flags,
                _method,
                _t,
                _d,
                _crc2,
                _c,
                _u,
                local_namelen,
                local_extra,
            ) = struct.unpack_from("<HHHHHIIIHH", local, 4)
            payload_start = abs_off + 30 + local_namelen + local_extra
            payload_size = comp
            payload_end = payload_start + payload_size - 1
            return payload_start, payload_end, payload_size
        pos += 46 + namelen + extra_len + comm_len
    raise FileNotFoundError(f"Member {member_name} not found in FigShare zip")


def extract_zip(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    print(f"Extracting {archive.name} -> {dest}")
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(dest)
    print("  extraction complete")


def git_clone(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and count_images(dest) > 0:
        print(f"Git dataset already present with images: {dest}")
        return
    if dest.exists() and any(dest.iterdir()):
        print(f"Destination already has files: {dest}")
        return
    if dest.exists():
        dest.rmdir()
    print(f"Cloning {url}")
    subprocess.run(["git", "clone", "--depth", "1", url, str(dest)], check=True)


def record_entry(dataset_id: str, spec: dict[str, Any], status: str, extra: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset_id": dataset_id,
        "dataset_name": spec["name"],
        "source_url": spec["url"],
        "download_date_utc": utc_now(),
        "local_path": str(spec["dest"].relative_to(ROOT)).replace("\\", "/"),
        "status": status,
        "notes": spec.get("notes", ""),
        **extra,
    }


def already_extracted(dest: Path) -> bool:
    extracted = dest / "extracted"
    if extracted.exists() and count_images(extracted) > 0:
        return True
    return count_images(dest) > 0


def download_one(dataset_id: str) -> dict[str, Any]:
    spec = DATASETS[dataset_id]
    dest: Path = spec["dest"]
    dest.mkdir(parents=True, exist_ok=True)
    extra: dict[str, Any] = {"expected_size_mb": spec.get("expected_mb")}
    extra["disk_free_gb_before"] = round(disk_free_gb(dest), 2)

    if spec["method"] == "blocked_cloudflare":
        extra["next_step"] = (
            "Open https://digitalcommons.usu.edu/all_datasets/48/ in a browser, "
            "complete the Cloudflare check, download SDNET2018.zip (listed as 515,903 kB), "
            "save it to datasets/raw/sdnet2018/, and extract to extracted/."
        )
        print(f"SKIP {dataset_id}: Cloudflare browser download required")
        return record_entry(dataset_id, spec, "blocked_cloudflare", extra)

    needed_gb = (spec.get("expected_mb", 0) * 3) / 1024
    if extra["disk_free_gb_before"] < max(needed_gb, 1.0):
        extra["error"] = (
            f"Insufficient disk space: {extra['disk_free_gb_before']:.2f} GB free, "
            f"need about {needed_gb:.2f} GB"
        )
        print(extra["error"])
        return record_entry(dataset_id, spec, "failed_disk_space", extra)

    try:
        if spec["method"] == "git":
            git_clone(spec["url"], dest)
            extra["archive_status"] = "git_clone"
            extra["verified_image_count"] = count_images(dest)
            extra["extracted"] = True
            return record_entry(dataset_id, spec, "downloaded_verified", extra)

        archive = dest / spec["archive_name"]
        extract_dir = dest / "extracted"

        if already_extracted(dest) and archive.exists() and zipfile.is_zipfile(archive):
            extra["archive_path"] = str(archive.relative_to(ROOT)).replace("\\", "/")
            extra["archive_bytes"] = archive.stat().st_size
            extra["archive_status"] = "already_present"
            extra["extracted"] = True
            extra["verified_image_count"] = count_images(extract_dir if extract_dir.exists() else dest)
            extra["extracted_path"] = str(extract_dir.relative_to(ROOT)).replace("\\", "/")
            print(f"SKIP {dataset_id}: already extracted ({extra['verified_image_count']} images)")
            extra["archive_sha256"] = sha256_file(archive)
            return record_entry(dataset_id, spec, "downloaded_verified", extra)

        if spec["method"] == "figshare_stored_member":
            expected = int(spec.get("expected_bytes") or 0)
            if archive.exists() and expected and archive.stat().st_size == expected and zipfile.is_zipfile(archive):
                print(f"Archive already present: {archive} ({archive.stat().st_size} bytes)")
            else:
                start, end, size = figshare_member_offsets(spec["url"], spec["member_name"])
                extra["range_start"] = start
                extra["range_end"] = end
                extra["expected_bytes"] = size
                extra["figshare_parent_bytes"] = FIGSHARE_RDD_BYTES
                extra["disk_free_gb_before"] = round(disk_free_gb(dest), 2)
                if extra["disk_free_gb_before"] < (size * 3) / (1024 ** 3):
                    extra["error"] = "Insufficient disk space for Czech subset"
                    return record_entry(dataset_id, spec, "failed_disk_space", extra)
                code = curl_download(spec["url"], archive, extra_headers=[f"Range: bytes={start}-{end}"])
                if code != 0:
                    extra["error"] = f"curl exit {code}"
                    return record_entry(dataset_id, spec, "failed", extra)
        elif spec["method"] == "http_zip":
            if archive.exists() and archive.stat().st_size > 1024 * 1024 and zipfile.is_zipfile(archive):
                print(f"Archive already present: {archive} ({archive.stat().st_size / (1024 ** 2):.1f} MB)")
            else:
                code = curl_download(spec["url"], archive)
                if code != 0:
                    extra["error"] = f"curl exit {code}"
                    return record_entry(dataset_id, spec, "failed", extra)
        else:
            extra["error"] = f"Unknown method {spec['method']}"
            return record_entry(dataset_id, spec, "failed", extra)

        extra["archive_path"] = str(archive.relative_to(ROOT)).replace("\\", "/")
        extra["archive_bytes"] = archive.stat().st_size
        problem = looks_like_error_page(archive)
        if problem:
            extra["error"] = problem
            extra["first_bytes"] = archive.read_bytes()[:180].decode("latin-1", errors="replace")
            extra["archive_status"] = "invalid"
            return record_entry(dataset_id, spec, "failed_invalid_archive", extra)
        if spec.get("expected_bytes") and archive.stat().st_size != spec["expected_bytes"]:
            extra["error"] = (
                f"Size mismatch: got {archive.stat().st_size}, expected {spec['expected_bytes']}"
            )
            extra["archive_status"] = "size_mismatch"
            return record_entry(dataset_id, spec, "failed_invalid_archive", extra)
        if not zipfile.is_zipfile(archive):
            extra["error"] = "Downloaded file is not a valid ZIP archive"
            extra["first_bytes"] = archive.read_bytes()[:200].decode("latin-1", errors="replace")
            extra["archive_status"] = "invalid"
            return record_entry(dataset_id, spec, "failed_invalid_archive", extra)

        extra["archive_sha256"] = sha256_file(archive)
        extra["archive_status"] = "present_valid_zip"
        if extract_dir.exists() and count_images(extract_dir) > 0:
            print(f"Already extracted with images: {extract_dir}")
        else:
            extract_zip(archive, extract_dir)
        extra["extracted"] = True
        extra["verified_image_count"] = count_images(extract_dir)
        extra["extracted_path"] = str(extract_dir.relative_to(ROOT)).replace("\\", "/")
        return record_entry(dataset_id, spec, "downloaded_verified", extra)
    except Exception as exc:
        extra["error"] = f"{type(exc).__name__}: {exc}"
        print(f"FAILED {dataset_id}: {extra['error']}")
        return record_entry(dataset_id, spec, "failed", extra)


def load_existing_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return {"datasets": []}
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"datasets": []}


def save_manifest(entries: list[dict[str, Any]]) -> Path:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_existing_manifest()
    by_id = {item.get("dataset_id"): item for item in existing.get("datasets", []) if item.get("dataset_id")}
    for entry in entries:
        by_id[entry["dataset_id"]] = entry
    payload = {
        "generated_utc": utc_now(),
        "repo_root_note": "Paths are relative to the repository root. Image archives must not be committed.",
        "disk_free_gb": round(disk_free_gb(ROOT), 2),
        "datasets": list(by_id.values()),
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Manifest written: {MANIFEST_PATH}")
    return MANIFEST_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download official InfraScan EDA dataset subsets.")
    parser.add_argument(
        "--dataset",
        default="all",
        help="Dataset id to download, or 'all'. Choices: " + ", ".join(DATASETS),
    )
    parser.add_argument("--list", action="store_true", help="List available dataset ids and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list:
        for key, spec in DATASETS.items():
            print(f"{key:16} {spec['expected_mb']:>6} MB  {spec['method']:24} {spec['name']}")
            print(f"{'':16} {spec['url']}")
        return 0

    selected = list(DATASETS) if args.dataset == "all" else [args.dataset]
    unknown = [item for item in selected if item not in DATASETS]
    if unknown:
        print(f"Unknown dataset id(s): {unknown}")
        return 2

    print(f"Repository root: {ROOT}")
    print(f"Free disk space: {disk_free_gb(ROOT):.2f} GB")
    entries = [download_one(dataset_id) for dataset_id in selected]
    save_manifest(entries)
    failed = [e for e in entries if not str(e["status"]).startswith("downloaded") and e["status"] != "blocked_cloudflare"]
    for entry in entries:
        print(f"{entry['dataset_id']}: {entry['status']} images={entry.get('verified_image_count')}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
