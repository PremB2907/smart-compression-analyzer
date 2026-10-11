"""AWS / Floci client provider and health diagnostics."""

from __future__ import annotations

import logging
import time
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError

from app.config import get_settings

logger = logging.getLogger(__name__)


def _client_config() -> Config:
    return Config(
        retries={"max_attempts": 3, "mode": "standard"},
        connect_timeout=2.0,
        read_timeout=5.0,
        s3={"addressing_style": "path"},
    )


def get_s3_client():
    settings = get_settings()
    endpoint = settings.aws_endpoint_url if settings.cloud_mode == "floci" else None
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        endpoint_url=endpoint,
        config=_client_config(),
    )


def get_dynamodb_client():
    settings = get_settings()
    endpoint = settings.aws_endpoint_url if settings.cloud_mode == "floci" else None
    return boto3.client(
        "dynamodb",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        endpoint_url=endpoint,
        config=_client_config(),
    )


def get_sqs_client():
    settings = get_settings()
    endpoint = settings.aws_endpoint_url if settings.cloud_mode == "floci" else None
    return boto3.client(
        "sqs",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        endpoint_url=endpoint,
        config=_client_config(),
    )


def check_floci_health() -> dict[str, Any]:
    """Inspects the reachability of S3, DynamoDB, and SQS on the configured Floci endpoint."""
    settings = get_settings()
    results: dict[str, Any] = {
        "cloud_mode": settings.cloud_mode,
        "endpoint_url": settings.aws_endpoint_url,
        "region": settings.aws_region,
        "overall_status": "healthy",
        "services": {},
    }

    if settings.cloud_mode != "floci":
        results["overall_status"] = "local_mode"
        results["message"] = "Application is running in LOCAL mode (bypassing Floci)"
        return results

    # 1. Probe S3
    s3_start = time.perf_counter()
    try:
        s3 = get_s3_client()
        s3.list_buckets()
        s3_latency = round((time.perf_counter() - s3_start) * 1000, 2)
        results["services"]["s3"] = {
            "status": "connected",
            "latency_ms": s3_latency,
            "bucket": settings.s3_bucket,
        }
    except (EndpointConnectionError, ClientError, Exception) as exc:
        results["services"]["s3"] = {"status": "error", "error": str(exc)}
        results["overall_status"] = "degraded"

    # 2. Probe DynamoDB
    ddb_start = time.perf_counter()
    try:
        ddb = get_dynamodb_client()
        ddb.list_tables()
        ddb_latency = round((time.perf_counter() - ddb_start) * 1000, 2)
        results["services"]["dynamodb"] = {
            "status": "connected",
            "latency_ms": ddb_latency,
            "table": settings.dynamodb_table,
        }
    except (EndpointConnectionError, ClientError, Exception) as exc:
        results["services"]["dynamodb"] = {"status": "error", "error": str(exc)}
        results["overall_status"] = "degraded"

    # 3. Probe SQS
    sqs_start = time.perf_counter()
    try:
        sqs = get_sqs_client()
        sqs.list_queues()
        sqs_latency = round((time.perf_counter() - sqs_start) * 1000, 2)
        results["services"]["sqs"] = {
            "status": "connected",
            "latency_ms": sqs_latency,
            "queue_name": settings.sqs_queue_name,
        }
    except (EndpointConnectionError, ClientError, Exception) as exc:
        results["services"]["sqs"] = {"status": "error", "error": str(exc)}
        results["overall_status"] = "degraded"

    if all(s.get("status") == "error" for s in results["services"].values()):
        results["overall_status"] = "unreachable"

    return results


def init_floci_resources() -> dict[str, str]:
    """Ensures S3 bucket, DynamoDB table, and SQS queue are provisioned in Floci."""
    settings = get_settings()
    created = {}

    # Provision S3 Bucket
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=settings.s3_bucket)
        created["s3_bucket"] = f"exists: {settings.s3_bucket}"
    except Exception:
        try:
            if settings.aws_region == "us-east-1":
                s3.create_bucket(Bucket=settings.s3_bucket)
            else:
                s3.create_bucket(
                    Bucket=settings.s3_bucket,
                    CreateBucketConfiguration={"LocationConstraint": settings.aws_region},
                )
            created["s3_bucket"] = f"created: {settings.s3_bucket}"
        except Exception as e:
            created["s3_bucket"] = f"error: {e}"

    # Provision DynamoDB Table
    ddb = get_dynamodb_client()
    try:
        ddb.describe_table(TableName=settings.dynamodb_table)
        created["dynamodb_table"] = f"exists: {settings.dynamodb_table}"
    except Exception:
        try:
            ddb.create_table(
                TableName=settings.dynamodb_table,
                KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            created["dynamodb_table"] = f"created: {settings.dynamodb_table}"
        except Exception as e:
            created["dynamodb_table"] = f"error: {e}"

    # Provision SQS Queue
    sqs = get_sqs_client()
    try:
        res = sqs.create_queue(QueueName=settings.sqs_queue_name)
        created["sqs_queue"] = f"ready: {res.get('QueueUrl')}"
    except Exception as e:
        created["sqs_queue"] = f"error: {e}"

    return created
