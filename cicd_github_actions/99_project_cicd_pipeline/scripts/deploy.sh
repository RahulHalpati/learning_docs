#!/usr/bin/env bash
# A MOCK deploy script. Real deploys differ wildly (kubectl, ECS, fly, ssh, ...),
# so this just prints what it would do — the pipeline shape is what matters.
# Replace the body with your platform's command.
set -euo pipefail

ENVIRONMENT="${1:?usage: deploy.sh <environment> <image>}"
IMAGE="${2:?usage: deploy.sh <environment> <image>}"

echo "→ Deploying ${IMAGE} to ${ENVIRONMENT}"
# e.g.  kubectl set image deploy/linkstash linkstash="${IMAGE}" -n "${ENVIRONMENT}"
#       flyctl deploy --image "${IMAGE}" --app "linkstash-${ENVIRONMENT}"
sleep 1
echo "✓ Deployed ${IMAGE} to ${ENVIRONMENT}"
