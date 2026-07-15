<#
.SYNOPSIS
  Upload cả bộ series: quét thư mục gốc (Season 1..N + X97) → ffmpeg HLS → MinIO.

.DESCRIPTION
  Dùng cho cấu trúc kiểu:
    02. X-Men - The Animated Series (Complete - 480p SD)\
      Season 1 (1992-93)\
      Season 2 (1993-94)\
      ...
      X97\

  Season 1–5 → SeriesSlug (mặc định x-men-animated)
  Folder X97  → X97SeriesSlug (mặc định x-men-97) — KHÔNG ghi đè S01 của TAS

.EXAMPLE
  # 1 lần: alias MinIO
  mc alias set cinehome https://minio-api-minio.apps.ocp01.npd.co minioadmin "<password>"

  # Xem sẽ xử lý gì (không convert)
  .\scripts\transcode-upload-series.ps1 `
    -RootDir "D:\Movie\X-Men - ANIME Series and CARTOON Shows (720p & 480p)\Cartoon Shows\02. X-Men - The Animated Series (Complete - 480p SD)" `
    -WhatIf

  # Chạy thật + tạo tập trên web nếu thiếu
  .\scripts\transcode-upload-series.ps1 `
    -RootDir "D:\Movie\...\02. X-Men - The Animated Series (Complete - 480p SD)" `
    -SkipExisting `
    -SyncCatalog
#>
param(
  [Parameter(Mandatory = $true)]
  [string]$RootDir,

  [string]$SeriesSlug = "x-men-animated",
  [string]$X97SeriesSlug = "x-men-97",
  [string]$MinioAlias = "cinehome",
  [string]$Bucket = "movies",
  [string]$ApiBase = "https://cinehome.apps.ocp01.npd.co/api",
  [switch]$SkipUpload,
  [switch]$SkipExisting,
  [switch]$SyncCatalog,
  [switch]$Insecure,
  [switch]$WhatIf,
  [string[]]$OnlyFolders = @()
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $RootDir)) {
  throw "Không thấy thư mục: $RootDir"
}

$seasonScript = Join-Path $PSScriptRoot "transcode-upload-season.ps1"
if (-not (Test-Path $seasonScript)) {
  throw "Thiếu $seasonScript"
}

$folders = Get-ChildItem -LiteralPath $RootDir -Directory | Sort-Object Name
if (-not $folders) {
  throw "Không có subfolder trong: $RootDir"
}

function Resolve-TargetSlug([string]$folderName) {
  if ($folderName -match '(?i)^x[\s''’`-]*97$|^xmen[\s''’`-]*97$|^x-men[\s''’`-]*97$') {
    return $X97SeriesSlug
  }
  if ($folderName -match '(?i)^season\s+\d+') {
    return $SeriesSlug
  }
  # Thư mục lạ: vẫn dùng SeriesSlug nếu bên trong có SxxExx
  return $SeriesSlug
}

Write-Host "========================================"
Write-Host " CineHome batch upload"
Write-Host " Root: $RootDir"
Write-Host " TAS  → $SeriesSlug"
Write-Host " X97  → $X97SeriesSlug"
Write-Host " SkipExisting=$SkipExisting SyncCatalog=$SyncCatalog"
Write-Host "========================================"

$started = Get-Date
$ran = 0

foreach ($dir in $folders) {
  if ($OnlyFolders.Count -gt 0 -and ($OnlyFolders -notcontains $dir.Name)) {
    continue
  }

  $mp4Count = @(Get-ChildItem -LiteralPath $dir.FullName -File -Filter *.mp4 -ErrorAction SilentlyContinue).Count
  if ($mp4Count -eq 0) {
    Write-Warning "Bỏ qua (không có .mp4): $($dir.Name)"
    continue
  }

  $slug = Resolve-TargetSlug $dir.Name
  Write-Host ""
  Write-Host "######## $($dir.Name) ($mp4Count tập) → $slug ########"

  $args = @{
    SourceDir   = $dir.FullName
    SeriesSlug  = $slug
    MinioAlias  = $MinioAlias
    Bucket      = $Bucket
    ApiBase     = $ApiBase
  }
  if ($SkipUpload) { $args.SkipUpload = $true }
  if ($SkipExisting) { $args.SkipExisting = $true }
  if ($SyncCatalog) { $args.SyncCatalog = $true }
  if ($Insecure) { $args.Insecure = $true }
  if ($WhatIf) { $args.WhatIf = $true }

  & $seasonScript @args
  $ran++
}

$elapsed = (Get-Date) - $started
Write-Host ""
Write-Host "========================================"
Write-Host " Xong $ran folder(s) trong $([int]$elapsed.TotalMinutes) phút"
Write-Host " Web: $ApiBase → /series/$SeriesSlug (và $X97SeriesSlug nếu có X97)"
Write-Host " Gợi ý: mở máy, chạy qua đêm với -SkipExisting để resume khi lỗi."
Write-Host "========================================"
