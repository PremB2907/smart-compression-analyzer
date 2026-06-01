# metrics/ocr_accuracy.py
"""Utility to compute OCR accuracy between original and compressed images.

Uses the Character Error Rate (CER) formula from the research paper:
  OCR_acc = 1 - CER(T_hat, T_ref) / |T_ref|

where CER is computed using the editdistance library.
"""

from pathlib import Path

import editdistance
import pytesseract
from PIL import Image

# Optional import for EasyOCR; if unavailable we fallback to pytesseract
try:
    import easyocr

    _easyocr_reader = easyocr.Reader(["en"], gpu=False)
    _easyocr_available = True
except Exception:
    _easyocr_available = False


def _extract_text(image_path: Path) -> str:
    """Extract text from an image using OCR.

    Tries EasyOCR first (if installed), otherwise falls back to pytesseract.

    Args:
        image_path: Path to the image file.

    Returns:
        Extracted text string.
    """
    if _easyocr_available:
        try:
            result = _easyocr_reader.readtext(str(image_path), detail=0)
            return " ".join(result)
        except Exception:
            pass
    # Fallback to pytesseract
    try:
        img = Image.open(image_path)
        return pytesseract.image_to_string(img)
    except Exception:
        return ""


# Alias used by batch_process.py
# that call _extract_text still work.
extract_text = _extract_text


def ocr_accuracy(t_hat: str, t_ref: str) -> float:
    """Compute OCR character accuracy using Character Error Rate (CER).

    Formula: OCR_acc = 1 - CER(T_hat, T_ref) / |T_ref|
    where CER = editdistance(T_hat, T_ref).

    Args:
        t_hat: OCR transcript extracted from the compressed image.
        t_ref: Reference OCR transcript from the original/lossless image.

    Returns:
        OCR accuracy in [0, 1]. 1.0 = perfect match.
    """
    if len(t_ref) == 0:
        return 1.0
    cer = editdistance.eval(t_hat, t_ref) / len(t_ref)
    return max(0.0, 1.0 - cer)
