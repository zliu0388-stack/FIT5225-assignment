import json
import boto3

s3 = boto3.client("s3")

def lambda_handler(event, context):
    print("Event received:")
    print(json.dumps(event))

    # Case 1: S3 trigger event
    if "Records" in event:
        record = event["Records"][0]

        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        print(f"Bucket: {bucket}")
        print(f"Key: {key}")

        s3.get_object(Bucket=bucket, Key=key)

        print("File loaded successfully")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "S3 upload event processed",
                "bucket": bucket,
                "key": key
            })
        }

    # Case 2: API Gateway event
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "message": "API Gateway connected to Lambda successfully"
        })
    }
