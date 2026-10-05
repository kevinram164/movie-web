@Library('platform@main') _

// BUILD_TARGET: auto | all | movie-api | movie-web | media-worker
// Central library: https://github.com/kevinram164/jenkins-shared-library
// dev-k8s: Jenkins cloud-native-platform → npd-harbor.co → bump deploy/dev-k8s/values/values-images.yaml → ArgoCD.

platformPipeline([
  project             : 'cinehome',
  harborHost          : 'npd-harbor.co',
  harborProject       : 'movie-web',
  gitBranch           : 'main',
  gitRepoUrl          : 'https://github.com/kevinram164/movie-web.git',
  gitopsValuesFile    : 'deploy/dev-k8s/values/values-images.yaml',
  kanikoUseCache      : false,
  vaultAddr           : 'http://vault.vault.svc.cluster.local:8200',
  vaultRole           : 'jenkins-kaniko',
  vaultHarborPath     : 'cinehome/harbor',
  vaultGithubPath     : 'platform/github',
  kanikoSkipTlsVerify : true,
])
