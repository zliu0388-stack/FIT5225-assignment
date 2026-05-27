from db import DataStore
from handlers.common import error, ok


def handler(event, _context):
    try:
        params = event.get("queryStringParameters") or {}
        thumbnail_url = params.get("thumbnail_url")
        if not thumbnail_url:
            return error("thumbnail_url query param is required")

        store = DataStore()
        item = store.lookup_thumbnail(thumbnail_url)
        if not item:
            return error("thumbnail not found", status_code=404)

        return ok({"media_id": item["media_id"], "file_url": item["file_url"]})
    except Exception as exc:
        return error("internal error", status_code=500, extra={"detail": str(exc)})
