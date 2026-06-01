# metrics/compression_ratio.py
"""Utility to compute compression ratio between original and compressed files."""

from pathlib import Path


def compression_ratio(original_path: Path, compressed_path: Path) -> float:
    """Calculate compression ratio.

    Args:
        original_path: Path to the original file.
        compressed_path: Path to the compressed file.

    Returns:
        Ratio (original size / compressed size). Returns 0 if compressed size is 0.
    """
    original_size = original_path.stat().st_size
    compressed_size = compressed_path.stat().st_size
    if compressed_size == 0:
        return 0.0
    return original_size / compressed_size
