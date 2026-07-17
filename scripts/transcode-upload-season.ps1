<#
.SYNOPSIS
  Convert 1 Season folder MP4(+SRT) to HLS and upload MinIO (+ optional catalog sync).

.EXAMPLE
  .\scripts\transcode-upload-season.ps1 `
    -SourceDir "D:\Movie\...\Season 1 (1992-93)" `
    -SeriesSlug "x-men-animated"

  Requires ffmpeg + mc on PATH (or tools\ in repo).
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

# Prefer repo tools\ (ffmpeg.exe, mc.exe) then PATH
$script:RepoTools = Join-Path (Split-Path $PSScriptRoot -Parent) "tools"
if (Test-Path $script:RepoTools) {
  $env:Path = "$script:RepoTools;$env:Path"
}

function Require-Cmd($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Missing command '$name' on PATH. Put $name.exe in tools\ or install ffmpeg/mc."
  }
}

function Get-McArgs {
  if ($Insecure) { return @("--insecure") }
  return @()
}

function Get-EpisodeTitle([string]$baseName) {
  if ($baseName -match '(?i)S\d{1,2}\s*E\d{1,3}\s*[--.]\s*(.+)$') {
    return ($Matches[1] -replace '\s+', ' ').Trim()
  }
  return $baseName
}

function Enable-InsecureTls {
  if ($script:CinehomeInsecureTlsDone) { return }
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  [Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
  $script:CinehomeInsecureTlsDone = $true
}

function Ensure-CatalogSeries(
  [string]$Api,
  [string]$Slug,
  [string]$Title = ""
) {
  if ($Insecure) { Enable-InsecureTls }
  if (-not $Title) {
    if ($Slug -eq "x-men-97") { $Title = "X-Men '97" }
    else { $Title = ($Slug -replace '-', ' ') }
  }
  # Probe: GET series; if 404, POST create. Retry once (first TLS handshake can fail transiently).
  $getUri = "$Api/series/$Slug"
  $notFound = $false
  for ($attempt = 1; $attempt -le 2; $attempt++) {
    try {
      Invoke-RestMethod -Method Get -Uri $getUri | Out-Null
      return
    } catch {
      $code = $null
      try { $code = [int]$_.Exception.Response.StatusCode } catch { }
      if ($code -eq 404) {
        $notFound = $true
        break
      }
      if ($attempt -eq 2) {
        Write-Warning "catalog series check failed ($getUri): $($_.Exception.Message)"
        return
      }
      Start-Sleep -Seconds 1
    }
  }
  if (-not $notFound) { return }
  $postUri = "$Api/series"
  $franchise = "other"
  if ($Slug -match '(?i)^x-?men') { $franchise = "x-men" }
  elseif ($Slug -match '(?i)spider') { $franchise = "spiderman" }
  elseif ($Slug -match '(?i)batman') { $franchise = "batman" }
  $body = @{
    slug          = $Slug
    title         = $Title
    english_title = $Title
    franchise     = $franchise
    year_start    = 2024
  } | ConvertTo-Json
  try {
    Invoke-RestMethod -Method Post -Uri $postUri -ContentType "application/json" -Body $body | Out-Null
    Write-Host "     + catalog: create series $Slug"
  } catch {
    $code = $null
    try { $code = [int]$_.Exception.Response.StatusCode } catch { }
    if ($code -eq 409) {
      Write-Host "     - catalog: series exists $Slug"
    } else {
      Write-Warning "catalog create series failed ($postUri): $($_.Exception.Message)"
    }
  }
}

function Ensure-CatalogEpisode(
  [string]$Api,
  [string]$Slug,
  [int]$Season,
  [int]$Number,
  [string]$Title
) {
  if ($Insecure) { Enable-InsecureTls }
  Ensure-CatalogSeries $Api $Slug
  $uri = "$Api/series/$Slug/seasons/$Season/episodes"
  $body = @{
    title            = $Title
    number           = $Number
    description      = ""
    duration_minutes = 22
  } | ConvertTo-Json
  try {
    Invoke-RestMethod -Method Post -Uri $uri -ContentType "application/json" -Body $body | Out-Null
    Write-Host "     + catalog: create S$Season E$Number"
  } catch {
    $code = $null
    try { $code = [int]$_.Exception.Response.StatusCode } catch { }
    if ($code -eq 409) {
      Write-Host "     - catalog: exists S$Season E$Number"
    } else {
      Write-Warning "catalog sync failed ($uri): $($_.Exception.Message)"
    }
  }
}

function Convert-SrtToVtt([string]$SrtPath, [string]$VttPath) {
  # Many fan-rip .srt are not UTF-8; try common encodings
  $encodings = @("UTF-8", "CP1252", "ISO-8859-1", "WINDOWS-1258", "CP1258")
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    foreach ($enc in $encodings) {
      if (Test-Path $VttPath) { Remove-Item -Force $VttPath -ErrorAction SilentlyContinue }
      $null = & ffmpeg -hide_banner -loglevel error -y -sub_charenc $enc -i $SrtPath $VttPath 2>&1
      if ($LASTEXITCODE -eq 0 -and (Test-Path $VttPath) -and ((Get-Item $VttPath).Length -gt 0)) {
        return $true
      }
    }
  } finally {
    $ErrorActionPreference = $prev
  }
  return $false
}

