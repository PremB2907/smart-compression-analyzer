# compression/jpeg_compressor.py
"""JPEG compression utilities.

Provides a simple function to compress an image to JPEG format using Pillow.
"""

from pathlib import Path

from PIL import Image


def compress_jpeg(input_path: Path, output_dir: Path, quality: int = 75) -> Path:
    """Compress an image to JPEG.

    Args:
        input_path: Path to the original image file.
        output_dir: Directory where the compressed file will be saved.
        quality: JPEG quality (1‑100). Higher means better quality, larger size.

    Returns:
        Path to the compressed JPEG file.
    """
    output_path = output_dir / f"{input_path.stem}_jpeg.jpg"
    with Image.open(input_path) as img:
        rgb_img = img.convert("RGB")  # JPEG does not support alpha
        rgb_img.save(output_path, "JPEG", quality=quality, optimize=True)
    return output_path
