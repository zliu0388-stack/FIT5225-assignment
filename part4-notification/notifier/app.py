"""
Triggered by DynamoDB Streams on the Part 3 media-files table.
When a new file is inserted or existing tags are updated, sends SNS email
notifications to users subscribed to the newly added tags.
"""
import json
import os
import boto3
from boto3.dynamodb.conditions import Attr
from boto3.dynamodb.types import TypeDeserializer

dynamodb    = boto3.resource('dynamodb')
sns         = boto3.client('sns')
deserializer = TypeDeserializer()

TABLE_NAME   = os.environ['SUBSCRIPTIONS_TABLE']
TOPIC_PREFIX = os.environ['SNS_TOPIC_PREFIX']


def handler(event, context):
    for record in event.get('Records', []):
        event_name = record.get('eventName')
        if event_name not in ('INSERT', 'MODIFY'):
            continue

        new_image = _deserialize(record['dynamodb'].get('NewImage', {}))

        if event_name == 'INSERT':
            # Notify for all tags on a newly uploaded file
            added_tags = set((new_image.get('tags_map') or {}).keys())
        else:
            # Notify only for tags that were not in the old version.
            # Special case: if status changed DELETED → ACTIVE (re-upload of a
            # previously deleted file), treat all current tags as new so that
            # subscribers receive a notification just like a fresh upload.
            old_image  = _deserialize(record['dynamodb'].get('OldImage', {}))
            old_status = old_image.get('status', 'ACTIVE')
            new_status = new_image.get('status', 'ACTIVE')
            new_tags   = set((new_image.get('tags_map') or {}).keys())
            if old_status == 'DELETED' and new_status == 'ACTIVE':
                added_tags = new_tags
            else:
                old_tags   = set((old_image.get('tags_map') or {}).keys())
                added_tags = new_tags - old_tags

        if not added_tags:
            continue

        file_url = new_image.get('file_url', '(unknown)')
        for tag in added_tags:
            _notify(tag, file_url)


def _notify(tag, file_url):
    """Find the SNS topic for this tag and publish an email notification."""
    table = dynamodb.Table(TABLE_NAME)

    # Find any subscriber to know the topic ARN (all share the same topic per tag)
    resp = table.scan(
        FilterExpression=Attr('tag').eq(tag),
        Limit=1
    )
    items = resp.get('Items', [])
    if not items:
        return  # Nobody subscribed to this tag

    topic_arn = items[0].get('sns_topic_arn')
    if not topic_arn:
        return

    message = (
        f"A new file tagged with '{tag}' has been added to AussieEcoLens.\n\n"
        f"File URL:\n{file_url}\n\n"
        f"To manage your notification preferences, visit the Notifications page.\n"
    )

    try:
        sns.publish(
            TopicArn=topic_arn,
            Subject=f"[AussieEcoLens] New {tag} sighting uploaded",
            Message=message
        )
        print(f"Notified subscribers for tag '{tag}' (file: {file_url})")
    except Exception as e:
        print(f"Failed to publish SNS for tag '{tag}': {e}")


def _deserialize(dynamo_item):
    """Convert DynamoDB JSON format to a plain Python dict."""
    return {k: deserializer.deserialize(v) for k, v in dynamo_item.items()}
