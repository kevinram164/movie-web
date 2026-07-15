<#
.SYNOPSIS
  Convert folder MP4(+SRT) → HLS → upload MinIO (CineHome)

.EXAMPLE
  .\scripts\transcode-upload-season.ps1 `
    -SourceDir "D:\Movie\...\Season 1 (1992-93)" `
    -SeriesSlug "x-men-animated" `
    -MinioAlias "cinehome"

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
  [switch]$SkipUpload,
  [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

function Require-Cmd($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Thiếu lệnh '$name' trên PATH. Cài ffmpeg và mc (MinIO client)."
  }
}

Require-Cmd ffmpeg
if (-not $SkipUpload) { Require-Cmd mc }

# Match: "... S01 E01 - Title.mp4" hoặc "S01E01"
$rx = [regex]'(?i)S(?<season>\d{1,2})\s*E(?<episode>\d{1,3})'

$videos = Get-ChildItem -Path $SourceDir -File -Filter *.mp4
if (-not $videos) {
  throw "Không thấy file .mp4 trong: $SourceDir"
}

Write-Host "==> Tìm thấy $($videos.Count) file MP4 trong $SourceDir"
Write-Host "==> Series slug: $SeriesSlug → MinIO $Bucket/<slug>/sXXeYY/"

foreach ($vid in $videos | Sort-Object Name) {
  $m = $rx.Match($vid.BaseName)
  if (-not $m.Success) {
    Write-Warning "Bỏ qua (không parse được Sxx Exx): $($vid.Name)"
    continue
  }

  $season = [int]$m.Groups["season"].Value
  $episode = [int]$m.Groups["episode"].Value
  $epCode = "s{0:D2}e{1:D2}" -f $season, $episode
  $objectPrefix = "$SeriesSlug/$epCode"
  $work = Join-Path $env:TEMP "cinehome-hls-$SeriesSlug-$epCode"

  Write-Host ""
  Write-Host "---- $($vid.Name)"
  Write-Host "     → $Bucket/$objectPrefix/"

  if ($WhatIf) { continue }

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
  if ($LASTEXITCODE -ne 0) { throw "ffmpeg failed: $($vid.Name)" }

  # Phụ đề .srt cùng tên → .vtt + gắn vào master.m3u8 (Safari / hls.js)
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
      Write-Host "     + phụ đề → subs.vi.vtt (+ master.m3u8)"
    }
  }

  if ($SkipUpload) {
    Write-Host "     (SkipUpload) HLS tại $work"
    continue
  }

  $dest = "${MinioAlias}/${Bucket}/${objectPrefix}"
  & mc mirror --overwrite $work $dest
  if ($LASTEXITCODE -ne 0) { throw "mc mirror failed: $dest" }
  Write-Host "     OK uploaded $dest"
}

Write-Host ""
Write-Host "Xong. Trên web mở series '$SeriesSlug' → tập tương ứng."
Write-Host "API seed key dạng: $SeriesSlug/s01e01/master.m3u8"
