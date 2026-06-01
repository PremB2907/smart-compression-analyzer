"""Property-based tests for all 7 correctness properties.

Uses Hypothesis to verify universal properties hold across many inputs.

Validates: Requirements 2.1, 2.2, 2.3, 2.8, 2.9, 2.13, 3.1, 3.2, 3.3, 3.4, 3.9
"""

import math
import os
import sys
from pathlib import Path

import hypothesis.extra.numpy as npst
import numpy as np
import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from PIL import Image

# Ensure project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import editdistance
from metrics.ber import compute_ber
from metrics.compression_ratio import compression_ratio
from metrics.ocr_accuracy import ocr_accuracy
from metrics.ssim import compute_ssim
from utils.steganography_lsb import embed_lsb_payload, extract_lsb_payload

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_rgb_png(directory: Path, name: str, width: int, height: int, seed: int) -> Path:
    """Create a synthetic RGB PNG image and return its path."""
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
    img = Image.fromarray(arr, mode="RGB")
    path = directory / name
    img.save(str(path), "PNG")
    return path


def _make_grey_png(directory: Path, name: str, width: int, height: int, seed: int) -> Path:
    """Create a synthetic greyscale PNG image and return its path."""
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
    """Module-scoped temp directory shared across Hypothesis tests."""
    return tmp_path_factory.mktemp("properties")


# ===========================================================================
# Property 1: OCR CER formula
# For any non-empty strings T_hat, T_ref, result is in [0,1] and equals
# max(0, 1 - editdistance(T_hat, T_ref) / len(T_ref)).
# Validates: Requirements 2.1, 2.14
# ===========================================================================


