terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Point the REAL aws provider at Floci. Remove this whole endpoints/skip block
# and the identical config provisions real AWS. That's the only difference.
provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test" # Floci ignores creds; any value works
  secret_key                  = "test"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    dynamodb       = "http://localhost:4566"
    s3             = "http://localhost:4566"
    sqs            = "http://localhost:4566"
    secretsmanager = "http://localhost:4566"
    ssm            = "http://localhost:4566"
  }
}

# --- the link table ---
resource "aws_dynamodb_table" "links" {
  name         = "links"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "slug"

  attribute {
    name = "slug"
    type = "S"
  }
}

# --- backup bucket ---
resource "aws_s3_bucket" "backups" {
  bucket = "linkstash-backups"
}

# --- events queue ---
resource "aws_sqs_queue" "events" {
  name = "linkstash-events"
}

# --- config & secrets (12-factor: config lives in AWS, not in code) ---
resource "aws_secretsmanager_secret" "app" {
  name = "linkstash/secret-key"
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id     = aws_secretsmanager_secret.app.id
  secret_string = "dev-secret-rotate-me" # a real deploy injects this out-of-band
}

resource "aws_ssm_parameter" "links_table" {
  name  = "/linkstash/links-table"
  type  = "String"
  value = aws_dynamodb_table.links.name # non-secret config, resolved from the resource
}

output "table_name" { value = aws_dynamodb_table.links.name }
output "bucket_name" { value = aws_s3_bucket.backups.id }
output "queue_url" { value = aws_sqs_queue.events.url }
output "secret_name" { value = aws_secretsmanager_secret.app.name }
output "table_param" { value = aws_ssm_parameter.links_table.name }
