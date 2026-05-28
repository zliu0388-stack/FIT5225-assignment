import json
import os
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

TABLE_NAME   = os.environ['SUBSCRIPTIONS_TABLE']
TOPIC_PREFIX = os.environ['SNS_TOPIC_PREFIX']

HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*'
}


def handler(event, context):
    try:
        body  = json.loads(event.get('body') or '{}')
        email = body.get('email', '').strip().lower()
        tag   = body.get('tag',   '').strip().lower()

        if not email or not tag:
            return _resp(400, {'message': 'email and tag are required'})

        table = dynamodb.Table(TABLE_NAME)

        # Prevent duplicate subscriptions
        existing = table.get_item(Key={'email': email, 'tag': tag}).get('Item')
        if existing:
            return _resp(200, {
                'message': f'Already subscribed to "{tag}".',
                'email': email,
                'tag': tag
            })

        # Create SNS topic (idempotent — returns existing ARN if topic already exists)
        topic_name = f"{TOPIC_PREFIX}{tag}"
        topic_arn  = sns.create_topic(Name=topic_name)['TopicArn']

        # Subscribe the email address to this topic
        sub_resp = sns.subscribe(
            TopicArn=topic_arn,
            Protocol='email',
            Endpoint=email,
            ReturnSubscriptionArn=True
        )
        sns_subscription_arn = sub_resp['SubscriptionArn']

        # Store the subscription in DynamoDB
        table.put_item(Item={
            'email':                email,
            'tag':                  tag,
            'sns_topic_arn':        topic_arn,
            'sns_subscription_arn': sns_subscription_arn,
            'created_at':           datetime.now(timezone.utc).isoformat()
        })

        return _resp(200, {
            'message': (
                f'Subscribed to "{tag}". '
                'Please check your email and confirm the AWS SNS subscription to start receiving alerts.'
            ),
            'email': email,
            'tag':   tag
        })

    except Exception as e:
        print(f'Subscribe error: {e}')
        return _resp(500, {'message': str(e)})


def _resp(status, body):
    return {
        'statusCode': status,
        'headers':    HEADERS,
        'body':       json.dumps(body)
    }
