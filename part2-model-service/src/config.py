import os


class Settings:
    aws_region = os.getenv("AWS_REGION", "ap-southeast-2")

    upload_bucket = os.getenv("UPLOAD_BUCKET", "fit5225-team102-aussie-ecolens").strip()
    upload_prefix = os.getenv("UPLOAD_PREFIX", "uploads/").strip()
    thumbnail_prefix = os.getenv("THUMBNAIL_PREFIX", "thumbnails/").strip()
    temp_prefix = os.getenv("TEMP_PREFIX", "temp/").strip()

    part3_upsert_url = os.getenv(
        "PART3_UPSERT_URL",
        "https://5jo3ferouh.execute-api.ap-southeast-2.amazonaws.com/prod/data/media",
    ).strip()
    part3_auth_token = os.getenv("PART3_AUTH_TOKEN", "").strip()

    model_bucket = os.getenv("MODEL_BUCKET", "fit5225-team102-aussie-ecolens").strip()
    md_model_key = os.getenv("MD_MODEL_KEY", "models/mdv5a.pt").strip()
    species_model_key = os.getenv("SPECIES_MODEL_KEY", "models/model.pt").strip()
    labels_key = os.getenv("LABELS_KEY", "models/labels.txt").strip()

    min_detection_conf = float(os.getenv("MIN_DETECTION_CONF", "0.2"))
    enable_model_inference = os.getenv("ENABLE_MODEL_INFERENCE", "true").lower() == "true"

    model_name = os.getenv("MODEL_NAME", "wildlife-detector")
    model_version = os.getenv("MODEL_VERSION", "v1")

    ffmpeg_path = os.getenv("FFMPEG_PATH", "/opt/bin/ffmpeg").strip()
    video_fps = int(os.getenv("VIDEO_FPS", "1"))
    video_max_frames = int(os.getenv("VIDEO_MAX_FRAMES", "5"))
