# Giai đoạn 9: GitOps Platform — CineHome

Phase 9 gom **platform** (Jenkins, Harbor, Vault, ESO) và **luồng GitOps** cho **CineHome** trên OpenShift.

> Trước đây mẫu app là banking-demo. Repo `movie-web` dùng Phase 9 cho **CineHome** (`npd-movie` + MinIO).

## Mục tiêu

- Mọi thứ trong cluster, trừ repo GitHub (`kevinram164/movie-web`).
- **CI**: Shared Library `cinehome` → Kaniko → Harbor project `movie-web`.
- **CD**: ArgoCD App of Apps → Helm/manifests; tag image trong `gitops/values-images.yaml`.
- **Secret**: Vault + ESO (Harbor pull → ns `npd-movie`).

## Namespace

| Namespace | Nội dung |
|-----------|----------|
| `argocd` | ArgoCD |
| `platform` | Jenkins, Harbor |
| `vault` / `external-secrets` | Vault + ESO |
| `postgres` | Postgres (DB `movie`) |
| `redis` | Redis (cache/session v2) |
| `minio` | MinIO buckets `movies`, `posters` |
| `npd-movie` | movie-api, movie-web |
| `observability` / `linkerd*` | Tuỳ chọn |

## Luồng hàng ngày

```text
git push main (apps/**)
  → Jenkins cinehomePipeline (BUILD_TARGET=auto|all)
  → Kaniko → harbor.../movie-web/movie-api|movie-web:<sha>
  → commit gitops/values-images.yaml
  → ArgoCD sync cinehome → rollout npd-movie
```

## Thư mục quan trọng

```text
phase9-gitops-platform/     # Platform + ArgoCD glue
apps/                       # movie-api, movie-web
charts/movie/               # Helm app
deploy/argocd/              # MinIO + cinehome Applications
deploy/routes/              # OpenShift Routes
gitops/values-images.yaml   # CI bump tags
jenkins-shared-library/     # cinehomePipeline
```

AppProject: **`cinehome-platform`**.

Chi tiết feature / Kafka v2: [ARCHITECTURE.md](../ARCHITECTURE.md).
