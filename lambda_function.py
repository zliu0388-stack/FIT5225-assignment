import json
import os
import mimetypes
import urllib.parse

import boto3

s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")
dynamodb = boto3.resource("dynamodb")

PART2_FUNCTION_NAME = os.environ.get("PART2_FUNCTION_NAME")
UPLOAD_BUCKET = os.environ.get("UPLOAD_BUCKET", "fit5225-team102-aussie-ecolens")
UPLOAD_PREFIX = os.environ.get("UPLOAD_PREFIX", "uploads/")
MEDIA_TABLE = os.environ.get("MEDIA_TABLE", "fit5225-team102-media-files")
AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
PRESIGN_EXPIRY = int(os.environ.get("PRESIGN_EXPIRY", "300"))

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "content-type,authorization",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}


def _resp(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(payload),
    }


def invoke_part2(bucket, key):
    if not PART2_FUNCTION_NAME:
        print("PART2_FUNCTION_NAME is not set, skip invoking Part2")
        return

    payload = {"Records": [{"s3": {"bucket": {"name": bucket}, "object": {"key": key}}}]}
    response = lambda_client.invoke(
        FunctionName=PART2_FUNCTION_NAME,
        InvocationType="Event",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    print("Part2 Lambda invoked:", response.get("StatusCode"))


def _guess_content_type(filename, media_type):
    guessed, _ = mimetypes.guess_type(filename)
    if guessed:
        return guessed
    return "video/mp4" if media_type == "video" else "application/octet-stream"


def _active_media_exists_for_checksum(checksum: str) -> bool:
    if not checksum:
        return False
    table = dynamodb.Table(MEDIA_TABLE)
    resp = table.query(
        IndexName="GSI1_checksum",
        KeyConditionExpression="checksum_sha256 = :c",
        ExpressionAttributeValues={":c": checksum},
        Limit=10,
    )
    for item in resp.get("Items", []):
        if item.get("status") != "DELETED":
            return True
    return False


def handle_presign(event):
    """Return a presigned S3 PUT URL so the browser uploads the file directly to
    S3, bypassing the API Gateway / Lambda payload limits (supports large files
    and videos)."""
    try:
        body = json.loads(event.get("body") or "{}")
    except Exception:
        return _resp(400, {"message": "invalid JSON body"})

    filename = os.path.basename((body.get("filename") or "").replace("\\", "/")).strip()
    checksum = (body.get("checksum") or "").strip()
    media_type = (body.get("media_type") or "").strip()

    if not filename:
        return _resp(400, {"message": "filename is required"})

    # Deduplication: S3 marker and/or an active Part3 record with the same checksum.
    if checksum:
        dedup_key = f"dedup/{checksum}.json"
        try:
            s3.head_object(Bucket=UPLOAD_BUCKET, Key=dedup_key)
            return _resp(409, {"message": "Duplicate file detected"})
        except s3.exceptions.ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code not in ("404", "NoSuchKey", "NotFound"):
                raise
        if _active_media_exists_for_checksum(checksum):
            return _resp(409, {"message": "Duplicate file detected"})

    object_key = f"{UPLOAD_PREFIX}{filename}"
    content_type = _guess_content_type(filename, media_type)

    upload_url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": UPLOAD_BUCKET, "Key": object_key, "ContentType": content_type},
        ExpiresIn=PRESIGN_EXPIRY,
    )

    file_url = f"https://{UPLOAD_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{urllib.parse.quote(object_key)}"
    return _resp(200, {
        "upload_url": upload_url,
        "file_url": file_url,
        "object_key": object_key,
        "content_type": content_type,
    })


def lambda_handler(event, context):
    print("Event received:")
    print(json.dumps(event)[:1000])

    # Case 1: S3 trigger event -> forward to Part 2
    if "Records" in event:
        record = event["Records"][0]
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        print(f"S3 event: bucket={bucket}, key={key}")
        invoke_part2(bucket, key)
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "S3 event processed, Part2 invoked", "key": key}),
        }

    # Case 2: API Gateway -> issue presigned upload URL
    return handle_presign(event)
