# FIT5225 Team102 Infrastructure Spec

## AWS Region
ap-southeast-2

## Cognito
- User Pool:
  - Client ID:
  - Hosted UI URL:
  
  ## S3
  Bucket:
  fit5225-team102-aussie-ecolens

Folders:
  - uploads/
  - thumbnails/
  - temp/
  
  ## Lambda Functions
  - fit5225-upload-handler

## API Gateway
Base URL:
  https://c801bncfa1.execute-api.ap-southeast-2.amazonaws.com

Routes:
  POST /upload

## Auth Token Format
Authorization: Bearer <JWT>
  
  ## Multi-cloud Design
  AWS Cognito JWT is forwarded to Oracle Cloud APIs for validation.