import json
import os
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')

TABLE_NAME = os.environ['SUBSCRIPTIONS_TABLE']

HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*'
}


def handler(event, context):
    try:
        params = event.get('queryStringParameters') or {}
        email  = params.get('email', '').strip().lower()

        if not email:
            return _resp(400, {'message': 'email query parameter is required'})

        table = dynamodb.Table(TABLE_NAME)
        result = table.query(
            KeyConditionExpression=Key('email').eq(email)
        )

        subscriptions = [
            {
                'tag':        item['tag'],
                'created_at': item.get('created_at', '')
            }
            for item in result.get('Items', [])
        ]

        return _resp(200, {'subscriptions': subscriptions})

    except Exception as e:
        print(f'List subscriptions error: {e}')
        return _resp(500, {'message': str(e)})


def _resp(status, body):
    return {
        'statusCode': status,
        'headers':    HEADERS,
        'body':       json.dumps(body)
    }
