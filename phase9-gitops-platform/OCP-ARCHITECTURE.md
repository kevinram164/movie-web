# OCP Architecture — CineHome

```text
Browser
   │
   ▼
Route cinehome.apps.ocp01.npd.co ──► Service movie-web (npd-movie)
   │                                      └─ /api proxy ──► movie-api
   │
Route minio-api-minio.apps… ──────► MinIO (HLS + posters)

CI:
  git push → Jenkins (cinehome library + Kaniko)
           → Harbor movie-web/*
           → bump gitops/values-images.yaml
           → ArgoCD sync cinehome

CD AppProject: cinehome-platform (app mới)
App cũ Kong/Coroot có thể vẫn gắn project banking-platform — OK nếu Healthy; không bắt buộc migrate ngay.

Namespaces tái dùng: kong, observability, platform, vault, postgres, redis
Namespaces mới: minio, npd-movie
```

Chi tiết giai đoạn: [OCP-DEPLOY-GUIDE.md](./OCP-DEPLOY-GUIDE.md)  
App domain: [ARCHITECTURE.md](../ARCHITECTURE.md)
