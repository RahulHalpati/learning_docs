# Convenience wrapper around the OpenTofu workflow.
#   make image    → build the linkstash image the config references
#   make init     → download the docker provider
#   make plan     → preview changes
#   make apply    → create/update the container
#   make verify   → curl the running service's /health
#   make destroy  → tear it all down
TOFU ?= tofu
APP_DIR := ../../../cicd_github_actions/99_project_cicd_pipeline

.PHONY: image init plan apply verify destroy fmt validate

image:
	docker build -t linkstash:local $(APP_DIR)

init:
	$(TOFU) init

fmt:
	$(TOFU) fmt -recursive

validate:
	$(TOFU) validate

plan:
	$(TOFU) plan

apply:
	$(TOFU) apply -auto-approve

verify:
	@curl -fsS $$($(TOFU) output -raw url)/health && echo " OK"

destroy:
	$(TOFU) destroy -auto-approve
