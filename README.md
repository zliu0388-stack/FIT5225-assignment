# FIT5225 Team102 - AWS Upload Pipeline

## Overview

This project implements a serverless upload pipeline using AWS services.

## Services Used

- Amazon Cognito
- Amazon S3
- AWS Lambda
- Amazon CloudWatch

## Architecture

User
→ Cognito Authentication
→ Upload File
→ Amazon S3 Bucket
→ Lambda Trigger
→ CloudWatch Logs

## S3 Trigger

Bucket:
fit5225-team102-aussie-ecolens

Prefix:
uploads/

Event:
s3:ObjectCreated:*

## Lambda

Function:
fit5225-upload-handler

Runtime:
Python 3.12
