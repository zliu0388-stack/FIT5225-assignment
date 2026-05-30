import os


class Settings:
    aws_region = os.getenv("AWS_REGION", "ap-southeast-2")
    media_table = os.getenv("MEDIA_TABLE", "fit5225-team102-media-files")
    tag_index_table = os.getenv("TAG_INDEX_TABLE", "fit5225-team102-tag-index")
    thumb_lookup_table = os.getenv("THUMB_LOOKUP_TABLE", "fit5225-team102-thumb-lookup")
    tag_subscription_table = os.getenv(
        "TAG_SUBSCRIPTION_TABLE", "fit5225-team102-tag-subscriptions"
    )
    bucket_name = os.getenv("BUCKET_NAME", "fit5225-team102-aussie-ecolens")

model_path = os.getenv("MODEL_PATH", "/opt/models/model.pt")
model_name = os.getenv("MODEL_NAME", "aussie-ecolens-detector")
model_version = os.getenv("MODEL_VERSION", "v1")
