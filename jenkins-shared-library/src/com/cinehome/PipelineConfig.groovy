package com.cinehome

class PipelineConfig implements Serializable {

    static final Map SERVICES = [
        'movie-api': [
            dockerfile  : 'Dockerfile',
            context     : 'apps/movie-api',
            helmKey     : 'movieApi',
            watchPath   : 'apps/movie-api',
            snapshotMode: 'full',
        ],
        'movie-web': [
            dockerfile  : 'Dockerfile',
            context     : 'phim-web-interface',
            helmKey     : 'movieWeb',
            watchPath   : 'phim-web-interface',
            snapshotMode: 'time',
        ],
        // v2 event-driven (NestJS worker) — BUILD_TARGET sẵn khi thêm code
        'media-worker': [
            dockerfile  : 'Dockerfile',
            context     : 'apps/media-worker',
            helmKey     : 'mediaWorker',
            watchPath   : 'apps/media-worker',
            snapshotMode: 'full',
            optional    : true,
        ],
    ]

    static Map mergeDefaults(Map user) {
        def defaults = [
            harborHost         : 'harbor-platform.apps.ocp01.npd.co',
            harborProject      : 'movie-web',
            gitBranch          : 'main',
            gitRepoUrl         : 'https://github.com/kevinram164/movie-web.git',
            gitopsValuesFile   : 'gitops/values-images.yaml',
            kanikoImage        : 'gcr.io/kaniko-project/executor:v1.23.2-debug',
            kanikoSkipTlsVerify: true,
            kanikoUseCache     : false,
            vaultAddr          : 'http://vault.vault.svc.cluster.local:8200',
            vaultRole          : 'jenkins-kaniko',
            vaultHarborPath    : 'cinehome/harbor',
            vaultGithubPath    : 'platform/github',
        ]
        return defaults + user
    }
}
