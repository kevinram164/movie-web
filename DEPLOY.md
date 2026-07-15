# Hướng dẫn triển khai CineHome trên OpenShift

Tài liệu này mô tả **từ đầu đến khi xem được phim** trên cluster OCP.  
Không chạy UI/API trên máy local — mọi thứ chạy trên cluster; máy Windows chỉ dùng để **đẩy phim** lên MinIO.

| Mục | Giá trị lab |
|-----|-------------|
| Repo | `https://github.com/kevinram164/movie-web.git` |
| Branch | `main` |
| Cluster | `ocp01.npd.co` |
| Web | https://cinehome.apps.ocp01.npd.co |
| MinIO Console | https://minio-console-minio.apps.ocp01.npd.co |
| MinIO API | https://minio-api-minio.apps.ocp01.npd.co |

**Đã có sẵn trên cluster (không cài lại):** Kong (`infra-kong`), Coroot, NFS CSI, ArgoCD, Harbor, Jenkins, Vault (lab phase9 trước).

---

## Sơ đồ nhanh

```text
[Máy Windows]  MP4+SRT ──ffmpeg──► HLS ──mc──► MinIO (OCP)
                                                      │
[Developer] git push ──► Jenkins+Kaniko ──► Harbor
                              │
                         bump values-images.yaml
                              │
                         ArgoCD sync
                              │
              movie-web + movie-api + MinIO + Postgres
                              │
              https://cinehome.apps.ocp01.npd.co
```

---

## Checklist tổng

| # | Việc | Xong khi |
|---|------|----------|
| A | Code trên GitHub `main` | `git push` OK |
| B | AppProject + repo ArgoCD | `cinehome-platform` tồn tại |
| C | Harbor project + pull secret | Image pull được vào `npd-movie` |
| D | Jenkins library + Multibranch | Pipeline green, image trên Harbor |
| E | Postgres (DB movie) | Job/init OK hoặc Postgres Healthy |
| F | Apply `cinehome-app-of-apps` | Pods Running, Route mở được |
| G | Upload HLS từ Windows | Mở tập trên web phát được |

---

## Bước A — Đẩy code lên GitHub

Trên máy dev (có `git` + credential GitHub):

```powershell
cd D:\Tai-lieu\LPI-DOCKER-K8S\movie-web
git status
git add .
git commit -m "feat: cinehome ui + series + gitops"
git push -u origin main
```

ArgoCD và Jenkins đọc repo **`kevinram164/movie-web`**, nhánh **`main`**.

---

## Bước B — AppProject ArgoCD

```bash
export ARGOCD_NS=argocd

# Kết nối repo movie-web trong ArgoCD UI (nếu chưa):
# Settings → Repositories → Connect Repo
# URL: https://github.com/kevinram164/movie-web.git

oc apply -f phase9-gitops-platform/environments/dev-ocp/appproject.yaml -n $ARGOCD_NS
oc get appproject cinehome-platform -n $ARGOCD_NS
```

Nếu còn project `banking-platform` với Kong/Coroot: **giữ nguyên**. App CineHome dùng project mới `cinehome-platform`.

---

## Bước C — Harbor + pull secret

### C.1 Project Harbor

1. Mở https://harbor-platform.apps.ocp01.npd.co  
2. Tạo project **`movie-web`** (private hoặc public lab)  
3. Robot accounts (hoặc tái dùng robot lab):
   - **ci-push** — push image (Jenkins Kaniko) → Vault `secret/platform/harbor`
   - **k8s-pull** — pull only → Vault `secret/platform/harbor-pull`

Ví dụ seed Vault (trong pod `vault-0`):

```bash
vault kv put secret/platform/harbor-pull \
  registry='harbor-platform.apps.ocp01.npd.co' \
  username='robot$movie-web+k8s-pull' \
  password='<TOKEN>'
```

### C.2 Namespace + secret pull

```bash
oc create ns npd-movie --dry-run=client -o yaml | oc apply -f -

# ESO tự sync nếu đã apply harbor-pull ExternalSecret (ns npd-movie)
oc get secret harbor-pull-creds -n npd-movie

# Cách tạm (copy từ ns khác):
# oc get secret harbor-pull-creds -n platform -o yaml | sed 's/namespace: platform/namespace: npd-movie/' | oc apply -f -
```

### C.3 Trust TLS Harbor (nếu kubelet báo x509)

Chạy script lab:  
`phase9-gitops-platform/environments/dev-ocp/scripts/harbor-registry-trust-setup.sh`  
Chi tiết: [INSTALL-TROUBLESHOOTING.md](./phase9-gitops-platform/environments/dev-ocp/INSTALL-TROUBLESHOOTING.md).

---

## Bước D — Jenkins CI (Kaniko)

### D.1 Shared Library

Jenkins → Manage Jenkins → System → **Global Pipeline Libraries** (hoặc JCasC đã cấu hình):

| Field | Value |
|-------|--------|
| Name | `cinehome` |
| Default version | `main` |
| Retrieval | Modern SCM → Git |
| Project repo | `https://github.com/kevinram164/movie-web.git` |
| Library path | `jenkins-shared-library` |

