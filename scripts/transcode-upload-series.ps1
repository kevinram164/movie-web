<#
.SYNOPSIS
  Batch upload a whole series: scan root (Season 1..N + X97) -> ffmpeg HLS -> MinIO.

.DESCRIPTION
  Expected layout:
    02. X-Men - The Animated Series (Complete - 480p SD)\
      Season 1 (1992-93)\
      Season 2 (1993-94)\
      ...
      X97\

  Season 1-5 -> SeriesSlug (default x-men-animated)
  Folder X97 -> X97SeriesSlug (default x-men-97) - does NOT overwrite TAS S01

.EXAMPLE
  mc alias set cinehome https://minio-api-minio.apps.ocp01.npd.co minioadmin "<password>" --insecure

  .\scripts\transcode-upload-series.ps1 `
    -RootDir "D:\Movie\...\02. X-Men - The Animated Series (Complete - 480p SD)" `
    -SkipExisting `
    -SyncCatalog `
    -Insecure
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
  throw "Folder not found: $RootDir"
}

$seasonScript = Join-Path $PSScriptRoot "transcode-upload-season.ps1"
if (-not (Test-Path $seasonScript)) {
  throw "Missing $seasonScript"
}

$folders = Get-ChildItem -LiteralPath $RootDir -Directory | Sort-Object Name
if (-not $folders) {
  throw "No subfolders in: $RootDir"
}

function Resolve-TargetSlug([string]$folderName) {
  if ($folderName -match '(?i)^x97$|^xmen.?97$|^x-men.?97$') {
    return $X97SeriesSlug
  }
  if ($folderName -match '(?i)^season\s+\d+') {
    return $SeriesSlug
  }
  return $SeriesSlug
}

Write-Host "========================================"
Write-Host " CineHome batch upload"
Write-Host " Root: $RootDir"
Write-Host " TAS  -> $SeriesSlug"
Write-Host " X97  -> $X97SeriesSlug"
Write-Host " SkipExisting=$SkipExisting SyncCatalog=$SyncCatalog"
Write-Host "========================================"

$started = Get-Date
$ran = 0

foreach ($dir in $folders) {
  if ($OnlyFolders.Count -gt 0 -and ($OnlyFolders -notcontains $dir.Name)) {
    continue
  }

  $vidCount = @(Get-ChildItem -LiteralPath $dir.FullName -File -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -match '(?i)^\.(mp4|mkv|m4v|mov)$' }).Count
  if ($vidCount -eq 0) {
    Write-Warning "Skip (no .mp4/.mkv): $($dir.Name)"
    continue
  }

  $slug = Resolve-TargetSlug $dir.Name
  Write-Host ""
  Write-Host "######## $($dir.Name) ($vidCount eps) -> $slug ########"

  $args = @{
    SourceDir  = $dir.FullName
    SeriesSlug = $slug
    MinioAlias = $MinioAlias
    Bucket     = $Bucket
    ApiBase    = $ApiBase
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
Write-Host " Done $ran folder(s) in $([int]$elapsed.TotalMinutes) min"
Write-Host " Web: $ApiBase /series/$SeriesSlug (and $X97SeriesSlug if X97)"
Write-Host " Tip: re-run with -SkipExisting to resume."
Write-Host "========================================"
