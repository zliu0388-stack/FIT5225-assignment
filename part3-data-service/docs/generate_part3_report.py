# -*- coding: utf-8 -*-
"""
Part3 Data Service 交付文档 PDF 生成器 (FIT5225 Team102 / AussieEcoLens)

用法:
    python generate_part3_report.py

截图: 把图片放到本脚本同级的 screenshots/ 目录, 文件名见 SHOTS 定义。
存在则自动嵌入, 不存在则画一个占位框 (灰色), 方便后补。
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    PageBreak, KeepTogether, Flowable,
)
from reportlab.lib.utils import ImageReader

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS_DIR = os.path.join(HERE, "screenshots")
OUT_PDF = os.path.join(HERE, "Part3-Data-Service-Report.pdf")

# 注册中文字体 (reportlab 自带 CID 字体, 无需外部 ttf)
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
CN = "STSong-Light"
MONO = "Courier"

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName=CN, fontSize=16,
                    spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#1a3b6e"))
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName=CN, fontSize=12.5,
                    spaceBefore=10, spaceAfter=5, textColor=colors.HexColor("#23527c"))
BODY = ParagraphStyle("Body", parent=styles["BodyText"], fontName=CN, fontSize=10,
                      leading=15, spaceAfter=5, alignment=TA_LEFT)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8.5, textColor=colors.HexColor("#555555"))
CODE = ParagraphStyle("Code", parent=styles["Code"], fontName=MONO, fontSize=8.2,
                      leading=11, backColor=colors.HexColor("#f4f6f8"),
                      borderPadding=6, leftIndent=4, spaceAfter=6, textColor=colors.HexColor("#222222"))
CAP = ParagraphStyle("Cap", parent=BODY, fontSize=8.5, alignment=TA_CENTER,
                     textColor=colors.HexColor("#666666"), spaceBefore=3)

TITLE = ParagraphStyle("Title", parent=styles["Title"], fontName=CN, fontSize=22,
                       textColor=colors.HexColor("#13294b"), spaceAfter=4)
SUBTITLE = ParagraphStyle("Sub", parent=styles["Title"], fontName=CN, fontSize=12,
                          textColor=colors.HexColor("#5a6b85"), spaceAfter=2)

# 需要的截图清单: (文件名, 标题说明)
SHOTS = {
    "01_cfn_stack": "CloudFormation 栈 fit5225-team102-part3-data 状态 (CREATE/UPDATE_COMPLETE)",
    "02_lambda_functions": "Lambda 控制台 — Part3 的 6 个函数列表",
    "03_apigateway_routes": "API Gateway — DataApi 的资源/路由 (6 个端点 + Cognito 授权方)",
    "04_dynamodb_tables": "DynamoDB — 4 张表列表 (media-files / tag-index / thumb-lookup / tag-subscriptions)",
    "05_media_table_items": "DynamoDB media-files 表内的真实数据项 (含 tags_map / checksum)",
    "06_auth_401": "无 token 调用任一接口返回 401 (证明 Cognito 鉴权生效)",
    "07_query_tags_200": "POST /query/tags 返回 200 + items",
    "08_query_similar_200": "POST /query/similar 返回 200",
    "09_thumbnail_200": "GET /query/thumbnail 返回 200 (缩略图反查原图)",
    "10_bulk_tag_200": "POST /tags/bulk 返回 200 (标签增/减, tags_version 递增)",
    "11_delete_200": "POST /files/delete 返回 200 (deleted 列表)",
    "12_cloudwatch_logs": "CloudWatch — 某个 Part3 Lambda 的执行日志",
}

PAGE_W, PAGE_H = A4
CONTENT_W = PAGE_W - 36 * mm  # 左右各 18mm


def _find_shot(key):
    for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
        p = os.path.join(SHOTS_DIR, key + ext)
        if os.path.exists(p):
            return p
    return None


class Placeholder(Flowable):
    """缺失截图时画一个灰色占位框。"""
    def __init__(self, text, width=CONTENT_W, height=70 * mm):
        super().__init__()
        self.width = width
        self.height = height
        self.text = text

    def draw(self):
        c = self.canv
        c.saveState()
        c.setDash(4, 3)
        c.setStrokeColor(colors.HexColor("#b0b0b0"))
        c.setFillColor(colors.HexColor("#fafafa"))
        c.rect(0, 0, self.width, self.height, stroke=1, fill=1)
        c.setFillColor(colors.HexColor("#999999"))
        c.setFont(CN, 10)
        c.drawCentredString(self.width / 2, self.height / 2 + 6, "[ 待补充截图 ]")
        c.setFont(CN, 8)
        # 简单换行
        max_chars = 46
        line = self.text
        y = self.height / 2 - 8
        while line:
            seg = line[:max_chars]
            line = line[max_chars:]
            c.drawCentredString(self.width / 2, y, seg)
            y -= 11
        c.restoreState()


def shot_block(key):
    """返回截图 flowable (图片或占位框) + 图注。"""
    desc = SHOTS[key]
    path = _find_shot(key)
    items = []
    if path:
        try:
            ir = ImageReader(path)
            iw, ih = ir.getSize()
            w = CONTENT_W
            h = w * ih / iw
            max_h = 110 * mm
            if h > max_h:
                h = max_h
                w = h * iw / ih
            img = Image(path, width=w, height=h)
            img.hAlign = "CENTER"
            items.append(img)
        except Exception:
            items.append(Placeholder(desc))
    else:
        items.append(Placeholder(desc))
    items.append(Paragraph("图: " + desc, CAP))
    items.append(Spacer(1, 6))
    return KeepTogether(items)


def code(text):
    safe = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("\n", "<br/>").replace(" ", "&nbsp;"))
    return Paragraph(safe, CODE)


def p(text):
    return Paragraph(text, BODY)


def h1(text):
    return Paragraph(text, H1)


def h2(text):
    return Paragraph(text, H2)


def make_table(data, col_widths=None, header=True):
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    ts = [
        ("FONTNAME", (0, 0), (-1, -1), CN),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cdd5df")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")]),
    ]
    if header:
        ts += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3b6e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 8.8),
        ]
    t.setStyle(TableStyle(ts))
    return t


def build():
    story = []

    # ── 封面 ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 40 * mm))
    story.append(Paragraph("FIT5225 Assignment 2", SUBTITLE))
    story.append(Paragraph("Part 3 — Data Service 技术交付文档", TITLE))
    story.append(Paragraph("AussieEcoLens · Serverless 野生动物媒体标注平台", SUBTITLE))
    story.append(Spacer(1, 14 * mm))
    meta = [
        ["团队", "Team 102"],
        ["区域 Region", "ap-southeast-2 (Sydney)"],
        ["CloudFormation 栈", "fit5225-team102-part3-data"],
        ["API Base URL", "https://5jo3ferouh.execute-api.ap-southeast-2.amazonaws.com/prod"],
        ["核心服务", "API Gateway · Lambda (Python 3.11) · DynamoDB · Cognito"],
    ]
    story.append(make_table(meta, col_widths=[40 * mm, CONTENT_W - 40 * mm], header=False))
    story.append(PageBreak())

    # ── 1. 概述 ─────────────────────────────────────────────────────────
    story.append(h1("1. 概述与职责"))
    story.append(p("Part 3 (Data Service) 是 AussieEcoLens 平台的<b>数据持久化与查询层</b>。"
                   "它对外提供一组经 Cognito 鉴权的 REST 接口, 接收 Part 2 (模型推理服务) 写入的"
                   "媒体标注结果, 并为 Part 4 (前端 / 通知 / 按图查询) 提供标签检索、缩略图反查、"
                   "批量改标签与删除等能力。整个服务以 AWS SAM 定义、Serverless 方式部署。"))
    story.append(p("<b>承担的职责:</b>"))
    for line in [
        "• 设计并维护 4 张 DynamoDB 表 (媒体主表 + 标签倒排索引 + 缩略图反查表 + 订阅表)。",
        "• 实现 6 个 Lambda 处理函数, 覆盖写入 (upsert)、查询、改标签、删除全流程。",
        "• 通过 API Gateway + Cognito Authorizer 暴露接口, 统一 Bearer JWT 鉴权。",
        "• 以最小权限 IAM 策略约束每个函数仅能访问其所需的表。",
        "• 为 Part 2 / Part 4 提供稳定的 API 契约 (api-contract.md)。",
    ]:
        story.append(p(line))

    # ── 2. 架构 ─────────────────────────────────────────────────────────
    story.append(h1("2. 系统架构与数据流"))
    story.append(p("Part 3 处于整个管线的中枢, 上游由 Part 2 写入, 下游由 Part 4 读取:"))
    story.append(code(
        "Part2 推理服务\n"
        "   │  (POST /data/media, Bearer JWT)\n"
        "   ▼\n"
        "API Gateway (DataApi, Cognito Authorizer, CORS *)\n"
        "   │\n"
        "   ├─ /data/media     → UpsertMediaFunction\n"
        "   ├─ /query/tags     → QueryTagsFunction\n"
        "   ├─ /query/similar  → QuerySimilarFunction\n"
        "   ├─ /query/thumbnail→ ThumbnailLookupFunction\n"
        "   ├─ /tags/bulk      → BulkTagFunction\n"
        "   └─ /files/delete   → DeleteFilesFunction\n"
        "          │\n"
        "          ▼\n"
        "DynamoDB: media-files | tag-index | thumb-lookup     S3 (删除原图/缩略图)\n"
        "          ▲\n"
        "          │  (查询/管理, Bearer JWT)\n"
        "Part4 前端 / 按图查询 / 通知"
    ))

    # ── 3. 数据模型 ─────────────────────────────────────────────────────
    story.append(h1("3. 数据模型 (DynamoDB)"))
    story.append(p("4 张表均为按需计费 (PAY_PER_REQUEST), 区域 ap-southeast-2。"))

    story.append(h2("3.1 media-files (媒体主表)"))
    story.append(p("主键 <b>media_id (HASH)</b>。记录每个媒体文件的全部元数据与标签。"))
    story.append(make_table([
        ["索引", "键", "用途"],
        ["主键", "media_id (S)", "媒体唯一标识 (UUID)"],
        ["GSI1_checksum", "checksum_sha256 (H) + created_at (R)", "按文件哈希做<b>去重</b>检索"],
        ["GSI2_file_url", "file_url (H)", "按文件 URL 反查 (删除/改标签用)"],
    ], col_widths=[34 * mm, 78 * mm, CONTENT_W - 112 * mm]))
    story.append(Spacer(1, 4))
    story.append(p("主要属性: owner_sub / owner_email / bucket / object_key / file_url / "
                   "thumbnail_url / media_type / checksum_sha256 / <b>tags_map (标签→次数)</b> / "
                   "tags_version / model_name / model_version / status (ACTIVE | DELETED) / "
                   "created_at / updated_at。删除采用<b>软删除</b> (status=DELETED)。"))

    story.append(h2("3.2 tag-index (标签倒排索引)"))
    story.append(p("主键 <b>tag (HASH) + media_id (RANGE)</b>。每个 (标签, 媒体) 一条记录, "
                   "支持按标签快速拉取媒体集合; 多标签 AND 查询通过对各标签结果集取交集实现。"))
    story.append(make_table([
        ["键", "类型", "说明"],
        ["tag", "S (HASH)", "标签名 (小写归一化)"],
        ["media_id", "S (RANGE)", "媒体 ID"],
        ["count / media_type / file_url / thumbnail_url / updated_at", "属性", "冗余字段, 查询免回主表"],
    ], col_widths=[70 * mm, 28 * mm, CONTENT_W - 98 * mm]))

    story.append(h2("3.3 thumb-lookup (缩略图反查表)"))
    story.append(p("主键 <b>thumbnail_url (HASH)</b>。前端拿到缩略图 URL 后反查原图 file_url / media_id。"))

    story.append(h2("3.4 tag-subscriptions (标签订阅表)"))
    story.append(p("主键 <b>tag (HASH) + subscriber (RANGE)</b>。由 Part 4 通知服务使用 (本表在 Part3 侧建立)。"))

    # ── 4. API ──────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(h1("4. API 接口规范"))
    story.append(p("Base URL: <font name='Courier'>https://5jo3ferouh.execute-api.ap-southeast-2."
                   "amazonaws.com/prod</font><br/>"
                   "所有接口均需请求头 <font name='Courier'>Authorization: Bearer &lt;id_token&gt;</font>。"))
    story.append(make_table([
        ["方法 + 路径", "功能", "Lambda"],
        ["POST /data/media", "写入/更新媒体与标签 (upsert)", "UpsertMediaFunction"],
        ["POST /query/tags", "多标签 AND + 最小次数查询", "QueryTagsFunction"],
        ["POST /query/similar", "按 tags_map 相似检索", "QuerySimilarFunction"],
        ["GET  /query/thumbnail", "缩略图 URL 反查原图", "ThumbnailLookupFunction"],
        ["POST /tags/bulk", "批量加/减标签 (operation 1/0)", "BulkTagFunction"],
        ["POST /files/delete", "删除文件 (软删 + 清 S3/索引)", "DeleteFilesFunction"],
    ], col_widths=[52 * mm, 60 * mm, CONTENT_W - 112 * mm]))

    story.append(h2("4.1 请求示例"))
    story.append(p("查询标签 (AND):"))
    story.append(code('POST /query/tags\n{ "tags": { "koala": 2, "magpie": 1 } }'))
    story.append(p("批量改标签:"))
    story.append(code('POST /tags/bulk\n{ "urls": ["https://.../uploads/x.jpg"],\n'
                      '  "tags": { "wombat": 1 }, "operation": 1 }   // 1=add, 0=remove'))
    story.append(p("错误码约定: <b>400</b> 参数错误 · <b>401</b> 未鉴权/Token 过期 · "
                   "<b>404</b> 资源不存在 · <b>500</b> 服务内部错误。"))

    # ── 5. 安全 ─────────────────────────────────────────────────────────
    story.append(h1("5. 安全与鉴权"))
    for line in [
        "• <b>Cognito JWT 鉴权</b>: API Gateway 配置 CognitoAuthorizer (User Pool "
        "ap-southeast-2_NgrJbyS3q), 每个请求校验 Bearer id_token, 未带/过期返回 401。",
        "• <b>最小权限 IAM</b>: 每个 Lambda 仅授予其所需表的 CRUD/Read 策略 "
        "(如 QueryTags 只读 media/tag-index; DeleteFiles 额外授予 S3 删除权限)。",
        "• <b>CORS</b>: AllowOrigin '*', 允许前端 (含后续迁移到 Oracle Cloud 的前端) 跨域访问。",
        "• <b>软删除</b>: 删除将 status 置为 DELETED 并清理索引/缩略图/S3, 主表记录保留以便审计。",
    ]:
        story.append(p(line))

    # ── 6. 部署 ─────────────────────────────────────────────────────────
    story.append(h1("6. 部署 (AWS SAM)"))
    story.append(p("使用 SAM 模板 template.yaml 定义全部资源, 一键构建/部署:"))
    story.append(code("sam build\n"
                      "sam deploy --stack-name fit5225-team102-part3-data \\\n"
                      "  --region ap-southeast-2 --capabilities CAPABILITY_IAM"))
    story.append(p("部署结果: <font name='Courier'>Successfully created/updated stack - "
                   "fit5225-team102-part3-data</font>。下列截图为部署后的控制台证据。"))
    story.append(shot_block("01_cfn_stack"))
    story.append(shot_block("02_lambda_functions"))
    story.append(PageBreak())
    story.append(shot_block("03_apigateway_routes"))
    story.append(shot_block("04_dynamodb_tables"))
    story.append(PageBreak())
    story.append(shot_block("05_media_table_items"))

    # ── 7. 测试与验证 ───────────────────────────────────────────────────
    story.append(h1("7. 测试与验证"))
    story.append(p("使用 Cognito 登录获取的 id_token 作为 Bearer, 对 6 个接口做了端到端联调, 结果如下:"))
    story.append(make_table([
        ["接口", "结果", "说明"],
        ["POST /data/media", "200", "写入媒体 + 标签索引 + 缩略图反查"],
        ["POST /query/tags", "200", "返回 items, 可查到目标媒体"],
        ["POST /query/similar", "200", "返回标签匹配的媒体"],
        ["GET  /query/thumbnail", "200", "缩略图 URL 反查到 file_url"],
        ["POST /tags/bulk", "200", "标签更新成功, tags_version 递增"],
        ["POST /files/delete", "200", "deleted 含目标 URL, not_found 为空"],
        ["(无 token)", "401", "Cognito 鉴权生效"],
    ], col_widths=[48 * mm, 22 * mm, CONTENT_W - 70 * mm]))
    story.append(Spacer(1, 6))
    story.append(p("<b>证据截图:</b>"))
    story.append(shot_block("06_auth_401"))
    story.append(shot_block("07_query_tags_200"))
    story.append(PageBreak())
    story.append(shot_block("08_query_similar_200"))
    story.append(shot_block("09_thumbnail_200"))
    story.append(PageBreak())
    story.append(shot_block("10_bulk_tag_200"))
    story.append(shot_block("11_delete_200"))
    story.append(PageBreak())
    story.append(shot_block("12_cloudwatch_logs"))

    # ── 8. 多云设计 ─────────────────────────────────────────────────────
    story.append(h1("8. 多云设计说明 (Part 4 迁移 Oracle Cloud)"))
    story.append(p("Part 4 (前端 / 通知 / 按图查询) 后续将迁移至 Oracle Cloud。经评估, "
                   "<b>Part 3 无需改动任何代码</b>:"))
    for line in [
        "• CORS 已为 '*', 前端迁到 Oracle 任意域名都能跨域调用 Part3。",
        "• Cognito 用户池在 AWS, 前端 (任意来源) 仍可正常登录, JWT 跨云调用 Part3 一样通过校验。",
        "• 按图查询为服务端到服务端的 HTTPS 调用 (调用 /query/similar), 跨云可直接打通。",
        "• 唯一注意点: 若 Part4 通知 Notifier 迁到 OCI, 它无法直接消费 AWS DynamoDB Stream, "
        "需 Part4 侧加转发桥; Part3 仅需保持 media-files 表的 Stream 开启。",
    ]:
        story.append(p(line))

    # ── 附录 ────────────────────────────────────────────────────────────
    story.append(h1("附录 A. 联调命令 (可复用)"))
    story.append(code(
        'API_BASE="https://5jo3ferouh.execute-api.ap-southeast-2.amazonaws.com/prod"\n\n'
        '# Query By Tags\n'
        'curl -i -X POST "$API_BASE/query/tags" \\\n'
        '  -H "Authorization: Bearer $TOKEN" \\\n'
        '  -H "Content-Type: application/json" \\\n'
        '  -d \'{"tags":{"koala":1}}\'\n\n'
        '# Bulk Tag (add)\n'
        'curl -i -X POST "$API_BASE/tags/bulk" \\\n'
        '  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \\\n'
        '  -d \'{"urls":["..."],"tags":{"wombat":1},"operation":1}\''
    ))

    doc = SimpleDocTemplate(
        OUT_PDF, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title="FIT5225 Part3 Data Service Report", author="Team 102",
    )

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont(CN, 8)
        canvas.setFillColor(colors.HexColor("#999999"))
        canvas.drawString(18 * mm, 9 * mm, "FIT5225 A2 · Team102 · Part3 Data Service")
        canvas.drawRightString(PAGE_W - 18 * mm, 9 * mm, "第 %d 页" % d.page)
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print("PDF generated:", OUT_PDF)

    missing = [k for k in SHOTS if _find_shot(k) is None]
    if missing:
        print("\n缺少以下截图 (放入 screenshots/ 后重跑):")
        for k in missing:
            print("  - %s.png  →  %s" % (k, SHOTS[k]))
    else:
        print("所有截图已就绪。")


if __name__ == "__main__":
    os.makedirs(SHOTS_DIR, exist_ok=True)
    build()
