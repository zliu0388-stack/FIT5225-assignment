from db import DataStore
from handlers.common import error, ok, parse_body


def handler(event, _context):
    try:
        body = parse_body(event)
        urls = body.get("urls", [])
        if not isinstance(urls, list) or not urls:
            return error("urls is required and must be a non-empty list")

        store = DataStore()
        result = store.delete_media_by_urls(urls)
        return ok(result)
    except Exception as exc:
        return error("internal error", status_code=500, extra={"detail": str(exc)})
