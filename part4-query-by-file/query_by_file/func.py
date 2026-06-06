"""
Oracle Functions entry point for query-by-file.
Deployed on Oracle Cloud Infrastructure (OCI).

Flow:
  1. Receive multipart/form-data POST containing a 'file' field
  2. Run the teacher-provided SpeciesNet model (model.pt) to identify the species
  3. Call AWS Part 3 /query/similar with the detected species tag
  4. Return matched media items — the uploaded file is NOT stored permanently

Model: fine-tuned SpeciesNet (WildObs National), identical to the model used by
Part 2 for auto-tagging, so detected tags match the database exactly.
"""
import io
import json
import os
import re

import fdk.response
import numpy as np
import requests
import torch
import torchvision.transforms as T
from PIL import Image

# ── Configuration ─────────────────────────────────────────────────────────────

_PART3_API_BASE = os.environ.get('PART3_API_BASE', '')

_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model.pt')

# Minimum confidence threshold — below this the detection is discarded.
_MIN_CONFIDENCE = 0.10

# ── Species classes ────────────────────────────────────────────────────────────
# Copied verbatim from AussieEcoLense/batch.py — must stay in sync with model.pt.

_CLASSES = [
    'Alectura_lathami', 'Antechinus_agilis', 'Bos_taurus',
    'Burhinus_grallarius', 'Canis_familiaris', 'Chalcophaps_longirostris',
    'Colluricincla_harmonica', 'Corcorax_melanorhamphos', 'Dacelo_novaeguineae',
    'Dama_dama', 'Eopsaltria_australis', 'Felis_catus', 'Geopelia_humeralis',
    'Gymnorhina_tibicen', 'Homo_sapiens', 'Isoodon_macrourus', 'Lepus_europaeus',
    'Macropus_giganteus', 'Menura_novaehollandiae', 'Mus_musculus',
    'Oryctolagus_cuniculus', 'Perameles_nasuta', 'Pitta_versicolor', 'Rattus',
    'Rattus_fuscipes', 'Rattus_rattus', 'Strepera_graculina', 'Sus_scrofa',
    'Tachyglossus_aculeatus', 'Thylogale_stigmatica', 'Trichosurus_caninus',
    'Trichosurus_cunninghami', 'Trichosurus_vulpecula', 'Varanus_varius',
    'Vombatus_ursinus', 'Vulpes_vulpes', 'Wallabia_bicolor', 'Canis_dingo',
    'Capra_hircus', 'Casuarius_casuarius', 'Heteromyias_cinereifrons',
    'Hypsiprymnodon_moschatus', 'Megapodius_reinwardt', 'Notamacropus_rufogriseus',
    'Orthonyx_spaldingii', 'Uromys_caudimaculatus',
]

# ── Image transform (must match training pre-processing) ──────────────────────

_transform = T.Compose([
    T.Resize((480, 480)),
    T.ToTensor(),          # -> [C, H, W] float32 in [0, 1]
])

# ── Model singleton ────────────────────────────────────────────────────────────

_model = None


def _load_model():
    """Load SpeciesNet model once and cache it for the lifetime of the container."""
    global _model
    if _model is None:
        _model = torch.load(_MODEL_PATH, map_location='cpu', weights_only=False)
        _model.eval()
        print('SpeciesNet model loaded.')
    return _model


# ── CORS headers ───────────────────────────────────────────────────────────────

_CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '3600',
    'Content-Type': 'application/json',
}


# ── FDK handler ───────────────────────────────────────────────────────────────

