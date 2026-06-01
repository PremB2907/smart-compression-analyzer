"""Lightweight CV heuristics for format recommendation (AI extensions beyond the paper)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def classify_document_type(image_path: Path) -> str:
    img = np.array(Image.open(image_path).convert("L"), dtype=np.float32)
    edges = np.abs(np.diff(img, axis=1)).mean()
    variance = img.var()
    if variance < 400:
        return "form"
    if edges > 25:
        return "newspaper"
    if variance > 3500:
        return "handwritten"
    h, w = img.shape
    if w > h * 1.2:
        return "scientific_paper"
    return "printed_text"


def predict_metrics(document_type: str) -> dict[str, dict[str, float]]:
    """Heuristic pre-compression quality predictions by format."""
    base = {
        "JPEG": {"ocr": 0.88, "ber": 0.12, "cr": 8.0},
        "PNG": {"ocr": 0.99, "ber": 0.01, "cr": 1.2},
        "TIFF": {"ocr": 0.99, "ber": 0.01, "cr": 1.1},
        "PDF": {"ocr": 0.90, "ber": 0.10, "cr": 10.0},
        "WebP": {"ocr": 0.87, "ber": 0.14, "cr": 9.0},
        "DjVu": {"ocr": 0.96, "ber": 0.05, "cr": 18.0},
    }
    boosts = {
        "printed_text": {"DjVu": 0.02, "PNG": 0.01},
        "handwritten": {"PNG": 0.03, "TIFF": 0.02},
        "scientific_paper": {"DjVu": 0.03, "PDF": 0.02},
        "form": {"PNG": 0.04, "TIFF": 0.03},
        "newspaper": {"DjVu": 0.04, "WebP": 0.01},
    }
    preds = {k: dict(v) for k, v in base.items()}
    for fmt, delta in boosts.get(document_type, {}).items():
        if fmt in preds:
            preds[fmt]["ocr"] = min(0.99, preds[fmt]["ocr"] + delta)
    return preds


def recommend_format(document_type: str) -> tuple[str, str]:
    preds = predict_metrics(document_type)
    best = max(preds.items(), key=lambda x: x[1]["ocr"] * x[1]["cr"] * (1 - x[1]["ber"]))
    reasons = {
        "printed_text": "DjVu preserves text layers and achieves high compression for printed scans.",
        "handwritten": "PNG lossless encoding preserves stroke detail for handwriting.",
        "scientific_paper": "DjVu JB2 foreground + IW44 background suits mixed text/graphics.",
        "form": "PNG ensures field boundaries and metadata survive lossless archival.",
        "newspaper": "DjVu IW44 handles halftone backgrounds common in newsprint.",
    }
    return best[0], reasons.get(document_type, "Balanced OCR, compression, and metadata survival.")
