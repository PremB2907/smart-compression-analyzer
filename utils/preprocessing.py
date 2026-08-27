# utils/preprocessing.py
"""Image preprocessing pipeline as described in the research paper (Section III-B).

Steps:
1. Greyscale normalisation: pixel intensities mapped to [0, 255]
2. Denoising: Gaussian smoothing (σ = 0.5)
3. Deskewing: rotation correction via Leptonica/PyTesseract
"""

from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


def preprocess_image(image_path: str | Path) -> np.ndarray:
    """Apply the paper's preprocessing pipeline to an image.

    Steps:
        1. Convert to greyscale (mode 'L'), normalise to [0, 255] uint8.
        2. Apply Gaussian denoising with σ = 0.5.
        3. Deskew using pytesseract OSD to detect and correct rotation.

    Args:
        image_path: Path to the input image file.

    Returns:
        Preprocessed greyscale image as a 2-D numpy array with dtype=uint8.
    """
    image_path = Path(image_path)

    # Step 1 — Greyscale normalisation
    if image_path.suffix.lower() == ".pdf":
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(str(image_path))
            if not images:
                raise ValueError("No pages found in PDF")
            grey_img = images[0].convert("L")
        except Exception as e:
            raise ValueError(f"Failed to load PDF in preprocessing: {e}") from e
    else:
        with Image.open(image_path) as img:
            grey_img = img.convert("L")
    arr = np.array(grey_img, dtype=np.float32)
    # Normalise to [0, 255] (handles images that may have been in a different range)
    arr_min, arr_max = arr.min(), arr.max()
    if arr_max > arr_min:
        arr = (arr - arr_min) / (arr_max - arr_min) * 255.0
    arr = arr.astype(np.uint8)

    # Step 2 — Gaussian denoising (σ = 0.5)
    arr = gaussian_filter(arr.astype(np.float32), sigma=0.5)
    arr = np.clip(arr, 0, 255).astype(np.uint8)

    # Step 3 — Deskew via pytesseract OSD
    try:
        import pytesseract

        pil_img = Image.fromarray(arr)
        osd = pytesseract.image_to_osd(pil_img, output_type=pytesseract.Output.DICT)
        angle = osd.get("rotate", 0)
        if angle != 0:
            pil_img = pil_img.rotate(-angle, expand=True, fillcolor=255)
            arr = np.array(pil_img, dtype=np.uint8)
    except Exception:
        # If OSD fails (e.g., not enough text for detection), skip deskewing
        pass

    return arr
