# Environment: dev-ocp — CineHome

Cluster **OpenShift** `ocp01.npd.co` · Repo **`movie-web`** · Branch **`main`**.

| Service | URL |
|---------|-----|
| CineHome | https://cinehome.apps.ocp01.npd.co |
| MinIO Console | https://minio-console-minio.apps.ocp01.npd.co |
| ArgoCD | https://argocd-server-argocd.apps.ocp01.npd.co |
| Harbor | https://harbor-platform.apps.ocp01.npd.co |
| Jenkins | https://jenkins-platform.apps.ocp01.npd.co |
| Vault | https://vault-platform.apps.ocp01.npd.co |

AppProject: **`cinehome-platform`**

## Apply

```bash
export ARGOCD_NS=argocd
oc apply -f phase9-gitops-platform/environments/dev-ocp/appproject.yaml -n $ARGOCD_NS
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/platform-app-of-apps.yaml -n $ARGOCD_NS
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/platform-routes-app-of-apps.yaml -n $ARGOCD_NS
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/infra-app-of-apps.yaml -n $ARGOCD_NS
# Sau CI:
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/cinehome-app-of-apps.yaml -n $ARGOCD_NS
```

Chi tiết: [../../OCP-DEPLOY-GUIDE.md](../../OCP-DEPLOY-GUIDE.md)

## Runbook

| Doc | Nội dung |
|-----|----------|
| [DISK-MONITORING.md](./DISK-MONITORING.md) | PVC/NFS, độ nở dữ liệu, disk master/worker, retention |
| [INSTALL-TROUBLESHOOTING.md](./INSTALL-TROUBLESHOOTING.md) | Lỗi SCC, Harbor, Vault, NFS |
| [INSTALL-NFS-CSI.md](./INSTALL-NFS-CSI.md) | Cài NFS CSI |
