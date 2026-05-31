import json
import urllib.parse

import requests

from config import Settings
from inference.pipeline import infer_tags_from_s3_object
from utils.media_utils import create_thumbnail, detect_media_type, read_s3_bytes


def _json(status_code: int, payload: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def _upsert_to_part3(item: dict) -> tuple[bool, str]:
    if not Settings.part3_upsert_url:
        return False, "PART3_UPSERT_URL is empty"

    headers = {"Content-Type": "application/json"}

    if Settings.part3_auth_token:
        headers["Authorization"] = f"Bearer {Settings.part3_auth_token}"

    payload = {
        "owner_sub": "unknown-user",
        "owner_email": "",
        "bucket": item["bucket"],
        "object_key": item["object_key"],
        "file_url": item["file_url"],
        "thumbnail_url": item.get("thumbnail_url"),
        "media_type": item["media_type"],
        "checksum_sha256": item["checksum_sha256"],
        "tags_map": item["tags_map"],
        "model_name": item["model_name"],
        "model_version": item["model_version"],
    }

    response = requests.post(
        Settings.part3_upsert_url,
        json=payload,
        headers=headers,
        timeout=20,
    )

    if not response.ok:
        return False, f"HTTP {response.status_code}: {response.text[:300]}"

    return True, response.text[:300]


def handler(event, _context):
    try:
        records = event.get("Records", [])

        if not records:
            return _json(400, {"error": "no records in S3 event"})

        results = []

        for record in records:
            bucket = record["s3"]["bucket"]["name"]
            key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

            if not key.startswith(Settings.upload_prefix):
                results.append({"key": key, "status": "skipped_wrong_prefix"})
                continue

            media_type = detect_media_type(key)

            if media_type == "unsupported":
                results.append({"key": key, "status": "skipped_unsupported_type"})
                continue

            inferred = infer_tags_from_s3_object(bucket, key)

            thumbnail_url = None

            if media_type == "image":
                image_bytes = read_s3_bytes(bucket, key)
                _, thumbnail_url = create_thumbnail(
                    bucket=bucket,
                    object_key=key,
                    image_bytes=image_bytes,
                )

            inferred["thumbnail_url"] = thumbnail_url

            ok, message = _upsert_to_part3(inferred)

            results.append(
                {
                    "key": key,
                    "media_type": media_type,
                    "checksum_sha256": inferred["checksum_sha256"],
                    "thumbnail_url": thumbnail_url,
                    "tags_map": inferred["tags_map"],
                    "upsert_ok": ok,
                    "upsert_message": message,
                }
            )

        return _json(200, {"message": "processed", "results": results})

    except Exception as exc:
        return _json(500, {"error": "auto-tag failed", "detail": str(exc)})
