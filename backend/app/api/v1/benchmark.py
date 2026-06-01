from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.benchmark import Benchmark
from app.models.user import User, UserRole
from app.tasks.processing import run_benchmark_task

router = APIRouter(prefix="/benchmark", tags=["Research Reproduction"])


@router.post("/run")
def start_benchmark(
    name: str = "Paper Reproduction",
    dataset_path: str = "dataset",
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.researcher, UserRole.admin)),
):
    root = Path(__file__).resolve().parents[4]
    full_path = root / dataset_path
    if not full_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Dataset not found: {dataset_path}")

    bench = Benchmark(user_id=user.id, name=name, dataset_path=str(full_path), status="pending")
    db.add(bench)
    db.commit()
    db.refresh(bench)

    run_benchmark_task.delay(bench.id, str(full_path))
    return {"benchmark_id": bench.id, "status": "started"}


@router.get("/{benchmark_id}")
def get_benchmark(
    benchmark_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    import json

    bench = (
        db.query(Benchmark)
        .filter(Benchmark.id == benchmark_id, Benchmark.user_id == user.id)
        .first()
    )
    if not bench:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    tables = json.loads(bench.tables_json) if bench.tables_json else {}
    return {
        "id": bench.id,
        "name": bench.name,
        "status": bench.status,
        "tables": tables,
        "table_labels": [
            "table_i_compression_quality",
            "table_ii_ocr_preservation",
            "table_iii_hidden_data",
            "table_iv_timing",
            "table_v_archival_ranking",
        ],
    }
