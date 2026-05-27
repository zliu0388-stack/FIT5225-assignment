from db import DataStore
from handlers.common import error, ok, parse_body

REQUIRED_FIELDS = [
    "owner_sub",
    "bucket",
    "object_key",
    "file_url",
    "media_type",
    "checksum_sha256",
]


def handler(event, _context):
    try:
        body = parse_body(event)
        missing = [f for f in REQUIRED_FIELDS if not body.get(f)]
        if missing:
            return error("missing required fields", extra={"fields": missing})

        if body.get("media_type") not in {"image", "video"}:
            return error("media_type must be image or video")

        store = DataStore()
        item = store.upsert_media(body)
        return ok({"message": "upsert success", "item": item}, status_code=201)
    except Exception as exc:
        return error("internal error", status_code=500, extra={"detail": str(exc)})
