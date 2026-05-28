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

async function uploadFile(file, checksum, token) {
    const formData = new FormData();
    formData.append('file',       file);
    formData.append('checksum',   checksum);
    formData.append('media_type', file.type.startsWith('video/') ? 'video' : 'image');

    const resp = await fetch(`${CONFIG.part1ApiBase}/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
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
    return data;
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
