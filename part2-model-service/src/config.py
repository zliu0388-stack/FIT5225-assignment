import os


class Settings:
    aws_region = os.getenv("AWS_REGION", "ap-southeast-2")

    part3_upsert_url = os.getenv("PART3_UPSERT_URL", "").strip()
    part3_auth_token = os.getenv("PART3_AUTH_TOKEN", "").strip()

    model_bucket = os.getenv("MODEL_BUCKET", "").strip()
    md_model_key = os.getenv("MD_MODEL_KEY", "models/mdv5a.pt")
    species_model_key = os.getenv("SPECIES_MODEL_KEY", "models/model.pt")
    labels_key = os.getenv("LABELS_KEY", "models/labels.txt")

    min_detection_conf = float(os.getenv("MIN_DETECTION_CONF", "0.2"))
