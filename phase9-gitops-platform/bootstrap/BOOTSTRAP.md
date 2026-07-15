# Bootstrap — Platform lần đầu (OpenShift only)

Repo chỉ hỗ trợ **OpenShift** (`environments/dev-ocp`).

Thứ tự:

1. **Platform + Infra** (Harbor, Vault, ESO, Jenkins, Postgres, Redis)
2. **CI/CD** (Jenkins `cinehome` → Harbor `movie-web`)
3. **CineHome app** sau cùng (`cinehome-app-of-apps`)

**Hướng dẫn đầy đủ:** [OCP-DEPLOY-GUIDE.md](../OCP-DEPLOY-GUIDE.md)

---

## Giai đoạn 1 — ArgoCD + AppProject

Xem [INSTALL-ARGOCD-UPSTREAM.md](../environments/dev-ocp/INSTALL-ARGOCD-UPSTREAM.md).

```bash
export ARGOCD_NS=argocd
oc apply -f phase9-gitops-platform/environments/dev-ocp/appproject.yaml -n $ARGOCD_NS
# Connect repo: https://github.com/kevinram164/movie-web.git  branch main
```

---

## Giai đoạn 2 — Platform

```bash
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/platform-app-of-apps.yaml -n $ARGOCD_NS
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/platform-routes-app-of-apps.yaml -n $ARGOCD_NS
```

Seed Vault (`platform/harbor`, **`cinehome/harbor-pull`**, `github`, `jenkins`) — [vault/README.md](../vault/README.md).  
Không ghi đè `platform/harbor-pull` (banking).

**Không** apply `cinehome-app-of-apps` ở bước này.

---

## Giai đoạn 2b — Observability (tuỳ chọn)

**Coroot đã Healthy trên cluster** → bỏ qua.  
Chỉ apply nếu cần (Linkerd/OTEL) — [observability/README.md](../observability/README.md).

---

## Giai đoạn 3 — Infra

```bash
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/infra-app-of-apps.yaml -n $ARGOCD_NS
```

Postgres + Redis. **Kong đã có** — không deploy lại.

---

## Giai đoạn 4 — CI

Harbor project `movie-web` · Jenkins library `cinehome` · Multibranch → `Jenkinsfile` · `BUILD_TARGET=all`.

---

## Giai đoạn 5 — CineHome

```bash
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/cinehome-app-of-apps.yaml -n $ARGOCD_NS
# hoặc: bash scripts/apply-cinehome.sh
```

UI: https://cinehome.apps.ocp01.npd.co
