# metrics/ssim.py
"""Utility to compute Structural Similarity Index (SSIM) between two images.

Uses skimage.metrics.structural_similarity.
"""

from pathlib import Path

from skimage import img_as_float, io
from skimage.metrics import structural_similarity


def compute_ssim(original_path: Path, compressed_path: Path) -> float:
    """Calculate SSIM between two images.

    Args:
        original_path: Path to the original image.
        compressed_path: Path to the compressed image.

    Returns:
        SSIM value (0‑1). Returns 0 if computation fails.
    """
    try:
        orig = img_as_float(io.imread(str(original_path)))
        comp = img_as_float(io.imread(str(compressed_path)))
        # Ensure same shape
        if orig.shape != comp.shape:
            from skimage.transform import resize

            comp = resize(comp, orig.shape, anti_aliasing=True)
        # For colour images use channel_axis=-1 (scikit-image >= 0.19)
        if orig.ndim == 3:
            ssim_val = structural_similarity(orig, comp, channel_axis=-1, data_range=1.0)
        else:
            ssim_val = structural_similarity(orig, comp, data_range=1.0)
        return ssim_val
    except Exception:
        return 0.0
