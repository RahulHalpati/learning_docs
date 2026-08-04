# Deploy linkstash to a local Kubernetes cluster (kind), end to end.
#   make cluster    → create a kind cluster
#   make image      → build the app image (from the CI/CD course)
#   make load       → load that image into the cluster (no registry needed)
#   make deploy     → kubectl apply the manifests
#   make verify     → port-forward + curl /health
#   make status     → pods / deployment / service
#   make restart    → rolling restart (watch zero-downtime)
#   make delete     → remove the app
#   make cluster-down → delete the cluster
CLUSTER ?= learn
IMAGE   ?= linkstash:local
APP_DIR := ../../cicd_github_actions/99_project_cicd_pipeline

.PHONY: cluster image load deploy verify status restart delete cluster-down all

cluster:
	kind create cluster --name $(CLUSTER)

image:
	docker build --load -t $(IMAGE) $(APP_DIR)

load:
	kind load docker-image $(IMAGE) --name $(CLUSTER)

deploy:
	kubectl apply -f manifests/
	kubectl -n linkstash rollout status deploy/linkstash --timeout=90s

status:
	kubectl -n linkstash get pods,deploy,svc -o wide

verify:
	@echo "port-forwarding svc/linkstash → localhost:8080 (Ctrl-C to stop after the check)"
	@kubectl -n linkstash port-forward svc/linkstash 8080:80 >/tmp/pf.log 2>&1 & \
	 PF=$$!; sleep 3; \
	 curl -fsS http://localhost:8080/health && echo " OK"; \
	 kill $$PF

restart:
	kubectl -n linkstash rollout restart deploy/linkstash
	kubectl -n linkstash rollout status deploy/linkstash

delete:
	kubectl delete -f manifests/ --ignore-not-found

cluster-down:
	kind delete cluster --name $(CLUSTER)

all: cluster image load deploy verify