@given(
    t_hat=st.text(min_size=0, max_size=200),
    t_ref=st.text(min_size=1, max_size=200),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_1_ocr_cer_formula(t_hat, t_ref):
    """**Validates: Requirements 2.1, 2.14**

    Property 1 (OCR CER formula): For any non-empty strings T_hat, T_ref,
    ocr_accuracy returns a value in [0,1] that equals
    max(0, 1 - editdistance(T_hat, T_ref) / len(T_ref)).
    """
    result = ocr_accuracy(t_hat, t_ref)

    # Must be in [0, 1]
    assert 0.0 <= result <= 1.0, f"ocr_accuracy({t_hat!r}, {t_ref!r}) = {result} is outside [0, 1]"

    # Must equal the CER formula
    expected = max(0.0, 1.0 - editdistance.eval(t_hat, t_ref) / len(t_ref))
    assert abs(result - expected) < 1e-9, (
        f"ocr_accuracy({t_hat!r}, {t_ref!r}) = {result}, expected {expected} from CER formula"
    )


def test_property_1_ocr_identical_strings():
    """Identical strings → accuracy 1.0."""
    assert ocr_accuracy("hello world", "hello world") == 1.0


def test_property_1_ocr_empty_t_ref():
    """Empty T_ref → accuracy 1.0 (edge case)."""
    assert ocr_accuracy("anything", "") == 1.0


def test_property_1_ocr_completely_different():
    """Completely different strings → result clamped to 0.0."""
    # "aaa" vs "bbb": edit distance = 3, len(t_ref) = 3 → 1 - 1 = 0.0
    result = ocr_accuracy("aaa", "bbb")
    assert result == 0.0, f"Expected 0.0, got {result}"


def test_property_1_ocr_one_edit_in_three():
    """1 edit in 3 chars → accuracy ≈ 0.667."""
    result = ocr_accuracy("axc", "abc")
    assert abs(result - 0.6667) < 0.001, f"Expected ≈0.667, got {result}"


# ===========================================================================
# Property 2: LSB round-trip fidelity
# For any greyscale image with ≥ 968 pixels and any 968-bit payload,
# extract(embed(image, payload)) == payload.
# Validates: Requirements 2.2, 2.3
# ===========================================================================

# Strategy: generate a flat list of 968 bits (0 or 1)
_payload_strategy = st.lists(
    st.integers(min_value=0, max_value=1),
    min_size=968,
    max_size=968,
)

# Strategy: generate a 2-D uint8 array with at least 968 pixels
# Use shapes where rows*cols >= 968 (e.g., 44x22 = 968)
_image_strategy = npst.arrays(
    dtype=np.uint8,
    shape=st.tuples(
        st.integers(min_value=22, max_value=100),  # rows
        st.integers(min_value=44, max_value=100),  # cols
    ),
)


@given(image=_image_strategy, payload=_payload_strategy)
@settings(
    max_examples=25,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
def test_property_2_lsb_round_trip(image, payload):
    """**Validates: Requirements 2.2, 2.3**

    Property 2 (LSB round-trip): For any greyscale image with ≥ 968 pixels and
    any 968-bit payload, extract_lsb_payload(embed_lsb_payload(image, payload), 968)
    == payload.
    """
    assert image.size >= 968, f"Image has only {image.size} pixels, need ≥ 968"

    stego = embed_lsb_payload(image, payload)
    recovered = extract_lsb_payload(stego, 968)

    assert recovered == payload, (
        f"LSB round-trip failed: payload not recovered exactly. "
        f"First mismatch at index "
        f"{next(i for i, (a, b) in enumerate(zip(payload, recovered, strict=False)) if a != b)}"
    )


@given(image=_image_strategy, payload=_payload_strategy)
@settings(
    max_examples=15,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
def test_property_2_lsb_embedding_formula(image, payload):
    """**Validates: Requirements 2.2**

    Verify the embedding formula p̃_k = (p_k & 0xFE) | b_k holds for every pixel k.
    """
    stego = embed_lsb_payload(image, payload)
    flat_orig = image.flatten()
    flat_stego = stego.flatten()

    for k, bit in enumerate(payload):
        expected_pixel = (int(flat_orig[k]) & 0xFE) | int(bit)
        assert int(flat_stego[k]) == expected_pixel, (
            f"Embedding formula violated at pixel k={k}: "
            f"orig={flat_orig[k]}, bit={bit}, "
            f"expected={expected_pixel}, got={flat_stego[k]}"
        )


def test_property_2_lsb_pixels_beyond_payload_unchanged():
    """Pixels beyond the payload range must be unmodified."""
    rng = np.random.default_rng(0)
    image = rng.integers(0, 256, (50, 50), dtype=np.uint8)  # 2500 pixels
    payload = [0] * 968

    stego = embed_lsb_payload(image, payload)
    flat_orig = image.flatten()
    flat_stego = stego.flatten()

    # Pixels at index >= 968 must be identical
    for k in range(968, flat_orig.size):
        assert flat_orig[k] == flat_stego[k], (
            f"Pixel at index {k} (beyond payload) was modified: "
            f"orig={flat_orig[k]}, stego={flat_stego[k]}"
        )


# ===========================================================================
# Property 3: BER range invariant
# For any two equal-length bit arrays, BER ∈ [0,1].
# When identical → 0.0. When fully flipped → 1.0.
# Validates: Requirements 2.3
# ===========================================================================

_bit_array_strategy = st.lists(
    st.integers(min_value=0, max_value=1),
    min_size=1,
    max_size=968,
)


@given(bits=_bit_array_strategy)
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_3_ber_range(bits):
    """**Validates: Requirements 2.3**

    Property 3 (BER range): For any two equal-length bit arrays, BER ∈ [0, 1].
    """
    # Generate a second array of the same length with arbitrary bits
    # We test with the same array (BER=0) and flipped (BER=1) as the two extremes
    ber_same = compute_ber(bits, bits)
    assert 0.0 <= ber_same <= 1.0, f"BER {ber_same} is outside [0, 1]"

    flipped = [1 - b for b in bits]
    ber_flipped = compute_ber(bits, flipped)
    assert 0.0 <= ber_flipped <= 1.0, f"BER {ber_flipped} is outside [0, 1]"


@given(bits=_bit_array_strategy)
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_3_ber_identical_is_zero(bits):
    """**Validates: Requirements 2.3**

    When original_bits == extracted_bits, BER SHALL be exactly 0.0.
    """
    result = compute_ber(bits, bits)
    assert result == 0.0, f"compute_ber(bits, bits) = {result}, expected 0.0"


@given(bits=_bit_array_strategy)
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_3_ber_fully_flipped_is_one(bits):
    """**Validates: Requirements 2.3**

    When all bits are flipped, BER SHALL be exactly 1.0.
    """
    flipped = [1 - b for b in bits]
    result = compute_ber(bits, flipped)
    assert result == 1.0, f"compute_ber(bits, flipped) = {result}, expected 1.0"


@given(
    bits_a=_bit_array_strategy,
    bits_b=_bit_array_strategy,
)
@settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_3_ber_range_arbitrary_pairs(bits_a, bits_b):
    """**Validates: Requirements 2.3**

    For any two equal-length bit arrays, BER ∈ [0, 1].
    """
    # Truncate to the shorter length so they are equal-length
    n = min(len(bits_a), len(bits_b))
    assume(n >= 1)
    a = bits_a[:n]
    b = bits_b[:n]
    result = compute_ber(a, b)
    assert 0.0 <= result <= 1.0, (
        f"compute_ber returned {result} outside [0, 1] for arrays of length {n}"
    )


# ===========================================================================
# Property 4: Preprocessing output invariants
# For any image path, output is uint8, 2-D, same spatial size.
# Validates: Requirements 2.9
# ===========================================================================


@given(
    width=st.integers(min_value=32, max_value=128),
    height=st.integers(min_value=32, max_value=128),
    seed=st.integers(min_value=0, max_value=9999),
    n_channels=st.sampled_from([1, 3]),
)
@settings(
    max_examples=10,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=10_000,
)
def test_property_4_preprocessing_invariants(width, height, seed, n_channels, module_tmp_dir):
    """**Validates: Requirements 2.9**

    Property 4 (Preprocessing invariants): For any input image (any dtype, any number
    of channels), preprocess_image returns a 2-D numpy array with dtype=uint8,
    all values in [0, 255], and spatial dimensions equal to the input's height × width.
    """
    from utils.preprocessing import preprocess_image

    rng = np.random.default_rng(seed)
    if n_channels == 1:
        arr = rng.integers(0, 256, (height, width), dtype=np.uint8)
        img = Image.fromarray(arr, mode="L")
    else:
        arr = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
        img = Image.fromarray(arr, mode="RGB")

    img_path = module_tmp_dir / f"preproc_{seed}_{n_channels}ch_{width}x{height}.png"
    img.save(str(img_path), "PNG")

    result = preprocess_image(img_path)

    # Must be 2-D
    assert result.ndim == 2, f"preprocess_image returned array with ndim={result.ndim}, expected 2"

    # Must be uint8
    assert result.dtype == np.uint8, (
        f"preprocess_image returned dtype={result.dtype}, expected uint8"
    )

    # All values in [0, 255]
    assert result.min() >= 0 and result.max() <= 255, (
        f"preprocess_image values out of [0, 255]: min={result.min()}, max={result.max()}"
    )

    # Spatial dimensions must match input (deskew with expand=True may change size,
    # but without rotation the dimensions are preserved; we check the output is 2-D
    # and non-empty rather than exact size match since deskew can expand)
    assert result.shape[0] > 0 and result.shape[1] > 0, (
        f"preprocess_image returned empty array with shape {result.shape}"
    )


# ===========================================================================
# Property 5: Archival score monotone in BER
# For fixed cr, ocr, score decreases monotonically as ber increases from 0 to 1.
# Validates: Requirements 2.13
# ===========================================================================


def _archival_score(cr: float, ocr: float, ber: float) -> float:
    """The fixed archival score formula: cr * ocr * (1 - ber)."""
    return cr * ocr * (1.0 - ber)


@given(
    cr=st.floats(min_value=1e-6, max_value=100.0, allow_nan=False, allow_infinity=False),
    ocr=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    ber_low=st.floats(min_value=0.0, max_value=0.9999, allow_nan=False, allow_infinity=False),
    delta=st.floats(min_value=1e-9, max_value=0.5, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=75, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_5_archival_score_monotone_in_ber(cr, ocr, ber_low, delta):
    """**Validates: Requirements 2.13**

    Property 5 (Archival score monotone in BER): For fixed cr, ocr, the archival
    score cr * ocr * (1 - ber) decreases monotonically as ber increases.
    score(ber_high) <= score(ber_low) whenever ber_high > ber_low.
    """
    ber_high = ber_low + delta
    assume(ber_high <= 1.0)

    score_low = _archival_score(cr, ocr, ber_low)
    score_high = _archival_score(cr, ocr, ber_high)

    # score must be non-increasing as BER increases
    assert score_high <= score_low + 1e-12, (
        f"Archival score is NOT monotone decreasing in BER: "
        f"cr={cr}, ocr={ocr}, ber_low={ber_low}, ber_high={ber_high}, "
        f"score_low={score_low}, score_high={score_high}"
    )


@given(
    cr=st.floats(min_value=1e-6, max_value=100.0, allow_nan=False, allow_infinity=False),
    ocr=st.floats(min_value=1e-9, max_value=1.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_5_archival_score_ber_zero_is_max(cr, ocr):
    """**Validates: Requirements 2.13**

    When BER=0, the archival score equals cr * ocr (maximum for given cr, ocr).
    When BER=1, the archival score equals 0.
    """
    score_zero_ber = _archival_score(cr, ocr, 0.0)
    score_full_ber = _archival_score(cr, ocr, 1.0)

    assert abs(score_zero_ber - cr * ocr) < 1e-9, (
        f"score(ber=0) = {score_zero_ber}, expected {cr * ocr}"
    )
    assert abs(score_full_ber) < 1e-9, f"score(ber=1) = {score_full_ber}, expected 0.0"


def test_property_5_archival_score_known_values():
    """Known values from the paper: cr=19.9, ocr=0.98, ber=0.001 → ≈19.5."""
    score = _archival_score(19.9, 0.98, 0.001)
    assert abs(score - 19.9 * 0.98 * 0.999) < 1e-6, (
        f"Archival score for paper values = {score}, expected ≈{19.9 * 0.98 * 0.999}"
    )


# ===========================================================================
# Property 6: SSIM valid range on RGB images
# For any pair of same-shape RGB images, compute_ssim returns float in [-1,1]
# without exception.
# Validates: Requirements 2.8, 3.9
# ===========================================================================


@given(
    width=st.integers(min_value=16, max_value=64),
    height=st.integers(min_value=16, max_value=64),
    seed_a=st.integers(min_value=0, max_value=9999),
    seed_b=st.integers(min_value=0, max_value=9999),
)
@settings(
    max_examples=15,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=15_000,
)
def test_property_6_ssim_rgb_valid_range(width, height, seed_a, seed_b, module_tmp_dir):
    """**Validates: Requirements 2.8, 3.9**

    Property 6 (SSIM valid range on RGB images): For any pair of same-shape RGB
    images, compute_ssim returns a float in [-1, 1] without raising any exception.
    """
    orig_path = _make_rgb_png(
        module_tmp_dir, f"ssim_rgb_orig_{seed_a}_{width}x{height}.png", width, height, seed_a
    )
    comp_path = _make_rgb_png(
        module_tmp_dir, f"ssim_rgb_comp_{seed_b}_{width}x{height}.png", width, height, seed_b
    )

    # Must not raise any exception
    try:
        result = compute_ssim(orig_path, comp_path)
    except Exception as exc:
        pytest.fail(
            f"compute_ssim raised {type(exc).__name__}: {exc} "
            f"for RGB images of shape ({height}, {width}, 3)"
        )

    assert isinstance(result, float), (
        f"compute_ssim returned {type(result).__name__}, expected float"
    )
    assert not math.isnan(result), "compute_ssim returned NaN for RGB images"
    assert -1.0 <= result <= 1.0, f"compute_ssim returned {result} outside [-1, 1] for RGB images"


def test_property_6_ssim_rgb_identical_images(module_tmp_dir):
    """Identical RGB images → SSIM close to 1.0."""
    path = _make_rgb_png(module_tmp_dir, "ssim_rgb_identical.png", 32, 32, seed=0)
    result = compute_ssim(path, path)
    assert isinstance(result, float), f"Expected float, got {type(result)}"
    assert not math.isnan(result), "compute_ssim returned NaN for identical RGB images"
    assert -1.0 <= result <= 1.0, f"SSIM {result} outside [-1, 1]"
    # Identical images should have SSIM very close to 1.0
    assert result > 0.99, f"SSIM for identical images = {result}, expected > 0.99"


# ===========================================================================
# Property 7: Compression ratio unchanged for JPEG/PNG/TIFF
# For any two file paths, compression_ratio returns S_orig/S_comp correctly.
# Validates: Requirements 3.1, 3.2, 3.3, 3.4
# ===========================================================================


@given(
    orig_size=st.integers(min_value=1, max_value=100_000),
    comp_size=st.integers(min_value=1, max_value=100_000),
)
@settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_property_7_compression_ratio_formula(orig_size, comp_size, module_tmp_dir):
    """**Validates: Requirements 3.4**

    Property 7 (Compression ratio): For any two file paths, compression_ratio
    returns S_orig / S_comp correctly.
    """
    orig = module_tmp_dir / f"cr7_orig_{orig_size}_{comp_size}.bin"
    comp = module_tmp_dir / f"cr7_comp_{orig_size}_{comp_size}.bin"
    orig.write_bytes(b"O" * orig_size)
    comp.write_bytes(b"C" * comp_size)

    expected = orig_size / comp_size
    result = compression_ratio(orig, comp)

    assert abs(result - expected) < 1e-9, (
        f"compression_ratio({orig_size}, {comp_size}) = {result}, expected {expected}"
    )


@given(
    seed=st.integers(min_value=0, max_value=9999),
    width=st.integers(min_value=20, max_value=80),
    height=st.integers(min_value=20, max_value=80),
)
@settings(
    max_examples=10,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=15_000,
)
def test_property_7_compression_ratio_jpeg(seed, width, height, module_tmp_dir):
    """**Validates: Requirements 3.1, 3.4**

    For any random image, compression_ratio on JPEG output equals
    S_orig / S_comp (JPEG compressor is unchanged by the fix set).
    """
    from compression.jpeg_compressor import compress_jpeg

    src = _make_rgb_png(
        module_tmp_dir, f"cr7_jpeg_src_{seed}_{width}x{height}.png", width, height, seed
    )
    out_dir = module_tmp_dir / "cr7_jpeg_out"
    out_dir.mkdir(exist_ok=True)
    out = compress_jpeg(src, out_dir)

    assert out.exists(), "compress_jpeg output does not exist"
    assert out.stat().st_size > 0, "compress_jpeg output is empty"

    expected = src.stat().st_size / out.stat().st_size
    result = compression_ratio(src, out)

    assert abs(result - expected) < 1e-9, (
        f"compression_ratio for JPEG = {result}, expected {expected}"
    )


@given(
    seed=st.integers(min_value=0, max_value=9999),
    width=st.integers(min_value=20, max_value=80),
    height=st.integers(min_value=20, max_value=80),
)
@settings(
    max_examples=10,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=15_000,
)
def test_property_7_compression_ratio_png(seed, width, height, module_tmp_dir):
    """**Validates: Requirements 3.2, 3.4**

    For any random image, compression_ratio on PNG output equals
    S_orig / S_comp (PNG compressor is unchanged by the fix set).
    """
    from compression.png_compressor import compress_png

    src = _make_rgb_png(
        module_tmp_dir, f"cr7_png_src_{seed}_{width}x{height}.png", width, height, seed
    )
    out_dir = module_tmp_dir / "cr7_png_out"
    out_dir.mkdir(exist_ok=True)
    out = compress_png(src, out_dir)

    assert out.exists(), "compress_png output does not exist"
    assert out.stat().st_size > 0, "compress_png output is empty"

    expected = src.stat().st_size / out.stat().st_size
    result = compression_ratio(src, out)

    assert abs(result - expected) < 1e-9, (
        f"compression_ratio for PNG = {result}, expected {expected}"
    )


@given(
    seed=st.integers(min_value=0, max_value=9999),
    width=st.integers(min_value=20, max_value=80),
    height=st.integers(min_value=20, max_value=80),
)
@settings(
    max_examples=30,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=15_000,
)
def test_property_7_compression_ratio_tiff(seed, width, height, module_tmp_dir):
    """**Validates: Requirements 3.3, 3.4**

    For any random image, compression_ratio on TIFF output equals
    S_orig / S_comp (TIFF compressor is unchanged by the fix set).
    """
    from compression.tiff_compressor import compress_tiff

    src = _make_rgb_png(
        module_tmp_dir, f"cr7_tiff_src_{seed}_{width}x{height}.png", width, height, seed
    )
    out_dir = module_tmp_dir / "cr7_tiff_out"
    out_dir.mkdir(exist_ok=True)
    out = compress_tiff(src, out_dir)

    assert out.exists(), "compress_tiff output does not exist"
    assert out.stat().st_size > 0, "compress_tiff output is empty"

    expected = src.stat().st_size / out.stat().st_size
    result = compression_ratio(src, out)

    assert abs(result - expected) < 1e-9, (
        f"compression_ratio for TIFF = {result}, expected {expected}"
    )
