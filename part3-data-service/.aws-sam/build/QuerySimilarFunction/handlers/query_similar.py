from db import DataStore
from handlers.common import error, ok, parse_body


def handler(event, _context):
    """
    该接口用于“按上传查询文件的标签查找相似文件”。
    当前版本假设上游 ML 已返回 tags_map，本接口只负责 DB 检索。
    """
    try:
        body = parse_body(event)
        tags_map = body.get("tags_map", {})
        if not isinstance(tags_map, dict) or not tags_map:
            return error("tags_map is required and must be a non-empty object")

        store = DataStore()
        items = store.query_by_tags(tags_map)
        return ok({"items": items})
    except Exception as exc:
        return error("internal error", status_code=500, extra={"detail": str(exc)})
