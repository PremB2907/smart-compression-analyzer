"""Bug condition exploration tests.

These tests MUST FAIL on unfixed code — failure confirms the bugs exist.
DO NOT attempt to fix the tests or the code when they fail.

Each test encodes the EXPECTED (correct) behavior. They will pass after fixes are applied.

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.8, 1.10, 1.13
"""

import os
import sys

# Ensure project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Bug 1.1 — OCR accuracy uses SequenceMatcher instead of CER formula
# ---------------------------------------------------------------------------
def test_bug_1_1_ocr_accuracy_cer():
    """Bug 1.1: ocr_accuracy should use CER (editdistance), not SequenceMatcher.

    For t_hat="axc", t_ref="abc" the edit distance is 1 over 3 chars → accuracy ≈ 0.667.
    SequenceMatcher returns an inflated value (≈ 0.667 at word level but the current
    implementation operates on word lists, so for single-word inputs it returns 1.0 or 0.0
    depending on exact match — not the character-level CER).

    We test the function signature directly with string arguments (the fixed signature).
    On unfixed code the function takes image paths, so calling it with strings will either
    raise a TypeError/AttributeError or return a wrong value.
    """
    from metrics.ocr_accuracy import ocr_accuracy

    # After the fix, signature is ocr_accuracy(t_hat: str, t_ref: str) -> float
    # On unfixed code this call will fail (wrong signature / wrong computation)
    result = ocr_accuracy("axc", "abc")
    # Expected: 1 - editdistance("axc","abc") / len("abc") = 1 - 1/3 ≈ 0.6667
    assert abs(result - 0.6667) < 0.001, (
        f"Bug 1.1: Expected OCR accuracy ≈ 0.667 for 1-edit-in-3-char pair, got {result}. "
        "SequenceMatcher returns an inflated value — fix not applied."
    )


# ---------------------------------------------------------------------------
# Bug 1.2 — Missing LSB embedding module
# ---------------------------------------------------------------------------
def test_bug_1_2_missing_lsb_embedding():
    """Bug 1.2: utils/steganography_lsb.py does not exist yet.

    Importing it should raise ImportError on unfixed code.
    """
    try:
        import utils.steganography_lsb  # noqa: F401

        # If import succeeds the module exists — bug is fixed (test should pass after fix)
        # On unfixed code this line is never reached
        lsb_present = True
    except (ImportError, ModuleNotFoundError):
        lsb_present = False

    assert lsb_present, (
        "Bug 1.2: utils/steganography_lsb.py does not exist. "
        "LSB embedding step is missing from the pipeline."
    )


# ---------------------------------------------------------------------------
# Bug 1.3 — Missing BER module
# ---------------------------------------------------------------------------
def test_bug_1_3_missing_ber_module():
    """Bug 1.3: metrics/ber.py does not exist yet.

    Importing metrics.ber should raise ModuleNotFoundError on unfixed code.
    """
    try:
        import metrics.ber  # noqa: F401

        ber_present = True
    except (ImportError, ModuleNotFoundError):
        ber_present = False

    assert ber_present, (
        "Bug 1.3: metrics.ber module not found (ModuleNotFoundError). "
        "metrics/ber.py has not been created yet."
    )


# ---------------------------------------------------------------------------
# Bug 1.4 — MSE wired into production pipeline
# ---------------------------------------------------------------------------
def test_bug_1_4_mse_in_pipeline():
    """Bug 1.4: pipeline must import and call compute_mse."""
    pipeline_path = os.path.join(PROJECT_ROOT, "backend", "app", "services", "pipeline.py")
    with open(pipeline_path, encoding="utf-8") as f:
        source = f.read()

    assert "compute_mse" in source, (
        "Bug 1.4: 'compute_mse' not found in backend pipeline. "
        "MSE metric is not wired into the compression pipeline."
    )


# ---------------------------------------------------------------------------
# Bug 1.5 — WebP quality default is 80 instead of 75
# ---------------------------------------------------------------------------
def test_bug_1_5_webp_quality_default():
    """Bug 1.5: compress_webp default quality should be 75 (paper Section III-D).

    Inspect the source of webp_compressor.py and assert the default is 75.
    On unfixed code the default is 80 — this test will fail.
    """
    webp_path = os.path.join(PROJECT_ROOT, "compression", "webp_compressor.py")
    with open(webp_path, encoding="utf-8") as f:
        source = f.read()

    assert "quality: int = 75" in source, (
        "Bug 1.5: WebP quality default is not 75. "
        "Found 80 instead of the paper-specified 75 in webp_compressor.py."
    )


# ---------------------------------------------------------------------------
# Bug 1.7 — DjVu converter uses img2djvu instead of c44
# ---------------------------------------------------------------------------
def test_bug_1_7_djvu_uses_c44():
    """Bug 1.7: convert_djvu should invoke 'c44 -slice 74', not 'img2djvu'.

    Inspect the source of djvu_converter.py and assert the command contains 'c44'.
    On unfixed code the command is 'img2djvu' — this test will fail.
    """
    djvu_path = os.path.join(PROJECT_ROOT, "compression", "djvu_converter.py")
    with open(djvu_path, encoding="utf-8") as f:
        source = f.read()

    assert '"c44"' in source, (
        "Bug 1.7: DjVu converter does not use 'c44'. "
        "Found 'img2djvu' instead of the paper-specified 'c44' tool."
    )


# ---------------------------------------------------------------------------
# Bug 1.8 — SSIM uses deprecated multichannel=True parameter
# ---------------------------------------------------------------------------
def test_bug_1_8_ssim_no_multichannel_param():
    """Bug 1.8: compute_ssim should NOT use the deprecated 'multichannel' kwarg.

    On scikit-image >= 0.19 this raises a TypeError. Inspect the source and assert
    'multichannel' is NOT present.
    On unfixed code 'multichannel=True' is in the source — this test will fail.
    """
    ssim_path = os.path.join(PROJECT_ROOT, "metrics", "ssim.py")
    with open(ssim_path, encoding="utf-8") as f:
        source = f.read()

    assert "multichannel" not in source, (
        "Bug 1.8: 'multichannel' parameter found in metrics/ssim.py. "
        "This deprecated kwarg causes TypeError on scikit-image >= 0.19. "
        "Replace with channel_axis=-1."
    )


# ---------------------------------------------------------------------------
# Bug 1.10 — Legacy Streamlit charts removed (Recharts in frontend)
# ---------------------------------------------------------------------------
def test_bug_1_10_dashboard_charts_replaced():
    """Streamlit dashboard removed; metrics charts live in frontend/src/components/charts/."""
    charts_path = os.path.join(
        PROJECT_ROOT, "frontend", "src", "components", "charts", "metric-charts.tsx"
    )
    assert os.path.isfile(charts_path), (
        "Expected Next.js metric charts at frontend/src/components/charts/metric-charts.tsx"
    )


# ---------------------------------------------------------------------------
# Bug 1.13 — Archival score formula does not factor in BER
# ---------------------------------------------------------------------------
def test_bug_1_13_archival_score_includes_ber():
    """Bug 1.13: archival score must be cr * ocr * (1 - ber) in backend pipeline."""
    pipeline_path = os.path.join(PROJECT_ROOT, "backend", "app", "services", "pipeline.py")
    with open(pipeline_path, encoding="utf-8") as f:
        source = f.read()

    assert "(1 - ber)" in source, (
        "Bug 1.13: Archival score formula does not factor in BER. "
        "Expected: cr * ocr * (1 - ber) in archival_recommendations()."
    )
