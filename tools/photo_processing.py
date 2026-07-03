"""Shared image processing helpers for local curation and web export."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps


# Local trusted originals can include stitched panoramas above Pillow's default
# decompression-bomb threshold.
Image.MAX_IMAGE_PIXELS = None

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
EXIF_ORIENTATION = 274
SWAPPED_ORIENTATIONS = {5, 6, 7, 8}


def oriented_size(image: Image.Image) -> tuple[int, int]:
    width, height = image.size
    try:
        orientation = image.getexif().get(EXIF_ORIENTATION)
    except Exception:
        orientation = None
    if orientation in SWAPPED_ORIENTATIONS:
        return height, width
    return width, height


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
            return oriented_size(image)
    except Exception:
        return 0, 0


def write_web_jpeg(source: Path, target: Path, max_edge: int, quality: int, force: bool = False) -> tuple[int, int]:
    with Image.open(source) as original:
        width, height = oriented_size(original)
        if target.exists() and not force:
            return width, height
        original.draft("RGB", (max_edge, max_edge))
        image = ImageOps.exif_transpose(original).convert("RGB")
        output = image.copy()
        output.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        target.parent.mkdir(parents=True, exist_ok=True)
        output.save(target, "JPEG", quality=quality, optimize=True, progressive=True)
        return width, height
