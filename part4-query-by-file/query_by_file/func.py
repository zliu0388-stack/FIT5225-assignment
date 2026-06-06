"""
Oracle Functions entry point for query-by-file.
Deployed on Oracle Cloud, uses OCI Vision for species detection.
The original AWS Lambda (app.py) is kept untouched as backup.

Flow:
  1. Receive multipart/form-data POST with a 'file' field
  2. Run OCI Vision to detect objects/species (resource principal auth)
  3. Call AWS Part 3 /query/similar with the detected tags
  4. Return matched media items — query file is NOT stored permanently
"""
import io
import json
import os
import re
import base64

import fdk.response
import oci
import requests

_PART3_API_BASE = os.environ.get('PART3_API_BASE', '')
_COMPARTMENT_ID = os.environ.get('OCI_COMPARTMENT_ID', '')

# Generic labels that do NOT correspond to specific species.
# Keep identical to app.py so behaviour is consistent.
_GENERIC_LABELS = {
    'animal', 'mammal', 'wildlife', 'nature', 'outdoors', 'fauna',
    'wild', 'wilderness', 'land', 'plant', 'tree', 'bush', 'forest',
    'water', 'sky', 'photo', 'photography', 'image', 'reptile',
    'vertebrate', 'creature', 'organism', 'carnivore', 'herbivore',
    'insect', 'invertebrate', 'amphibian', 'marsupial', 'rodent',
    'primate', 'canine', 'feline', 'bovine', 'bird', 'fish',
    'terrestrial', 'arboreal', 'nocturnal', 'diurnal',
}


# Mapping from OCI Vision common English labels to the species epithet tags
# stored in the database by Part 2's wildlife ML model.
# Part 2 uses the 6th column of labels.txt (species epithet, lowercase+underscore).
# OCI Vision returns generic English object names, so we translate them here.
_OCI_TO_DB_TAG = {
    # Canis familiaris → 'familiaris' (dingo in the wildlife model)
    'dog':              'familiaris',
    'dingo':            'familiaris',
    # Felis catus → 'catus'
    'cat':              'catus',
    # Bos taurus → 'taurus'
    'cow':              'taurus',
    'cattle':           'taurus',
    'bull':             'taurus',
    'calf':             'taurus',
    # Sus scrofa → 'scrofa'
    'pig':              'scrofa',
    'boar':             'scrofa',
    'wild_boar':        'scrofa',
    'swine':            'scrofa',
    # Casuarius casuarius → 'casuarius'
    'cassowary':        'casuarius',
    # Alectura lathami → 'lathami'
    'turkey':           'lathami',
    'brush_turkey':     'lathami',
    'brushturkey':      'lathami',
    # Hypsiprymnodon moschatus → 'moschatus'
    'rat_kangaroo':     'moschatus',
    'musky_rat_kangaroo': 'moschatus',
    # Thylogale stigmatica → 'stigmatica'
    'pademelon':        'stigmatica',
    'red-legged_pademelon': 'stigmatica',
    # Perameles nasuta → 'nasuta'
    'bandicoot':        'nasuta',
    'long-nosed_bandicoot': 'nasuta',
    # Uromys caudimaculatus → 'caudimaculatus'
    'white-tailed_rat': 'caudimaculatus',
    'giant_rat':        'caudimaculatus',
    # Heteromyias cinereifrons → 'cinereifrons'
    'robin':            'cinereifrons',
    'grey-headed_robin': 'cinereifrons',
    # Megapodius reinwardt → 'reinwardt'
    'scrubfowl':        'reinwardt',
    'orange-footed_scrubfowl': 'reinwardt',
    # Orthonyx spaldingii → 'spaldingii'
    'chowchilla':       'spaldingii',
    # Macropus giganteus → 'giganteus'
    'kangaroo':         'giganteus',
    'eastern_gray_kangaroo': 'giganteus',
    # Vombatus ursinus → 'ursinus'
    'wombat':           'ursinus',
    # Trichosurus vulpecula → 'vulpecula'
    'possum':           'vulpecula',
    'brushtail':        'vulpecula',
    # Dacelo novaeguineae → 'novaeguineae'
    'kookaburra':       'novaeguineae',
    # Vulpes vulpes → 'vulpes'
    'fox':              'vulpes',
    # Oryctolagus cuniculus → 'cuniculus'
    'rabbit':           'cuniculus',
    # Tachyglossus aculeatus → 'aculeatus'
    'echidna':          'aculeatus',
}


_CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '3600',
    'Content-Type': 'application/json'
}


def handler(ctx, data: io.BytesIO = None):
    """Oracle Functions handler — replaces AWS Lambda handler in app.py."""
    try:
        body = data.read() if data else b''
        headers = {k.lower(): (v[0] if isinstance(v, list) else v)
                   for k, v in dict(ctx.Headers()).items()}

        # Handle CORS preflight (OPTIONS request)
        if headers.get('access-control-request-method') or \
                headers.get('access-control-request-headers'):
            return fdk.response.Response(
                ctx, response_data='', status_code=200, headers=_CORS_HEADERS
            )

        content_type = headers.get('content-type', '')
        auth_header  = headers.get('authorization', '')

        file_bytes, _ = _extract_file(body, content_type)
        tags_map = _detect_tags_oci(file_bytes)

        if not tags_map:
            result = {
                'items': [],
                'detected_tags': {},
                'message': 'No species detected in the uploaded file.'
            }
            return fdk.response.Response(
                ctx,
                response_data=json.dumps(result),
                headers={'Content-Type': 'application/json'}
            )

        items = _query_similar(tags_map, auth_header)
        result = {'items': items, 'detected_tags': tags_map}

        return fdk.response.Response(
            ctx,
            response_data=json.dumps(result),
            headers={'Content-Type': 'application/json'}
        )

    except ValueError as e:
        return fdk.response.Response(
            ctx,
            response_data=json.dumps({'message': str(e)}),
            status_code=400,
            headers={'Content-Type': 'application/json'}
        )
    except Exception as e:
        import traceback
        print(f'Unexpected error: {traceback.format_exc()}')
        return fdk.response.Response(
            ctx,
            response_data=json.dumps({'message': 'Internal server error'}),
            status_code=500,
            headers={'Content-Type': 'application/json'}
        )


def _get_oci_vision_client():
    """Create OCI Vision client. Uses API key from env vars, falls back to resource principal."""
    key_content = os.environ.get('OCI_PRIVATE_KEY_CONTENT', '').replace('\\n', '\n')
    if key_content:
        config = {
            "user": os.environ.get('OCI_USER_OCID', ''),
            "fingerprint": os.environ.get('OCI_FINGERPRINT', ''),
            "tenancy": os.environ.get('OCI_TENANCY_OCID', ''),
            "region": os.environ.get('OCI_REGION', 'ap-melbourne-1'),
            "key_content": key_content
        }
        return oci.ai_vision.AIServiceVisionClient(config)
    signer = oci.auth.signers.get_resource_principals_signer()
    return oci.ai_vision.AIServiceVisionClient({}, signer=signer)


def _detect_tags_oci(file_bytes: bytes) -> dict:
    """
    Use OCI Vision Object Detection to identify species in the image.
    Authentication uses API key from env vars (or resource principal as fallback).
    """
    try:
        client = _get_oci_vision_client()

        analyze_details = oci.ai_vision.models.AnalyzeImageDetails(
            image=oci.ai_vision.models.InlineImageDetails(
                data=base64.b64encode(file_bytes).decode('ascii')
            ),
            features=[
                oci.ai_vision.models.ImageObjectDetectionFeature(
                    feature_type='OBJECT_DETECTION',
                    max_results=20
                )
            ],
            compartment_id=_COMPARTMENT_ID
        )

        response = client.analyze_image(analyze_details)

        tags = {}
        for obj in response.data.detected_objects:
            name = obj.name.lower().replace(' ', '_')
            if name in _GENERIC_LABELS or len(name) < 4:
                continue
            # Translate OCI Vision common name to the species epithet tag
            # used by Part 2's wildlife ML model in the database.
            db_tag = _OCI_TO_DB_TAG.get(name, name)
            tags[db_tag] = tags.get(db_tag, 0) + 1

        return tags

    except Exception as e:
        print(f'OCI Vision error: {e}')
        return {}


def _query_similar(tags_map: dict, auth_header: str) -> list:
    """Call AWS Part 3 /query/similar — identical logic to app.py."""
    if not _PART3_API_BASE:
        print('PART3_API_BASE not configured')
        return []
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
    Parse multipart/form-data and return (file_bytes, extension).
    Identical to app.py — no changes to multipart parsing logic.
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
