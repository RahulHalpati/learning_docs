"""The storage layer, using boto3 against AWS services.

The ONE thing that makes this run on LocalStack instead of real AWS is the
`endpoint_url` — set `AWS_ENDPOINT_URL=http://localhost:4566` (or pass it) and
every call goes to LocalStack. Unset it and the identical code talks to real AWS.
That's the whole trick: normal SDK code, one env var.
"""

from __future__ import annotations

import os
import time

import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE = os.environ.get("LINKS_TABLE", "links")
BUCKET = os.environ.get("BACKUP_BUCKET", "linkstash-backups")
QUEUE = os.environ.get("EVENTS_QUEUE", "linkstash-events")


def _endpoint() -> str | None:
    # LocalStack exposes everything on one endpoint; real AWS uses none (SDK default).
    return os.environ.get("AWS_ENDPOINT_URL") or None


def client(service: str):
    return boto3.client(service, region_name=REGION, endpoint_url=_endpoint())


def resource(service: str):
    return boto3.resource(service, region_name=REGION, endpoint_url=_endpoint())


class LinkStore:
    """CRUD for short links, backed by DynamoDB, S3, and SQS."""

    def __init__(self):
        self.ddb = resource("dynamodb").Table(TABLE)
        self.s3 = client("s3")
        self.sqs = client("sqs")

    def put(self, slug: str, url: str) -> None:
        self.ddb.put_item(Item={"slug": slug, "url": url, "created": int(time.time())})
        self._emit(f"created:{slug}")

    def get(self, slug: str) -> str | None:
        item = self.ddb.get_item(Key={"slug": slug}).get("Item")
        return item["url"] if item else None

    def backup(self, slug: str, url: str) -> str:
        """Write a backup object to S3; return its key."""
        key = f"links/{slug}.txt"
        self.s3.put_object(Bucket=BUCKET, Key=key, Body=url.encode())
        return key

    def _emit(self, message: str) -> None:
        q = self.sqs.get_queue_url(QueueName=QUEUE)["QueueUrl"]
        self.sqs.send_message(QueueUrl=q, MessageBody=message)

    def drain_events(self) -> list[str]:
        """Read (and delete) any pending event messages."""
        q = self.sqs.get_queue_url(QueueName=QUEUE)["QueueUrl"]
        out = []
        resp = self.sqs.receive_message(QueueUrl=q, MaxNumberOfMessages=10, WaitTimeSeconds=1)
        for m in resp.get("Messages", []):
            out.append(m["Body"])
            self.sqs.delete_message(QueueUrl=q, ReceiptHandle=m["ReceiptHandle"])
        return out
