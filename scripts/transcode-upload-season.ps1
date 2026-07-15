<#
.SYNOPSIS
  Convert 1 folder Season MP4(+SRT) → HLS → MinIO (+ optional sync catalog API)

.EXAMPLE
  .\scripts\transcode-upload-season.ps1 `
    -SourceDir "D:\Movie\...\Season 1 (1992-93)" `
    -SeriesSlug "x-men-animated"

  Yêu cầu: ffmpeg + mc trên PATH; đã chạy:
    mc alias set cinehome https://minio-api-minio.apps.ocp01.npd.co USER PASS
#>
param(
  [Parameter(Mandatory = $true)]
  [string]$SourceDir,

  [Parameter(Mandatory = $true)]
  [string]$SeriesSlug,

  [string]$MinioAlias = "cinehome",
  [string]$Bucket = "movies",
  [string]$ApiBase = "https://cinehome.apps.ocp01.npd.co/api",
  [switch]$SkipUpload,
  [switch]$SkipExisting,
  [switch]$SyncCatalog,
  [switch]$Insecure,
  [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

# Ưu tiên tools/ trong repo (ffmpeg.exe, mc.exe) rồi mới tới PATH
$script:RepoTools = Join-Path (Split-Path $PSScriptRoot -Parent) "tools"
if (Test-Path $script:RepoTools) {
  $env:Path = "$script:RepoTools;$env:Path"
}

function Require-Cmd($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Thiếu lệnh '$name' trên PATH. Đặt $name.exe vào folder tools\ của repo, hoặc cài ffmpeg / mc."
  }
}

function Get-EpisodeTitle([string]$baseName) {
  if ($baseName -match '(?i)S\d{1,2}\s*E\d{1,3}\s*[-–.]\s*(.+)$') {
    return ($Matches[1] -replace '\s+', ' ').Trim()
  }
  return $baseName
}

function Ensure-CatalogEpisode(
  [string]$Api,
  [string]$Slug,
  [int]$Season,
  [int]$Number,
  [string]$Title
) {
  $uri = "$Api/series/$Slug/seasons/$Season/episodes"
  $body = @{
    title             = $Title
    number            = $Number
    description       = ""
    duration_minutes  = 22
  } | ConvertTo-Json
  try {
    Invoke-RestMethod -Method Post -Uri $uri -ContentType "application/json" -Body $body | Out-Null
    Write-Host "     + catalog: tạo S$Season E$Number"
  } catch {
    $code = $null
    try { $code = [int]$_.Exception.Response.StatusCode } catch { }
    if ($code -eq 409) {
      Write-Host "     · catalog: đã có S$Season E$Number"
    } else {
      Write-Warning "catalog sync thất bại ($uri): $($_.Exception.Message)"
    }
  }
}

function Get-McArgs {
  if ($Insecure) { return @("--insecure") }
  return @()
}

function Test-MinioObject([string]$Alias, [string]$BucketName, [string]$Key) {
  # mc ghi ERROR ra stderr khi object chưa có — với $ErrorActionPreference=Stop
  # PowerShell coi là terminating; cần Continue + nuốt stderr.
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $null = & mc @(Get-McArgs) stat "$Alias/$BucketName/$Key" 2>&1
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  } finally {
    $ErrorActionPreference = $prev
  }
}

Require-Cmd ffmpeg
if (-not $SkipUpload) { Require-Cmd mc }

$rx = [regex]'(?i)S(?<season>\d{1,2})\s*E(?<episode>\d{1,3})'

$videos = Get-ChildItem -Path $SourceDir -File -Filter *.mp4
if (-not $videos) {
  throw "Không thấy file .mp4 trong: $SourceDir"
}

Write-Host "==> $($videos.Count) MP4 trong $SourceDir"
Write-Host "==> Series: $SeriesSlug → $Bucket/<slug>/sXXeYY/"

$ok = 0
$skip = 0
$fail = 0

