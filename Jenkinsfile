@Library('cinehome') _

// BUILD_TARGET: auto | all | movie-api | movie-web | media-worker
// Kaniko + Vault SA jenkins-kaniko (cùng pattern banking-demo)

cinehomePipeline([
  harborHost          : 'harbor-platform.apps.ocp01.npd.co',
  harborProject       : 'movie-web',
  gitBranch           : 'main',
  gitRepoUrl          : 'https://github.com/kevinram164/movie-web.git',
  gitopsValuesFile    : 'gitops/values-images.yaml',
  vaultAddr           : 'http://vault.vault.svc.cluster.local:8200',
  vaultRole           : 'jenkins-kaniko',
  vaultHarborPath     : 'platform/harbor',
  vaultGithubPath     : 'platform/github',
  kanikoSkipTlsVerify : true,
])
