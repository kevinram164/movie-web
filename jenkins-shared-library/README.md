# Jenkins Shared Library — CineHome (`movie-web`)

Pattern giống `banking-demo`: **Kaniko + Harbor + Vault SA + bump GitOps**.

## Luồng

```text
git push → Jenkins Multibranch (Jenkinsfile)
  → @Library('cinehome') → cinehomePipeline()
  → Kaniko build (Vault harbor creds)
  → push harbor-platform.../movie-web/<service>:<sha7>
  → commit gitops/values-images.yaml (Vault GitHub PAT)
  → ArgoCD sync
```

## Services

| Service | Context | Helm key | Harbor image |
|---------|---------|----------|--------------|
| `movie-api` | `apps/movie-api` | `movieApi` | `.../movie-web/movie-api` |
| `movie-web` | `phim-web-interface` | `movieWeb` | `.../movie-web/movie-web` |
| `media-worker` | `apps/media-worker` | `mediaWorker` | optional (v2 Kafka worker) |

`BUILD_TARGET`: `auto` | `all` | tên service.

## Đăng ký library trên Jenkins

Modern Shared Library (Modern SCM → Git):

| Field | Value |
|-------|--------|
| Name | `cinehome` |
| Default version | `main` |
| Repo | `https://github.com/kevinram164/movie-web.git` |
| Library path | `jenkins-shared-library` |

Hoặc thêm vào JCasC Jenkins (tương tự banking-demo).

## Job

1. Harbor project **`movie-web`**
2. Multibranch Pipeline → repo `movie-web`, branch `main`
3. Script path: `Jenkinsfile` (root)

Secret: tái dùng Vault `platform/harbor` + `platform/github`, SA `jenkins-kaniko` (đã có trên OCP).

## Jenkinsfile root

```groovy
@Library('cinehome') _

cinehomePipeline([
  harborHost          : 'harbor-platform.apps.ocp01.npd.co',
  harborProject       : 'movie-web',
  gitBranch           : 'main',
  gitRepoUrl          : 'https://github.com/kevinram164/movie-web.git',
  gitopsValuesFile    : 'gitops/values-images.yaml',
  vaultAddr           : 'http://vault.vault.svc.cluster.local:8200',
  vaultRole           : 'jenkins-kaniko',
  kanikoSkipTlsVerify : true,
])
```
