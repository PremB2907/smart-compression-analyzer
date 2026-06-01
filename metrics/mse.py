# metrics/mse.py
"""Utility to compute Mean Squared Error (MSE) between two images.

Uses NumPy to calculate the average squared difference per channel.
"""

from pathlib import Path

import numpy as np
from skimage import io


def compute_mse(original_path: Path, compressed_path: Path) -> float:
    """Calculate MSE between two images.

    Args:
        original_path: Path to the original image.
        compressed_path: Path to the compressed image.

    Returns:
        MSE value (float). Returns 0 if computation fails.
    """
    try:
        orig = io.imread(str(original_path)).astype(np.float32)
        comp = io.imread(str(compressed_path)).astype(np.float32)
        if orig.shape != comp.shape:
            from skimage.transform import resize

            comp = resize(comp, orig.shape, anti_aliasing=True, preserve_range=True)
        diff = orig - comp
        mse = np.mean(np.square(diff))
        return float(mse)
    except Exception:
        return 0.0
