from collections import Counter
from pathlib import Path
from typing import Dict

from PIL import Image

from config import Settings
from utils.media_utils import (
    detect_media_type,
    download_s3_object,
    make_s3_url,
    sha256_file,
)

_detector = None
_classifier = None


def _ensure_models():
    global _detector, _classifier

    if _detector is not None and _classifier is not None:
        return _detector, _classifier

    from inference.animal_detector import AnimalDetector
    from inference.model_assets import ensure_default_assets
    from inference.species_classifier import SpeciesClassifier

    paths = ensure_default_assets()

    _detector = AnimalDetector(
        model_path=paths["md_model_path"],
        min_conf=Settings.min_detection_conf,
    )

    _classifier = SpeciesClassifier(
        model_path=paths["species_model_path"],
        labels_path=paths["labels_path"],
    )

    return _detector, _classifier


def _clip_bbox(img_w: int, img_h: int, detection: Dict) -> tuple[int, int, int, int]:
    x, y, w, h = detection["bbox"]

    left = max(0, int(x * img_w))
    top = max(0, int(y * img_h))
    right = min(img_w, int((x + w) * img_w))
    bottom = min(img_h, int((y + h) * img_h))

    return left, top, right, bottom


def infer_tags_from_s3_object(bucket: str, key: str) -> Dict:
    media_type = detect_media_type(key)
    local_path = download_s3_object(bucket, key)
    checksum = sha256_file(local_path)

    if media_type != "image":
        return {
            "bucket": bucket,
            "object_key": key,
            "media_type": media_type,
            "checksum_sha256": checksum,
            "tags_map": {"video": 1},
            "model_name": Settings.model_name,
            "model_version": Settings.model_version,
            "file_url": make_s3_url(bucket, key),
        }

    if not Settings.enable_model_inference:
        raise RuntimeError(
            "ENABLE_MODEL_INFERENCE is false. Real model inference is required for submission."
        )

    detector, classifier = _ensure_models()

    tags_counter = Counter()
    image = Image.open(local_path).convert("RGB")
    detections = detector.detect(local_path)

    for detection in detections:
        left, top, right, bottom = _clip_bbox(image.width, image.height, detection)

        if right <= left or bottom <= top:
            continue

        crop = image.crop((left, top, right, bottom))
        crop_path = f"/tmp/{Path(key).stem}_crop.jpg"
        crop.save(crop_path)

        species, confidence = classifier.classify(crop_path)

        if confidence >= 0.1 and species != "unknown":
            tags_counter[species] += 1

    tags_map = dict(tags_counter)

    if not tags_map:
        tags_map = {"wildlife": 1}

    return {
        "bucket": bucket,
        "object_key": key,
        "media_type": media_type,
        "checksum_sha256": checksum,
        "tags_map": tags_map,
        "model_name": Settings.model_name,
        "model_version": Settings.model_version,
        "file_url": make_s3_url(bucket, key),
    }
