#!/usr/bin/env bash
# Builds the gateway image, boots a local kind cluster if needed, deploys the
# stable/canary split from k8s/, and proves the traffic split by sampling
# /health through the shared Service. Requires: docker, kind, kubectl, and a
# local `ollama serve` reachable from Docker Desktop.
set -euo pipefail

CLUSTER_NAME="llmops-demo"
NAMESPACE="llmops"
IMAGE="llmops-gateway:latest"
SAMPLES="${SAMPLES:-50}"

cd "$(dirname "$0")/.."

if ! kind get clusters | grep -qx "$CLUSTER_NAME"; then
  echo "==> Creating kind cluster $CLUSTER_NAME"
  kind create cluster --name "$CLUSTER_NAME"
fi

echo "==> Building $IMAGE"
docker build -t "$IMAGE" .

echo "==> Loading image into kind"
kind load docker-image "$IMAGE" --name "$CLUSTER_NAME"

echo "==> Applying manifests"
kubectl apply -f k8s/namespace.yaml -f k8s/configmap.yaml \
  -f k8s/deployment-stable.yaml -f k8s/deployment-canary.yaml -f k8s/service.yaml

kubectl -n "$NAMESPACE" rollout status deployment/gateway-stable --timeout=120s
kubectl -n "$NAMESPACE" rollout status deployment/gateway-canary --timeout=120s

echo "==> Sampling $SAMPLES requests through the Service"
kubectl -n "$NAMESPACE" delete pod trafficgen --ignore-not-found --now >/dev/null
kubectl -n "$NAMESPACE" run trafficgen --image=curlimages/curl --restart=Never -- sleep 3600 >/dev/null
kubectl -n "$NAMESPACE" wait --for=condition=Ready pod/trafficgen --timeout=60s >/dev/null

kubectl -n "$NAMESPACE" exec trafficgen -- sh -c \
  "for i in \$(seq 1 $SAMPLES); do curl -s http://gateway.$NAMESPACE.svc:8080/health; echo; done" \
  | grep -o '"track":"[a-z]*"' | sort | uniq -c

echo "==> Cleaning up traffic generator pod"
kubectl -n "$NAMESPACE" delete pod trafficgen --now >/dev/null

echo "==> Done. Inspect further with: kubectl -n $NAMESPACE get deploy,pods"
echo "    Promote the canary:  kubectl -n $NAMESPACE scale deploy/gateway-canary --replicas=9 && kubectl -n $NAMESPACE scale deploy/gateway-stable --replicas=1"
echo "    Roll back the canary: kubectl -n $NAMESPACE scale deploy/gateway-canary --replicas=0"
echo "    Tear down: kind delete cluster --name $CLUSTER_NAME"
