# CineHome v2 — Kiến trúc (Node.js + Kafka + Full features)

Mục tiêu: web phim nhà trên OCP, **học event-driven**, stack **Node.js** (không Python), đủ feature “gần Netflix lab”.

---

## 1. Trả lời nhanh

| Câu hỏi | Quyết định |
|--------|------------|
| Event-driven? | **Có — Kafka (Strimzi) làm bus chính** |
| Đổi sang Node.js? | **Có** — thay `movie-api` Python bằng Node (NestJS hoặc Fastify + TypeScript) |
| Full feature? | Thiết kế dưới đây; **triển khai theo phase** (không làm một phát) |

**Stack đề xuất**

| Layer | Công nghệ |
|-------|-----------|
| API | NestJS + TypeScript (module rõ, dễ auth/RBAC) |
| Web | React + Vite + TypeScript (giữ UI hiện tại, mở rộng) |
| Admin | React route `/admin/*` cùng spa (hoặc app riêng sau) |
| DB | PostgreSQL (catalog, user, progress, rating…) |
| Cache | Redis (session/cache đề xuất) |
| Object | MinIO (raw, HLS ABR, posters, subtitles) |
| Events | Kafka (Strimzi) |
| Auth | JWT (access) + refresh trong HttpOnly cookie; Vault/ESO cho secret |
| CD | ArgoCD App of Apps (như hiện tại) |
| CI | **Jenkins + Kaniko + Shared Library `cinehome`** → Harbor → bump `gitops/values-images.yaml` |
| API Gateway | **Kong — đã có trên cluster** (`infra-kong`, tái dùng, không cài lại) |
| Observability | **Coroot — đã có** (`observability-coroot-ce` + operator); OTEL/Linkerd tuỳ chọn |

---

## 2. Sơ đồ tổng thể

```text
                         ┌─────────────┐
                         │  movie-web  │  React (user + admin UI)
                         │  Route OCP  │
                         └──────┬──────┘
                                │ /api
                         ┌──────▼──────┐
                         │ Kong (có sẵn)│  jwt / rate-limit / route (phase auth+)
                         │  ns kong    │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │  movie-api  │  NestJS (BFF + domain API)
                         │  npd-movie  │
                         └──────┬──────┘
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
         Postgres            Redis             MinIO
         (OLTP)            (cache)         (objects)
                                │
                         movie-api PRODUCE
                                ▼
                         ┌─────────────┐
                         │   Kafka     │  Strimzi (mới — học event-driven)
                         │  (topics)   │
                         └──────┬──────┘
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
       media-worker      notify-worker     recommend-worker
```

**Tái dùng cluster:** Kong (`infra-kong` Healthy) + Coroot (`observability` Healthy).  
MVP sớm có thể nginx proxy `/api` thẳng `movie-api`; khi có JWT/RBAC thì đưa `/api` qua Kong.

---

## 3. Service boundaries (Node.js)

### 3.1 `movie-api` (NestJS)

- Auth/RBAC, catalog CRUD (admin), watchlist, history, progress, rating, comment
- Upload **initiate** (presigned PUT MinIO) — không stream file qua API
- Produce Kafka events
- Read model cho UI (REST)
- Đề xuất: đọc từ Redis/Postgres (worker ghi sẵn)

### 3.2 `media-worker` (NestJS microservice / plain Node consumer)

- Consume `media.uploaded`
- `ffprobe` → metadata
- Transcode ABR HLS (360p/720p/1080p) + master playlist
- Gắn phụ đề nếu có (VTT/SRT → convert VTT, copy vào HLS package)
- Upload kết quả MinIO → produce `media.ready` / `media.failed`

### 3.3 `notify-worker` (optional phase)

- Consume `media.ready`, `comment.created`…
- Push realtime (SSE/WebSocket qua api) hoặc ghi notification table

### 3.4 `recommend-worker` (phase sau)

- Consume `playback.completed`, `rating.created`
- Job định kỳ hoặc stream aggregate → top genre / collab đơn giản → Redis

**Không** nhét ffmpeg vào `movie-api` — worker scale riêng, đúng tinh thần event-driven.

---

## 4. Kafka topics & event contracts

| Topic | Key | Producer | Consumer | Payload (gợi ý) |
|-------|-----|----------|----------|-----------------|
| `media.uploaded` | `movieId` | movie-api | media-worker | `{ movieId, rawKey, userId, originalName }` |
| `media.processing` | `movieId` | media-worker | (optional UI) | `{ movieId, stage, percent? }` |
| `media.ready` | `movieId` | media-worker | movie-api*, notify, recommend | `{ movieId, hlsMasterKey, variants[], subtitleKeys[] }` |
| `media.failed` | `movieId` | media-worker | movie-api*, notify | `{ movieId, error }` |
| `playback.progress` | `userId` | movie-api | recommend (optional) | `{ userId, movieId, positionSec, durationSec }` |
| `playback.completed` | `userId` | movie-api | recommend | `{ userId, movieId }` |
| `rating.created` | `movieId` | movie-api | recommend | `{ userId, movieId, score }` |
| `comment.created` | `movieId` | movie-api | notify | `{ userId, movieId, commentId }` |
| `user.registered` | `userId` | movie-api | (audit) | `{ userId, email }` |

