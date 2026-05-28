"""
Part 4 — Query by Uploaded File Lambda

Flow:
  1. Receive multipart/form-data POST with a 'file' field (image or video)
  2. Run YOLOv8 inference to detect species → {label: count} map
  3. Call Part 3 /query/similar with the detected tags
  4. Return matched media items to the frontend
"""
import json
import os
import re
import base64
import tempfile
import requests
from ultralytics import YOLO

# ── Load model once at cold start (cached for warm invocations) ────────────
_MODEL_PATH = os.environ.get('MODEL_PATH', '/var/task/yolov8n.pt')
_model = YOLO(_MODEL_PATH)

_PART3_API_BASE = os.environ['PART3_API_BASE']

_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*'
}


def handler(event, context):
    try:
        # API Gateway sends binary bodies as base64 when BinaryMediaTypes is set
        raw_body = event.get('body') or ''
        body = base64.b64decode(raw_body) if event.get('isBase64Encoded') else raw_body.encode()

        headers = event.get('headers') or {}
        content_type = headers.get('content-type') or headers.get('Content-Type') or ''

        # Extract file bytes + original extension from the multipart payload
        file_bytes, file_ext = _extract_file(body, content_type)

        # Write to /tmp (the only writable path in Lambda)
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as f:
            f.write(file_bytes)
            tmp_path = f.name

        try:
            tags_map = _run_inference(tmp_path)
        finally:
            os.unlink(tmp_path)

        if not tags_map:
            return _resp(200, {
                'items': [],
                'detected_tags': {},
                'message': 'No objects detected in the uploaded file.'
            })

        # Forward detected tags to Part 3's similar-search API
        auth = headers.get('Authorization') or headers.get('authorization') or ''
        items = _query_similar(tags_map, auth)

        return _resp(200, {'items': items, 'detected_tags': tags_map})

    except ValueError as e:
        return _resp(400, {'message': str(e)})
    except Exception as e:
        print(f'Unexpected error: {e}')
        return _resp(500, {'message': 'Internal server error'})


# ── YOLO inference ─────────────────────────────────────────────────────────

def _run_inference(file_path: str) -> dict:
    """Run YOLO on the file and return {class_label: count}."""
    results = _model(file_path, verbose=False)
    counts = {}
    for result in results:
        for cls_id in result.boxes.cls.tolist():
            label = result.names[int(cls_id)].lower()
            counts[label] = counts.get(label, 0) + 1
    return counts


# ── Part 3 similar query ───────────────────────────────────────────────────

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


# ── Multipart parser ───────────────────────────────────────────────────────

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

        # Determine file extension from original filename if present
        ext = '.jpg'
        fname_match = re.search(r'filename="([^"]+)"', headers_text, re.IGNORECASE)
        if fname_match:
            _, ext_candidate = os.path.splitext(fname_match.group(1))
            if ext_candidate:
                ext = ext_candidate.lower()

        return content.rstrip(b'\r\n'), ext

    raise ValueError('No "file" field found in request body')


# ── Response helper ────────────────────────────────────────────────────────

def _resp(status: int, body: dict) -> dict:
    return {
        'statusCode': status,
        'headers': _HEADERS,
        'body': json.dumps(body)
    }
