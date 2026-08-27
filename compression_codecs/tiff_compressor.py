# compression/tiff_compressor.py
"""TIFF compression utilities.

Provides a simple function to save an image as TIFF with optional compression.
"""

from pathlib import Path

from PIL import Image


def compress_tiff(input_path: Path, output_dir: Path, compression: str = "tiff_lzw") -> Path:
    """Compress an image to TIFF.

    Args:
        input_path: Path to the original image.
        output_dir: Directory for the compressed file.
        compression: TIFF compression scheme (e.g., "tiff_lzw", "tiff_adobe_deflate").

    Returns:
        Path to the compressed TIFF file.
    """
    output_path = output_dir / f"{input_path.stem}_tiff.tiff"
    with Image.open(input_path) as img:
        img.save(output_path, "TIFF", compression=compression)
    return output_path
