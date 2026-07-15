# Jenkins Shared Library — CineHome

**Canonical library nằm ở root repo:** [`../../jenkins-shared-library/`](../../jenkins-shared-library/)

Đăng ký trên Jenkins:

| Field | Value |
|-------|--------|
| Name | `cinehome` |
| Default version | `main` |
| Repo | `https://github.com/kevinram164/movie-web.git` |
| Library path | `jenkins-shared-library` |

`Jenkinsfile` (root):

```groovy
@Library('cinehome') _

cinehomePipeline([
  harborHost          : 'harbor-platform.apps.ocp01.npd.co',
  harborProject       : 'movie-web',
  gitBranch           : 'main',
  gitRepoUrl          : 'https://github.com/kevinram164/movie-web.git',
  gitopsValuesFile    : 'gitops/values-images.yaml',
  kanikoSkipTlsVerify : true,
])
```

Không dùng `banking-demo` / `bankingDemoPipeline` nữa.
