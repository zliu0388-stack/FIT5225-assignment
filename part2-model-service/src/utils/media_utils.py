import hashlib
import io
from pathlib import Path

import boto3
from PIL import Image

from config import Settings

s3 = boto3.client("s3", region_name=Settings.aws_region)


def read_s3_bytes(bucket: str, key: str) -> bytes:
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def detect_media_type(key: str) -> str:
    lower = key.lower()
    if lower.endswith((".jpg", ".jpeg", ".png", ".webp")):
        return "image"
    if lower.endswith((".mp4", ".mov", ".avi", ".mkv")):
        return "video"
    return "unsupported"


def make_s3_url(bucket: str, key: str) -> str:
    return f"https://{bucket}.s3.{Settings.aws_region}.amazonaws.com/{key}"


def build_thumbnail_key(object_key: str) -> str:
    stem = Path(object_key).stem
    return f"{Settings.thumbnail_prefix}{stem}_thumb.jpg"


def create_thumbnail(bucket: str, object_key: str, image_bytes: bytes) -> tuple[str, str]:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image.thumbnail((300, 300))

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=80, optimize=True)
    output.seek(0)

    thumbnail_key = build_thumbnail_key(object_key)

    s3.put_object(
        Bucket=bucket,
        Key=thumbnail_key,
        Body=output.getvalue(),
        ContentType="image/jpeg",
    )

    return thumbnail_key, make_s3_url(bucket, thumbnail_key)
