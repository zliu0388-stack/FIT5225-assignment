import hashlib
import io
import tempfile
from pathlib import Path

import boto3
import cv2
from PIL import Image

from config import Settings

s3_client = boto3.client("s3", region_name=Settings.aws_region)


def read_s3_bytes(bucket: str, key: str) -> bytes:
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()


def download_s3_object(bucket: str, key: str) -> str:
    suffix = Path(key).suffix.lower() or ".jpg"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        local_path = tmp.name

    s3_client.download_file(bucket, key, local_path)
    return local_path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()

    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            h.update(chunk)

    return h.hexdigest()


def detect_media_type(key: str) -> str:
    lower_key = key.lower()

    if lower_key.endswith((".jpg", ".jpeg", ".png", ".webp")):
        return "image"

    if lower_key.endswith((".mp4", ".mov", ".avi", ".mkv")):
        return "video"

    return "unsupported"


def make_s3_url(bucket: str, key: str) -> str:
    return f"https://{bucket}.s3.{Settings.aws_region}.amazonaws.com/{key}"


def build_thumbnail_key(object_key: str) -> str:
    safe_key = object_key.replace("/", "_")
    filename_stem = Path(safe_key).stem
    return f"{Settings.thumbnail_prefix}{filename_stem}_thumb.jpg"


def create_thumbnail(
    bucket: str,
    object_key: str,
    image_bytes: bytes,
) -> tuple[str, str]:

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image.thumbnail((300, 300))

    output = io.BytesIO()

    image.save(
        output,
        format="JPEG",
        quality=80,
        optimize=True,
    )

    output.seek(0)

    thumbnail_key = build_thumbnail_key(object_key)

    s3_client.put_object(
        Bucket=bucket,
        Key=thumbnail_key,
        Body=output.getvalue(),
        ContentType="image/jpeg",
    )

    return thumbnail_key, make_s3_url(bucket, thumbnail_key)


def extract_first_video_frame(
    bucket: str,
    object_key: str,
) -> tuple[bytes, str]:
    """
    Extract only the first frame from video.
    Keeps Lambda lightweight and stable.
    """

    video_path = download_s3_object(bucket, object_key)

    cap = cv2.VideoCapture(video_path)

    success, frame = cap.read()

    if not success:
        cap.release()
        raise RuntimeError("Failed to extract first frame from video")

    cap.release()

    success, encoded = cv2.imencode(".jpg", frame)

    if not success:
        raise RuntimeError("Failed to encode frame")

    frame_bytes = encoded.tobytes()

    thumbnail_key, thumbnail_url = create_thumbnail(
        bucket=bucket,
        object_key=object_key,
        image_bytes=frame_bytes,
    )

    return frame_bytes, thumbnail_url
