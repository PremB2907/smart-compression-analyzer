"""SQS task queue service for asynchronous compression jobs."""

from __future__ import annotations

import json
import logging
from typing import Any

from botocore.exceptions import ClientError

from app.config import get_settings
from app.services.cloud.client import get_sqs_client

logger = logging.getLogger(__name__)


class SQSQueueService:
    def __init__(self, queue_name: str | None = None) -> None:
        self.settings = get_settings()
        self.queue_name = queue_name or self.settings.sqs_queue_name
        self.sqs = get_sqs_client()
        self.queue_url = self._get_or_create_queue()

    def _get_or_create_queue(self) -> str:
        try:
            res = self.sqs.get_queue_url(QueueName=self.queue_name)
            return res["QueueUrl"]
        except ClientError:
            try:
                res = self.sqs.create_queue(
                    QueueName=self.queue_name,
                    Attributes={
                        "VisibilityTimeout": "300",
                        "MessageRetentionPeriod": "86400",
                    },
                )
                logger.info("Created SQS queue %s: %s", self.queue_name, res.get("QueueUrl"))
                return res["QueueUrl"]
            except Exception as e:
                logger.warning("Could not auto-create SQS queue %s: %s", self.queue_name, e)
                return ""

    def send_job(self, payload: dict[str, Any]) -> str:
        """Publishes a compression task to SQS."""
        if not self.queue_url:
            self.queue_url = self._get_or_create_queue()
        message_body = json.dumps(payload)
        try:
            res = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=message_body,
            )
            return res.get("MessageId", "")
        except Exception as exc:
            logger.error("Failed to send message to SQS queue %s: %s", self.queue_url, exc)
            raise

    def receive_jobs(
        self, max_messages: int = 1, wait_time_sec: int = 5
    ) -> list[dict[str, Any]]:
        """Polls SQS for pending compression jobs."""
        if not self.queue_url:
            self.queue_url = self._get_or_create_queue()
            if not self.queue_url:
                return []
        try:
            res = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time_sec,
                VisibilityTimeout=300,
            )
            messages = res.get("Messages", [])
            out = []
            for msg in messages:
                try:
                    body = json.loads(msg["Body"])
                    out.append(
                        {
                            "message_id": msg.get("MessageId"),
                            "receipt_handle": msg.get("ReceiptHandle"),
                            "payload": body,
                        }
                    )
                except Exception as json_err:
                    logger.warning("Failed to decode SQS message %s: %s", msg.get("MessageId"), json_err)
            return out
        except Exception as exc:
            logger.error("Failed to receive messages from SQS queue %s: %s", self.queue_url, exc)
            return []

    def delete_job(self, receipt_handle: str) -> None:
        """Deletes processed message from SQS."""
        if not self.queue_url:
            return
        try:
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
            )
        except Exception as exc:
            logger.error("Failed to delete SQS message: %s", exc)

    def get_queue_attributes(self) -> dict[str, str]:
        if not self.queue_url:
            return {}
        try:
            res = self.sqs.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
            )
            return res.get("Attributes", {})
        except Exception as exc:
            logger.warning("Failed to fetch SQS queue attributes: %s", exc)
            return {}
