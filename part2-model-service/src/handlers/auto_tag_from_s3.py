import json
import urllib.parse

import requests

from config import Settings
from inference.pipeline import infer_tags_from_s3_object


def _json(status_code: int, payload: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def _upsert_to_part3(item: dict) -> tuple[bool, str]:
    if not Settings.part3_upsert_url:
        return False, "PART3_UPSERT_URL is empty; skip writeback"

    headers = {"Content-Type": "application/json"}
    if Settings.part3_auth_token:
        headers["Authorization"] = f"Bearer {Settings.part3_auth_token}"

    # owner_sub may be unavailable in raw S3 events; keep placeholder for framework.
    payload = {
        "owner_sub": "unknown-user",
        "owner_email": "",
        "bucket": item["bucket"],
        "object_key": item["object_key"],
        "file_url": item["file_url"],
        "thumbnail_url": None,
        "media_type": item["media_type"],
        "checksum_sha256": item["checksum_sha256"],
        "tags_map": item["tags_map"],
        "model_name": item["model_name"],
        "model_version": item["model_version"],
        "status": "ACTIVE",
    }

    resp = requests.post(
        Settings.part3_upsert_url, json=payload, headers=headers, timeout=20
    )
    if not resp.ok:
        return False, f"Part3 upsert failed: HTTP {resp.status_code} {resp.text[:300]}"
    return True, "ok"


def handler(event, _context):
    try:
        records = event.get("Records", [])
        if not records:
            return _json(400, {"error": "no records in S3 event"})

        results = []
        for record in records:
            bucket = record["s3"]["bucket"]["name"]
            key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

            # Framework currently focuses on images first.
            if not key.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                results.append({"key": key, "status": "skipped_non_image"})
                continue

            inferred = infer_tags_from_s3_object(bucket, key)
            ok, msg = _upsert_to_part3(inferred)
            results.append(
                {
                    "key": key,
                    "tags_map": inferred["tags_map"],
                    "upsert_ok": ok,
                    "upsert_message": msg,
                }
            )

        return _json(200, {"message": "processed", "results": results})

    except Exception as exc:
        return _json(500, {"error": "auto-tag failed", "detail": str(exc)})
