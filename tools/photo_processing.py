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


def extract_accent_color(path: Path, fallback: str = "#9a9287") -> str:
    try:
        with Image.open(path) as original:
            original.draft("RGB", (320, 320))
            image = ImageOps.exif_transpose(original).convert("RGB")
            image.thumbnail((96, 96), Image.Resampling.LANCZOS)
            quantized = image.quantize(colors=8, method=Image.Quantize.MEDIANCUT).convert("RGB")
            colors = quantized.getcolors(96 * 96) or []
    except Exception:
        return fallback

    best_score = -1.0
    best_color = None
    for count, (red, green, blue) in colors:
        high = max(red, green, blue) / 255
        low = min(red, green, blue) / 255
        saturation = high - low
        lightness = (high + low) / 2
        if lightness < 0.12 or lightness > 0.92:
            continue
        score = count * (0.52 + saturation) * (1 - abs(lightness - 0.52))
        if score > best_score:
            best_score = score
            best_color = (red, green, blue)

    if best_color is None:
        return fallback
    return "#{:02x}{:02x}{:02x}".format(*best_color)


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
