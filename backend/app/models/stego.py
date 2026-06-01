from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StegoPayload(Base):
    __tablename__ = "stego_payloads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id"), unique=True)
    uuid: Mapped[str] = mapped_column(String(32))
    timestamp: Mapped[str] = mapped_column(String(25))
    checksum: Mapped[str] = mapped_column(String(64))
    payload_bits: Mapped[int] = mapped_column(Integer, default=968)
    embedding_psnr: Mapped[float | None] = mapped_column(Float, nullable=True)
    stego_storage_key: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    image = relationship("ImageRecord", back_populates="stego_payload")


class RecoveredPayload(Base):
    __tablename__ = "recovered_payloads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    compression_run_id: Mapped[int] = mapped_column(ForeignKey("compression_runs.id"), unique=True)
    recovered_uuid: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recovered_timestamp: Mapped[str | None] = mapped_column(String(25), nullable=True)
    recovered_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recovery_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    ber: Mapped[float | None] = mapped_column(Float, nullable=True)
    corrupted_bits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bit_damage_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    compression_run = relationship("CompressionRun", back_populates="recovered_payload")
