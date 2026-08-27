# compression/png_compressor.py
"""PNG compression utilities.

Uses Pillow to save PNG with optimization.
"""

from pathlib import Path

from PIL import Image


def compress_png(input_path: Path, output_dir: Path, compress_level: int = 6) -> Path:
    """Compress an image to PNG.

    Args:
        input_path: Path to the original image.
        output_dir: Directory for the compressed file.
        compress_level: Pillow PNG compression level (0‑9). Higher is slower but smaller.
    Returns:
        Path to the compressed PNG file.
    """
    output_path = output_dir / f"{input_path.stem}_png.png"
    with Image.open(input_path) as img:
        img.save(output_path, "PNG", optimize=True, compress_level=compress_level)
    return output_path
