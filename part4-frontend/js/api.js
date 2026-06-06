// ── Shared helpers ────────────────────────────────────────────────────────────

async function computeSHA256(file) {
    const buffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

function formatFileSize(bytes) {
    if (bytes < 1024)             return `${bytes} B`;
    if (bytes < 1024 * 1024)     return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ── Internal fetch wrappers ───────────────────────────────────────────────────

async function _post(url, body, token) {
    const resp = await fetch(url, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
    });
    let data;
    try { data = await resp.json(); } catch { data = {}; }
    if (!resp.ok) {
        const err = new Error(data.message || `HTTP ${resp.status}`);
        err.status = resp.status;
        err.data   = data;
        throw err;
    }
    return data;
}

async function _get(url, token) {
    const resp = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    let data;
    try { data = await resp.json(); } catch { data = {}; }
    if (!resp.ok) {
        const err = new Error(data.message || `HTTP ${resp.status}`);
        err.status = resp.status;
        err.data   = data;
        throw err;
    }
    return data;
}

// ── Part 1: File upload ───────────────────────────────────────────────────────

// Two-step upload: ask Part 1 for a presigned S3 URL, then PUT the file straight
// to S3. This bypasses the API Gateway / Lambda payload limits, so large images
// and videos upload fine.
async function uploadFile(file, checksum, token) {
    const media_type = file.type.startsWith('video/') ? 'video' : 'image';

    // Step 1 — request a presigned upload URL (also runs the duplicate check)
    const resp = await fetch(`${CONFIG.part1ApiBase}/upload`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ filename: file.name, checksum, media_type })
    });

    let data;
    try { data = await resp.json(); } catch { data = {}; }

    if (resp.status === 409) {
        const err = new Error('Duplicate file detected');
        err.isDuplicate = true;
        err.status = 409;
        throw err;
    }
    if (!resp.ok) {
        const err = new Error(data.message || 'Upload failed');
        err.status = resp.status;
        err.data   = data;
        throw err;
    }

    // Step 2 — upload the file bytes directly to S3 via the presigned URL.
    // The Content-Type must match the one the URL was signed with.
    const putResp = await fetch(data.upload_url, {
        method: 'PUT',
        headers: { 'Content-Type': data.content_type || file.type || 'application/octet-stream' },
        body: file
    });

    if (!putResp.ok) {
        const err = new Error(`Storage upload failed (HTTP ${putResp.status})`);
        err.status = putResp.status;
        throw err;
    }

    return { file_url: data.file_url, object_key: data.object_key };
}

// ── Part 3: Query APIs ────────────────────────────────────────────────────────

async function queryByTags(tags, token) {
    return _post(`${CONFIG.part3ApiBase}/query/tags`, { tags }, token);
}

async function lookupThumbnail(thumbnailUrl, token) {
    const enc = encodeURIComponent(thumbnailUrl);
    return _get(`${CONFIG.part3ApiBase}/query/thumbnail?thumbnail_url=${enc}`, token);
}

async function querySimilar(tagsMap, token) {
    return _post(`${CONFIG.part3ApiBase}/query/similar`, { tags_map: tagsMap }, token);
}

// ── Part 3: Management APIs ───────────────────────────────────────────────────

async function bulkTag(urls, tags, operation, token) {
    return _post(`${CONFIG.part3ApiBase}/tags/bulk`, { urls, tags, operation }, token);
}

async function deleteFiles(urls, token) {
    return _post(`${CONFIG.part3ApiBase}/files/delete`, { urls }, token);
}