`Jenkinsfile` root gọi:

```groovy
@Library('cinehome') _
cinehomePipeline([...])
```

### D.2 Multibranch job

1. New Item → **Multibranch Pipeline** (tên ví dụ `cinehome`)  
2. Branch source: GitHub / Git → `movie-web`  
3. Discover branches: `main`  
4. Script path: `Jenkinsfile`  
5. Scan / Build  

### D.3 Build lần đầu

**Build with Parameters** → `BUILD_TARGET` = **`all`**

Pipeline kỳ vọng:

```text
Checkout
Build movie-api
Build movie-web      ← context: phim-web-interface
Update GitOps        ← commit gitops/values-images.yaml
```

### D.4 Checkpoint Harbor

Harbor project `movie-web` phải có:

- `movie-api:<sha7>` (và/hoặc `latest` nếu bạn tag thêm)  
- `movie-web:<sha7>`

Tag thật do CI ghi vào `gitops/values-images.yaml`.

---

## Bước E — Postgres (DB `movie`)

Infra Postgres (nếu chưa):

```bash
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/infra-app-of-apps.yaml -n $ARGOCD_NS
```

ArgoCD app `cinehome` còn Job `movie-db-init` (tạo DB/user `movie`) khi sync giai đoạn F.  
Nếu Postgres đã có từ lab banking: Job sẽ tạo DB `movie` trên instance hiện có (kiểm tra secret name Postgres khớp Job).

Kiểm tra:

```bash
oc get pods -n postgres
# hoặc sau khi cinehome sync:
oc logs -n postgres job/movie-db-init
```

Đổi mật khẩu mặc định trong:

- `phase9-gitops-platform/infra-values/postgres.yaml`  
- `charts/movie/values.yaml` (`DATABASE_URL`)  
trước khi dùng nghiêm túc.

---

## Bước F — Deploy CineHome (ArgoCD)

### F.1 Apply App of Apps

```bash
bash scripts/apply-cinehome.sh
```

Hoặc:

```bash
oc apply -f phase9-gitops-platform/environments/dev-ocp/appproject.yaml -n argocd
oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/cinehome-app-of-apps.yaml -n argocd
```

### F.2 Apps con sẽ xuất hiện

| Application | Namespace | Vai trò |
|-------------|-----------|---------|
| `infra-minio` | `minio` | Object storage |
| `minio-routes` | `minio` | Route API + Console |
| `minio-bucket-policy` | `minio` | Bucket public-read + CORS |
| `movie-db-init` | `postgres` | Tạo DB `movie` |
| `cinehome` | `npd-movie` | Helm `movie-api` + `movie-web` |
| `cinehome-routes` | `npd-movie` | Route UI |

Trong ArgoCD UI: sync nếu chưa Auto Sync; đợi **Healthy / Synced**.

### F.3 Kiểm tra pods

```bash
oc get pods -n minio
oc get pods -n npd-movie
oc get route -n npd-movie
oc get route -n minio

oc logs -n npd-movie deploy/movie-api --tail=50
# Kỳ vọng: [seed] movies=... series=3  (hoặc series đã có từ lần trước)
```

### F.4 Mở web

Trình duyệt: **https://cinehome.apps.ocp01.npd.co**

Bạn sẽ thấy:

- Brand **CineHome**  
- Hero (thường Batman series)  
- Hàng **X-Men / Spider-Man / Batman**  
- Vào series → danh sách tập  

**Lúc này player có thể chưa có hình** nếu chưa upload HLS — bình thường.

### F.5 MinIO password

Mặc định lab trong `deploy/minio/values.yaml`:

- User: `minioadmin`  
- Password: xem `auth.rootPassword` trong file đó  

Đổi password trước khi expose ra ngoài nhà.

---

## Bước G — Đổ phim từ Windows lên MinIO

File trên ổ `D:\` chỉ cần **`.mp4` + `.srt`**. Script sẽ convert HLS rồi upload.

### G.1 Cài tool trên Windows

1. **ffmpeg** — thêm vào PATH  
2. **mc.exe** (MinIO Client) — thêm vào PATH  

### G.2 Kết nối MinIO trên OCP

PowerShell (máy Windows phải resolve / reach `*.apps.ocp01.npd.co` — LAN/VPN):

```powershell
mc.exe alias set cinehome https://minio-api-minio.apps.ocp01.npd.co minioadmin "<PASSWORD>"
mc.exe ls cinehome
mc.exe ls cinehome/movies
```

### G.3 Upload cả Season 1 X-Men

```powershell
cd D:\Tai-lieu\LPI-DOCKER-K8S\movie-web

.\scripts\transcode-upload-season.ps1 `
  -SourceDir "D:\Movie\X-Men - ANIME series and CARTOON shows (720p & 480p)\Cartoon shows\02. X-Men - The Animated series (Complete - 480p SD)\Season 1 (1992-93)" `
  -SeriesSlug "x-men-animated"
