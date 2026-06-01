# metrics/psnr.py
"""Utility to compute Peak Signal-to-Noise Ratio (PSNR) between two images.

Uses skimage.metrics.peak_signal_noise_ratio.
"""

from pathlib import Path

from skimage import io
from skimage.metrics import peak_signal_noise_ratio


def compute_psnr(original_path: Path, compressed_path: Path) -> float:
    """Calculate PSNR (in dB) between two images.

    Args:
        original_path: Path to the original image file.
        compressed_path: Path to the compressed image file.

    Returns:
        PSNR value in decibels. Returns 0 if computation fails.
    """
    try:
        orig = io.imread(str(original_path))
        comp = io.imread(str(compressed_path))
        # Ensure same shape; if not, resize compressed to original shape
        if orig.shape != comp.shape:
            # Simple resize using numpy (could use cv2, but keep minimal)
            from skimage.transform import resize

            comp = resize(comp, orig.shape, anti_aliasing=True)
        return peak_signal_noise_ratio(orig, comp, data_range=255)
    except Exception:
        return 0.0
