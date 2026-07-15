#!/usr/bin/env bash
# Apply CineHome GitOps apps lên ArgoCD (OCP)
set -euo pipefail

ARGOCD_NS="${ARGOCD_NS:-argocd}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# AppProject: cinehome-platform
# bash scripts/apply-cinehome.sh

echo "==> Update AppProject cinehome-platform"
oc apply -f "$ROOT/phase9-gitops-platform/environments/dev-ocp/appproject.yaml" -n "$ARGOCD_NS"

echo "==> CineHome App of Apps"
oc apply -f "$ROOT/phase9-gitops-platform/environments/dev-ocp/argocd/applications/cinehome-app-of-apps.yaml" -n "$ARGOCD_NS"

echo "Done. Mở ArgoCD → sync cinehome-app-of-apps"
echo "URLs:"
echo "  UI:     https://cinehome.apps.ocp01.npd.co"
echo "  MinIO:  https://minio-console-minio.apps.ocp01.npd.co"
echo "  API S3: https://minio-api-minio.apps.ocp01.npd.co"
