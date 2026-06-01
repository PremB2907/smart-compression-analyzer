from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CompressionRun(Base):
    __tablename__ = "compression_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id"))
    format: Mapped[str] = mapped_column(String(32))
    compressed_storage_key: Mapped[str] = mapped_column(String(1024))
    reconstructed_storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    encode_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    decode_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    upload = relationship("Upload", back_populates="compression_runs")
    metrics = relationship("MetricRecord", back_populates="compression_run", uselist=False)
    ocr_result = relationship("OCRResult", back_populates="compression_run", uselist=False)
    recovered_payload = relationship(
        "RecoveredPayload", back_populates="compression_run", uselist=False
    )


class MetricRecord(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    compression_run_id: Mapped[int] = mapped_column(ForeignKey("compression_runs.id"), unique=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    compression_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    mse: Mapped[float | None] = mapped_column(Float, nullable=True)
    psnr: Mapped[float | None] = mapped_column(Float, nullable=True)
    ssim: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    cer: Mapped[float | None] = mapped_column(Float, nullable=True)
    ber: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload_recovery_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    throughput_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding_psnr: Mapped[float | None] = mapped_column(Float, nullable=True)


class OCRResult(Base):
    __tablename__ = "ocr_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    compression_run_id: Mapped[int] = mapped_column(ForeignKey("compression_runs.id"), unique=True)
    reference_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    recovered_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    diff_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_avg: Mapped[float | None] = mapped_column(Float, nullable=True)

    compression_run = relationship("CompressionRun", back_populates="ocr_result")
