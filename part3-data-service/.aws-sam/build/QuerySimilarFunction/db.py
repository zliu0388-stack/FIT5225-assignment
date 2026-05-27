import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Attr, Key

from config import Settings


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class DataStore:
    def __init__(self) -> None:
        resource = boto3.resource("dynamodb", region_name=Settings.aws_region)
        self.media_table = resource.Table(Settings.media_table)
        self.tag_index_table = resource.Table(Settings.tag_index_table)
        self.thumb_lookup_table = resource.Table(Settings.thumb_lookup_table)
        self.s3 = boto3.client("s3", region_name=Settings.aws_region)

    def upsert_media(self, item: Dict) -> Dict:
        media_id = item.get("media_id") or str(uuid.uuid4())
        created_at = item.get("created_at") or _now_iso()
        updated_at = _now_iso()
        tags_map = {
            str(k).strip().lower(): int(v)
            for k, v in (item.get("tags_map") or {}).items()
            if str(k).strip() and int(v) > 0
        }

        media_item = {
            "media_id": media_id,
            "owner_sub": item["owner_sub"],
            "owner_email": item.get("owner_email", ""),
            "bucket": item["bucket"],
            "object_key": item["object_key"],
            "file_url": item["file_url"],
            "thumbnail_url": item.get("thumbnail_url"),
            "media_type": item["media_type"],
            "checksum_sha256": item["checksum_sha256"],
            "tags_map": tags_map,
            "tags_version": int(item.get("tags_version", 1)),
            "model_name": item.get("model_name", "unknown-model"),
            "model_version": item.get("model_version", "unknown"),
            "status": item.get("status", "ACTIVE"),
            "created_at": created_at,
            "updated_at": updated_at,
        }

        self.media_table.put_item(Item=media_item)

        if media_item["thumbnail_url"]:
            self.thumb_lookup_table.put_item(
                Item={
                    "thumbnail_url": media_item["thumbnail_url"],
                    "media_id": media_id,
                    "file_url": media_item["file_url"],
                    "owner_sub": media_item["owner_sub"],
                    "created_at": created_at,
                }
            )

        # 直接覆盖同 media_id 的标签索引
        for tag, count in tags_map.items():
            self.tag_index_table.put_item(
                Item={
                    "tag": tag,
                    "media_id": media_id,
                    "count": int(count),
                    "media_type": media_item["media_type"],
                    "file_url": media_item["file_url"],
                    "thumbnail_url": media_item.get("thumbnail_url"),
                    "updated_at": updated_at,
                }
            )

        return media_item

    def query_by_tags(self, tags: Dict[str, int]) -> List[Dict]:
        normalized = {
            str(tag).strip().lower(): max(1, int(min_count))
            for tag, min_count in tags.items()
            if str(tag).strip()
        }
        if not normalized:
            return []

        result_sets = []
        count_maps_by_media = {}
        for tag, min_count in normalized.items():
            resp = self.tag_index_table.query(
                KeyConditionExpression=Key("tag").eq(tag),
                FilterExpression=Attr("count").gte(min_count),
            )
            items = resp.get("Items", [])
            ids = {i["media_id"] for i in items}
            result_sets.append(ids)
            for i in items:
                media_id = i["media_id"]
                count_maps_by_media.setdefault(media_id, {})
                count_maps_by_media[media_id][tag] = i.get("count", 0)

        if not result_sets:
            return []

        matched_ids = set.intersection(*result_sets)
        if not matched_ids:
            return []

        results = []
        for media_id in matched_ids:
            resp = self.media_table.get_item(Key={"media_id": media_id})
            item = resp.get("Item")
            if not item or item.get("status") == "DELETED":
                continue
            results.append(
                {
                    "media_id": media_id,
                    "media_type": item.get("media_type"),
                    "thumbnail_url": item.get("thumbnail_url"),
                    "file_url": item.get("file_url"),
                    "count_map": count_maps_by_media.get(media_id, {}),
                }
            )
        return results

    def lookup_thumbnail(self, thumbnail_url: str) -> Optional[Dict]:
        resp = self.thumb_lookup_table.get_item(Key={"thumbnail_url": thumbnail_url})
        return resp.get("Item")

    def get_media_by_file_url(self, file_url: str) -> Optional[Dict]:
        resp = self.media_table.query(
            IndexName="GSI2_file_url",
            KeyConditionExpression=Key("file_url").eq(file_url),
            Limit=1,
        )
        items = resp.get("Items", [])
        if not items:
            return None
        return items[0]

    def update_tags(self, media_item: Dict, tags: Dict[str, int], operation: int) -> Dict:
        current = media_item.get("tags_map", {})
        updated = dict(current)

        for tag, delta in tags.items():
            n_tag = str(tag).strip().lower()
            if not n_tag:
                continue
            n_delta = max(1, int(delta))
            old = int(updated.get(n_tag, 0))
            if operation == 1:
                new_count = old + n_delta
            else:
                new_count = max(0, old - n_delta)

            if new_count == 0:
                updated.pop(n_tag, None)
                self.tag_index_table.delete_item(
                    Key={"tag": n_tag, "media_id": media_item["media_id"]}
                )
            else:
                updated[n_tag] = new_count
                self.tag_index_table.put_item(
                    Item={
                        "tag": n_tag,
                        "media_id": media_item["media_id"],
                        "count": new_count,
                        "media_type": media_item["media_type"],
                        "file_url": media_item["file_url"],
                        "thumbnail_url": media_item.get("thumbnail_url"),
                        "updated_at": _now_iso(),
                    }
                )

        new_version = int(media_item.get("tags_version", 1)) + 1
        self.media_table.update_item(
            Key={"media_id": media_item["media_id"]},
            UpdateExpression="SET tags_map = :tags, tags_version = :ver, updated_at = :ts",
            ExpressionAttributeValues={
                ":tags": updated,
                ":ver": new_version,
                ":ts": _now_iso(),
            },
        )
        media_item["tags_map"] = updated
        media_item["tags_version"] = new_version
        return media_item

    def delete_media_by_urls(self, urls: List[str]) -> Dict[str, List[str]]:
        deleted = []
        not_found = []

        for file_url in urls:
            item = self.get_media_by_file_url(file_url)
            if not item:
                not_found.append(file_url)
                continue

            media_id = item["media_id"]

            # 删除 S3 文件（最佳努力，不让单个失败阻塞 DB 清理）
            try:
                self.s3.delete_object(Bucket=item["bucket"], Key=item["object_key"])
            except Exception:
                pass

            thumb_url = item.get("thumbnail_url")
            if thumb_url:
                try:
                    thumb_key = thumb_url.split(".amazonaws.com/")[-1]
                    self.s3.delete_object(Bucket=item["bucket"], Key=thumb_key)
                except Exception:
                    pass
                self.thumb_lookup_table.delete_item(Key={"thumbnail_url": thumb_url})

            for tag in (item.get("tags_map") or {}).keys():
                self.tag_index_table.delete_item(Key={"tag": tag, "media_id": media_id})

            self.media_table.update_item(
                Key={"media_id": media_id},
                UpdateExpression="SET #s = :deleted, updated_at = :ts",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":deleted": "DELETED", ":ts": _now_iso()},
            )
            deleted.append(file_url)

        return {"deleted": deleted, "not_found": not_found}
