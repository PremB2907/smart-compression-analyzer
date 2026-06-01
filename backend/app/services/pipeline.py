"""Paper-aligned document compression pipeline for SecureArchive AI."""

from __future__ import annotations

import hashlib
import logging
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compression.djvu_converter import convert_djvu
from compression.jpeg_compressor import compress_jpeg as compress_jpeg_file
from compression.pdf_converter import convert_pdf
from compression.png_compressor import compress_png
from compression.subprocess_utils import run_command
from compression.tiff_compressor import compress_tiff
from compression.webp_compressor import compress_webp
from metrics.ber import compute_ber, compute_payload_accuracy
from metrics.compression_ratio import compression_ratio
from metrics.mse import compute_mse
from metrics.ocr_accuracy import extract_text, ocr_accuracy
from metrics.psnr import compute_psnr
from metrics.ssim import compute_ssim
from utils.preprocessing import preprocess_image
from utils.steganography_lsb import (
    PAYLOAD_BITS,
    bits_to_string,
    build_payload,
    embed_lsb_payload,
    extract_lsb_payload,
)

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)
REFERENCE_SIZE = (settings.reference_width, settings.reference_height)
CMD_TIMEOUT = settings.external_command_timeout_sec

FORMATS = ("JPEG", "PNG", "TIFF", "PDF", "WebP", "DjVu")


@dataclass
class PipelineResult:
    reference_path: Path
    stego_path: Path
    payload_uuid: str
    payload_timestamp: str
    payload_checksum: str
    payload_bits: list[int]
    original_payload_str: str
    ground_truth_text: str
    embedding_psnr: float
    formats: dict[str, dict[str, Any]] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)


def _resize_reference(arr: np.ndarray) -> np.ndarray:
    pil = Image.fromarray(arr)
    pil = pil.resize(REFERENCE_SIZE, Image.Resampling.LANCZOS)
    return np.array(pil, dtype=np.uint8)


def _embedding_psnr(original: np.ndarray, stego: np.ndarray) -> float:
    mse = float(np.mean((original.astype(float) - stego.astype(float)) ** 2))
    if mse == 0:
        return float("inf")
    return float(10 * np.log10((255.0**2) / mse))


def _compress_jpeg(src: Path, out_dir: Path) -> Path:
    return compress_jpeg_file(src, out_dir, quality=75)


def _ocr_diff(ref: str, hyp: str) -> dict:
    import difflib

    matcher = difflib.SequenceMatcher(None, ref, hyp)
    ops = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        ops.append({"type": tag, "ref_start": i1, "ref_end": i2, "hyp_start": j1, "hyp_end": j2})
    return {"operations": ops, "ref_len": len(ref), "hyp_len": len(hyp)}


def _decode_to_grayscale(path: Path) -> np.ndarray | None:
    ext = path.suffix.lower()
    if ext == ".djvu":
        temp_png = path.with_suffix(".decoded.png")
        try:
            run_command(
                ["ddjvu", "-format=png", str(path), str(temp_png)],
                timeout=CMD_TIMEOUT,
            )
            return np.array(Image.open(temp_png).convert("L"), dtype=np.uint8)
        except (RuntimeError, OSError, ValueError) as exc:
            logger.warning("DjVu decode failed for %s: %s", path.name, exc)
            return None
        finally:
            if temp_png.exists():
                temp_png.unlink(missing_ok=True)
    try:
        return np.array(Image.open(path).convert("L"), dtype=np.uint8)
    except (OSError, ValueError) as exc:
        logger.warning("Image decode failed for %s: %s", path.name, exc)
        return None


def _save_reconstructed(src: Path, out_dir: Path, fmt: str) -> Path | None:
    arr = _decode_to_grayscale(src)
    if arr is None:
        return None
    out = out_dir / f"{fmt.lower()}_reconstructed.png"
    Image.fromarray(arr).save(out, "PNG")
    return out


