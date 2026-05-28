import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

TABLE_NAME = os.environ['SUBSCRIPTIONS_TABLE']

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

        # Look up the stored subscription
        item = table.get_item(Key={'email': email, 'tag': tag}).get('Item')
        if not item:
            return _resp(404, {'message': f'No subscription found for "{tag}" with email "{email}".'})

        # Unsubscribe from SNS (the ARN may be "PendingConfirmation" if never confirmed)
        sns_arn = item.get('sns_subscription_arn', '')
        if sns_arn and sns_arn != 'PendingConfirmation':
            try:
                sns.unsubscribe(SubscriptionArn=sns_arn)
            except Exception as e:
                print(f'SNS unsubscribe warning (continuing): {e}')

        # Remove from DynamoDB
        table.delete_item(Key={'email': email, 'tag': tag})

        return _resp(200, {
            'message': f'Unsubscribed from "{tag}" alerts.',
            'email': email,
            'tag':   tag
        })

    except Exception as e:
        print(f'Unsubscribe error: {e}')
        return _resp(500, {'message': str(e)})


def _resp(status, body):
    return {
        'statusCode': status,
        'headers':    HEADERS,
        'body':       json.dumps(body)
    }
