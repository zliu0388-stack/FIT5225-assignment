# Part3 联调记录与 D 组对接信息

## 1) 部署与修复记录（已完成）

- 部署栈：`fit5225-team102-part3-data`
- 区域：`ap-southeast-2`
- API Base URL：`https://5jo3ferouh.execute-api.ap-southeast-2.amazonaws.com/prod`
- 关键修复：
  - 移除 Lambda 保留环境变量 `AWS_REGION`（否则创建函数失败）
  - 修复 DynamoDB `Decimal` 序列化（`Object of type Decimal is not JSON serializable`）

最终状态：`Successfully created/updated stack - fit5225-team102-part3-data in ap-southeast-2`

---

## 2) 本次联调命令（可复用）

> 说明：以下为最终可用命令模板。`TOKEN` 使用 Cognito Hosted UI 登录后获取的 `id_token`。

```bash
export API_BASE="https://5jo3ferouh.execute-api.ap-southeast-2.amazonaws.com/prod"
export FILE_URL="https://fit5225-team102-aussie-ecolens.s3.ap-southeast-2.amazonaws.com/uploads/demo-koala.jpg"
export THUMB_URL="https://fit5225-team102-aussie-ecolens.s3.ap-southeast-2.amazonaws.com/thumbnails/demo-koala.jpg"
```

### 2.1 Query By Tags

```bash
curl -i -X POST "${API_BASE}/query/tags" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"tags":{"koala":1}}'
```

### 2.2 Query Similar

```bash
curl -i -X POST "${API_BASE}/query/similar" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"tags_map":{"koala":1}}'
```

### 2.3 Thumbnail Lookup

```bash
ENC_THUMB_URL=$(python3 -c "import urllib.parse,os;print(urllib.parse.quote(os.environ['THUMB_URL'], safe=''))")
curl -i -X GET "${API_BASE}/query/thumbnail?thumbnail_url=${ENC_THUMB_URL}" \
  -H "Authorization: Bearer ${TOKEN}"
```

### 2.4 Bulk Tag（add）

```bash
curl -i -X POST "${API_BASE}/tags/bulk" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"urls":["'"${FILE_URL}"'"],"tags":{"wombat":1},"operation":1}'
```

### 2.5 Delete Files

```bash
curl -i -X POST "${API_BASE}/files/delete" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"urls":["'"${FILE_URL}"'"]}'
```

---

## 3) 本次联调结果（实际执行）

- `POST /query/tags`：`200`
  - 返回 `items`，可查到 `demo-koala.jpg`
- `POST /query/similar`：`200`
  - 返回与 `koala` 标签匹配的媒体
- `GET /query/thumbnail`：`200`
  - 能从 `thumbnail_url` 反查 `file_url`
- `POST /tags/bulk`：`200`
  - 标签更新成功，`tags_map` 包含新增 `wombat`，`tags_version` 递增
- `POST /files/delete`：`200`
  - `deleted` 包含目标 URL，`not_found` 为空

结论：Part3 Data API（含 Cognito 鉴权）联调通过，可提供给 UI 组接入。

---

## 4) 发给 D 组的最终对接信息（可直接复制）

```
[Part3 Data Service 对接信息 - 最终版]

1) Base URL
https://5jo3ferouh.execute-api.ap-southeast-2.amazonaws.com/prod

2) 鉴权
Header:
Authorization: Bearer <id_token>
Content-Type: application/json

3) 已可用接口
- POST /data/media
- POST /query/tags
- POST /query/similar
- GET  /query/thumbnail?thumbnail_url=<url_encoded>
- POST /tags/bulk
- POST /files/delete

4) 请求示例
A. 查询标签（AND）
POST /query/tags
{
  "tags": {"koala": 1, "magpie": 1}
}

B. 相似查询（按 tags_map）
POST /query/similar
{
  "tags_map": {"koala": 1}
}

C. 缩略图反查原图
GET /query/thumbnail?thumbnail_url=https%3A%2F%2F...%2Fthumbnails%2Fdemo-koala.jpg

D. 批量加/减标签
POST /tags/bulk
{
  "urls": ["https://.../uploads/demo-koala.jpg"],
  "tags": {"wombat": 1},
  "operation": 1
}
# operation: 1=add, 0=remove

E. 删除文件
POST /files/delete
{
  "urls": ["https://.../uploads/demo-koala.jpg"]
}

5) 联调状态
- Cognito 鉴权已通
- 6 个核心 API 已实测可用
- 可开始 UI 接口接入与联调

6) 注意事项
- token 过期（默认 1h）需重新登录获取 id_token
- 所有接口均需 Bearer token
- /query/thumbnail 的参数需 URL encode
```

---

## 5) 建议后续动作

- D 组先接：`/query/tags`、`/query/thumbnail`（最容易先做 UI 展示）
- 再接：`/tags/bulk`、`/files/delete`（管理功能）
- 最后接：`/query/similar`（文件上传后相似检索）

