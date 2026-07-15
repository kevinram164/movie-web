# Phase 9 — GitOps Platform cho **CineHome** (OpenShift `dev-ocp`)

Platform CI/CD + infra + deploy web phim **CineHome** trên OCP.

**App code / Helm / Routes:** root repo (`apps/`, `charts/movie/`, `deploy/`)  
**Jenkins library:** root [`jenkins-shared-library/`](../jenkins-shared-library/) (`cinehome`)  
**Hướng dẫn OCP:** [OCP-DEPLOY-GUIDE.md](./OCP-DEPLOY-GUIDE.md)  
**Kiến trúc app:** [../ARCHITECTURE.md](../ARCHITECTURE.md)

## Thứ tự triển khai

| Giai đoạn | Nội dung | Deploy app? |
|-----------|----------|-------------|
| 0 | NFS CSI + StorageClass `nfs-csi` | Không |
| 1 | ArgoCD + AppProject `cinehome-platform` | Không |
| 2 | Platform: Harbor, Vault, ESO, Jenkins + Routes | Không |
| 2b | Observability — **đã có** Coroot (Healthy/Synced); OTEL/Linkerd tuỳ chọn | Không |
| 3 | Infra: Postgres, Redis — **Kong đã có** (`infra-kong`, giữ nguyên, không deploy lại) | Không |
| 4 | CI: Jenkins `cinehomePipeline` → Harbor `movie-web` | Không |
| 5 | ArgoCD `cinehome-app-of-apps` (MinIO + movie-api/web + Routes) | **Có** |

```bash
export ARGOCD_NS=argocd

oc apply -f phase9-gitops-platform/environments/dev-ocp/appproject.yaml -n $ARGOCD_NS

oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/platform-app-of-apps.yaml -n $ARGOCD_NS
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/platform-routes-app-of-apps.yaml -n $ARGOCD_NS
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/infra-app-of-apps.yaml -n $ARGOCD_NS

# Sau Jenkins build green:
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/cinehome-app-of-apps.yaml -n $ARGOCD_NS
```

## URL (ocp01.npd.co)

| Service | URL |
|---------|-----|
| CineHome | https://cinehome.apps.ocp01.npd.co |
| MinIO Console | https://minio-console-minio.apps.ocp01.npd.co |
| Harbor | https://harbor-platform.apps.ocp01.npd.co |
| Jenkins | https://jenkins-platform.apps.ocp01.npd.co |
| ArgoCD | https://argocd-server-argocd.apps.ocp01.npd.co |
| Vault | https://vault-platform.apps.ocp01.npd.co |

## Namespace

| Namespace | Nội dung |
|-----------|----------|
| `argocd` | ArgoCD |
| `platform` | Jenkins, Harbor |
| `vault` / `external-secrets` | Vault + ESO |
| `postgres` / `redis` | DB + cache |
| `minio` | Object storage HLS/poster |
| `kong` | **Đã có sẵn** — API gateway (tái dùng cho `/api` sau) |
| `npd-movie` | movie-api, movie-web |
| `observability` | **Đã có** Coroot CE + Operator |

## Cấu trúc ArgoCD

```text
platform-app-of-apps      → harbor, vault, ESO, jenkins
platform-routes           → Routes platform
infra-app-of-apps         → postgres, redis
cinehome-app-of-apps      → deploy/argocd (MinIO, cinehome, routes, db-init)
```

Chi tiết Phase 9: [PHASE9.md](./PHASE9.md)
