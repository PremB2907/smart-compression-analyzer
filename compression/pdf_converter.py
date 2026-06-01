# compression/pdf_converter.py
"""PDF conversion utilities.

Converts an image to a PDF with a JPEG 2000 embedded stream at nominal 10:1 ratio,
as specified in the research paper (Section III-D).

Uses img2pdf for PDF wrapping and Pillow for JPEG 2000 encoding.
"""

import io
from pathlib import Path

from PIL import Image


def convert_pdf(input_path: Path, output_dir: Path) -> Path:
    """Convert an image to a PDF with a JPEG 2000 embedded stream.

    The JPEG 2000 compression is set to a nominal 10:1 ratio (quality_layers=[10])
    to match the paper's PDF benchmark settings.

    Args:
        input_path: Path to the original image file.
        output_dir: Directory for the produced PDF.

    Returns:
        Path to the generated PDF file.
    """
    import img2pdf

    output_path = output_dir / f"{input_path.stem}_pdf.pdf"
    output_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as img:
        # Convert to greyscale for consistent benchmarking
        grey_img = img.convert("L")
        # Encode to JPEG 2000 in memory at nominal 10:1 compression ratio
        buf = io.BytesIO()
        grey_img.save(buf, format="JPEG2000", quality_mode="rates", quality_layers=[10])
        jpeg2000_bytes = buf.getvalue()

    # Wrap the JPEG 2000 stream in a PDF container
    pdf_bytes = img2pdf.convert(jpeg2000_bytes)
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)

    return output_path
