import hashlib
import tempfile
from collections import Counter
from pathlib import Path
from typing import Dict

import boto3
from PIL import Image

from config import Settings
from inference.animal_detector import AnimalDetector
from inference.model_assets import ensure_default_assets
from inference.species_classifier import SpeciesClassifier

s3_client = boto3.client("s3", region_name=Settings.aws_region)

_detector = None
_classifier = None


def _ensure_models():
    global _detector, _classifier
    if _detector is not None and _classifier is not None:
        return _detector, _classifier

    paths = ensure_default_assets()
    _detector = AnimalDetector(
        model_path=paths["md_model_path"], min_conf=Settings.min_detection_conf
    )
    _classifier = SpeciesClassifier(
        model_path=paths["species_model_path"], labels_path=paths["labels_path"]
    )
    return _detector, _classifier


def _download_s3_object(bucket: str, key: str) -> str:
    suffix = Path(key).suffix.lower() or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        local_path = tmp.name
    s3_client.download_file(bucket, key, local_path)
    return local_path


def _sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _clip_bbox(img_w: int, img_h: int, bbox: Dict) -> tuple:
    x, y, w, h = bbox["bbox"]
    left = max(0, int(x * img_w))
    top = max(0, int(y * img_h))
    right = min(img_w, int((x + w) * img_w))
    bottom = min(img_h, int((y + h) * img_h))
    return left, top, right, bottom


def infer_tags_from_s3_object(bucket: str, key: str) -> Dict:
    detector, classifier = _ensure_models()
    local_path = _download_s3_object(bucket, key)
    checksum = _sha256_of_file(local_path)

    tags_counter = Counter()
    image = Image.open(local_path).convert("RGB")
    detections = detector.detect(local_path)

    for idx, det in enumerate(detections):
        left, top, right, bottom = _clip_bbox(image.width, image.height, det)
        if right <= left or bottom <= top:
            continue
        crop = image.crop((left, top, right, bottom))
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            crop_path = tmp.name
        crop.save(crop_path)
        species, conf = classifier.classify(crop_path)
        if conf >= 0.1 and species != "unknown":
            tags_counter[species] += 1

    return {
        "bucket": bucket,
        "object_key": key,
        "media_type": "image",
        "checksum_sha256": checksum,
        "tags_map": dict(tags_counter),
        "model_name": "mdv5a+speciesnet",
        "model_version": "provided-private-model",
        "file_url": f"https://{bucket}.s3.{Settings.aws_region}.amazonaws.com/{key}",
    }
