# batch_process.py
"""Batch processing script for the Smart Document Compression Analyzer.

Implements the full paper pipeline for each image:
  1. Preprocessing (greyscale normalisation, Gaussian σ=0.5, deskewing)
  2. LSB steganographic embedding (UUID + timestamp + SHA-256, 968 bits)
  3. Compression to 6 formats
  4. Metrics: CR, MSE, PSNR, SSIM, OCR accuracy (CER), BER, Payload Recovery

Usage::
    python batch_process.py --input ./dataset --output ./results/report.csv
"""

import argparse
import csv
import hashlib
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from compression.djvu_converter import convert_djvu
from compression.jpeg_compressor import compress_jpeg
from compression.pdf_converter import convert_pdf
from compression.png_compressor import compress_png
from compression.tiff_compressor import compress_tiff
from compression.webp_compressor import compress_webp
from metrics.ber import compute_ber, compute_payload_accuracy
from metrics.compression_ratio import compression_ratio
from metrics.mse import compute_mse
from metrics.ocr_accuracy import extract_text, ocr_accuracy
from metrics.psnr import compute_psnr
from metrics.ssim import compute_ssim
from PIL import Image
from utils.preprocessing import preprocess_image
from utils.steganography_lsb import (
    PAYLOAD_BITS,
    bits_to_string,
    build_payload,
    embed_lsb_payload,
    extract_lsb_payload,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

COMPRESSION_FUNCS = {
    "JPEG": compress_jpeg,
    "PNG": compress_png,
    "WebP": compress_webp,
    "TIFF": compress_tiff,
    "PDF": convert_pdf,
    "DjVu": convert_djvu,
}


def process_file(input_path: Path, out_dir: Path) -> dict:
    """Compress a single file with all formats and compute metrics.

    Returns a dictionary where keys are column names for the CSV.
    """
    results = {"Filename": input_path.name}

    # Step 1: Preprocessing
    try:
        preprocessed_arr = preprocess_image(input_path)
    except Exception as e:
        logger.error("Preprocessing failed for %s: %s", input_path.name, e)
        return results

    # Step 2: LSB embedding
    doc_uuid = uuid.uuid4().hex
    timestamp = datetime.now(UTC).isoformat()[:25]
    checksum = hashlib.sha256(preprocessed_arr.tobytes()).hexdigest()
    original_payload_str = doc_uuid[:32] + timestamp[:25] + checksum[:64]
    payload_bits = build_payload(doc_uuid, timestamp, checksum)
    stego_arr = embed_lsb_payload(preprocessed_arr, payload_bits)

    # Save stego image as PNG
    stego_path = out_dir / f"{input_path.stem}_stego.png"
    Image.fromarray(stego_arr).save(str(stego_path), "PNG")

    # Step 3: Extract reference OCR transcript once
    t_ref = extract_text(stego_path)

    # Step 4: Compress and measure metrics
    for fmt, func in COMPRESSION_FUNCS.items():
        start = time.time()
        try:
            out_path = func(stego_path, out_dir)
        except Exception as e:
            logger.warning("%s compression failed for %s: %s", fmt, input_path.name, e)
            continue
        encode_time = time.time() - start

        # Decode time
        start = time.time()
        try:
            _img = Image.open(out_path)
            _img.load()
        except Exception:
            pass
        decode_time = time.time() - start

        cr = compression_ratio(stego_path, out_path)
        mse_val = compute_mse(stego_path, out_path)
        psnr_val = compute_psnr(stego_path, out_path)
        ssim_val = compute_ssim(stego_path, out_path)

        t_hat = extract_text(out_path)
        ocr_acc = ocr_accuracy(t_hat, t_ref)

        try:
            decoded_arr = np.array(Image.open(out_path).convert("L"), dtype=np.uint8)
            extracted_bits = extract_lsb_payload(decoded_arr, PAYLOAD_BITS)
            ber_val = compute_ber(payload_bits, extracted_bits)
            extracted_payload_str = bits_to_string(extracted_bits)
            payload_acc = compute_payload_accuracy(original_payload_str, extracted_payload_str)
        except Exception:
            ber_val = 0.5
            payload_acc = 0.0

        results.update(
            {
                f"{fmt}_size": out_path.stat().st_size,
                f"{fmt}_cr": cr,
                f"{fmt}_mse": mse_val,
                f"{fmt}_psnr": psnr_val,
                f"{fmt}_ssim": ssim_val,
                f"{fmt}_ocr": ocr_acc,
                f"{fmt}_ber": ber_val,
                f"{fmt}_payload_acc": payload_acc,
                f"{fmt}_enc_time": encode_time,
                f"{fmt}_dec_time": decode_time,
            }
        )
    return results


def main():
    parser = argparse.ArgumentParser(description="Batch run compression analysis.")
    parser.add_argument(
        "--input", type=str, required=True, help="Directory with source images/PDFs"
    )
    parser.add_argument("--output", type=str, required=True, help="CSV file to write results")
    parser.add_argument(
        "--temp", type=str, default="./batch_tmp", help="Temporary folder for intermediate files"
    )
    args = parser.parse_args()

    input_dir = Path(args.input)
    out_csv = Path(args.output)
    temp_dir = Path(args.temp)
    temp_dir.mkdir(parents=True, exist_ok=True)

    extensions = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".pdf"}
    files = [p for p in input_dir.rglob("*") if p.suffix.lower() in extensions]

    if not files:
        logger.warning("No supported files found in the input directory.")
        return

    header = ["Filename"]
    for fmt in COMPRESSION_FUNCS.keys():
        header.extend(
            [
                f"{fmt}_size",
                f"{fmt}_cr",
                f"{fmt}_mse",
                f"{fmt}_psnr",
                f"{fmt}_ssim",
                f"{fmt}_ocr",
                f"{fmt}_ber",
                f"{fmt}_payload_acc",
                f"{fmt}_enc_time",
                f"{fmt}_dec_time",
            ]
        )

    with out_csv.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        for file_path in files:
            logger.info("Processing: %s", file_path.name)
            row = process_file(file_path, temp_dir)
            writer.writerow(row)

    logger.info("Batch processing completed. Results saved to %s", out_csv)


if __name__ == "__main__":
    main()
