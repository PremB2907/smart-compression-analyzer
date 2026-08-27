"""Preservation property tests.

These tests MUST PASS on unfixed code — they capture the baseline behaviour of
modules that are NOT being changed by the fix set (JPEG, PNG, TIFF compressors,
compression_ratio, PSNR, and the greyscale SSIM code path).

Running them before any fix confirms the baseline. Re-running them after each fix
confirms no regressions were introduced.

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.9
"""

import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest

# Hypothesis for property-based testing
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from PIL import Image

# Ensure project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from compression_codecs.jpeg_compressor import compress_jpeg
from compression_codecs.png_compressor import compress_png
from compression_codecs.tiff_compressor import compress_tiff
from metrics.compression_ratio import compression_ratio
from metrics.psnr import compute_psnr
from metrics.ssim import compute_ssim

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_png(
    directory: Path, name: str, width: int = 100, height: int = 100, seed: int = 42
) -> Path:
    """Create a small synthetic RGB PNG image and return its path."""
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
    img = Image.fromarray(arr, mode="RGB")
    path = directory / name
    img.save(str(path), "PNG")
    return path


def _make_grey_png(
    directory: Path, name: str, width: int = 100, height: int = 100, seed: int = 0
) -> Path:
    """Create a small synthetic greyscale PNG image and return its path."""
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, (height, width), dtype=np.uint8)
    img = Image.fromarray(arr, mode="L")
    path = directory / name
    img.save(str(path), "PNG")
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def module_tmp_dir(tmp_path_factory):
    """Module-scoped temp directory so Hypothesis tests can share it."""
    return tmp_path_factory.mktemp("preservation")


# ---------------------------------------------------------------------------
# Property: compress_jpeg output is non-zero and file exists
# Validates: Requirements 3.1
# ---------------------------------------------------------------------------


def test_compress_jpeg_basic(tmp_path):
    """compress_jpeg produces a non-zero output file for a simple image."""
    src = _make_png(tmp_path, "src.png")
    out = compress_jpeg(src, tmp_path)
    assert out.exists(), "compress_jpeg output file does not exist"
    assert out.stat().st_size > 0, "compress_jpeg output file is empty"


@given(seed=st.integers(min_value=0, max_value=9999))
@settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_compress_jpeg_output_nonempty_property(seed, module_tmp_dir):
    """**Validates: Requirements 3.1**

    For any random image, compress_jpeg output file size is non-zero and file exists.
    """
    out_dir = module_tmp_dir / "jpeg_out"
    out_dir.mkdir(exist_ok=True)
    src = _make_png(module_tmp_dir, f"jpeg_src_{seed}.png", seed=seed)
    out = compress_jpeg(src, out_dir)
    assert out.exists(), f"compress_jpeg output does not exist for seed={seed}"
    assert out.stat().st_size > 0, f"compress_jpeg output is empty for seed={seed}"


# ---------------------------------------------------------------------------
# Property: compress_png output is non-zero and file exists
# Validates: Requirements 3.2
# ---------------------------------------------------------------------------


def test_compress_png_basic(tmp_path):
    """compress_png produces a non-zero output file for a simple image."""
    src = _make_png(tmp_path, "src.png")
    out = compress_png(src, tmp_path)
    assert out.exists(), "compress_png output file does not exist"
    assert out.stat().st_size > 0, "compress_png output file is empty"


@given(seed=st.integers(min_value=0, max_value=9999))
@settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_compress_png_output_nonempty_property(seed, module_tmp_dir):
    """**Validates: Requirements 3.2**

    For any random image, compress_png output file size is non-zero and file exists.
    """
    out_dir = module_tmp_dir / "png_out"
    out_dir.mkdir(exist_ok=True)
    src = _make_png(module_tmp_dir, f"png_src_{seed}.png", seed=seed)
    out = compress_png(src, out_dir)
    assert out.exists(), f"compress_png output does not exist for seed={seed}"
    assert out.stat().st_size > 0, f"compress_png output is empty for seed={seed}"


