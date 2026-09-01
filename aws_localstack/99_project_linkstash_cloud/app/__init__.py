"""linkstash-cloud — the cloud-native storage layer for the linkstash app.

The same link shortener from the CI/CD & OpenTofu courses, but its data lives in
AWS services: links in DynamoDB, backups in S3, events on SQS. Everything runs
against Floci, so it's real AWS SDK code with zero cloud bill.
"""

__version__ = "1.0.0"
