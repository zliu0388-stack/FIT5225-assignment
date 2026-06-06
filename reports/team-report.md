# FIT5225 Assignment 2 — Team Report

**Team 102 — AussieEcoLens: A Multi-Cloud Serverless Wildlife Observation Platform**

| Member | Student ID |
|---|---|
| [Member 1 — Part 1] | [ID] |
| [Member 2 — Part B / Part 2] | [ID] |
| [You — Part 3] | [ID] |
| [Member 4 — Part D / Part 4] | [ID] |

**Source code:** [INSERT GitHub/GitLab repository link — share privately with the teaching team]

> Formatting note: export to PDF in Arial / Helvetica / Times New Roman, 12 pt. Per the brief,
> tables, the architecture diagram, UI screenshots and references are **excluded** from the
> 1000-word limit. Replace every `[...]` placeholder before submission.

---

## 1. Overview

AussieEcoLens is a serverless platform that lets users upload wildlife images and videos,
automatically tags the species detected using pre-trained ML models, stores the results in a
highly available database, and lets users search, manage and subscribe to tagged media. The
system is deployed across **two cloud providers**: AWS hosts authentication, storage, compute,
the database and messaging, while the secondary cloud (Oracle Cloud) hosts the front end and
its supporting services. AWS Cognito issues the identity tokens that authorise requests across
both clouds.

## 2. Architecture

> 🖼️ **[INSERT ARCHITECTURE DIAGRAM HERE — use official AWS and Oracle Cloud icons]**

The end-to-end flow is:

1. A user signs up / signs in through **AWS Cognito**; every page and API requires a valid JWT.
2. The user uploads a file, which is stored in an **Amazon S3** bucket (`uploads/` prefix).
3. The S3 event triggers the **Part 2 model-service Lambda** (a container image). It computes a
   SHA-256 checksum for **deduplication**, generates a **thumbnail**, runs **species detection**
   (extracting one frame per second for videos), and posts the detected tags plus file URLs to
   the Part 3 API.
4. **Part 3** persists media and tags in **Amazon DynamoDB** and exposes Cognito-secured REST
   APIs (via **API Gateway + Lambda**) for querying and management.
5. A **DynamoDB Stream** drives **tag-based notifications** through **Amazon SNS**.
6. The **front end** and **query-by-file** service run on the secondary cloud and call the AWS
   APIs by forwarding the Cognito JWT.

## 3. Design and Implementation Choices

**Authentication & authorisation.** We use AWS Cognito with API Gateway Cognito authorizers, so
every endpoint validates a Bearer JWT. Each Lambda is granted least-privilege IAM permissions
(only the tables/buckets it needs). The same JWT is forwarded to the secondary cloud to
authorise cross-cloud requests.

**Model handling.** The ML model and label file are loaded from S3 via environment variables, so
a new model version can be deployed **without changing source code**.

**File handling.** Duplicate uploads are rejected using a SHA-256 checksum. Image uploads
generate an aspect-ratio-preserving thumbnail; videos are sampled at **one frame per second** to
reduce processing while still detecting species across the clip.

**Data & queries.** DynamoDB stores a media master table plus an inverted **tag-index** table,
enabling efficient **logical-AND** tag queries with minimum counts. Global secondary indexes
support checksum and file-URL lookups for deduplication and deletion.

**Notifications.** New/updated media flow through a DynamoDB Stream to a notifier that publishes
to per-tag SNS topics, so users are emailed when their subscribed species appear.

**Query by file.** An uploaded query image is analysed (AWS Rekognition) and matched against the
database via the similar-media API, without persisting the query file.

## 4. Member Contributions

*(Excluded from the word count. Maximum 100 words per member.)*

| Name & Student ID | % | Elements contributed |
|---|---|---|
| [Member 1] — [ID] | 23% | **Part 1 – Authentication & Upload.** Configured the AWS Cognito user pool and app client; built sign-up, email verification, login and sign-out; implemented the file-upload API and S3 storage with client-side checksum and IAM roles. |
| [Member 2] — [ID] | 24% | **Part B – Model Service.** Designed the wildlife detection and species-classification inference pipeline (animal detector + species classifier), video frame extraction, and the tagging logic that produces the species tag counts. |
| [You] — [ID] | 28% | **Part 3 – Data Service** (full): DynamoDB schema (4 tables + GSIs), six Cognito-secured query/management APIs, least-privilege IAM, SAM deployment. **Also** containerised and deployed the Part 2 model service (Dockerfile, dependency/runtime fixes) and led the Part 2↔Part 3 end-to-end integration and testing. |
| [Member 4] — [ID] | 25% | **Part D – UI, Notifications & Query-by-File.** Built the full web front end (upload, search, manage, notifications pages), tag-based SNS email notifications, the query-by-file service, and the secondary-cloud hosting. |

## 5. User Guide (Testing the Application)

1. **Sign up** — open the app and register with email, first/last name and password.

   > 📷 **[SCREENSHOT: Sign-up page]**

2. **Verify & sign in** — confirm the email code, then log in.

   > 📷 **[SCREENSHOT: Login page]**

3. **Upload media** — drag-and-drop an image or video; a duplicate is detected automatically.

   > 📷 **[SCREENSHOT: Upload page — success + duplicate-detected states]**

4. **Auto-tagging result** — after a few seconds the file is tagged and a thumbnail is generated.

   > 📷 **[SCREENSHOT: Dashboard / gallery showing the tagged item + thumbnail]**

5. **Query by tags** — search e.g. `{"koala": 2, "magpie": 1}` (logical AND, minimum counts).

   > 📷 **[SCREENSHOT: Search results showing matching thumbnails]**

6. **Query by species** — search a single species, e.g. `dingo`, to find all matching media.

   > 📷 **[SCREENSHOT: Species query results]**

7. **Thumbnail lookup** — paste a thumbnail URL to retrieve the full-size file URL.

   > 📷 **[SCREENSHOT: Thumbnail lookup result]**

8. **Query by file** — upload an image; the system finds database media sharing its tags.

   > 📷 **[SCREENSHOT: Query-by-file result]**

9. **Bulk tag add/remove** — manually add or remove tags on selected files.

   > 📷 **[SCREENSHOT: Manage-tags page]**

10. **Delete files** — remove files and their thumbnails/records.

    > 📷 **[SCREENSHOT: Delete confirmation]**

11. **Tag notifications** — subscribe to a species and receive an email when new matching media
    is added.

    > 📷 **[SCREENSHOT: Notifications/subscription page + sample email]**

---

*Approx. assessed word count (Sections 1–3 and 5): ~750 words — within the 1000-word limit.
Tables, the architecture diagram, screenshots and references are excluded.*
