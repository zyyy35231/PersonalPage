#!/usr/bin/env python3
"""Prepare web-sized photo assets and draft data entries for the Zy portfolio."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "photo"


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


def image_orientation(width: int, height: int) -> str:
    ratio = width / height
    if ratio > 2:
        return "panorama"
    if ratio > 1.08:
        return "landscape"
    if ratio < 0.92:
        return "portrait"
    return "square"


def resize_to_limit(image: Image.Image, max_edge: int) -> Image.Image:
    output = image.copy()
    output.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    return output


def save_jpeg(image: Image.Image, path: Path, quality: int, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "JPEG", quality=quality, optimize=True, progressive=True)


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


def draft_entry(path: Path, slug: str, width: int, height: int, out_dir: Path) -> dict:
    year_match = re.search(r"(20\d{2})", path.name)
    year = year_match.group(1) if year_match else str(datetime.fromtimestamp(path.stat().st_mtime).year)
    image_path = out_dir / f"{slug}.jpg"
    thumb_path = out_dir / "thumbs" / f"{slug}.jpg"
    return {
        "id": slug,
        "title": path.stem,
        "series": "未分类",
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
    args = parser.parse_args()

    source = Path(args.source)
    out_dir = Path(args.out)
    data_path = Path(args.data)
    entries = read_existing_data(data_path)
    known_ids = {entry["id"] for entry in entries}

    for path in source_files(source, args.files):
        slug = slugify(path.stem)
        image_out = out_dir / f"{slug}.jpg"
        thumb_out = out_dir / "thumbs" / f"{slug}.jpg"

        with Image.open(path) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
            full = resize_to_limit(image, args.max_edge)
            thumb = resize_to_limit(image, args.thumb_edge)
            save_jpeg(full, image_out, args.quality, args.force)
            save_jpeg(thumb, thumb_out, args.thumb_quality, args.force)
            width, height = image.size

        if slug not in known_ids:
            entries.append(draft_entry(path, slug, width, height, out_dir))
            known_ids.add(slug)

        print(f"prepared {path.name} -> {image_out}")

    write_data(data_path, entries)
    print(f"updated {data_path}")


if __name__ == "__main__":
    main()
