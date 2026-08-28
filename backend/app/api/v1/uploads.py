import hashlib
import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.audit import AuditLog
from app.models.compression import CompressionRun, MetricRecord, OCRResult
from app.models.image import ImageRecord
from app.models.stego import StegoPayload
from app.models.upload import Upload, UploadStatus
from app.models.user import User
from app.schemas.upload import (
    AnalysisResult,
    BatchUploadResponse,
    MetricOut,
    OCRDiffOut,
    StegoOut,
    UploadResponse,
)
from app.services.ai_extensions import classify_document_type, predict_metrics, recommend_format
from app.services.pipeline import archival_recommendations
from app.services.storage import StorageService
from app.tasks.processing import process_upload_task

router = APIRouter(prefix="/uploads", tags=["Uploads"])
settings = get_settings()


def _validate_file(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.allowed_ext_set:
        raise HTTPException(
            status_code=400, detail=f"Unsupported type. Allowed: {settings.allowed_extensions}"
        )


@router.post("", response_model=BatchUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_files(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if len(files) > settings.max_files_per_batch:
        raise HTTPException(
            status_code=400, detail=f"Maximum {settings.max_files_per_batch} files per batch"
        )

    storage = StorageService()
    created: list[Upload] = []

    for file in files:
        _validate_file(file)
        content = await file.read()
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=400, detail=f"File exceeds {settings.max_upload_size_mb}MB limit"
            )

        checksum = hashlib.sha256(content).hexdigest()
        tmp_path: Path | None = None
        try:
            filename = file.filename or "upload"
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=Path(filename).suffix
            ) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)
            key = storage.upload_file(tmp_path, prefix="uploads")
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)

        upload = Upload(
            user_id=user.id,
            original_filename=file.filename,
            storage_key=key,
            mime_type=file.content_type,
            size_bytes=len(content),
            checksum_sha256=checksum,
            status=UploadStatus.processing,
        )
        db.add(upload)
        db.flush()
        db.commit()  # Commit early so the synchronous celery task can fetch this upload

        task = process_upload_task.delay(upload.id)
        upload.celery_task_id = task.id
        created.append(upload)

        db.add(
            AuditLog(
                user_id=user.id,
                action="upload.create",
                resource_type="upload",
                resource_id=upload.id,
                details=file.filename,
            )
        )
        db.commit()

    return BatchUploadResponse(
        uploads=[UploadResponse.model_validate(u) for u in created],
        message="Processing started asynchronously",
    )


@router.get("", response_model=list[UploadResponse])
def list_uploads(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return db.query(Upload).filter(Upload.user_id == user.id).order_by(Upload.id.desc()).all()


@router.get("/{upload_id}", response_model=AnalysisResult)
def get_analysis(
    upload_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    upload = db.query(Upload).filter(Upload.id == upload_id, Upload.user_id == user.id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    from app.services.storage import StorageService
    storage = StorageService()
    original_url = storage.get_presigned_url(upload.storage_key)

    runs = db.query(CompressionRun).filter(CompressionRun.upload_id == upload.id).all()
    metrics_out: list[MetricOut] = []
    ocr_map: dict[str, OCRDiffOut] = {}
    errors: dict[str, str] = {}

    if upload.error_message:
        errors["pipeline"] = upload.error_message

    for run in runs:
        m = db.query(MetricRecord).filter(MetricRecord.compression_run_id == run.id).first()
        ocr = db.query(OCRResult).filter(OCRResult.compression_run_id == run.id).first()
        if m:
            reconstructed_url = (
                storage.get_presigned_url(run.reconstructed_storage_key)
                if run.reconstructed_storage_key
                else None
            )
            compressed_url = (
                storage.get_presigned_url(run.compressed_storage_key)
                if run.compressed_storage_key
                else None
            )
            metrics_out.append(
                MetricOut(
                    format=run.format,
                    compression_ratio=m.compression_ratio,
                    file_size_bytes=m.file_size_bytes,
                    mse=m.mse,
                    psnr=m.psnr,
                    ssim=m.ssim,
                    ocr_accuracy=m.ocr_accuracy,
                    cer=m.cer,
                    ber=m.ber,
                    payload_recovery_pct=m.payload_recovery_pct,
                    encode_time_ms=run.encode_time_ms,
                    decode_time_ms=run.decode_time_ms,
                    throughput_mbps=m.throughput_mbps,
                    reconstructed_url=reconstructed_url,
                    compressed_url=compressed_url,
                )
            )
        if ocr:
            diff = json.loads(ocr.diff_json) if ocr.diff_json else {}
            ocr_map[run.format] = OCRDiffOut(
                reference_text=ocr.reference_text or "",
                recovered_text=ocr.recovered_text or "",
                diff=diff,
            )

    stego_out = None
    image = db.query(ImageRecord).filter(ImageRecord.upload_id == upload.id).first()
    if image:
        stego = db.query(StegoPayload).filter(StegoPayload.image_id == image.id).first()
        if stego:
            stego_out = StegoOut(
                uuid=stego.uuid,
                timestamp=stego.timestamp,
                checksum=stego.checksum,
                payload_bits=stego.payload_bits,
                embedding_psnr=stego.embedding_psnr,
            )

    recommendations = {}
    research_tables = None
    ai_prediction = None
    if upload.status == UploadStatus.completed and metrics_out:
        pseudo_pipeline = type("P", (), {"formats": {}})()
        for m in metrics_out:
            pseudo_pipeline.formats[m.format] = {
                "compression_ratio": m.compression_ratio or 0,
                "ocr_accuracy": m.ocr_accuracy or 0,
                "ber": m.ber or 1,
            }
        recommendations = archival_recommendations(pseudo_pipeline)

    return AnalysisResult(
        upload_id=upload.id,
        status=upload.status.value,
        original_url=original_url,
        steganography=stego_out,
        metrics=metrics_out,
        ocr_by_format=ocr_map,
        recommendations=recommendations,
        research_tables=research_tables,
        ai_prediction=ai_prediction,
        errors=errors,
    )


@router.get("/{upload_id}/task")
def task_status(
    upload_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    upload = db.query(Upload).filter(Upload.id == upload_id, Upload.user_id == user.id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # Map database upload status to celery state strings where appropriate
    if upload.status == UploadStatus.completed:
        state = "SUCCESS"
    elif upload.status == UploadStatus.failed:
        state = "FAILURE"
    else:
        state = "PENDING"
        if upload.celery_task_id:
            try:
                from app.celery_app import celery_app
                result = celery_app.AsyncResult(upload.celery_task_id)
                state = result.state
            except Exception:
                # If Redis is offline/unreachable, fallback to the database status
                if upload.status == UploadStatus.processing:
                    state = "PENDING"

    return {"upload_id": upload_id, "status": upload.status.value, "celery_state": state}


@router.post("/{upload_id}/ai-preview")
def ai_preview(
    upload_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    upload = db.query(Upload).filter(Upload.id == upload_id, Upload.user_id == user.id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    storage = StorageService()
    path: Path | None = None
    doc_type: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(upload.original_filename).suffix
        ) as tmp:
            path = Path(tmp.name)
        storage.download_to_path(upload.storage_key, path)
        doc_type = classify_document_type(path)
    finally:
        if path is not None:
            path.unlink(missing_ok=True)
    doc_type = doc_type or "printed_text"
    fmt, reason = recommend_format(doc_type)
    return {
        "document_type": doc_type,
        "recommended_format": fmt,
        "reason": reason,
        "predicted_metrics": predict_metrics(doc_type),
    }
