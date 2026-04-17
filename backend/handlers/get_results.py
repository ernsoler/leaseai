"""
Lambda: get-results
Public endpoint — fetches a stored lease analysis by analysis_id + user_id.
Ownership is enforced via the DynamoDB composite key (user_id, analysis_id).
"""
import os
import json
import decimal
import logging
import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
ANALYSES_TABLE = os.environ["ANALYSES_TABLE"]


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(
            body,
            default=lambda x: float(x) if isinstance(
                x, decimal.Decimal) else str(x),
        ),
    }


def handler(event: dict, context) -> dict:
    analysis_id = (event.get("pathParameters") or {}).get("id")
    if not analysis_id:
        return _response(400, {"error": "Missing analysis id"})

    params = event.get("queryStringParameters") or {}
    user_id = params.get("user_id")

    if not user_id:
        return _response(400, {"error": "Missing user_id query parameter"})

    table = dynamodb.Table(ANALYSES_TABLE)
    result = table.get_item(
        Key={"user_id": user_id, "analysis_id": analysis_id})
    item = result.get("Item")
    if not item:
        return _response(404, {"error": f"Analysis {analysis_id} not found"})

    # Strip internal fields before returning to public callers
    item.pop("s3_key", None)

    logger.info("Fetched analysis=%s user=%s", analysis_id, user_id)
    return _response(200, item)
