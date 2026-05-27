from db import DataStore
from handlers.common import error, ok, parse_body


def handler(event, _context):
    try:
        body = parse_body(event)
        tags = body.get("tags", {})
        if not isinstance(tags, dict) or not tags:
            return error("tags is required and must be an object, e.g. {\"koala\":2}")

        store = DataStore()
        items = store.query_by_tags(tags)
        return ok({"items": items})
    except Exception as exc:
        return error("internal error", status_code=500, extra={"detail": str(exc)})
