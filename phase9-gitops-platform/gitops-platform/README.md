# GitOps Platform Applications — CineHome

AppProject: **`cinehome-platform`**  
Repo: `kevinram164/movie-web` · branch `main`

| App of Apps | Nội dung |
|-------------|----------|
| `platform-app-of-apps` | Harbor, Vault, ESO, Jenkins |
| `observability-app-of-apps` | Coroot, OTEL, Linkerd (tuỳ chọn) |
| `infra-app-of-apps` | Postgres, Redis |
| `cinehome-app-of-apps` | → `deploy/argocd` (MinIO + app + routes) |

Bootstrap:

```bash
oc apply -f phase9-gitops-platform/gitops-platform/project.yaml -n argocd
oc apply -f phase9-gitops-platform/gitops-platform/app-of-apps.yaml -n argocd
```

OCP overlay khuyến nghị: `environments/dev-ocp/`.
