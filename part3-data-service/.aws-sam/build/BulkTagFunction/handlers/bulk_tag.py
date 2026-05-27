from db import DataStore
from handlers.common import error, ok, parse_body


def handler(event, _context):
    try:
        body = parse_body(event)
        urls = body.get("urls", [])
        tags = body.get("tags", {})
        operation = body.get("operation")

        if not isinstance(urls, list) or not urls:
            return error("urls is required and must be a non-empty list")
        if not isinstance(tags, dict) or not tags:
            return error("tags is required and must be a non-empty object")
        if operation not in (0, 1):
            return error("operation must be 0(remove) or 1(add)")

        store = DataStore()
        updated = []
        not_found = []
        for url in urls:
            item = store.get_media_by_file_url(url)
            if not item:
                not_found.append(url)
                continue
            new_item = store.update_tags(item, tags, operation)
            updated.append(
                {
                    "media_id": new_item["media_id"],
                    "file_url": new_item["file_url"],
                    "tags_map": new_item["tags_map"],
                    "tags_version": new_item["tags_version"],
                }
            )

        return ok({"updated": updated, "not_found": not_found})
    except Exception as exc:
        return error("internal error", status_code=500, extra={"detail": str(exc)})
