# linkstash-cloud — run core AWS services locally with Floci, no cloud bill.
#   make install → python deps + awslocal/aws CLIs
#   make up      → start Floci (detached, waits for healthy)
#   make apply   → provision DynamoDB + S3 + SQS with OpenTofu
#   make seed    → run the boto3 demo (put/get/backup/events)
#   make verify  → list the created resources with awslocal
#   make test    → pytest integration tests against Floci
#   make down    → stop Floci

export AWS_ENDPOINT_URL ?= http://localhost:4566
export AWS_ACCESS_KEY_ID ?= test
export AWS_SECRET_ACCESS_KEY ?= test
export AWS_DEFAULT_REGION ?= us-east-1

TOFU ?= tofu

.PHONY: install up down apply destroy seed verify test

install:
	pip install -r requirements.txt awscli-local awscli

up:
	docker run -d --name floci -p 4566:4566 floci/floci:latest
	@until curl -sf http://localhost:4566/_localstack/health >/dev/null; do sleep 1; done
	@echo "Floci ready."

down:
	docker rm -f floci

apply:
	cd infra && $(TOFU) init && $(TOFU) apply -auto-approve

destroy:
	cd infra && $(TOFU) destroy -auto-approve

seed:
	python -m app.demo

verify:
	@echo "DynamoDB tables:" && awslocal dynamodb list-tables
	@echo "S3 buckets:"      && awslocal s3 ls
	@echo "SQS queues:"      && awslocal sqs list-queues

test:
	python -m pytest
