from collections import Counter
from pathlib import Path
from typing import Dict

from PIL import Image

from config import Settings
from app_utils.media_utils import (
    detect_media_type,
    download_s3_object,
    extract_video_frames,
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


def _infer_tags_on_image_path(image_path: str, stem: str) -> Counter:
    detector, classifier = _ensure_models()
    tags_counter = Counter()

    image = Image.open(image_path).convert("RGB")
    detections = detector.detect(image_path)

    for detection in detections:
        left, top, right, bottom = _clip_bbox(image.width, image.height, detection)

        if right <= left or bottom <= top:
            continue

        crop = image.crop((left, top, right, bottom))
        crop_path = f"/tmp/{stem}_crop.jpg"
        crop.save(crop_path)

        species, confidence = classifier.classify(crop_path)

        if confidence >= 0.1 and species != "unknown":
            tags_counter[species] += 1

    return tags_counter


def infer_tags_from_s3_object(bucket: str, key: str) -> Dict:
    media_type = detect_media_type(key)
    local_path = download_s3_object(bucket, key)
    checksum = sha256_file(local_path)

    if not Settings.enable_model_inference:
        raise RuntimeError(
            "ENABLE_MODEL_INFERENCE is false. Real model inference is required for submission."
        )

    tags_counter = Counter()
    stem = Path(key).stem.replace("/", "_")

    thumbnail_frame_bytes = None

    if media_type == "image":
        tags_counter.update(_infer_tags_on_image_path(local_path, stem))
    elif media_type == "video":
        frame_paths = extract_video_frames(local_path)
        for idx, frame_path in enumerate(frame_paths):
            tags_counter.update(_infer_tags_on_image_path(frame_path, f"{stem}_f{idx}"))
        with open(frame_paths[0], "rb") as frame_file:
            thumbnail_frame_bytes = frame_file.read()
    else:
        raise ValueError(f"unsupported media type for inference: {media_type}")

    result = {
        "bucket": bucket,
        "object_key": key,
        "media_type": media_type,
        "checksum_sha256": checksum,
        "tags_map": dict(tags_counter) or {"wildlife": 1},
        "model_name": Settings.model_name,
        "model_version": Settings.model_version,
        "file_url": make_s3_url(bucket, key),
    }

    if thumbnail_frame_bytes is not None:
        result["thumbnail_frame_bytes"] = thumbnail_frame_bytes

    return result
