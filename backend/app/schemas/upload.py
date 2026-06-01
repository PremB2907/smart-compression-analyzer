from datetime import datetime

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    id: int
    original_filename: str
    status: str
    celery_task_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BatchUploadResponse(BaseModel):
    uploads: list[UploadResponse]
    message: str


class MetricOut(BaseModel):
    format: str
    compression_ratio: float | None
    file_size_bytes: int | None
    mse: float | None
    psnr: float | None
    ssim: float | None
    ocr_accuracy: float | None
    cer: float | None
    ber: float | None
    payload_recovery_pct: float | None
    encode_time_ms: float | None
    decode_time_ms: float | None
    throughput_mbps: float | None


class OCRDiffOut(BaseModel):
    reference_text: str
    recovered_text: str
    diff: dict
    confidence_avg: float | None = None


class StegoOut(BaseModel):
    uuid: str
    timestamp: str
    checksum: str
    payload_bits: int
    embedding_psnr: float | None
    payload_size_bytes: int = 121


class AnalysisResult(BaseModel):
    upload_id: int
    status: str
    steganography: StegoOut | None
    metrics: list[MetricOut]
    ocr_by_format: dict[str, OCRDiffOut]
    recommendations: dict
    research_tables: dict | None = None
    ai_prediction: dict | None = None
    errors: dict[str, str] = Field(default_factory=dict)
