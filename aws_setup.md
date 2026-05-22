# FIT5225 Team102 - AWS Infrastructure Setup

## Overview

This document describes the AWS infrastructure configuration for Team102 AussieEcoLens.

The infrastructure includes:

- AWS Cognito authentication
- IAM roles and permissions
- Amazon S3 storage
- AWS Lambda trigger processing
- CloudWatch logging

Region used:

ap-southeast-2 (Sydney)

---

# 1. Cognito Authentication

## Cognito User Pool

Used for:

- User registration
- Email verification
- Login/logout
- Token generation

## Hosted UI

Managed login page is enabled through Cognito Hosted UI.

Authentication flow:

Register -> Email Verification -> Login -> Token Issued

## App Client

App client created:

fit5225-team102-ui-v2

Authentication type:

Choice-based sign-in
Secure Remote Password (SRP)

## Token Usage

Frontend should send token using:

Authorization: Bearer <id_token>

---

# 2. IAM Configuration

## Lambda Execution Role

Role created:

fit5225-team102-lambda-role

Permissions include:

- CloudWatch logging
- S3 access
- Lambda execution

---

# 3. S3 Storage

## Bucket

Bucket name:

fit5225-team102-aussie-ecolens

Region:

ap-southeast-2

## Folder Structure

uploads/
thumbnails/
temp/

## Recommended Upload Path

uploads/{username}/{filename}

Example:

uploads/cherry/kangaroo.jpg

---

# 4. Lambda Trigger

## Lambda Function

Function name:

fit5225-upload-handler

Runtime:

Python 3.12

## Trigger

S3 event trigger:

s3:ObjectCreated:*

Trigger prefix:

uploads/

## Current Function Behavior

Current Lambda verifies that uploaded files can be detected successfully from S3.

CloudWatch logs confirm:

File loaded successfully

---

# 5. CloudWatch Logging

CloudWatch log group:

/aws/lambda/fit5225-upload-handler

Used for:

- Trigger debugging
- Upload monitoring
- Lambda execution tracking

---

# 6. Team API / Interface Agreement

## Authentication Header

Authorization: Bearer <id_token>

## S3 File Structure

uploads/{username}/{filename}
thumbnails/{username}/{filename}

## Recommended API Response Format

{
  "success": true,
  "file_url": "https://...",
  "thumbnail_url": "https://..."
}

---

# 7. GitHub Repository

Repository:

https://github.com/zliu0388-stack/FIT5225-assignment

---

# Status

Completed:

- Cognito setup
- Hosted login UI
- IAM role configuration
- S3 bucket creation
- Lambda trigger integration
- CloudWatch logging
- GitHub repository integration

Pending future integration:

- API Gateway
- ML tagging Lambda
- Thumbnail generation Lambda
- Video frame extraction Lambda
- Oracle Cloud integration
