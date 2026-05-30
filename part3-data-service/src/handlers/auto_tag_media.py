import os
import tempfile
import urllib.parse
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import boto3

from config import Settings
from db import DataStore
from handlers.common import error, ok


s3_client = boto3.client("s3", region_name=Settings.aws_region)
_model = None


def handler(event, _context):
    try:
        records = _parse_event(event)
        if not records:
            return error("no valid media record found in event")

        store = DataStore()
        saved_items = []

        for record in records:
            bucket = record["bucket"]
            object_key = record["object_key"]
            media_type = record.get("media_type") or _infer_media_type(object_key)

            if media_type not in {"image", "video"}:
                return error("media_type must be image or video")

            local_path = _download_from_s3(bucket, object_key)

            if media_type == "image":
                tags_map = _detect_image_tags(local_path)
            else:
                tags_map = _detect_video_tags(local_path)

            item = {
                "owner_sub": record.get("owner_sub", "unknown-user"),
                "owner_email": record.get("owner_email", ""),
                "bucket": bucket,
                "object_key": object_key,
                "file_url": record.get("file_url") or _build_s3_url(bucket, object_key),
                "thumbnail_url": record.get("thumbnail_url"),
                "media_type": media_type,
                "checksum_sha256": record.get("checksum_sha256", "unknown"),
                "tags_map": tags_map,
                "model_name": Settings.model_name,
                "model_version": Settings.model_version,
                "status": "ACTIVE",
            }

            saved_items.append(store.upsert_media(item))

            try:
                os.remove(local_path)
            except OSError:
                pass

        return ok({
            "message": "auto tagging success",
            "items": saved_items
        }, status_code=201)

    except Exception as exc:
        return error("auto tagging failed", status_code=500, extra={"detail": str(exc)})


def _parse_event(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "Records" in event:
        records = []
        for record in event.get("Records", []):
            s3_info = record.get("s3", {})
            bucket = s3_info.get("bucket", {}).get("name")
            key = s3_info.get("object", {}).get("key")

            if bucket and key:
                records.append({
                    "bucket": bucket,
                    "object_key": urllib.parse.unquote_plus(key),
                    "owner_sub": record.get("owner_sub", "unknown-user"),
                    "owner_email": record.get("owner_email", ""),
                    "checksum_sha256": record.get("checksum_sha256", "unknown"),
                    "thumbnail_url": record.get("thumbnail_url"),
                    "file_url": record.get("file_url"),
                    "media_type": record.get("media_type"),
                })

        return records

    if "bucket" in event and ("object_key" in event or "key" in event):
        return [{
            "bucket": event["bucket"],
            "object_key": event.get("object_key") or event.get("key"),
            "owner_sub": event.get("owner_sub", "unknown-user"),
            "owner_email": event.get("owner_email", ""),
            "checksum_sha256": event.get("checksum_sha256", "unknown"),
            "thumbnail_url": event.get("thumbnail_url"),
            "file_url": event.get("file_url"),
            "media_type": event.get("media_type"),
        }]

    return []


def _download_from_s3(bucket: str, object_key: str) -> str:
    suffix = Path(object_key).suffix or ".tmp"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        local_path = tmp.name

    s3_client.download_file(bucket, object_key, local_path)
    return local_path


def _get_model():
    global _model

    if _model is None:
        from ultralytics import YOLO
        _model = YOLO(Settings.model_path)

    return _model


def _detect_image_tags(image_path: str) -> Dict[str, int]:
    model = _get_model()
    results = model(image_path)

    counter = Counter()

    for result in results:
        names = result.names

        if result.boxes is None:
            continue

        for cls_id in result.boxes.cls:
            tag = _normalise_tag(names[int(cls_id)])
            if tag:
                counter[tag] += 1

    return dict(counter)


def _detect_video_tags(video_path: str) -> Dict[str, int]:
    import cv2

    model = _get_model()
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise ValueError("unable to open video file")

    fps = cap.get(cv2.CAP_PROP_FPS) or 1
    frame_interval = max(1, int(fps))

    counter = Counter()
    frame_index = 0

    while True:
        ok_frame, frame = cap.read()
        if not ok_frame:
            break

        if frame_index % frame_interval == 0:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                frame_path = tmp.name

            cv2.imwrite(frame_path, frame)

            try:
                image_tags = _detect_image_tags(frame_path)
                counter.update(image_tags)
            finally:
                try:
                    os.remove(frame_path)
                except OSError:
                    pass

        frame_index += 1

    cap.release()
    return dict(counter)


def _normalise_tag(tag: str) -> str:
    return str(tag).strip().lower().replace(" ", "_")


def _infer_media_type(object_key: str) -> str:
    ext = Path(object_key).suffix.lower()

    if ext in {".jpg", ".jpeg", ".png", ".webp"}:
        return "image"

    if ext in {".mp4", ".mov", ".avi", ".mkv"}:
        return "video"

    raise ValueError(f"cannot infer media type from extension: {ext}")


def _build_s3_url(bucket: str, object_key: str) -> str:
    encoded_key = urllib.parse.quote(object_key)
    return f"https://{bucket}.s3.{Settings.aws_region}.amazonaws.com/{encoded_key}"
