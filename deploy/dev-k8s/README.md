# CineHome — dev-k8s

GitOps cho CineHome trên cụm kubeadm NPD. Platform và infra (Vault, Harbor, Jenkins, Postgres, Redis, MinIO, OTEL) do repo [cloud-native-platform](https://github.com/kevinram164/cloud-native-platform) quản lý, xem `phase9-gitops-platform/K8S-DEPLOY-GUIDE.md`. Thư mục `deploy/argocd`, `deploy/minio*`, `deploy/routes`, `deploy/mesh` là của cụm OCP, dev-k8s không dùng.

## Cấu trúc

| Đường dẫn | Nội dung |
|-----------|----------|
| `argocd/appproject.yaml` | AppProject `cinehome` (repo này, ns `npd-movie` + `postgres`) |
| `argocd/app-of-apps.yaml` | Root `cinehome-root-dev-k8s` |
| `argocd/applications/` | `cinehome-db-init` (wave 0), `cinehome` (1), `cinehome-ingress` (2), `cinehome-cloudflared` (3) |
| `manifests/db-init/` | PreSync Job tạo/ALTER DB + user `movie` trên `postgres-ha` |
| `manifests/ingress/` | `npd-movie.co` → `movie-web:8080` (class `haproxy`) |
| `manifests/cloudflared/` | Tunnel `cinehome.automationecom.click` |
| `values/values-dev-k8s.yaml` | Bật Vault Agent, CORS |
| `values/values-images.yaml` | Image `npd-harbor.co/movie-web/*` — Jenkins bump `tag` |
| `values/values-observability.yaml` | OTEL → collector ns `observability` |

Luồng truy cập:

```
Internet ── cinehome.automationecom.click ── Cloudflare ── cloudflared (npd-movie) ──┐
LAN ─────── npd-movie.co ── f5-lb ── HAProxy ingress ─────────────────────────────────┤
                                                                                     ▼
                         movie-web:8080 (Next.js) ── /api ──► movie-api:8080 ──► postgres-ha, redis-ha, MinIO
                                                  └─ /media ─► minio.minio.svc:9000 (bucket movies, posters)
                         media-worker ◄── Redis queue cinehome:media:jobs ── ffmpeg → MinIO
```

## Secret qua Vault Agent Injector

| Vault (KV v2) | Role | SA (namespace) | Dùng cho |
|---------------|------|----------------|----------|
| `secret/cinehome/app` `{DATABASE_URL, REDIS_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY}` | `cinehome-app` | `movie-api`, `media-worker` (npd-movie) | `/vault/secrets/env`, container chạy `. /vault/secrets/env && exec ...` |
| `secret/cinehome/movie-db` `{password}` | `cinehome-db-init` | `movie-db-init` (postgres) | Password user `movie` |
| `secret/cinehome/cloudflared` `{token}` | `cinehome-cloudflared` | `cloudflared` (npd-movie) | `/vault/secrets/token` → `cloudflared --token-file` |
| `secret/cinehome/harbor-pull` `{registry, username, password}` | — | — | `create-harbor-pull-secret.sh` → Secret `harbor-pull-creds` |
| `secret/cinehome/harbor` `{username, password}` | `jenkins-kaniko` | — | Jenkins push image |

Đổi secret trong Vault thì restart deployment tương ứng.

## Triển khai

Vault dùng lại data OCP nên `secret/cinehome/*` thường đã có. Kiểm tra trước, chỉ `put` khi thiếu hoặc sai (`harbor-pull.registry` phải là `npd-harbor.co`, `cloudflared` phải có key `token`):

```bash
v() { kubectl exec -i -n vault vault-0 -- env VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN="$VAULT_TOKEN" vault "$@"; }
for p in app movie-db cloudflared harbor harbor-pull; do echo "== $p"; v kv get -format=json secret/cinehome/$p | jq -r '.data.data | keys[]'; done
v kv get -field=registry secret/cinehome/harbor-pull

# Key tunnel cũ tên khác (vd. tunnel_token) → copy sang key token
# v kv patch secret/cinehome/cloudflared token="$(v kv get -field=<key-cũ> secret/cinehome/cloudflared)"

# Mật khẩu movie phải khớp DATABASE_URL. Redis/MinIO dùng chung với platform.
v kv put secret/cinehome/movie-db username=movie password='<movie-pw>' database=movie
v kv put secret/cinehome/app \
  DATABASE_URL='postgresql+psycopg2://movie:<movie-pw>@postgres-ha-postgresql-primary.postgres.svc.cluster.local:5432/movie' \
  REDIS_URL='redis://:Mbfs%402025@redis-ha.redis.svc.cluster.local:6379/0' \
  MINIO_ACCESS_KEY='minioadmin' MINIO_SECRET_KEY='<minio-root-pw>'
# Token tunnel: Zero Trust → Networks → Tunnels → <tunnel> → Configure → token (hoặc lấy từ Vault OCP secret/cinehome/cloudflared)
v kv put secret/cinehome/cloudflared token='<tunnel-token>'
v kv put secret/cinehome/harbor-pull registry=npd-harbor.co username='robot$movie-web+k8s-pull' password='<token>'
v kv put secret/cinehome/harbor username='robot$movie-web+ci-push' password='<token>'

# Policy/role cinehome-*, rồi pull secret cho npd-movie
bash cloud-native-platform/phase9-gitops-platform/environments/dev-k8s/scripts/vault-setup-k8s-auth.sh
VAULT_PATH=secret/cinehome/harbor-pull NAMESPACES=npd-movie \
  bash cloud-native-platform/phase9-gitops-platform/environments/dev-k8s/scripts/create-harbor-pull-secret.sh

kubectl apply -f deploy/dev-k8s/argocd/appproject.yaml
kubectl apply -f deploy/dev-k8s/argocd/app-of-apps.yaml
```

## Chuyển tunnel từ OCP

Cùng một tunnel (cùng token) chạy connector ở hai cụm thì Cloudflare chia request cho cả hai. Trước khi bật trên dev-k8s:

```bash
# Trên OCP: tắt auto-sync root + app cloudflared rồi scale 0 (selfHeal sẽ kéo lại nếu chỉ scale)
oc -n argocd patch application cinehome-app-of-apps-dev-ocp --type merge -p '{"spec":{"syncPolicy":null}}'
oc -n argocd patch application cinehome-cloudflared --type merge -p '{"spec":{"syncPolicy":null}}'
oc -n npd-movie scale deploy/cloudflared --replicas=0
```

Trên Zero Trust dashboard, public hostname `cinehome.automationecom.click` giữ nguyên service `http://movie-web.npd-movie.svc.cluster.local:8080` (cùng tên Service/namespace trên dev-k8s). Mọi connector của một tunnel nhận request cho mọi hostname của tunnel đó, nên tunnel này chỉ nên chứa hostname của CineHome; hệ thống khác dùng tunnel riêng. Tab Connectors chỉ nên còn các pod `cloudflared` của dev-k8s.

## Kiểm tra

```bash
kubectl -n postgres logs job/movie-db-init -c init
kubectl -n npd-movie get pods
kubectl -n npd-movie logs deploy/movie-api -c vault-agent-init
kubectl -n npd-movie logs deploy/cloudflared | grep -i "Registered tunnel connection"
curl -sk https://npd-movie.co/api/health
curl -sI https://cinehome.automationecom.click
```

| Triệu chứng | Kiểm tra |
|-------------|----------|
| Pod kẹt `Init` (`vault-agent-init`) | Chưa seed `secret/cinehome/*` hoặc chưa chạy lại `vault-setup-k8s-auth.sh` |
| `ImagePullBackOff` | Secret `harbor-pull-creds` trong `npd-movie`; robot `movie-web+k8s-pull` còn hạn |
| movie-api `password authentication failed for user "movie"` | `secret/cinehome/movie-db.password` khác mật khẩu trong `DATABASE_URL`; sync lại `cinehome-db-init` |
| cloudflared `Provided Tunnel token is not valid` | Token sai/đã rotate; `--token-file` cần cloudflared >= 2025.4.0 |
| Cloudflare `1033` / `502` | cloudflared chưa connect, hoặc public hostname trỏ sai service |
| Video/poster 404 | Bucket `movies`/`posters` (Job `minio-bucket-init` ở platform), `MEDIA_PROXY_TARGET` |
