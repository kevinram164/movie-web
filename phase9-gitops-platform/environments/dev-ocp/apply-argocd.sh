#!/usr/bin/env bash
# Bootstrap ArgoCD GitOps — CineHome trên OpenShift
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

ARGOCD_NS="${ARGOCD_NS:-argocd}"
CLI="${CLI:-oc}"

echo "==> ArgoCD namespace: $ARGOCD_NS"
$CLI get ns "$ARGOCD_NS" >/dev/null 2>&1 || { echo "Namespace $ARGOCD_NS not found"; exit 1; }

echo "==> Apply AppProject cinehome-platform"
$CLI apply -f phase9-gitops-platform/environments/dev-ocp/appproject.yaml -n "$ARGOCD_NS"

echo "==> Apply root App of Apps (platform/infra/cinehome wrappers)"
$CLI apply -f phase9-gitops-platform/environments/dev-ocp/argocd/app-of-apps.yaml -n "$ARGOCD_NS"

echo "Done."
echo "  Root app : cinehome-platform-root-dev-ocp"
echo "  Branch   : main"
echo "  App      : cinehome-app-of-apps-dev-ocp (sau khi Harbor có image)"
echo "  UI       : https://cinehome.apps.ocp01.npd.co"
if [[ "$ARGOCD_NS" == "openshift-gitops" ]]; then
  echo "  ArgoCD   : https://openshift-gitops-server-openshift-gitops.apps.ocp01.npd.co"
else
  echo "  ArgoCD   : https://argocd-server-argocd.apps.ocp01.npd.co"
fi
