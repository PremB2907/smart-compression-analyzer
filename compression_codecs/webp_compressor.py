# compression/webp_compressor.py
"""WebP compression utilities.

Uses Pillow to save images as WebP with configurable quality.
"""

from pathlib import Path

from PIL import Image


def compress_webp(input_path: Path, output_dir: Path, quality: int = 75) -> Path:
    """Compress an image to WebP.

    Args:
        input_path: Path to the original image.
        output_dir: Directory for the compressed file.
        quality: WebP quality (0‑100). Higher means better quality.

    Returns:
        Path to the compressed WebP file.
    """
    output_path = output_dir / f"{input_path.stem}_webp.webp"
    with Image.open(input_path) as img:
        rgb_img = img.convert("RGB")
        rgb_img.save(output_path, "WEBP", quality=quality, method=6)
    return output_path
