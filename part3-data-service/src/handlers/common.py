import json
from decimal import Decimal
from typing import Any, Dict, Optional


def parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get("body")
    if body is None:
        return {}
    if isinstance(body, dict):
        return body
    if isinstance(body, str) and body.strip():
        return json.loads(body)
    return {}


def _json_default(value: Any):
    if isinstance(value, Decimal):
        # DynamoDB numbers are Decimal; keep integers stable for clients.
        return int(value) if value % 1 == 0 else float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def ok(payload: Dict[str, Any], status_code: int = 200) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(payload, ensure_ascii=False, default=_json_default),
    }


def error(message: str, status_code: int = 400, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = {"error": message}
    if extra:
        payload.update(extra)
    return ok(payload, status_code=status_code)
