"""
Part 4 — Query by Uploaded File Lambda

Flow:
  1. Receive multipart/form-data POST with a 'file' field (image or video)
  2. Run AWS Rekognition DetectLabels to detect objects/species
  3. Call Part 3 /query/similar with the detected tags
  4. Return matched media items to the frontend
"""
import json
import os
import re
import base64
import boto3
import requests

_PART3_API_BASE = os.environ['PART3_API_BASE']
_rekognition = boto3.client('rekognition', region_name='ap-southeast-2')

_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*'
}


def handler(event, context):
    try:
        raw_body = event.get('body') or ''
        body = base64.b64decode(raw_body) if event.get('isBase64Encoded') else raw_body.encode()

        headers = event.get('headers') or {}
        content_type = headers.get('content-type') or headers.get('Content-Type') or ''

        file_bytes, _ = _extract_file(body, content_type)

        resp = _rekognition.detect_labels(
            Image={'Bytes': file_bytes},
            MaxLabels=20,
            MinConfidence=60
        )
        tags_map = _extract_species_tags(resp.get('Labels', []))

        if not tags_map:
            return _resp(200, {
                'items': [],
                'detected_tags': {},
                'message': 'No objects detected in the uploaded file.'
            })

        auth = headers.get('Authorization') or headers.get('authorization') or ''
        items = _query_similar(tags_map, auth)

        return _resp(200, {'items': items, 'detected_tags': tags_map})

    except ValueError as e:
        return _resp(400, {'message': str(e)})
    except Exception as e:
        print(f'Unexpected error: {e}')
        return _resp(500, {'message': 'Internal server error'})


# Generic Rekognition labels that do NOT correspond to specific species
# and would never match Part 2's custom species classifier output.
_GENERIC_LABELS = {
    'animal', 'mammal', 'wildlife', 'nature', 'outdoors', 'fauna',
    'wild', 'wilderness', 'land', 'plant', 'tree', 'bush', 'forest',
    'water', 'sky', 'photo', 'photography', 'image', 'reptile',
    'vertebrate', 'creature', 'organism', 'carnivore', 'herbivore',
    'insect', 'invertebrate', 'amphibian', 'marsupial', 'rodent',
    'primate', 'canine', 'feline', 'bovine', 'bird', 'fish',
    'terrestrial', 'arboreal', 'nocturnal', 'diurnal',
}


def _extract_species_tags(labels: list) -> dict:
    """
    Filter Rekognition labels to keep only specific species names that are
    likely to match Part 2's custom species classifier output (lowercase,
    spaces→underscores). Generic / category-level labels are excluded.
    """
    tags = {}
    for label in labels:
        name = label['Name'].lower().replace(' ', '_')
        # Skip generic category labels
        if name in _GENERIC_LABELS:
            continue
        # Skip very short names (usually generic)
        if len(name) < 4:
            continue
        tags[name] = 1
    return tags


def _query_similar(tags_map: dict, auth_header: str) -> list:
    """Call Part 3 /query/similar and return the items list."""
    resp = requests.post(
        f'{_PART3_API_BASE}/query/similar',
        json={'tags_map': tags_map},
        headers={
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        },
        timeout=15
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get('items', data.get('results', []))


def _extract_file(body: bytes, content_type: str):
    """
    Parse a multipart/form-data body and return (file_bytes, extension).
    Looks for the form field named 'file'.
    """
    boundary_match = re.search(r'boundary=([^\s;]+)', content_type, re.IGNORECASE)
    if not boundary_match:
        raise ValueError('Missing boundary in Content-Type header')

    boundary = boundary_match.group(1).strip('"')
    delimiter = f'--{boundary}'.encode()

    for part in body.split(delimiter)[1:]:
        if not part or part.strip() in (b'--', b'--\r\n'):
            break
        if b'\r\n\r\n' not in part:
            continue

        headers_raw, content = part.split(b'\r\n\r\n', 1)
        headers_text = headers_raw.decode('utf-8', errors='ignore')

        if 'name="file"' not in headers_text and "name='file'" not in headers_text:
            continue

        ext = '.jpg'
        fname_match = re.search(r'filename="([^"]+)"', headers_text, re.IGNORECASE)
        if fname_match:
            _, ext_candidate = os.path.splitext(fname_match.group(1))
            if ext_candidate:
                ext = ext_candidate.lower()

        return content.rstrip(b'\r\n'), ext

    raise ValueError('No "file" field found in request body')


def _resp(status: int, body: dict) -> dict:
    return {
        'statusCode': status,
        'headers': _HEADERS,
        'body': json.dumps(body)
    }