function Inject-SubsIntoMaster([string]$MasterPath, [string]$WorkDir) {
  $subsPl = Join-Path $WorkDir "subs.vi.m3u8"
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

  $masterText = Get-Content -Raw $MasterPath
  if ($masterText -notmatch 'TYPE=SUBTITLES') {
    $media = '#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="Vietnamese",DEFAULT=YES,AUTOSELECT=YES,FORCED=NO,LANGUAGE="vi",URI="subs.vi.m3u8"'
    $masterText = $masterText -replace '(#EXTM3U\r?\n)', "`$1$media`n"
    $masterText = $masterText -replace '(#EXT-X-STREAM-INF:[^\r\n]+)', '$1,SUBTITLES="subs"'
    [System.IO.File]::WriteAllText($MasterPath, $masterText)
  }
}

function Test-MinioObject([string]$Alias, [string]$BucketName, [string]$Key) {
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

$videos = @(Get-ChildItem -Path $SourceDir -File -Recurse | Where-Object {
  $_.Extension -match '(?i)^\.(mp4|mkv|m4v|mov)$'
})
if (-not $videos) {
  throw "No video files (.mp4/.mkv) in: $SourceDir"
}

Write-Host "==> $($videos.Count) video(s) in $SourceDir"
Write-Host "==> Series: $SeriesSlug -> $Bucket/<slug>/sXXeYY/"

$ok = 0
$skip = 0
$fail = 0

foreach ($vid in $videos | Sort-Object Name) {
  $m = $rx.Match($vid.BaseName)
  if (-not $m.Success) {
    Write-Warning "Skip (cannot parse SxxExx): $($vid.Name)"
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
  Write-Host "     -> $Bucket/$objectPrefix/"

  if ($WhatIf) {
    Write-Host "     (WhatIf) title='$title'"
    continue
  }

  if ($SkipExisting -and -not $SkipUpload) {
    if (Test-MinioObject $MinioAlias $Bucket $masterKey) {
      Write-Host "     SKIP (already on MinIO)"
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
    if (Convert-SrtToVtt $srt $vtt) {
      Inject-SubsIntoMaster $master $work
      Write-Host "     + subtitle -> subs.vi.vtt"
    } else {
      Write-Warning "subtitle convert failed (charset): $(Split-Path $srt -Leaf) - video still uploaded"
    }
  }

  if ($SkipUpload) {
    Write-Host "     (SkipUpload) HLS at $work"
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
Write-Host "Done season: ok=$ok skip=$skip fail=$fail -> $SeriesSlug"
