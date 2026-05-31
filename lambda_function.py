import json
import boto3
import os

s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")

PART2_FUNCTION_NAME = os.environ.get("PART2_FUNCTION_NAME")


def invoke_part2(bucket, key):
    if not PART2_FUNCTION_NAME:
        print("PART2_FUNCTION_NAME is not set, skip invoking Part2")
        return

    payload = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": bucket
                    },
                    "object": {
                        "key": key
                    }
                }
            }
        ]
    }

    response = lambda_client.invoke(
        FunctionName=PART2_FUNCTION_NAME,
        InvocationType="Event",
        Payload=json.dumps(payload).encode("utf-8")
    )

    print("Part2 Lambda invoked:")
    print(response)


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

        invoke_part2(bucket, key)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "S3 upload event processed and Part2 invoked",
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
