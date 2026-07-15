# OCP Deploy Guide — CineHome (Phase 9)

Triển khai GitOps platform + **CineHome** trên OpenShift `ocp01.npd.co`.

Repo: `https://github.com/kevinram164/movie-web.git` (branch **`main`**)

## Tài liệu liên quan

| Doc | Mục đích |
|-----|----------|
| [../DEPLOY.md](../DEPLOY.md) | **Hướng dẫn triển khai CineHome đầy đủ (khuyên dùng)** |
| [README.md](./README.md) | Quick start giai đoạn |
| [PHASE9.md](./PHASE9.md) | Tổng quan namespace / luồng |
| [OCP-ARCHITECTURE.md](./OCP-ARCHITECTURE.md) | Sơ đồ Route / CI |
| [../ARCHITECTURE.md](../ARCHITECTURE.md) | Kiến trúc app + Kafka v2 |
| [../README.md](../README.md) | Upload HLS / MinIO |
| [environments/dev-ocp/INSTALL-NFS-CSI.md](./environments/dev-ocp/INSTALL-NFS-CSI.md) | NFS CSI |
| [environments/dev-ocp/INSTALL-ARGOCD-UPSTREAM.md](./environments/dev-ocp/INSTALL-ARGOCD-UPSTREAM.md) | ArgoCD + SCC |
| [jenkins-shared-library/README.md](../jenkins-shared-library/README.md) | CI `cinehome` |

## Nguyên tắc

**ArgoCD chỉ sync CineHome app ở giai đoạn cuối**, sau platform + infra + image trên Harbor.

| Giai đoạn | Việc | App? |
|-----------|------|------|
| 0 | NFS CSI `nfs-csi` | Không |
| 1 | ArgoCD + AppProject `cinehome-platform` | Không |
| 2 | Harbor, Vault, ESO, Jenkins + Routes | Không |
| 2b | Observability — **Coroot đã Healthy/Synced**, bỏ qua nếu còn dùng được | Không |
| 3 | Postgres, Redis — **Kong đã có (`infra-kong`), không apply lại** | Không |
| 4 | Jenkins Multibranch → Kaniko → Harbor `movie-web` | Không |
| 5 | `cinehome-app-of-apps` (MinIO + API/UI + Routes) | **Có** |

```text
Harbor / Vault / Jenkins     cinehomePipeline          cinehome-app-of-apps
Postgres / Redis             bump values-images.yaml   https://cinehome.apps.ocp01.npd.co
MinIO (giai đoạn 5)          Harbor movie-web/*
```

## Namespace map

| NS | Vai trò | URL / ghi chú |
|----|---------|---------------|
| `argocd` | ArgoCD | argocd-server-argocd.apps… |
| `platform` | Harbor, Jenkins | harbor-platform…, jenkins-platform… |
| `vault` | Vault | vault-platform… |
| `postgres` / `redis` | DB + cache | ClusterIP |
| `kong` | **Đã có** API gateway | tái dùng |
| `minio` | Object storage | minio-api-…, minio-console-… |
| `npd-movie` | CineHome app | **cinehome.apps.ocp01.npd.co** |
| `observability` | **Đã có** Coroot CE + operator | coroot-platform… |

## Giai đoạn 1 — ArgoCD + AppProject

Làm theo [INSTALL-ARGOCD-UPSTREAM.md](./environments/dev-ocp/INSTALL-ARGOCD-UPSTREAM.md).

```bash
export ARGOCD_NS=argocd
oc apply -f phase9-gitops-platform/environments/dev-ocp/appproject.yaml -n $ARGOCD_NS
```

Checkpoint: AppProject **`cinehome-platform`**; repo `movie-web` connected.

## Giai đoạn 2 — Platform

```bash
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/platform-app-of-apps.yaml -n $ARGOCD_NS
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/platform-routes-app-of-apps.yaml -n $ARGOCD_NS
```

### Harbor

1. UI Harbor → project **`movie-web`**
2. Robot push (CI) + pull (k8s) → seed Vault `platform/harbor`, `platform/harbor-pull` (như lab trước)
3. ESO tạo `harbor-pull-creds` trong **`npd-movie`** + `platform`  
   (`vault/external-secrets/harbor-pull-external-secret.yaml`)

```bash
oc create ns npd-movie --dry-run=client -o yaml | oc apply -f -
# Sau ESO sync:
oc get secret harbor-pull-creds -n npd-movie
```

Trust TLS Harbor: [INSTALL-TROUBLESHOOTING.md](./environments/dev-ocp/INSTALL-TROUBLESHOOTING.md) / script `harbor-registry-trust-setup.sh`.

### Jenkins

- Shared Library JCasC: name **`cinehome`**, path `jenkins-shared-library`
- Multibranch: repo `movie-web`, branch `main`, script `Jenkinsfile`
- SA `jenkins-kaniko` + Vault role (giữ như lab cũ)
- Lần đầu: **BUILD_TARGET=all**

## Giai đoạn 3 — Infra

```bash
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/infra-app-of-apps.yaml -n $ARGOCD_NS
```

Chỉ sync **Postgres + Redis** (values: `infra-values/`).  

**Kong:** cluster đã có `infra-kong` (Synced/Healthy) — **giữ nguyên**, không xoá / không deploy chồng.  
Sau này CineHome gắn Route `/api` → Kong → `movie-api` (JWT plugin, rate-limit).

**Coroot:** `observability-coroot-ce` + `observability-coroot-operator` đã Healthy — **giữ nguyên**. App `npd-movie` chỉ cần OTEL (nếu bật) trỏ collector sẵn có.

## Giai đoạn 4 — CI green

Pipeline stages:

```text
Checkout → Build movie-api → Build movie-web → Update GitOps
```

Harbor phải có:

- `movie-web/movie-api:<tag>`
- `movie-web/movie-web:<tag>`

## Giai đoạn 5 — CineHome

```bash
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/cinehome-app-of-apps.yaml -n $ARGOCD_NS
# hoặc: bash scripts/apply-cinehome.sh
```

Sync mang theo: MinIO, bucket policy, db-init Job, Helm cinehome, Routes.

Upload HLS: xem [../README.md](../README.md).

## Khác banking-demo

| Cũ (banking) | Mới (CineHome) |
|--------------|----------------|
| AppProject `banking-platform` | `cinehome-platform` |
| ns `npd-banking` | `npd-movie` + `minio` |
| Library `banking-demo` | `cinehome` |
| Harbor `banking-demo` | `movie-web` |
| Kong / Rabbit / Phase 8 services | Không dùng (MinIO + movie-api/web) |
| Branch `dev-ocp` trên banking-demo | Branch **`main`** trên movie-web |

Nếu cluster còn AppProject/Application banking cũ: xoá thủ công trên ArgoCD trước khi apply bộ CineHome để tránh lệch destination.
