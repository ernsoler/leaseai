"""
Lambda: submit
Public endpoint — takes an s3_key, writes a pending stub to DynamoDB,
enqueues to SQS for async processing, and returns {analysis_id, user_id}.
No auth required.
"""
import os
import json
import uuid
import time
import re
import logging
from datetime import datetime, timezone

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
sqs_client = boto3.client("sqs")

ANALYSES_TABLE = os.environ["ANALYSES_TABLE"]
ANALYSES_QUEUE_URL = os.environ["ANALYSES_QUEUE_URL"]
USER_ID = os.environ.get("USER_ID", "demo")

# uploads/{YYYYMMDD-HHMMSS}/{uuid}.pdf
_S3_KEY_RE = re.compile(r"^uploads/\d{8}-\d{6}/[0-9a-f-]{36}\.pdf$")


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }


def handler(event: dict, context) -> dict:
    try:
        body = json.loads(event.get("body") or "{}")
        s3_key = body.get("s3_key")

        if not s3_key:
            return _response(400, {"error": "Missing s3_key"})

        if not _S3_KEY_RE.match(s3_key):
            return _response(400, {"error": "Invalid s3_key format"})

        analysis_id = str(uuid.uuid4())
        user_id = USER_ID
        created_at = datetime.now(timezone.utc).isoformat()

        table = dynamodb.Table(ANALYSES_TABLE)
        table.put_item(Item={
            "user_id": user_id,
            "analysis_id": analysis_id,
            "status": "pending",
            "created_at": created_at,
            "s3_key": s3_key,
            "expire_at": int(time.time()) + (30 * 24 * 3600),  # TTL: 30 days
        })
        logger.info("Created pending stub analysis_id=%s user_id=%s", analysis_id, user_id)

        message = {
            "analysis_id": analysis_id,
            "user_id": user_id,
            "s3_key": s3_key,
            "created_at": created_at,
        }
        sqs_client.send_message(
            QueueUrl=ANALYSES_QUEUE_URL,
            MessageBody=json.dumps(message),
        )
        logger.info("Enqueued analysis_id=%s to SQS", analysis_id)

        return _response(200, {"analysis_id": analysis_id, "user_id": user_id})

    except Exception:
        logger.exception("Unexpected error in submit handler")
        return _response(500, {"error": "Internal server error"})
