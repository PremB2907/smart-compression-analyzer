from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.compression import CompressionRun, MetricRecord
from app.models.upload import Upload, UploadStatus
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    uploads = db.query(Upload).filter(Upload.user_id == user.id).all()
    upload_ids = [u.id for u in uploads]
    total_files = len(uploads)
    completed = sum(1 for u in uploads if u.status == UploadStatus.completed)

    metrics = (
        db.query(MetricRecord)
        .join(CompressionRun)
        .filter(CompressionRun.upload_id.in_(upload_ids))
        .all()
        if upload_ids
        else []
    )

    avg_cr = _avg([m.compression_ratio for m in metrics])
    avg_ocr = _avg([m.ocr_accuracy for m in metrics if m.ocr_accuracy is not None])
    avg_ber = _avg([m.ber for m in metrics if m.ber is not None])

    by_format: dict[str, dict] = {}
    for m in metrics:
        run = db.query(CompressionRun).filter(CompressionRun.id == m.compression_run_id).first()
        if not run:
            continue
        fmt = run.format
        if fmt not in by_format:
            by_format[fmt] = {"cr": [], "ocr": [], "ber": [], "psnr": [], "ssim": []}
        if m.compression_ratio:
            by_format[fmt]["cr"].append(m.compression_ratio)
        if m.ocr_accuracy is not None:
            by_format[fmt]["ocr"].append(m.ocr_accuracy)
        if m.ber is not None:
            by_format[fmt]["ber"].append(m.ber)
        if m.psnr is not None:
            by_format[fmt]["psnr"].append(m.psnr)
        if m.ssim is not None:
            by_format[fmt]["ssim"].append(m.ssim)

    chart_data = {
        fmt: {
            "avg_compression_ratio": _avg(vals["cr"]),
            "avg_ocr_accuracy": _avg(vals["ocr"]),
            "avg_ber": _avg(vals["ber"]),
            "avg_psnr": _avg(vals["psnr"]),
            "avg_ssim": _avg(vals["ssim"]),
        }
        for fmt, vals in by_format.items()
    }

    leaderboard = sorted(
        [
            {
                "format": fmt,
                "score": (d["avg_compression_ratio"] or 0)
                * (d["avg_ocr_accuracy"] or 0)
                * (1 - (d["avg_ber"] or 1)),
            }
            for fmt, d in chart_data.items()
        ],
        key=lambda x: x["score"],
        reverse=True,
    )

    return {
        "cards": {
            "total_files": total_files,
            "completed_analyses": completed,
            "avg_compression_ratio": avg_cr,
            "avg_ocr_accuracy": avg_ocr,
            "avg_ber": avg_ber,
        },
        "charts": chart_data,
        "leaderboard": leaderboard,
        "formulas": {
            "compression_ratio": "CR = S_original / S_compressed",
            "psnr": "PSNR = 10 * log10(255² / MSE)",
            "ssim": "SSIM(x,y) per Wang et al.",
            "ocr_accuracy": "OCR_acc = 1 - CER(T̂, T_ref)",
            "cer": "CER = editdistance(T̂, T_ref) / |T_ref|",
            "ber": "BER = Σ(b̂_k ≠ b_k) / N, N=968",
            "archival_score": "Score = CR × OCR_acc × (1 - BER)",
        },
    }


def _avg(values: list) -> float | None:
    import math
    filtered = [v for v in values if v is not None and not math.isinf(v) and not math.isnan(v)]
    if not filtered:
        return None
    return round(sum(filtered) / len(filtered), 4)
