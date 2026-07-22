# Custom SCC theo ServiceAccount (dự phòng)

**Hướng chính:** [INSTALL-SCC-HARDENED.md](../INSTALL-SCC-HARDENED.md) — `namespace-scc-setup.sh` (UID range + `nonroot` cả namespace).

Chỉ dùng các file trong thư mục này khi **không patch được** UID vào dải namespace (image bắt buộc UID cố định).

| File | Khi nào |
|------|---------|
| `argocd-redis-scc.yaml` | Redis bắt buộc UID 999, không patch được |
| `argocd-dex-scc.yaml` | Giữ Dex SSO + không scale 0 |
| `harbor-scc.yaml` | Harbor UID 999/10000 (entrypoint `/harbor/entrypoint.sh`) |
| `jenkins-scc.yaml` | Jenkins bắt buộc UID 1000 (chart cũ) |
| `kong-scc.yaml` | Kong bắt buộc UID 1000 — `kong-scc-setup.sh` |

**Bitnami infra (NFS + UID 1001)** — GitOps prereq (không nằm trong thư mục này):

| Manifest / script | Namespace |
|-------------------|-----------|
| `gitops-platform/manifests/postgres-prereq/` + `scripts/postgres-scc-setup.sh` | `postgres` — SCC `postgres-uid1001` |
| `gitops-platform/manifests/redis-prereq/` + `scripts/redis-scc-setup.sh` | `redis` — SCC `redis-uid1001` |
| `deploy/minio-prereq/minio-scc.yaml` | `minio` — SCC `minio-uid1001` |

Không dùng `restricted-v2` cho các SA trên: NFS không tôn trọng fsGroup → data dir `2770` owner 1001 sẽ Permission denied.