foreach ($vid in $videos | Sort-Object Name) {
  $m = $rx.Match($vid.BaseName)
  if (-not $m.Success) {
    Write-Warning "Bỏ qua (không parse SxxExx): $($vid.Name)"
    $fail++
    continue
  }

  $season = [int]$m.Groups["season"].Value
  $episode = [int]$m.Groups["episode"].Value
  $epCode = "s{0:D2}e{1:D2}" -f $season, $episode
  $objectPrefix = "$SeriesSlug/$epCode"
  $masterKey = "$objectPrefix/master.m3u8"
  $work = Join-Path $env:TEMP "cinehome-hls-$SeriesSlug-$epCode"
  $title = Get-EpisodeTitle $vid.BaseName

  Write-Host ""
  Write-Host "---- $($vid.Name)"
  Write-Host "     → $Bucket/$objectPrefix/"

  if ($WhatIf) {
    Write-Host "     (WhatIf) title='$title'"
    continue
  }

  if ($SkipExisting -and -not $SkipUpload) {
    if (Test-MinioObject $MinioAlias $Bucket $masterKey) {
      Write-Host "     SKIP (đã có trên MinIO)"
      if ($SyncCatalog) {
        Ensure-CatalogEpisode $ApiBase $SeriesSlug $season $episode $title
      }
      $skip++
      continue
    }
  }

  if (Test-Path $work) { Remove-Item -Recurse -Force $work }
  New-Item -ItemType Directory -Force -Path $work | Out-Null

  $master = Join-Path $work "master.m3u8"
  $seg = Join-Path $work "seg_%04d.ts"

  & ffmpeg -hide_banner -loglevel error -y -i $vid.FullName `
    -c:v libx264 -preset veryfast -crf 22 `
    -c:a aac -b:a 128k `
    -hls_time 6 -hls_playlist_type vod `
    -hls_segment_filename $seg `
    $master
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "ffmpeg failed: $($vid.Name)"
    $fail++
    continue
  }

  $srt = Join-Path $vid.DirectoryName ($vid.BaseName + ".srt")
  if (Test-Path $srt) {
    $vtt = Join-Path $work "subs.vi.vtt"
    & ffmpeg -hide_banner -loglevel error -y -i $srt $vtt
    if ($LASTEXITCODE -eq 0) {
      $subsPl = Join-Path $work "subs.vi.m3u8"
      @"
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:99999
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-PLAYLIST-TYPE:VOD
#EXTINF:99999.0,
subs.vi.vtt
#EXT-X-ENDLIST
"@ | Set-Content -Path $subsPl -Encoding utf8

      $masterText = Get-Content -Raw $master
      if ($masterText -notmatch 'TYPE=SUBTITLES') {
        $media = '#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="Vietnamese",DEFAULT=YES,AUTOSELECT=YES,FORCED=NO,LANGUAGE="vi",URI="subs.vi.m3u8"'
        $masterText = $masterText -replace '(#EXTM3U\r?\n)', "`$1$media`n"
        $masterText = $masterText -replace '(#EXT-X-STREAM-INF:[^\r\n]+)', '$1,SUBTITLES="subs"'
        [System.IO.File]::WriteAllText($master, $masterText)
      }
      Write-Host "     + phụ đề → subs.vi.vtt"
    }
  }

  if ($SkipUpload) {
    Write-Host "     (SkipUpload) HLS tại $work"
    $ok++
    continue
  }

  $dest = "${MinioAlias}/${Bucket}/${objectPrefix}"
  & mc @(Get-McArgs) mirror --overwrite $work $dest
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "mc mirror failed: $dest"
    $fail++
    continue
  }
  Write-Host "     OK uploaded"

  if ($SyncCatalog) {
    Ensure-CatalogEpisode $ApiBase $SeriesSlug $season $episode $title
  }

  Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
  $ok++
}

Write-Host ""
Write-Host "Xong season: ok=$ok skip=$skip fail=$fail → $SeriesSlug"
