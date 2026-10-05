{{/*
Vault Agent Injector: render /vault/secrets/env (export KEY='value') từ .Values.vault.appPath.
Cú pháp template Vault bọc trong backtick để Helm giữ nguyên cho agent.
Usage: include "cinehome.vault.podAnnotations" (dict "root" $ "keys" .Values.movieApi.secretEnvKeys)
*/}}
{{- define "cinehome.vault.podAnnotations" -}}
{{- $v := .root.Values.vault -}}
vault.hashicorp.com/agent-inject: "true"
vault.hashicorp.com/agent-init-first: "true"
vault.hashicorp.com/agent-pre-populate-only: "true"
vault.hashicorp.com/role: {{ $v.role | quote }}
vault.hashicorp.com/agent-inject-secret-env: {{ $v.appPath | quote }}
vault.hashicorp.com/agent-inject-template-env: |
  {{`{{ with secret "`}}{{ $v.appPath }}{{`" }}`}}
  {{- range .keys }}
  export {{ . }}='{{`{{ .Data.data.`}}{{ . }}{{` }}`}}'
  {{- end }}
  {{`{{ end }}`}}
{{- end -}}
