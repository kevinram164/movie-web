package com.cinehome

class ChangeDetector implements Serializable {

    static List<String> buildTargetChoices() {
        def services = PipelineConfig.SERVICES.findAll { k, v -> !v.optional }.keySet().sort() as List
        def optional = PipelineConfig.SERVICES.findAll { k, v -> v.optional }.keySet().sort() as List
        return ['auto', 'all'] + services + optional
    }

    static List<String> resolve(def steps, Map cfg) {
        // all / auto: bỏ media-worker optional cho đến khi có Dockerfile
        def required = PipelineConfig.SERVICES.findAll { k, v -> !v.optional }.keySet().sort() as List
        def allKnown = PipelineConfig.SERVICES.keySet().sort() as List

        if (steps.env.FORCE_BUILD_ALL == 'true') {
            steps.echo 'FORCE_BUILD_ALL=true — build required services'
            return required
        }

        def target = steps.params?.BUILD_TARGET ?: cfg.buildTarget ?: 'auto'
        steps.echo "BUILD_TARGET=${target}"

        if (target == 'all') {
            return required
        }
        if (target != 'auto') {
            if (!PipelineConfig.SERVICES.containsKey(target)) {
                steps.error("Unknown BUILD_TARGET: ${target}")
            }
            return [target]
        }

        return detectChanged(steps, cfg, allKnown)
    }

    private static List<String> detectChanged(def steps, Map cfg, List<String> all) {
        def changed = [] as Set
        try {
            def diff = steps.sh(
                script: "git diff --name-only HEAD~1 HEAD 2>/dev/null || git diff --name-only origin/${cfg.gitBranch}...HEAD",
                returnStdout: true,
            ).trim()
            if (!diff) {
                steps.echo 'auto: không có diff — bỏ qua build. Chọn BUILD_TARGET=all hoặc tên service.'
                return []
            }
            diff.split('\n').each { path ->
                PipelineConfig.SERVICES.each { name, meta ->
                    if (meta.optional) {
                        return // chỉ build optional khi BUILD_TARGET=<svc>
                    }
                    def watch = meta.watchPath ?: meta.context
                    if (path.startsWith("${watch}/") || path == "${watch}/Dockerfile") {
                        changed << name
                    }
                }
            }
        } catch (ignored) {
            steps.echo 'auto: change detection failed — bỏ qua build.'
            return []
        }
        if (changed.isEmpty()) {
            steps.echo 'auto: diff không chạm apps/* — bỏ qua build.'
        } else {
            steps.echo "auto: build ${changed.sort().join(', ')}"
        }
        return changed.sort() as List
    }
}
