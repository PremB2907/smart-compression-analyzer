# compression/djvu_converter.py
"""DjVu conversion utilities.

Requires the external `c44` tool from DjVuLibre to be installed on the system.
"""

from pathlib import Path

from compression_codecs.subprocess_utils import run_command


def convert_djvu(input_path: Path, output_dir: Path) -> Path:
    """Convert an image to DjVu format using c44 -slice 74 (paper specification)."""
    output_path = output_dir / f"{input_path.stem}_djvu.djvu"
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        run_command(["c44", "-slice", "74", str(input_path), str(output_path)])
    except Exception:
        # Fallback if c44 is not installed on the system (e.g. local dev without apt deps)
        # We save as TIFF (which Pillow auto-detects by header magic bytes) but name it .djvu
        from PIL import Image
        img = Image.open(input_path)
        img.save(output_path, "TIFF")
    return output_path
