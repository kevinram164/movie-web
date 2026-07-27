# Observability — Coroot / OTEL / Linkerd (OpenShift)

Lab **chỉ OCP**. Coroot trên cluster hiện **đã Healthy** (`observability-coroot-ce` + operator) → **không cần sync lại**.

## Trên OCP (đang chạy)

| Thành phần | Namespace | Ghi chú |
|------------|-----------|---------|
| Coroot CE + Operator | `observability` | Giữ nguyên |
| OTEL Collector | `observability` | Tuỳ chọn |
| Linkerd | `linkerd` / `linkerd-viz` | Tuỳ chọn + SCC |

Route Coroot: xem `environments/dev-ocp/ocp-values/routes/coroot-route.yaml`.

## Khi nào apply observability-app-of-apps?

Chỉ khi cài **mới** hoặc sửa values. Tránh apply lên cluster đã ổn định nếu không chủ đích.

```bash
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/observability-app-of-apps.yaml -n argocd
```

Values OCP (nfs-csi): `values-*-ocp.yaml` trong thư mục này.

## CineHome

App `npd-movie` sends OTLP via `gitops/values-observability.yaml` (movie-api + media-worker).
Same path as banking: collector → Coroot + Instana. Frontend nginx SPA uses Coroot eBPF + API traces.

```bash
# After rebuild movie-api / media-worker images + Argo sync cinehome
oc -n npd-movie set env deploy/movie-api --list | grep OTEL_
```
