import json
import boto3

s3 = boto3.client('s3')

def lambda_handler(event, context):

    print("S3 trigger received:")
    print(json.dumps(event))

    record = event['Records'][0]

    bucket = record['s3']['bucket']['name']
    key = record['s3']['object']['key']

    print(f"Bucket: {bucket}")
    print(f"Key: {key}")

    response = s3.get_object(
        Bucket=bucket,
        Key=key
    )

    print("File loaded successfully")

    return {
        'statusCode': 200,
        'body': json.dumps('Success')
    }
