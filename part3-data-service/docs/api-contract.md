# Part3 API Contract (Data)

基地址示例：`https://<api-id>.execute-api.ap-southeast-2.amazonaws.com`

鉴权：`Authorization: Bearer <id_token>`

---

## 1) Upsert Media

- **Method**: `POST`
- **Path**: `/data/media`
- **用途**: 上传/标注流程完成后写入或更新媒体数据

请求体：

```json
{
  "media_id": "optional-uuid",
  "owner_sub": "cognito-sub",
  "owner_email": "user@example.com",
  "bucket": "fit5225-team102-aussie-ecolens",
  "object_key": "uploads/x.jpg",
  "file_url": "https://...",
  "thumbnail_url": "https://...",
  "media_type": "image",
  "checksum_sha256": "hex-string",
  "tags_map": { "koala": 3, "wombat": 1 },
  "model_name": "wildlife-detector",
  "model_version": "v1"
}
```

---

## 2) Query By Tags (AND + count)

- **Method**: `POST`
- **Path**: `/query/tags`

请求体：

```json
{
  "tags": {
    "koala": 2,
    "magpie": 1
  }
}
```

响应体：

```json
{
  "items": [
    {
      "media_id": "uuid",
      "media_type": "image",
      "thumbnail_url": "https://...",
      "file_url": "https://...",
      "count_map": { "koala": 3, "magpie": 1 }
    }
  ]
}
```

---

## 3) Thumbnail Lookup

- **Method**: `GET`
- **Path**: `/query/thumbnail`
- **QueryString**: `thumbnail_url=https://...`

响应体：

```json
{
  "media_id": "uuid",
  "file_url": "https://..."
}
```

---

## 4) Bulk Tag Operation

- **Method**: `POST`
- **Path**: `/tags/bulk`

请求体：

```json
{
  "urls": ["https://.../a.jpg", "https://.../b.jpg"],
  "tags": { "koala": 1, "wombat": 1 },
  "operation": 1
}
```

`operation`:
- `1` = add
- `0` = remove

---

## 5) Delete Files

- **Method**: `POST`
- **Path**: `/files/delete`

请求体：

```json
{
  "urls": ["https://.../a.jpg", "https://.../video.mp4"]
}
```

---

## 6) 错误码约定

- `400`: 参数缺失或格式错误
- `404`: 资源不存在
- `500`: 服务内部错误