def run_pipeline(input_path: Path, work_dir: Path) -> PipelineResult:
    work_dir.mkdir(parents=True, exist_ok=True)

    preprocessed = preprocess_image(input_path)
    preprocessed = _resize_reference(preprocessed)

    doc_uuid = uuid.uuid4().hex
    timestamp = datetime.now(UTC).isoformat()[:25]
    checksum = hashlib.sha256(preprocessed.tobytes()).hexdigest()
    payload_bits = build_payload(doc_uuid, timestamp, checksum)
    original_payload_str = doc_uuid[:32] + timestamp[:25] + checksum[:64]
    stego_arr = embed_lsb_payload(preprocessed, payload_bits)
    embedding_psnr = _embedding_psnr(preprocessed, stego_arr)

    reference_path = work_dir / "reference.png"
    stego_path = work_dir / "stego.png"
    Image.fromarray(preprocessed).save(reference_path, "PNG")
    Image.fromarray(stego_arr).save(stego_path, "PNG")

    ground_truth = extract_text(stego_path).strip()

    compressors = {
        "JPEG": lambda s, d: _compress_jpeg(s, d),
        "PNG": compress_png,
        "TIFF": compress_tiff,
        "PDF": convert_pdf,
        "WebP": compress_webp,
        "DjVu": convert_djvu,
    }

    result = PipelineResult(
        reference_path=reference_path,
        stego_path=stego_path,
        payload_uuid=doc_uuid,
        payload_timestamp=timestamp,
        payload_checksum=checksum,
        payload_bits=payload_bits,
        original_payload_str=original_payload_str,
        ground_truth_text=ground_truth,
        embedding_psnr=embedding_psnr,
    )

    for fmt, func in compressors.items():
        fmt_dir = work_dir / fmt.lower()
        fmt_dir.mkdir(exist_ok=True)
        t0 = time.perf_counter()
        try:
            out_path = func(stego_path, fmt_dir)
        except Exception as exc:
            result.errors[fmt] = str(exc)
            continue
        encode_ms = (time.perf_counter() - t0) * 1000

        t1 = time.perf_counter()
        try:
            img = Image.open(out_path)
            img.load()
        except Exception:
            pass
        decode_ms = (time.perf_counter() - t1) * 1000

        reconstructed = _save_reconstructed(out_path, fmt_dir, fmt)
        cr = compression_ratio(stego_path, out_path)
        mse_val = compute_mse(stego_path, out_path)
        psnr_val = compute_psnr(stego_path, out_path)
        ssim_val = compute_ssim(stego_path, out_path)

        t_hat = extract_text(out_path)
        ocr_acc = ocr_accuracy(t_hat, ground_truth)
        cer = 1.0 - ocr_acc if ground_truth else 0.0

        decoded_arr = _decode_to_grayscale(out_path)
        if decoded_arr is not None:
            extracted_bits = extract_lsb_payload(decoded_arr, PAYLOAD_BITS)
            ber_val = compute_ber(payload_bits, extracted_bits)
            extracted_str = bits_to_string(extracted_bits)
            payload_acc = compute_payload_accuracy(original_payload_str, extracted_str)
            corrupted = sum(a != b for a, b in zip(payload_bits, extracted_bits, strict=False))
        else:
            ber_val = 1.0
            payload_acc = 0.0
            extracted_str = ""
            corrupted = PAYLOAD_BITS

        size_bytes = out_path.stat().st_size
        throughput = (size_bytes / max(encode_ms / 1000, 1e-6)) / (1024 * 1024)

        result.formats[fmt] = {
            "compressed_path": out_path,
            "reconstructed_path": reconstructed,
            "file_size_bytes": size_bytes,
            "compression_ratio": cr,
            "mse": mse_val,
            "psnr": psnr_val,
            "ssim": ssim_val,
            "ocr_accuracy": ocr_acc,
            "cer": cer,
            "ber": ber_val,
            "payload_recovery_pct": payload_acc * 100,
            "encode_time_ms": encode_ms,
            "decode_time_ms": decode_ms,
            "throughput_mbps": throughput,
            "recovered_text": t_hat,
            "extracted_payload": extracted_str,
            "corrupted_bits": corrupted,
            "ocr_diff": _ocr_diff(ground_truth, t_hat),
        }

    return result


def archival_recommendations(pipeline: PipelineResult) -> dict[str, Any]:
    scores = {}
    for fmt, data in pipeline.formats.items():
        cr = data.get("compression_ratio") or 0
        ocr = data.get("ocr_accuracy") or 0
        ber = data.get("ber") or 1
        scores[fmt] = cr * ocr * (1 - ber)

    if not scores:
        return {"best_archival": None, "explanations": []}

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best = ranked[0][0]
    explanations = [
        f"Best overall archival score ({ranked[0][1]:.2f}): {best} — balances CR, OCR, and hidden-data BER.",
    ]
    ocr_best = max(pipeline.formats.items(), key=lambda x: x[1].get("ocr_accuracy", 0))[0]
    storage_best = max(pipeline.formats.items(), key=lambda x: x[1].get("compression_ratio", 0))[0]
    meta_best = min(pipeline.formats.items(), key=lambda x: x[1].get("ber", 1))[0]

    if ocr_best != best:
        explanations.append(f"If OCR is priority → {ocr_best}")
    if meta_best != best:
        explanations.append(f"If perfect metadata preservation required → {meta_best}")
    if storage_best != best:
        explanations.append(f"If storage cost priority → {storage_best}")

    return {
        "best_archival": best,
        "best_ocr": ocr_best,
        "best_storage": storage_best,
        "best_security": meta_best,
        "leaderboard": [{"format": f, "score": s} for f, s in ranked],
        "explanations": explanations,
    }


def generate_research_tables(pipeline: PipelineResult) -> dict[str, list[dict]]:
    """Generate Tables I–V style summaries from a single pipeline run."""
    rows = []
    for fmt, d in pipeline.formats.items():
        rows.append(
            {
                "Format": fmt,
                "CR": round(d["compression_ratio"], 2),
                "PSNR (dB)": round(d["psnr"], 2) if d["psnr"] == d["psnr"] else None,
                "SSIM": round(d["ssim"], 4),
                "OCR Acc": round(d["ocr_accuracy"] * 100, 2),
                "BER": round(d["ber"] * 100, 3),
                "Payload %": round(d["payload_recovery_pct"], 2),
            }
        )
    return {
        "table_i_compression_quality": rows,
        "table_ii_ocr_preservation": sorted(rows, key=lambda r: r["OCR Acc"], reverse=True),
        "table_iii_hidden_data": sorted(rows, key=lambda r: r["BER"]),
        "table_iv_timing": [
            {
                "Format": fmt,
                "Encode (ms)": round(d["encode_time_ms"], 2),
                "Decode (ms)": round(d["decode_time_ms"], 2),
                "Throughput (MB/s)": round(d["throughput_mbps"], 3),
            }
            for fmt, d in pipeline.formats.items()
        ],
        "table_v_archival_ranking": archival_recommendations(pipeline)["leaderboard"],
    }