def handler(ctx, data: io.BytesIO = None):
    """Oracle Functions entry point."""
    try:
        body = data.read() if data else b''
        headers = {k.lower(): (v[0] if isinstance(v, list) else v)
                   for k, v in dict(ctx.Headers()).items()}

        # Handle CORS preflight
        if headers.get('access-control-request-method') or \
                headers.get('access-control-request-headers'):
            return fdk.response.Response(
                ctx, response_data='', status_code=200, headers=_CORS_HEADERS
            )

        content_type = headers.get('content-type', '')
        auth_header  = headers.get('authorization', '')

        file_bytes, _ = _extract_file(body, content_type)
        tags_map = _detect_tags_model(file_bytes)

        if not tags_map:
            result = {
                'items': [],
                'detected_tags': {},
                'message': 'No species detected in the uploaded file.',
            }
            return fdk.response.Response(
                ctx,
                response_data=json.dumps(result),
                headers={'Content-Type': 'application/json'},
            )

        items = _query_similar(tags_map, auth_header)
        result = {'items': items, 'detected_tags': tags_map}

        return fdk.response.Response(
            ctx,
            response_data=json.dumps(result),
            headers={'Content-Type': 'application/json'},
        )

    except ValueError as exc:
        return fdk.response.Response(
            ctx,
            response_data=json.dumps({'message': str(exc)}),
            status_code=400,
            headers={'Content-Type': 'application/json'},
        )
    except Exception as exc:
        import traceback
        print(f'Unexpected error: {traceback.format_exc()}')
        return fdk.response.Response(
            ctx,
            response_data=json.dumps({'message': 'Internal server error'}),
            status_code=500,
            headers={'Content-Type': 'application/json'},
        )


# ── Species detection ─────────────────────────────────────────────────────────

def _detect_tags_model(file_bytes: bytes) -> dict:
    """
    Run the teacher-provided SpeciesNet model on the uploaded image.

    The model accepts input shape [B, H, W, C] = [1, 480, 480, 3] and outputs
    class logits for each of the 46 supported wildlife species.

    Returns:
        dict mapping species epithet -> confidence, e.g. {'familiaris': 0.923}
        Empty dict if confidence is below threshold or inference fails.
    """
    try:
        model = _load_model()

        img = Image.open(io.BytesIO(file_bytes)).convert('RGB')
        tensor = _transform(img)           # [3, 480, 480]
        tensor = tensor.unsqueeze(0)       # [1, 3, 480, 480]
        tensor = tensor.permute(0, 2, 3, 1)  # [1, 480, 480, 3]  (NHWC — matches training)

        with torch.no_grad():
            logits = model(tensor)
            probs  = torch.softmax(logits, dim=1)[0].cpu().numpy()

        best_idx   = int(np.argsort(probs)[::-1][0])
        confidence = float(probs[best_idx])

        print(f'Top prediction: {_CLASSES[best_idx]} ({confidence:.3f})')

        if confidence < _MIN_CONFIDENCE:
            return {}

        species_tag = _class_to_tag(_CLASSES[best_idx])
        return {species_tag: round(confidence, 3)}

    except Exception as exc:
        print(f'Model inference error: {exc}')
        return {}


def _class_to_tag(class_name: str) -> str:
    """
    Extract the species epithet (DB tag) from a class name.

    Examples:
        'Canis_familiaris' -> 'familiaris'
        'Casuarius_casuarius' -> 'casuarius'
        'Rattus' -> 'rattus'
    """
    parts = class_name.lower().split('_')
    return parts[1] if len(parts) >= 2 else parts[0]


# ── Part 3 query ──────────────────────────────────────────────────────────────

def _query_similar(tags_map: dict, auth_header: str) -> list:
    """Call AWS Part 3 /query/similar and return matched media items."""
    if not _PART3_API_BASE:
        print('PART3_API_BASE not configured')
        return []
    resp = requests.post(
        f'{_PART3_API_BASE}/query/similar',
        json={'tags_map': tags_map},
        headers={
            'Authorization': auth_header,
            'Content-Type': 'application/json',
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get('items', data.get('results', []))


# ── Multipart parser ──────────────────────────────────────────────────────────

def _extract_file(body: bytes, content_type: str):
    """
    Parse multipart/form-data body and return (file_bytes, extension).
    Raises ValueError if the 'file' field is missing or boundary is absent.
    """
    boundary_match = re.search(r'boundary=([^\s;]+)', content_type, re.IGNORECASE)
    if not boundary_match:
        raise ValueError('Missing boundary in Content-Type header')

    boundary  = boundary_match.group(1).strip('"')
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
