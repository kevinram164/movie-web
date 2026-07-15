# Harbor — CineHome (OpenShift)

Registry nội bộ: Jenkins Kaniko push → ArgoCD / kubelet pull.

| | |
|--|--|
| UI | https://harbor-platform.apps.ocp01.npd.co |
| Expose | OpenShift Route (`ocp-values/routes/harbor-route.yaml`) |
| Storage | `nfs-csi` |

## Sau khi sync `platform-harbor`

1. Đổi admin password.
2. Tạo project **`movie-web`**.
3. Robot accounts:
   - `ci-push` → Vault `secret/platform/harbor` (Kaniko — có thể dùng chung lab)
   - `k8s-pull` (project **movie-web**) → Vault **`secret/cinehome/harbor-pull`** → ESO → `harbor-pull-creds` (ns **`npd-movie`**)

> Banking đã dùng `secret/platform/harbor-pull` — **không ghi đè**. CineHome dùng path riêng.

```bash
vault kv put secret/cinehome/harbor-pull \
  registry='harbor-platform.apps.ocp01.npd.co' \
  username='robot$movie-web+k8s-pull' \
  password='<TOKEN>'
```

Trust TLS Harbor trên OCP: script `environments/dev-ocp/scripts/harbor-registry-trust-setup.sh`  
Chi tiết: [OCP-DEPLOY-GUIDE.md](../OCP-DEPLOY-GUIDE.md).
