import json
import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from app.celery_app import celery_app

logger = logging.getLogger(__name__)
from app.database import SessionLocal
from app.models.compression import CompressionRun, MetricRecord, OCRResult
from app.models.image import ImageRecord
from app.models.stego import RecoveredPayload, StegoPayload
from app.models.upload import Upload, UploadStatus
from app.services.pipeline import generate_research_tables, run_pipeline
from app.services.storage import StorageService


@celery_app.task(bind=True, name="process_upload")
def process_upload_task(self, upload_id: int):
    db = SessionLocal()
    storage = StorageService()
    work_dir = Path(tempfile.mkdtemp(prefix="securearchive_"))
    try:
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        if not upload:
            return {"error": "upload not found"}

        upload.status = UploadStatus.processing
        db.commit()

        local_input = work_dir / upload.original_filename
        storage.download_to_path(upload.storage_key, local_input)

        pipeline = run_pipeline(local_input, work_dir / "pipeline")

        ref_key = storage.upload_file(pipeline.reference_path, prefix="references")
        stego_key = storage.upload_file(pipeline.stego_path, prefix="stego")

        image = ImageRecord(
            upload_id=upload.id,
            reference_storage_key=ref_key,
            width=1000,
            height=1414,
            ground_truth_text=pipeline.ground_truth_text,
        )
        db.add(image)
        db.flush()

        stego_row = StegoPayload(
            image_id=image.id,
            uuid=pipeline.payload_uuid,
            timestamp=pipeline.payload_timestamp,
            checksum=pipeline.payload_checksum,
            payload_bits=968,
            embedding_psnr=pipeline.embedding_psnr,
            stego_storage_key=stego_key,
        )
        db.add(stego_row)

        for fmt, data in pipeline.formats.items():
            comp_key = storage.upload_file(data["compressed_path"], prefix="compressed")
            recon_key = None
            if data.get("reconstructed_path") and data["reconstructed_path"].exists():
                recon_key = storage.upload_file(data["reconstructed_path"], prefix="reconstructed")

            run = CompressionRun(
                upload_id=upload.id,
                format=fmt,
                compressed_storage_key=comp_key,
                reconstructed_storage_key=recon_key,
                encode_time_ms=data["encode_time_ms"],
                decode_time_ms=data["decode_time_ms"],
            )
            db.add(run)
            db.flush()

            db.add(
                MetricRecord(
                    compression_run_id=run.id,
                    file_size_bytes=data["file_size_bytes"],
                    compression_ratio=data["compression_ratio"],
                    mse=data["mse"],
                    psnr=data["psnr"],
                    ssim=data["ssim"],
                    ocr_accuracy=data["ocr_accuracy"],
                    cer=data["cer"],
                    ber=data["ber"],
                    payload_recovery_pct=data["payload_recovery_pct"],
                    throughput_mbps=data["throughput_mbps"],
                    embedding_psnr=pipeline.embedding_psnr,
                )
            )
            db.add(
                OCRResult(
                    compression_run_id=run.id,
                    reference_text=pipeline.ground_truth_text,
                    recovered_text=data["recovered_text"],
                    diff_json=json.dumps(data["ocr_diff"]),
                )
            )
            db.add(
                RecoveredPayload(
                    compression_run_id=run.id,
                    recovered_uuid=data["extracted_payload"][:32]
                    if data["extracted_payload"]
                    else None,
                    recovered_timestamp=data["extracted_payload"][32:57]
                    if len(data["extracted_payload"]) >= 57
                    else None,
                    recovered_checksum=data["extracted_payload"][57:121]
                    if len(data["extracted_payload"]) >= 121
                    else None,
                    recovery_pct=data["payload_recovery_pct"],
                    ber=data["ber"],
                    corrupted_bits=data["corrupted_bits"],
                    bit_damage_json=json.dumps(
                        {"corrupted_bits": data["corrupted_bits"], "total_bits": 968}
                    ),
                )
            )

        upload.status = UploadStatus.completed
        upload.completed_at = datetime.utcnow()
        db.commit()
        return {"upload_id": upload_id, "formats": list(pipeline.formats.keys())}
    except Exception as exc:
        logger.exception("Upload processing failed for id=%s", upload_id)
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        if upload:
            upload.status = UploadStatus.failed
            upload.error_message = str(exc)[:2000]
            db.commit()
        raise
    finally:
        db.close()
        shutil.rmtree(work_dir, ignore_errors=True)


@celery_app.task(name="run_benchmark")
def run_benchmark_task(benchmark_id: int, dataset_dir: str):
    from app.models.benchmark import Benchmark

    db = SessionLocal()
    try:
        bench = db.query(Benchmark).filter(Benchmark.id == benchmark_id).first()
        if not bench:
            return
        bench.status = "processing"
        db.commit()

        all_tables = []
        dataset = Path(dataset_dir)
        for img_path in sorted(dataset.glob("*")):
            if img_path.suffix.lower() not in {
                ".png",
                ".jpg",
                ".jpeg",
                ".tif",
                ".tiff",
                ".bmp",
                ".pdf",
            }:
                continue
            work = Path(tempfile.mkdtemp())
            try:
                pipeline = run_pipeline(img_path, work)
                all_tables.append(
                    {"file": img_path.name, "tables": generate_research_tables(pipeline)}
                )
            finally:
                shutil.rmtree(work, ignore_errors=True)

        bench.results_json = json.dumps(all_tables)
        bench.tables_json = json.dumps(aggregate_benchmark_tables(all_tables))
        bench.status = "completed"
        bench.completed_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


def aggregate_benchmark_tables(runs: list) -> dict:
    if not runs:
        return {}
    return runs[0].get("tables", {})
