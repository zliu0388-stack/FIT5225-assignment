# FIT5225 Assignment 2 — Individual Report

**Name:** [Your Name]   **Student ID:** [Your ID]   **Team:** 102 — AussieEcoLens

> Submission note: per the brief, use Arial / Helvetica / Times New Roman at 12 pt when
> exporting to PDF. Tables, diagrams, screenshots and references are excluded from the word
> count. Replace all `[...]` placeholders before submitting.

---

## My Role and Contribution (~150 words)

My primary responsibility was the **Part 3 Data Service**, the platform's persistence and
query layer. I designed the DynamoDB data model — a `media-files` master table with two
global secondary indexes (a checksum index for deduplication and a `file_url` index for
lookup/delete), a `tag-index` inverted table that powers logical-AND tag queries, plus
`thumb-lookup` and `tag-subscriptions` tables. I then implemented six Cognito-secured REST
endpoints (upsert, query-by-tags, query-similar, thumbnail lookup, bulk tag add/remove, and
delete) on API Gateway + Lambda (Python), each scoped with least-privilege IAM, and deployed
the stack via AWS SAM.

Beyond my own part, I **containerised and deployed the Part 2 model service**: I authored its
Dockerfile, resolved the Python dependency and runtime conflicts that blocked the image, and
shipped it as a Lambda container image, then drove the Part 2 → Part 3 end-to-end integration
and testing. The detection/classification model itself was designed by my teammate; my work
there was packaging, deployment and integration.

## Reflection on Teamwork (~150 words)

We split the system cleanly along the upload → tag → store → query → notify pipeline, which
let us work in parallel. My Part 2 teammate, [Teammate A], built the wildlife detection and
species-classification pipeline; [Teammate B] delivered the front end, tag-based notifications
and query-by-file on our secondary cloud. Agreeing on a written API contract early meant the
pieces integrated with few surprises.

Our hardest challenge was getting the Part 2 container Lambda to actually run — conflicting
dependencies (protobuf/setuptools, missing system libraries, module name shadowing) cost real
time to resolve. The multi-cloud requirement also forced us to think carefully about passing
AWS Cognito tokens to the secondary cloud, and short-lived tokens complicated longer demos.

Overall the team communicated well and unblocked each other; for example, I helped get Part 2
deployed so the front end could display real tagged data. I am happy with how we collaborated.

---

*Word count (two assessed sections): ~300 words — within the 500-word limit. Trim/expand the
bracketed details as needed.*
