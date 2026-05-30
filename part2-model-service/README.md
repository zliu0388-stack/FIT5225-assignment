# Part 2 Model Service (Framework)

This folder provides a **minimal framework** for Part B:

- Triggered by S3 upload events
- Runs provided models (`mdv5a.pt` + `model.pt`) for image tagging
- Sends standardized media records to Part 3 `/data/media`

## Why this is a framework

This code focuses on integration boundaries and deployment structure first.
You can evolve model accuracy/performance later without changing external contracts.

## Expected flow

1. User uploads file to S3 `uploads/`
2. Lambda (`AutoTagFromS3Function`) is triggered by S3 event
3. Service downloads image from S3
4. Service runs detector + species classifier
5. Service builds `tags_map`
6. Service posts media record to Part 3 `POST /data/media`

## Environment variables

- `AWS_REGION` (default: `ap-southeast-2`)
- `PART3_UPSERT_URL` (required for writeback)
- `PART3_AUTH_TOKEN` (optional bearer token for protected Part 3 endpoint)
- `MODEL_BUCKET` (required when model files are not packaged)
- `MD_MODEL_KEY` (default: `models/mdv5a.pt`)
- `SPECIES_MODEL_KEY` (default: `models/model.pt`)
- `LABELS_KEY` (default: `models/labels.txt`)
- `MIN_DETECTION_CONF` (default: `0.2`)

## Local setup

Python 3.12 recommended.

```bash
pip install -r requirements.txt
```

## Notes

- `model.pt` and `mdv5a.pt` are expected to be private assets; do not commit them.
- Current implementation handles image files in the main path.
- Video support can be added later by introducing frame extraction before inference.
