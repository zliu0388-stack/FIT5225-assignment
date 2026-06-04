import hashlib
import io
import subprocess
import tempfile
from pathlib import Path

import boto3
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


def create_thumbnail(bucket: str, object_key: str, image_bytes: bytes) -> tuple[str, str]:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image.thumbnail((300, 300))

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=80, optimize=True)
    output.seek(0)

    thumbnail_key = build_thumbnail_key(object_key)

    s3_client.put_object(
        Bucket=bucket,
        Key=thumbnail_key,
        Body=output.getvalue(),
        ContentType="image/jpeg",
    )

    return thumbnail_key, make_s3_url(bucket, thumbnail_key)


def ffmpeg_version() -> str:
    try:
        result = subprocess.run(
            [Settings.ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        return (result.stdout or result.stderr or "").splitlines()[0]
    except Exception as exc:
        return f"ffmpeg unavailable: {exc}"


def extract_video_frames(
    video_path: str,
    fps: int | None = None,
    max_frames: int | None = None,
) -> list[str]:
    fps = fps if fps is not None else Settings.video_fps
    max_frames = max_frames if max_frames is not None else Settings.video_max_frames

    out_dir = tempfile.mkdtemp(prefix="frames_")
    output_pattern = str(Path(out_dir) / "frame_%03d.jpg")

    cmd = [
        Settings.ffmpeg_path,
        "-i",
        video_path,
        "-vf",
        f"fps={fps}",
        "-frames:v",
        str(max_frames),
        "-q:v",
        "2",
        output_pattern,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed ({result.returncode}): {(result.stderr or '')[:500]}"
        )

    frames = sorted(str(p) for p in Path(out_dir).glob("frame_*.jpg"))
    if not frames:
        raise RuntimeError("ffmpeg produced no frames")

    return frames
