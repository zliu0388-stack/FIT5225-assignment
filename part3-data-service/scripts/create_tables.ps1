param(
  [string]$Region = "ap-southeast-2",
  [string]$MediaTable = "fit5225-team102-media-files",
  [string]$TagIndexTable = "fit5225-team102-tag-index",
  [string]$ThumbLookupTable = "fit5225-team102-thumb-lookup",
  [string]$TagSubscriptionTable = "fit5225-team102-tag-subscriptions"
)

Write-Host "Creating DynamoDB tables in region: $Region"

aws dynamodb create-table `
  --table-name $MediaTable `
  --attribute-definitions `
      AttributeName=media_id,AttributeType=S `
      AttributeName=checksum_sha256,AttributeType=S `
      AttributeName=created_at,AttributeType=S `
      AttributeName=file_url,AttributeType=S `
  --key-schema `
      AttributeName=media_id,KeyType=HASH `
  --global-secondary-indexes '[
    {
      "IndexName":"GSI1_checksum",
      "KeySchema":[
        {"AttributeName":"checksum_sha256","KeyType":"HASH"},
        {"AttributeName":"created_at","KeyType":"RANGE"}
      ],
      "Projection":{"ProjectionType":"ALL"}
    },
    {
      "IndexName":"GSI2_file_url",
      "KeySchema":[
        {"AttributeName":"file_url","KeyType":"HASH"}
      ],
      "Projection":{"ProjectionType":"ALL"}
    }
  ]' `
  --billing-mode PAY_PER_REQUEST `
  --region $Region

aws dynamodb create-table `
  --table-name $TagIndexTable `
  --attribute-definitions `
      AttributeName=tag,AttributeType=S `
      AttributeName=media_id,AttributeType=S `
  --key-schema `
      AttributeName=tag,KeyType=HASH `
      AttributeName=media_id,KeyType=RANGE `
  --billing-mode PAY_PER_REQUEST `
  --region $Region

aws dynamodb create-table `
  --table-name $ThumbLookupTable `
  --attribute-definitions `
      AttributeName=thumbnail_url,AttributeType=S `
  --key-schema `
      AttributeName=thumbnail_url,KeyType=HASH `
  --billing-mode PAY_PER_REQUEST `
  --region $Region

aws dynamodb create-table `
  --table-name $TagSubscriptionTable `
  --attribute-definitions `
      AttributeName=tag,AttributeType=S `
      AttributeName=subscriber,AttributeType=S `
  --key-schema `
      AttributeName=tag,KeyType=HASH `
      AttributeName=subscriber,KeyType=RANGE `
  --billing-mode PAY_PER_REQUEST `
  --region $Region

Write-Host "Done. Verify tables with:"
Write-Host "aws dynamodb list-tables --region $Region"
