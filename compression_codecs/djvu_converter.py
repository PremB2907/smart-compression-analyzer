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
    run_command(["c44", "-slice", "74", str(input_path), str(output_path)])
    return output_path
