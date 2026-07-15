# CineHome — web phim trên OpenShift + MinIO + GitOps

Stack xem phim tại nhà. Platform GitOps: [`phase9-gitops-platform/`](./phase9-gitops-platform/).  
UI: [`phim-web-interface/`](./phim-web-interface/) (Next.js) · API: [`apps/movie-api/`](./apps/movie-api/).

Kiến trúc: [ARCHITECTURE.md](./ARCHITECTURE.md) · Deploy: [phase9-gitops-platform/OCP-DEPLOY-GUIDE.md](./phase9-gitops-platform/OCP-DEPLOY-GUIDE.md)

## Catalog đã seed

| Series | Slug | HLS MinIO (mỗi tập) |
|--------|------|---------------------|
| X-Men Animations | `x-men-animated` | `x-men-animated/s01e01/master.m3u8` … |
| Spider-Man Animations | `spiderman-animated` | `spiderman-animated/s…` |
| Batman Animations | `batman-animated` | `batman-animated/s…` |

Upload ví dụ:

```bash
bash scripts/transcode-upload.sh /path/to/ep.mp4 x-men-animated/s01e01
```

## Upload phim từ Windows (MP4 + SRT)

Trên ổ cứng bạn chỉ cần **`.mp4` + `.srt`** (như folder Season 1 X-Men).  
**HLS** được tạo bằng `ffmpeg` rồi mới đẩy lên MinIO — web không stream thẳng MP4.

```powershell
# 1 lần: kết nối MinIO trên OCP
mc alias set cinehome https://minio-api-minio.apps.ocp01.npd.co minioadmin "<password>"

# Cả folder Season 1 → convert + upload
.\scripts\transcode-upload-season.ps1 `
  -SourceDir "D:\Movie\...\Season 1 (1992-93)" `
  -SeriesSlug "x-men-animated"
```

Script parse tên kiểu `X-Men T.A.S - S01 E01 - Night Of The Sentinels....mp4`  
→ MinIO: `movies/x-men-animated/s01e01/master.m3u8` (+ `.ts`, và `subs.vi.vtt` nếu có `.srt`).

| Series trên web | `-SeriesSlug` |
|-----------------|---------------|
| X-Men | `x-men-animated` |
| Spider-Man | `spiderman-animated` |
| Batman | `batman-animated` |

Chỉ convert không upload: thêm `-SkipUpload`. Thử parse: `-WhatIf`.

## Kiến trúc

```text
Browser → Route cinehome → movie-web (nginx)
                └─ /api → movie-api (FastAPI)
                              ├─ Postgres DB `movie`
                              └─ MinIO (buckets movies, posters)
Browser → Route minio-api → MinIO (HLS .m3u8 + .ts public-read)
```

| Thành phần | Namespace | Vai trò |
|---|---|---|
| `movie-web` | `npd-movie` | UI + proxy `/api` |
| `movie-api` | `npd-movie` | Catalog + stream URL |
| MinIO | `minio` | Object storage phim HLS |
| Postgres | `postgres` | DB `movie` (Job init) |

## URL (lab ocp01.npd.co)

| Service | URL |
|---|---|
| CineHome | https://cinehome.apps.ocp01.npd.co |
| MinIO Console | https://minio-console-minio.apps.ocp01.npd.co |
| MinIO API | https://minio-api-minio.apps.ocp01.npd.co |

## Thứ tự triển khai

### 0. Chuẩn bị Harbor

Tạo project Harbor `movie-web`, rồi copy pull secret sang namespace app:

```bash
oc create namespace npd-movie --dry-run=client -o yaml | oc apply -f -
oc get secret harbor-pull-creds -n npd-banking -o yaml \
  | sed 's/namespace: npd-banking/namespace: npd-movie/' \
  | oc apply -f -
```

(Điều chỉnh tên secret/namespace cho khớp lab của bạn.)

### 1. CI — Jenkins + Kaniko + Shared Library

Cùng pattern banking: Vault SA `jenkins-kaniko`, không Jenkins Credential Store.

1. Harbor project **`movie-web`**
2. Đăng ký Shared Library name **`cinehome`**, path `jenkins-shared-library` (xem [jenkins-shared-library/README.md](./jenkins-shared-library/README.md))
3. Multibranch Pipeline → repo này, `Jenkinsfile` root
4. Build với `BUILD_TARGET=all` (lần đầu) hoặc `auto` sau này

```text
Checkout → Build movie-api → Build movie-web → Update GitOps (values-images.yaml)
```

Bootstrap thủ công (nếu chưa có Jenkins job):

```bash
HARBOR=harbor-platform.apps.ocp01.npd.co/movie-web
docker build -t $HARBOR/movie-api:latest apps/movie-api
docker build -t $HARBOR/movie-web:latest apps/movie-web
docker push $HARBOR/movie-api:latest
docker push $HARBOR/movie-web:latest
```

### 2. Apply GitOps

```bash
# AppProject đã thêm repo movie-web + ns minio / npd-movie
bash scripts/apply-cinehome.sh
```

ArgoCD sẽ sync:

1. `infra-minio` — MinIO + PVC `nfs-csi` 200Gi  
2. `minio-routes` + `minio-bucket-policy` — Route + public-read/CORS  
3. `movie-db-init` — tạo role/DB `movie` trên Postgres  
4. `cinehome` — movie-api + movie-web  
5. `cinehome-routes` — Route UI  

### 3. Đổ phim (HLS → MinIO)

```bash
# Cài mc, trỏ tới MinIO API
mc alias set local https://minio-api-minio.apps.ocp01.npd.co minioadmin 'ChangeMeMinioMovie2026!'

# Transcode + upload (cần ffmpeg)
bash scripts/transcode-upload.sh /path/to/phim.mp4 night-drive
```

Demo seed trong API dùng `hls_key=night-drive/master.m3u8` cho phim **Night Drive**.  
Upload đúng key đó là xem được ngay.

Poster (tuỳ chọn):

```bash
mc cp poster.jpg local/posters/night-drive.jpg
```

### 4. Thêm phim mới qua API

```bash
curl -X POST https://cinehome.apps.ocp01.npd.co/api/movies \
  -H 'Content-Type: application/json' \
  -d '{
    "slug":"my-movie",
    "title":"Phim của tôi",
    "year":2024,
    "genre":"Action",
    "duration_minutes":120,
    "poster_key":"my-movie.jpg",
    "hls_key":"my-movie/master.m3u8"
  }'
```

## Cấu trúc repo

```text
apps/movie-api/          FastAPI
apps/movie-web/          React + hls.js
charts/movie/            Helm chart
deploy/argocd/           ArgoCD Applications
deploy/minio/            values + bucket policy Job
deploy/movie/            Postgres init Job
deploy/routes/           OpenShift Routes
gitops/values-images.yaml
scripts/
```

## Secret cần đổi trước production nhà

- MinIO password: `deploy/minio/values.yaml` → `auth.rootPassword`
- Postgres user `movie` / password `movie` trong Job + `charts/movie/values.yaml`  
  (sau này đẩy vào Vault + ESO như banking)

## Dev local nhanh

```bash
# API (cần Postgres + MinIO reachable, hoặc sửa DATABASE_URL)
cd apps/movie-api && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080

# UI
cd apps/movie-web && npm install && npm run dev
```

## Lưu ý HLS

- Bucket `movies` / `posters` phải **anonymous download** (Job `minio-bucket-policy` đã set).
- Player load `master.m3u8`; segment `.ts` relative path phải cùng prefix trên MinIO.
- CORS MinIO đã mở GET/HEAD cho browser.
