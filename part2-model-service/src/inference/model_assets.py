import hashlib
import os
from pathlib import Path

import boto3

from config import Settings

_CACHE_DIR = Path("/tmp/model_cache")
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

s3_client = boto3.client("s3", region_name=Settings.aws_region)


def _cache_path(bucket: str, key: str) -> Path:
    digest = hashlib.md5(f"{bucket}:{key}".encode("utf-8")).hexdigest()
    suffix = Path(key).suffix
    return _CACHE_DIR / f"{digest}{suffix}"


def ensure_local_model(bucket: str, key: str) -> str:
    if not bucket:
        raise ValueError("MODEL_BUCKET is required for model asset download")

    local_path = _cache_path(bucket, key)
    if local_path.exists() and local_path.stat().st_size > 0:
        return str(local_path)

    local_path.parent.mkdir(parents=True, exist_ok=True)
    s3_client.download_file(bucket, key, str(local_path))
    return str(local_path)


def ensure_default_assets() -> dict:
    return {
        "md_model_path": ensure_local_model(Settings.model_bucket, Settings.md_model_key),
        "species_model_path": ensure_local_model(
            Settings.model_bucket, Settings.species_model_key
        ),
        "labels_path": ensure_local_model(Settings.model_bucket, Settings.labels_key),
    }
