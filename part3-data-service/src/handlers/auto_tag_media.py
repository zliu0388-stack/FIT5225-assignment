import json
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
rekognition_client = boto3.client("rekognition", region_name=Settings.aws_region)


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

            if media_type == "image":
                tags_map = _detect_image_tags(bucket, object_key)
            else:
                local_path = _download_from_s3(bucket, object_key)
                try:
                    tags_map = _detect_video_tags(local_path)
                finally:
                    try:
                        os.remove(local_path)
                    except OSError:
                        pass

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

        return ok({
            "message": "auto tagging success",
            "items": saved_items
        }, status_code=201)

    except Exception as exc:
        return error("auto tagging failed", status_code=500, extra={"detail": str(exc)})


def _parse_event(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    # API Gateway event
    if "body" in event:
        body = event["body"]

        if isinstance(body, str):
            body = json.loads(body or "{}")

        return _parse_event(body)

    # Standard S3 event
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

    # Custom direct event
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


def _detect_image_tags(bucket: str, object_key: str) -> Dict[str, int]:
    response = rekognition_client.detect_labels(
        Image={
            "S3Object": {
                "Bucket": bucket,
                "Name": object_key,
            }
        },
        MaxLabels=20,
        MinConfidence=60,
    )

    counter = Counter()

    for label in response.get("Labels", []):
        tag = _normalise_tag(label.get("Name", ""))
        if tag:
            counter[tag] += 1

    return dict(counter)


def _detect_video_tags(video_path: str) -> Dict[str, int]:
    import cv2

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
                with open(frame_path, "rb") as image_file:
                    response = rekognition_client.detect_labels(
                        Image={"Bytes": image_file.read()},
                        MaxLabels=20,
                        MinConfidence=60,
                    )

                for label in response.get("Labels", []):
                    tag = _normalise_tag(label.get("Name", ""))
                    if tag:
                        counter[tag] += 1

            finally:
                try:
                    os.remove(frame_path)
                except OSError:
                    pass

        frame_index += 1

    cap.release()
    return dict(counter)


def _download_from_s3(bucket: str, object_key: str) -> str:
    suffix = Path(object_key).suffix or ".tmp"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        local_path = tmp.name

    s3_client.download_file(bucket, object_key, local_path)
    return local_path


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
