# linkstash-cloud — run core AWS services locally with LocalStack, no cloud bill.
#   make install → python deps + localstack/awslocal CLIs
#   make up      → start LocalStack (detached)
#   make apply   → provision DynamoDB + S3 + SQS with OpenTofu
#   make seed    → run the boto3 demo (put/get/backup/events)
#   make verify  → list the created resources with awslocal
#   make test    → pytest integration tests against LocalStack
#   make down    → stop LocalStack

export AWS_ENDPOINT_URL ?= http://localhost:4566
export AWS_ACCESS_KEY_ID ?= test
export AWS_SECRET_ACCESS_KEY ?= test
export AWS_DEFAULT_REGION ?= us-east-1
export LOCALSTACK_ACKNOWLEDGE_ACCOUNT_REQUIREMENT ?= 1

TOFU ?= tofu

.PHONY: install up down apply destroy seed verify test

install:
	pip install -r requirements.txt localstack awscli-local awscli

up:
	localstack start -d
	localstack wait -t 60

down:
	localstack stop

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
