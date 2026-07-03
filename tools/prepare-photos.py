#!/usr/bin/env python3
"""Prepare web-sized photo assets and draft data entries for the Zy portfolio."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from photo_processing import IMAGE_EXTENSIONS, image_orientation, write_web_jpeg


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "photo"


def curation_slug(path: Path) -> str:
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:8]
    return f"{slugify(path.stem)}-{digest}"


def read_existing_data(path: Path) -> list[dict]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    match = re.search(r"window\.ZY_PHOTOS\s*=\s*(\[.*?\]);?\s*$", text, re.S)
    if not match:
        raise ValueError(f"Cannot parse {path}. Expected `window.ZY_PHOTOS = [...]`.")
    return json.loads(match.group(1))


def write_data(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(entries, ensure_ascii=False, indent=2)
    path.write_text(f"window.ZY_PHOTOS = {body};\n", encoding="utf-8")


def source_files(source: Path, selected: list[str]) -> list[Path]:
    if selected:
        files = [source / item for item in selected]
    else:
        files = sorted(path for path in source.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS)
    missing = [path for path in files if not path.exists()]
    if missing:
        names = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Missing source files: {names}")
    return files


def curation_entries(path: Path, status: str) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Curation draft not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    photos = payload.get("photos", []) if isinstance(payload, dict) else []
    entries = []
    for item in photos:
        if item.get("status") != status:
            continue
        source_path = Path(item.get("sourcePath", ""))
        if not source_path.exists() or source_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        entries.append(item)
    return entries


def draft_entry(path: Path, slug: str, width: int, height: int, out_dir: Path, curation: dict | None = None) -> dict:
    year_match = re.search(r"(20\d{2})", path.name)
    year = year_match.group(1) if year_match else str(datetime.fromtimestamp(path.stat().st_mtime).year)
    image_path = out_dir / f"{slug}.jpg"
    thumb_path = out_dir / "thumbs" / f"{slug}.jpg"
    series = (curation or {}).get("series") or "未分类"
    return {
        "id": slug,
        "title": path.stem,
        "series": series,
        "year": year,
        "image": image_path.as_posix(),
        "thumb": thumb_path.as_posix(),
        "alt": f"{path.stem} 的摄影作品",
        "orientation": image_orientation(width, height),
        "featured": False,
        "cameraMeta": ""
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate web images and draft Zy portfolio data.")
    parser.add_argument("files", nargs="*", help="Photo filenames inside --source. If omitted, all images are processed.")
    parser.add_argument("--source", default="Photos", help="Source photo folder.")
    parser.add_argument("--out", default="assets/photos", help="Output folder for web images.")
    parser.add_argument("--data", default="assets/photo-data.js", help="Portfolio data file to update.")
    parser.add_argument("--max-edge", type=int, default=2400, help="Maximum edge for full web images.")
    parser.add_argument("--thumb-edge", type=int, default=900, help="Maximum edge for thumbnails.")
    parser.add_argument("--quality", type=int, default=88, help="JPEG quality for full images.")
    parser.add_argument("--thumb-quality", type=int, default=82, help="JPEG quality for thumbnails.")
    parser.add_argument("--force", action="store_true", help="Regenerate existing web images.")
    parser.add_argument("--from-curation", help="Read selected source photos from a curation draft JSON file.")
    parser.add_argument("--curation-status", default="selected", help="Curation status to import. Defaults to selected.")
    args = parser.parse_args()

    source = Path(args.source)
    out_dir = Path(args.out)
    data_path = Path(args.data)
    entries = read_existing_data(data_path)
    known_ids = {entry["id"] for entry in entries}
    if args.from_curation:
        curation_items = curation_entries(Path(args.from_curation), args.curation_status)
        if not curation_items:
            print(f"no photos with status {args.curation_status!r} in {args.from_curation}")
            return
        work_items = [(Path(item["sourcePath"]), item, curation_slug(Path(item["sourcePath"]))) for item in curation_items]
    else:
        work_items = [(path, None, slugify(path.stem)) for path in source_files(source, args.files)]

    for path, curation, slug in work_items:
        image_out = out_dir / f"{slug}.jpg"
        thumb_out = out_dir / "thumbs" / f"{slug}.jpg"

        width, height = write_web_jpeg(path, image_out, args.max_edge, args.quality, args.force)
        write_web_jpeg(path, thumb_out, args.thumb_edge, args.thumb_quality, args.force)

        if slug not in known_ids:
            entries.append(draft_entry(path, slug, width, height, out_dir, curation))
            known_ids.add(slug)

        print(f"prepared {path.name} -> {image_out}")

    write_data(data_path, entries)
    print(f"updated {data_path}")


if __name__ == "__main__":
    main()
