"""Asynchronous SQS compression job worker reusing existing pipeline code."""

from __future__ import annotations

import logging
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.services.cloud.dynamo_meta import DynamoMetaRepository
from app.services.cloud.s3_storage import S3StorageEngine
from app.services.cloud.sqs_queue import SQSQueueService
from app.services.pipeline import archival_recommendations, run_pipeline

logger = logging.getLogger(__name__)


class CloudCompressionWorker:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.s3 = S3StorageEngine()
        self.dynamo = DynamoMetaRepository()
        self.sqs = SQSQueueService()

    def process_job(self, job_data: dict[str, Any]) -> dict[str, Any]:
        """Executes the compression pipeline for a single job payload."""
        job_id = job_data.get("job_id")
        s3_key = job_data.get("s3_key")
        filename = job_data.get("filename", "input.png")

        if not job_id or not s3_key:
            raise ValueError(f"Invalid job payload: {job_data}")

        logger.info("Starting processing for cloud job %s (key: %s)", job_id, s3_key)
        self.dynamo.update_job_status(job_id, "PROCESSING")

        work_dir = Path(tempfile.mkdtemp(prefix=f"floci_work_{job_id}_"))
        start_time = time.perf_counter()

        try:
            local_input = work_dir / filename
            self.s3.download_to_path(s3_key, local_input)

            # Invoke existing research pipeline
            pipeline = run_pipeline(local_input, work_dir / "pipeline")

            # Upload generated artifacts to S3
            ref_key = self.s3.upload_file(pipeline.reference_path, prefix="references")
            stego_key = self.s3.upload_file(pipeline.stego_path, prefix="stego")

            formats_record: dict[str, Any] = {}
            for fmt, data in pipeline.formats.items():
                comp_key = self.s3.upload_file(data["compressed_path"], prefix="compressed")
                recon_key = None
                if data.get("reconstructed_path") and data["reconstructed_path"].exists():
                    recon_key = self.s3.upload_file(
                        data["reconstructed_path"], prefix="reconstructed"
                    )

                formats_record[fmt] = {
                    "compressed_s3_key": comp_key,
                    "reconstructed_s3_key": recon_key,
                    "file_size_bytes": data.get("file_size_bytes"),
                    "compression_ratio": data.get("compression_ratio"),
                    "mse": data.get("mse"),
                    "psnr": data.get("psnr"),
                    "ssim": data.get("ssim"),
                    "ocr_accuracy": data.get("ocr_accuracy"),
                    "cer": data.get("cer"),
                    "ber": data.get("ber"),
                    "payload_recovery_pct": data.get("payload_recovery_pct"),
                    "encode_time_ms": data.get("encode_time_ms"),
                    "decode_time_ms": data.get("decode_time_ms"),
                    "throughput_mbps": data.get("throughput_mbps"),
                }

            recommendations = archival_recommendations(pipeline)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            # Record final measurements in DynamoDB
            self.dynamo.record_job_results(
                job_id=job_id,
                formats_data=formats_record,
                duration_ms=duration_ms,
                embedding_psnr=pipeline.embedding_psnr,
                recommendations=recommendations,
            )

            logger.info("Successfully completed cloud job %s in %.2f ms", job_id, duration_ms)
            return {
                "job_id": job_id,
                "status": "COMPLETED",
                "duration_ms": duration_ms,
                "formats": list(formats_record.keys()),
            }

        except Exception as exc:
            logger.exception("Cloud job %s failed: %s", job_id, exc)
            self.dynamo.update_job_status(job_id, "FAILED", error_message=str(exc))
            raise
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def process_single_queued_job(self, wait_time_sec: int = 2) -> bool:
        """Pulls a single message from SQS and processes it. Returns True if a message was handled."""
        messages = self.sqs.receive_jobs(max_messages=1, wait_time_sec=wait_time_sec)
        if not messages:
            return False

        msg = messages[0]
        receipt = msg.get("receipt_handle")
        payload = msg.get("payload", {})

        try:
            self.process_job(payload)
            if receipt:
                self.sqs.delete_job(receipt)
            return True
        except Exception:
            # Message will become visible again after VisibilityTimeout
            logger.error("Error processing job %s; leaving in queue for retry", payload.get("job_id"))
            return False

    def run_worker_loop(self, poll_interval_sec: int = 2) -> None:
        """Continuous polling loop for worker daemon."""
        logger.info("Starting Cloud Compression SQS Worker daemon...")
        while True:
            try:
                handled = self.process_single_queued_job(wait_time_sec=poll_interval_sec)
                if not handled:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Worker stopped by user.")
                break
            except Exception as exc:
                logger.error("Unexpected worker error: %s", exc)
                time.sleep(2)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = CloudCompressionWorker()
    worker.run_worker_loop()
