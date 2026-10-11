"""DynamoDB repository for compression job metadata and results."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from botocore.exceptions import ClientError

from app.config import get_settings
from app.services.cloud.client import get_dynamodb_client

logger = logging.getLogger(__name__)


def _to_dynamo_safe(val: Any) -> Any:
    """Recursively converts floats to Decimals and serializes unsupported types for DynamoDB."""
    if isinstance(val, float):
        import math
        if math.isnan(val) or math.isinf(val):
            return None
        return Decimal(str(round(val, 6)))
    if isinstance(val, dict):
        return {k: _to_dynamo_safe(v) for k, v in val.items() if _to_dynamo_safe(v) is not None}
    if isinstance(val, (list, tuple)):
        return [_to_dynamo_safe(item) for item in val if _to_dynamo_safe(item) is not None]
    return val


def _from_dynamo_safe(val: Any) -> Any:
    """Converts Decimals back to standard floats / ints."""
    if isinstance(val, Decimal):
        return float(val) if val % 1 else int(val)
    if isinstance(val, dict):
        return {k: _from_dynamo_safe(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_from_dynamo_safe(item) for item in val]
    return val


class DynamoMetaRepository:
    def __init__(self, table_name: str | None = None) -> None:
        self.settings = get_settings()
        self.table_name = table_name or self.settings.dynamodb_table
        self.client = get_dynamodb_client()
        self._ensure_table()

    def _ensure_table(self) -> None:
        try:
            self.client.describe_table(TableName=self.table_name)
        except ClientError:
            try:
                self.client.create_table(
                    TableName=self.table_name,
                    KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
                    AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
                    BillingMode="PAY_PER_REQUEST",
                )
                logger.info("Created DynamoDB table: %s", self.table_name)
            except Exception as e:
                logger.warning("Could not auto-create DynamoDB table %s: %s", self.table_name, e)

    def create_job(
        self,
        job_id: str,
        filename: str,
        file_size_bytes: int,
        checksum_sha256: str,
        user_id: int | None = None,
        s3_key: str | None = None,
    ) -> dict[str, Any]:
        """Initializes a new job entry in DynamoDB."""
        item = {
            "job_id": {"S": job_id},
            "filename": {"S": filename},
            "file_size_bytes": {"N": str(file_size_bytes)},
            "checksum_sha256": {"S": checksum_sha256},
            "status": {"S": "PENDING"},
            "created_at": {"S": datetime.now(UTC).isoformat()},
        }
        if user_id is not None:
            item["user_id"] = {"N": str(user_id)}
        if s3_key:
            item["s3_key"] = {"S": s3_key}

        try:
            self.client.put_item(TableName=self.table_name, Item=item)
            return {"job_id": job_id, "status": "PENDING"}
        except Exception as exc:
            logger.error("Failed to create job in DynamoDB: %s", exc)
            raise

    def update_job_status(
        self, job_id: str, status: str, error_message: str | None = None
    ) -> None:
        update_expr = "SET #s = :status, updated_at = :now"
        expr_names = {"#s": "status"}
        expr_values = {
            ":status": {"S": status},
            ":now": {"S": datetime.now(UTC).isoformat()},
        }
        if error_message:
            update_expr += ", error_message = :err"
            expr_values[":err"] = {"S": str(error_message)[:2000]}

        try:
            self.client.update_item(
                TableName=self.table_name,
                Key={"job_id": {"S": job_id}},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
            )
        except Exception as exc:
            logger.error("Failed to update job status in DynamoDB for %s: %s", job_id, exc)

    def record_job_results(
        self,
        job_id: str,
        formats_data: dict[str, Any],
        duration_ms: float,
        embedding_psnr: float | None = None,
        recommendations: dict[str, Any] | None = None,
    ) -> None:
        """Stores the complete analysis run results and metrics in DynamoDB."""
        now = datetime.now(UTC).isoformat()
        clean_formats = _to_dynamo_safe(formats_data)
        clean_recs = _to_dynamo_safe(recommendations or {})

        payload_json = json.dumps(
            {
                "formats": formats_data,
                "recommendations": recommendations or {},
            },
            default=str,
        )

        update_expr = (
            "SET #s = :status, completed_at = :now, duration_ms = :dur, "
            "results_json = :results"
        )
        expr_names = {"#s": "status"}
        expr_values = {
            ":status": {"S": "COMPLETED"},
            ":now": {"S": now},
            ":dur": {"N": str(round(duration_ms, 2))},
            ":results": {"S": payload_json},
        }

        if embedding_psnr is not None:
            update_expr += ", embedding_psnr = :emb_psnr"
            expr_values[":emb_psnr"] = {"N": str(round(embedding_psnr, 4))}

        try:
            self.client.update_item(
                TableName=self.table_name,
                Key={"job_id": {"S": job_id}},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
            )
        except Exception as exc:
            logger.error("Failed to record job results in DynamoDB for %s: %s", job_id, exc)
            raise

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Retrieves a single job record from DynamoDB."""
        try:
            res = self.client.get_item(
                TableName=self.table_name,
                Key={"job_id": {"S": job_id}},
            )
            item = res.get("Item")
            if not item:
                return None
            return self._unmarshal_item(item)
        except Exception as exc:
            logger.error("Failed to get job from DynamoDB: %s", exc)
            return None

    def list_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        """Lists recent jobs from DynamoDB using scan."""
        try:
            res = self.client.scan(TableName=self.table_name, Limit=limit)
            items = res.get("Items", [])
            return [self._unmarshal_item(i) for i in items]
        except Exception as exc:
            logger.error("Failed to list jobs from DynamoDB: %s", exc)
            return []

    def _unmarshal_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Converts DynamoDB attribute map to a standard Python dictionary."""
        out = {}
        for k, v in item.items():
            if "S" in v:
                out[k] = v["S"]
            elif "N" in v:
                n_str = v["N"]
                out[k] = float(n_str) if "." in n_str else int(n_str)
            elif "BOOL" in v:
                out[k] = v["BOOL"]
            elif "NULL" in v:
                out[k] = None
        if "results_json" in out:
            try:
                parsed = json.loads(out["results_json"])
                out["formats"] = parsed.get("formats", {})
                out["recommendations"] = parsed.get("recommendations", {})
            except Exception:
                pass
        return out
