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

## Lỗi: `Could not find any definition of libraries [cinehome]`

Jenkins **chưa đăng ký** Global Pipeline Library tên `cinehome`.  
(JCasC trong repo chỉ có hiệu lực nếu Helm Jenkins sync từ repo này và reload — lab cũ thường vẫn chỉ có `banking-demo`.)

### Cách sửa ngay (UI — ~2 phút)

1. Mở https://jenkins-platform.apps.ocp01.npd.co  
2. **Manage Jenkins** → **System** (hoặc **Configure System**)  
3. Kéo tới **Global Pipeline Libraries** → **Add**  
4. Điền:

| Field | Value |
|-------|--------|
| Name | `cinehome` |
| Default version | `main` |
| Load implicitly | không bắt buộc |
| Allow default version to be overridden | ✓ |
| Retrieval method | **Modern SCM** |
| Source Code Management | **Git** |
| Project Repository | `https://github.com/kevinram164/movie-web.git` |
| Credentials | (trống nếu repo public; hoặc GitHub PAT nếu private) |
| Library Path | `jenkins-shared-library` |

5. **Save**  
6. Chạy lại job Multibranch / Build `main`

### Kiểm tra

Build lại phải qua được dòng `@Library('cinehome') _` và vào stage **Checkout**.

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