```

Script hiểu tên dạng:

`X-Men T.A.S - S01 E01 - Night Of The Sentinels (Part 1).mp4`

→ MinIO:

`movies/x-men-animated/s01e01/master.m3u8` + `seg_*.ts` + `subs.vi.vtt` (nếu có `.srt`)

| Series trên web | `-SeriesSlug` |
|-----------------|---------------|
| X-Men | `x-men-animated` |
| Spider-Man | `spiderman-animated` |
| Batman | `batman-animated` |

Thử parse không upload: thêm `-WhatIf`  
Chỉ convert local: `-SkipUpload`

### G.4 Kiểm tra object

```powershell
mc.exe ls cinehome/movies/x-men-animated/
mc.exe ls cinehome/movies/x-men-animated/s01e01/
```

Hoặc MinIO Console → bucket `movies`.

### G.5 Xem trên web

1. Mở https://cinehome.apps.ocp01.npd.co  
2. Vào **X-Men Animations**  
3. Chọn tập đã upload (ví dụ S01E01)  

Nếu tập **chưa có trong DB** (seed chỉ vài tập đầu): cần mở rộng seed hoặc `POST /api` thêm episode — xem mục H.

---

## Bước H — Seed vs số tập thật

API khi start seed **3 series** với một ít tập demo (không đủ 13 tập Season 1).

| Tình huống | Cách xử lý |
|------------|------------|
| Upload đúng `s01e01`… các tập đã seed | Web phát được ngay |
| Upload `s01e12` nhưng DB chưa có episode | Thêm episode vào seed / gọi API tạo (sẽ bổ sung admin sau) hoặc mình mở rộng seed cho đủ season |

Hiện tại: ưu tiên upload các tập đã có trong seed trước (`s01e01`–`s01e04`, `s02e…` tùy franchise), rồi mở rộng catalog.

---

## Thứ tự apply ArgoCD gợi ý (tóm tắt lệnh)

```bash
export ARGOCD_NS=argocd

# B — project
oc apply -f phase9-gitops-platform/environments/dev-ocp/appproject.yaml -n $ARGOCD_NS

# Platform / routes / infra — CHỈ nếu chưa có trên cluster
# oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/platform-app-of-apps.yaml -n $ARGOCD_NS
# oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/platform-routes-app-of-apps.yaml -n $ARGOCD_NS
# oc apply -f phase9-gitops-platform/environments/dev-ocp/argocd/applications/infra-app-of-apps.yaml -n $ARGOCD_NS

# D — Jenkins BUILD_TARGET=all  (chờ Harbor có image)

# F — CineHome
bash scripts/apply-cinehome.sh
```

---

## Kiểm tra lỗi thường gặp

| Triệu chứng | Việc kiểm |
|-------------|-----------|
| Pod `ImagePullBackOff` | Harbor project, `harbor-pull-creds`, TLS trust |
| `movie-api` CrashLoop | Postgres chưa Ready / sai `DATABASE_URL` / xem `oc logs` |
| Web mở được nhưng catalog trống | API lỗi — `oc logs deploy/movie-api`; CORS; rewrite Next |
| Vào tập → player đen | Chưa có HLS trên MinIO đúng key; CORS bucket; Route minio-api |
| `mc` timeout từ Windows | Không vào được apps domain — VPN/DNS/firewall |
| ArgoCD `project not found` | Chưa apply AppProject `cinehome-platform` |
| App cũ vẫn `banking-platform` | Kong/Coroot giữ nguyên; CineHome dùng project mới |

```bash
oc get pods -n npd-movie
oc describe pod -n npd-movie -l app.kubernetes.io/component=movie-api
oc logs -n npd-movie deploy/movie-web --tail=80
oc get application -n argocd | findstr cinehome
```

---

## URL sau khi xong

| Service | URL |
|---------|-----|
| CineHome | https://cinehome.apps.ocp01.npd.co |
| MinIO Console | https://minio-console-minio.apps.ocp01.npd.co |
| MinIO API (S3/HLS) | https://minio-api-minio.apps.ocp01.npd.co |
| Harbor | https://harbor-platform.apps.ocp01.npd.co |
| Jenkins | https://jenkins-platform.apps.ocp01.npd.co |
| ArgoCD | https://argocd-server-argocd.apps.ocp01.npd.co |

---

## Tài liệu liên quan

| File | Nội dung |
|------|----------|
| [phase9-gitops-platform/OCP-DEPLOY-GUIDE.md](./phase9-gitops-platform/OCP-DEPLOY-GUIDE.md) | Platform / giai đoạn ArgoCD ngắn |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Kiến trúc v2 (Node/Kafka) — roadmap |
| [jenkins-shared-library/README.md](./jenkins-shared-library/README.md) | CI `cinehome` |
| [scripts/transcode-upload-season.ps1](./scripts/transcode-upload-season.ps1) | Upload season từ Windows |

---

## Kết quả mong đợi “xong”

1. `oc get pods -n npd-movie` → `movie-api`, `movie-web` Running  
2. `oc get pods -n minio` → MinIO Running  
3. Trình duyệt mở CineHome thấy 3 series  
4. Sau upload X-Men S01E01 → bấm tập → có tiếng/hình HLS  

Nếu bạn báo đang kẹt **bước nào** (B/C/D/F/G), gửi `oc get pods` / log / screenshot ArgoCD để xử lý tiếp.
