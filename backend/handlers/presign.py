"""
Lambda: get-presigned-url
Generates a presigned S3 PUT URL for direct PDF upload from the browser.
Public endpoint — API Gateway usage plan handles rate limiting.
"""
import os
import json
import uuid
import logging
from datetime import datetime, timezone
import boto3

from backend.lib.constants import ContentType

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")

BUCKET_NAME = os.environ["BUCKET_NAME"]
PRESIGN_EXPIRY = 300       # 5 minutes
MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


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
        content_type = body.get("content_type", ContentType.PDF)

        if content_type != ContentType.PDF:
            return _response(400, {"error": "Only PDF files are accepted"})

        date_prefix = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        file_id = str(uuid.uuid4())
        s3_key = f"uploads/{date_prefix}/{file_id}.pdf"

        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": s3_key,
                "ContentType": content_type,
                "ContentLength": MAX_SIZE_BYTES,
            },
            ExpiresIn=PRESIGN_EXPIRY,
        )

        logger.info("Generated presigned URL key=%s", s3_key)
        return _response(200, {"upload_url": presigned_url, "s3_key": s3_key})

    except Exception:
        logger.exception("Error generating presigned URL")
        return _response(500, {"error": "Internal server error"})