# ---------------------------------------------------------------------------
# Property: compress_tiff output is non-zero and file exists
# Validates: Requirements 3.3
# ---------------------------------------------------------------------------


def test_compress_tiff_basic(tmp_path):
    """compress_tiff produces a non-zero output file for a simple image."""
    src = _make_png(tmp_path, "src.png")
    out = compress_tiff(src, tmp_path)
    assert out.exists(), "compress_tiff output file does not exist"
    assert out.stat().st_size > 0, "compress_tiff output file is empty"


@given(seed=st.integers(min_value=0, max_value=9999))
@settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_compress_tiff_output_nonempty_property(seed, module_tmp_dir):
    """**Validates: Requirements 3.3**

    For any random image, compress_tiff output file size is non-zero and file exists.
    """
    out_dir = module_tmp_dir / "tiff_out"
    out_dir.mkdir(exist_ok=True)
    src = _make_png(module_tmp_dir, f"tiff_src_{seed}.png", seed=seed)
    out = compress_tiff(src, out_dir)
    assert out.exists(), f"compress_tiff output does not exist for seed={seed}"
    assert out.stat().st_size > 0, f"compress_tiff output is empty for seed={seed}"


# ---------------------------------------------------------------------------
# Property: compression_ratio returns S_orig / S_comp correctly
# Validates: Requirements 3.4
# ---------------------------------------------------------------------------


def test_compression_ratio_basic(tmp_path):
    """compression_ratio returns orig_size / comp_size for known file sizes."""
    orig = tmp_path / "orig.bin"
    comp = tmp_path / "comp.bin"
    orig.write_bytes(b"A" * 1000)
    comp.write_bytes(b"B" * 200)
    ratio = compression_ratio(orig, comp)
    assert abs(ratio - 5.0) < 1e-9, f"Expected 5.0, got {ratio}"


def test_compression_ratio_zero_compressed(tmp_path):
    """compression_ratio returns 0.0 when compressed file is empty."""
    orig = tmp_path / "orig.bin"
    comp = tmp_path / "comp_empty.bin"
    orig.write_bytes(b"A" * 100)
    comp.write_bytes(b"")
    ratio = compression_ratio(orig, comp)
    assert ratio == 0.0, f"Expected 0.0 for empty compressed file, got {ratio}"


@given(
    orig_size=st.integers(min_value=1, max_value=10_000),
    comp_size=st.integers(min_value=1, max_value=10_000),
)
@settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_compression_ratio_formula_property(orig_size, comp_size, module_tmp_dir):
    """**Validates: Requirements 3.4**

    For any two file paths, compression_ratio returns S_orig / S_comp correctly.
    """
    orig = module_tmp_dir / f"cr_orig_{orig_size}_{comp_size}.bin"
    comp = module_tmp_dir / f"cr_comp_{orig_size}_{comp_size}.bin"
    orig.write_bytes(b"X" * orig_size)
    comp.write_bytes(b"Y" * comp_size)
    expected = orig_size / comp_size
    result = compression_ratio(orig, comp)
    assert abs(result - expected) < 1e-9, (
        f"compression_ratio({orig_size}, {comp_size}) = {result}, expected {expected}"
    )


# ---------------------------------------------------------------------------
# Property: compute_psnr returns a float (not None, not NaN)
# Validates: Requirements 3.5
# ---------------------------------------------------------------------------


def test_compute_psnr_identical_images(tmp_path):
    """compute_psnr on identical images returns a large positive float (not NaN)."""
    src = _make_png(tmp_path, "src.png")
    result = compute_psnr(src, src)
    assert result is not None, "compute_psnr returned None"
    assert isinstance(result, float), f"compute_psnr returned {type(result)}, expected float"
    assert not math.isnan(result), "compute_psnr returned NaN for identical images"


