"""Shared image processing helpers for local curation and web export."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}


def image_orientation(width: int, height: int) -> str:
    if not width or not height:
        return "unknown"
    ratio = width / height
    if ratio > 2:
        return "panorama"
    if ratio > 1.05:
        return "landscape"
    if ratio < 0.95:
        return "portrait"
    return "square"


def read_image_size(path: Path) -> tuple[int, int]:
    try:
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image)
            return image.size
    except Exception:
        return 0, 0


def write_web_jpeg(source: Path, target: Path, max_edge: int, quality: int, force: bool = False) -> tuple[int, int]:
    with Image.open(source) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
        width, height = image.size
        if target.exists() and not force:
            return width, height
        output = image.copy()
        output.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        target.parent.mkdir(parents=True, exist_ok=True)
        output.save(target, "JPEG", quality=quality, optimize=True, progressive=True)
        return width, height