\* `movie-api` có thể **vừa produce vừa consume** `media.ready` để cập nhật status phim = `READY` (hoặc dùng CDC — không cần giai đoạn đầu).

**Quy ước**

- Schema JSON + field `eventId`, `occurredAt`, `type`, `version`
- Idempotent consumer: lưu `eventId` đã xử lý hoặc upsert theo `movieId`+stage
- At-least-once: worker phải chịu retry

---

## 5. Domain features — thiết kế chi tiết

### 5.1 Đăng nhập / phân quyền

**Roles**

| Role | Quyền chính |
|------|-------------|
| `viewer` | Xem, search, watchlist, progress, rating, comment |
| `uploader` | + upload phim (hoặc gộp admin nhà) |
| `admin` | + CRUD phim, duyệt comment, user management, dashboard |

**Auth**

- Register / Login → bcrypt password → JWT access (15–30m) + refresh token (Redis hoặc bảng `refresh_tokens`)
- Guard NestJS: `@Roles('admin')`
- Route UI: `/login`, `/register`; admin `/admin` bảo vệ client + server

**DB**

```text
users(id, email, password_hash, display_name, role, created_at)
refresh_tokens(id, user_id, token_hash, expires_at)
```

---

### 5.2 Watchlist, continue watching, lịch sử

```text
watchlist(user_id, movie_id, added_at)  PK(user, movie)

watch_progress(
  user_id, movie_id,
  position_sec, duration_sec,
  updated_at
)  — continue watching = position > 30s AND position/duration < 0.9

watch_history(
  id, user_id, movie_id,
  watched_at, position_sec, completed bool
)
```

**API**

- `POST/DELETE /api/me/watchlist/:movieId`
- `GET /api/me/watchlist`
- `PUT /api/me/progress` → DB + produce `playback.progress`
- `GET /api/me/continue` — từ `watch_progress`
- `GET /api/me/history`

Player UI: định kỳ (mỗi 10–15s) gửi progress; khi near end → `playback.completed`.

---

### 5.3 Upload phim từ UI

```text
1. Client POST /api/movies/upload-init { title, filename, contentType }
2. API tạo movie status=UPLOADING, trả:
   - movieId
   - presigned PUT URL (MinIO raw/)
3. Client PUT file thẳng MinIO
4. Client POST /api/movies/:id/upload-complete
5. API produce media.uploaded
6. media-worker: ABR + subs → media.ready
7. API consume → status=READY, hls_key, variants
```

**Trạng thái phim:** `DRAFT → UPLOADING → PROCESSING → READY | FAILED`

UI: progress bar upload (XHR/fetch); status badge polling hoặc SSE từ `media.processing`.

---

### 5.4 Rating, comment, đề xuất

```text
ratings(user_id, movie_id, score 1..5, updated_at)  UNIQUE(user, movie)
comments(id, user_id, movie_id, body, created_at, deleted_at)
movies.avg_rating, ratings_count  — cập nhật khi rating event

recommendations cache (Redis):
  rec:user:{id} → [movieIds]
  rec:trending → [movieIds]
```

**Đề xuất lab (đơn giản, đủ học event)**

1. Cùng genre với phim đã xem/rate cao  
2. Trending = nhiều `playback.completed` 7 ngày  
3. (Sau) item-item co-occurrence từ history  

Worker rebuild Redis khi nhận `rating.created` / `playback.completed` hoặc cron 15’.

---

### 5.5 Phụ đề / đa ngôn ngữ / ABR

**MinIO layout**

```text
raw/{movieId}/source.mkv
hls/{movieId}/
  master.m3u8
  v360/index.m3u8 + seg_*.ts
  v720/...
  v1080/...
  subs/
    vi.vtt
    en.vtt
posters/{movieId}.jpg
```

**master.m3u8** — EXT-X-STREAM-INF 360/720/1080; **EXT-X-MEDIA** TYPE=SUBTITLES cho từng ngôn ngữ.

**Upload phụ đề**

- Admin/uploader: `POST` + presigned PUT `subs/{lang}.vtt` hoặc kèm lúc processing (worker convert SRT→VTT)
- Metadata trong DB: `movie_subtitles(movie_id, lang, label, key)`

**Player**

- hls.js: chọn level ABR tự động; `video` textTracks / hls subtitle tracks
- UI: menu chất lượng + ngôn ngữ phụ đề

**ffmpeg gợi ý worker**

- 1 input → 3 video ladder + AAC
- Hoặc 3 pass riêng rồi ghép master (đơn giản vận hành lab)