def test_compute_psnr_different_images(tmp_path):
    """compute_psnr on different images returns a finite float."""
    src = _make_png(tmp_path, "src.png", seed=1)
    comp_jpeg = compress_jpeg(src, tmp_path)
    result = compute_psnr(src, comp_jpeg)
    assert result is not None, "compute_psnr returned None"
    assert isinstance(result, float), f"compute_psnr returned {type(result)}, expected float"
    assert not math.isnan(result), "compute_psnr returned NaN"


@given(
    seed_a=st.integers(min_value=0, max_value=999),
    seed_b=st.integers(min_value=0, max_value=999),
)
@settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_compute_psnr_returns_float_property(seed_a, seed_b, module_tmp_dir):
    """**Validates: Requirements 3.5**

    For any two image paths, compute_psnr returns a float (not None, not NaN).
    """
    orig = _make_png(module_tmp_dir, f"psnr_orig_{seed_a}.png", seed=seed_a)
    comp = _make_png(module_tmp_dir, f"psnr_comp_{seed_b}.png", seed=seed_b)
    result = compute_psnr(orig, comp)
    assert result is not None, "compute_psnr returned None"
    assert isinstance(result, float), (
        f"compute_psnr returned {type(result).__name__}, expected float"
    )
    assert not math.isnan(result), f"compute_psnr returned NaN for seeds ({seed_a}, {seed_b})"


# ---------------------------------------------------------------------------
# Property: compute_ssim on greyscale images returns a float in [-1, 1]
# Validates: Requirements 3.9
# ---------------------------------------------------------------------------


def test_compute_ssim_greyscale_basic(tmp_path):
    """compute_ssim on identical greyscale images returns a float in [-1, 1]."""
    src = _make_grey_png(tmp_path, "grey.png")
    result = compute_ssim(src, src)
    assert result is not None, "compute_ssim returned None"
    assert isinstance(result, float), f"compute_ssim returned {type(result)}, expected float"
    assert not math.isnan(result), "compute_ssim returned NaN"
    assert -1.0 <= result <= 1.0, f"compute_ssim result {result} is outside [-1, 1]"


def test_compute_ssim_greyscale_different(tmp_path):
    """compute_ssim on different greyscale images returns a float in [-1, 1]."""
    src = _make_grey_png(tmp_path, "grey_a.png", seed=10)
    other = _make_grey_png(tmp_path, "grey_b.png", seed=20)
    result = compute_ssim(src, other)
    assert result is not None, "compute_ssim returned None"
    assert isinstance(result, float), f"compute_ssim returned {type(result)}, expected float"
    assert not math.isnan(result), "compute_ssim returned NaN"
    assert -1.0 <= result <= 1.0, f"compute_ssim result {result} is outside [-1, 1]"


@given(
    seed_a=st.integers(min_value=0, max_value=999),
    seed_b=st.integers(min_value=0, max_value=999),
)
@settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_compute_ssim_greyscale_range_property(seed_a, seed_b, module_tmp_dir):
    """**Validates: Requirements 3.9**

    For any pair of greyscale images, compute_ssim returns a float in [-1, 1]
    (single-channel code path — unaffected by the multichannel fix).
    """
    orig = _make_grey_png(module_tmp_dir, f"ssim_orig_{seed_a}.png", seed=seed_a)
    comp = _make_grey_png(module_tmp_dir, f"ssim_comp_{seed_b}.png", seed=seed_b)
    result = compute_ssim(orig, comp)
    assert result is not None, "compute_ssim returned None"
    assert isinstance(result, float), (
        f"compute_ssim returned {type(result).__name__}, expected float"
    )
    assert not math.isnan(result), f"compute_ssim returned NaN for seeds ({seed_a}, {seed_b})"
    assert -1.0 <= result <= 1.0, (
        f"compute_ssim result {result} is outside [-1, 1] for seeds ({seed_a}, {seed_b})"
    )
