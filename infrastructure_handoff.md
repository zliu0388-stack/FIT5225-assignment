# FIT5225 Team102 Infrastructure Handoff

## AWS

### S3 Bucket
fit5225-team102-aussie-ecolens

### API Gateway Endpoint
https://c801bncfa1.execute-api.ap-southeast-2.amazonaws.com/upload

### Cognito

User Pool ID:
  ap-southeast-2_NgrJbyS3q

Client ID:
  5k2a9ipn97p3efqfev1gtl07r9

Region:
  ap-southeast-2

## Oracle Cloud

### VCN
fit5225-team102-vcn

### Subnet
fit5225-subnet

### Application
fit5225-team102-oracle-app

## Notes

- API Gateway is protected using Cognito JWT Authorizer
- Upload route:
  POST /upload
- Unauthorized requests are blocked automatically