---

### 5.6 Admin dashboard

Route `/admin` (role `admin`):

| Module | Chức năng |
|--------|-----------|
| Overview | Số phim READY/PROCESSING, user, comment mới |
| Movies | List, sửa metadata, re-process, xoá |
| Uploads | Hàng đợi processing (status từ DB/events) |
| Users | Đổi role, khoá |
| Comments | Ẩn/xoá moderation |
| Storage | Link MinIO console (read-only hint) |

Metrics lab: đếm SQL + Kafka lag (Strimzi metrics → Coroot sau).

---

## 6. API surface (tóm tắt)

```text
Auth
  POST /api/auth/register|login|refresh|logout
  GET  /api/me

Catalog
  GET  /api/movies?q&genre&page
  GET  /api/movies/:id
  GET  /api/movies/:id/stream   → signed/public HLS master URL + variants + subs

Social
  PUT  /api/movies/:id/rating
  GET  /api/movies/:id/comments
  POST /api/movies/:id/comments

Me
  watchlist / continue / history / progress

Upload
  POST /api/movies/upload-init
  POST /api/movies/:id/upload-complete
  POST /api/movies/:id/subtitles/init

Admin
  CRUD /api/admin/movies|users|comments
  POST /api/admin/movies/:id/reprocess  → media.uploaded lại

Recommend
  GET  /api/me/recommendations
  GET  /api/movies/trending
```

---

## 7. Map sang OCP / GitOps

| Namespace | Workload |
|-----------|----------|
| `kafka` / `strimzi` | Kafka cluster + topics (KafkaTopic CRs) |
| `minio` | MinIO (giữ) |
| `postgres` | DB `movie` (giữ) |
| `redis` | cache/session (đã có infra) |
| `npd-movie` | movie-api, movie-web, media-worker, (+ notify/recommend) |

ArgoCD apps mới: `infra-kafka`, `cinehome` (helm multi-deploy), `cinehome-workers`.

Secret: Vault → ESO → `movie-db`, `minio`, `jwt-secret`, `kafka` (nếu cần).

### CI (chốt theo lab hiện tại)

```text
@Library('cinehome') _  →  cinehomePipeline()
  Kaniko (SA jenkins-kaniko + Vault platform/harbor)
  Harbor project movie-web
  GitOps bump gitops/values-images.yaml (Vault platform/github)
```

Library nằm tại `jenkins-shared-library/` (package `com.cinehome`).  
Jenkinsfile root gọi pipeline — không viết Kaniko inline.  
`media-worker` đã khai báo trong `PipelineConfig` (optional) cho phase Kafka.

---

## 8. Lộ trình triển khai (phase)

| Phase | Nội dung | Outcome |
|-------|----------|---------|
| **P0** | Rewrite `movie-api` NestJS + giữ UI catalog/stream tối thiểu | Bỏ Python |
| **P1** | Auth JWT + roles + bảo vệ admin stub | Login được |
| **P2** | Strimzi Kafka + topics; media-worker ffmpeg ABR | Event-driven thật |
| **P3** | Upload UI + status PROCESSING→READY | Upload từ web |
| **P4** | Watchlist / progress / history | Continue watching |
| **P5** | Rating + comment | Social |
| **P6** | Subtitles + ABR UI controls | Đa chất lượng/phụ đề |
| **P7** | recommend-worker + admin dashboard | “Đầy đủ lab” |

Mỗi phase merge được, chạy trên OCP, học được khái niệm trước khi thêm feature.

---

## 9. Khác biệt so với MVP Python hiện tại

| MVP (hiện tại) | v2 |
|----------------|----|
| FastAPI Python | NestJS TypeScript |
| Seed demo + HLS có sẵn | Upload → Kafka → worker |
| 1 bitrate giả định | ABR 360/720/1080 |
| Không auth | RBAC |
| Không progress | Continue + history |
| Không social | Rating/comment/recommend |
| Không admin | Dashboard |

Code Python `apps/movie-api` **thay thế** (không maintain song song lâu). UI `apps/movie-web` **nâng cấp** TypeScript + routes mới.

---

## 10. Rủi ro / phạm vi lab

- ABR ffmpeg nặng CPU — worker limit 1–2 replica, queue Kafka chịu backlog  
- Presigned MinIO + CORS + Route TLS cần chỉnh đúng  
- Kafka + Strimzi thêm độ phức tạp OCP (đáng vì mục tiêu học)  
- “Đề xuất” lab = heuristic, không ML production  

---

## Quyết định cần confirm trước khi code P0

1. **NestJS** (đề xuất) hay **Fastify thuần**?  
2. Kafka qua **Strimzi operator** trên OCP?  
3. Bắt đầu **P0 + P1** (rewrite Node + auth) trước, hay **P0 + P2** (Node + Kafka skeleton) song song?
