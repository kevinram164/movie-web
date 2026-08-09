<#
.SYNOPSIS
  Convert local .srt next to videos -> subs.vi.vtt (+ playlist) and upload to MinIO.
  Also patches master.m3u8 with EXT-X-MEDIA subtitles line when missing.

.EXAMPLE
  .\scripts\backfill-subs-season.ps1 `
    -SourceDir "D:\Movie\...\Show.S01...[TGx]" `
    -SeriesSlug "new-batman-series" `
    -Insecure
#>
param(
  [Parameter(Mandatory = $true)]
  [string]$SourceDir,
  [Parameter(Mandatory = $true)]
  [string]$SeriesSlug,
  [string]$MinioAlias = "cinehome",
  [string]$Bucket = "movies",
  [switch]$Insecure
)

$ErrorActionPreference = "Stop"
$script:RepoTools = Join-Path (Split-Path $PSScriptRoot -Parent) "tools"
if (Test-Path $script:RepoTools) {
  $env:Path = "$script:RepoTools;$env:Path"
}

function Get-McArgs {
  if ($Insecure) { return @("--insecure") }
  return @()
}

function Convert-SrtToVtt([string]$SrtPath, [string]$VttPath) {
  $encodings = @("UTF-8", "CP1252", "ISO-8859-1", "WINDOWS-1258", "CP1258")
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    foreach ($enc in $encodings) {
      if (Test-Path -LiteralPath $VttPath) { Remove-Item -LiteralPath $VttPath -Force -ErrorAction SilentlyContinue }
      $null = & ffmpeg -hide_banner -loglevel error -y -sub_charenc $enc -i $SrtPath $VttPath 2>&1
      if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $VttPath) -and ((Get-Item -LiteralPath $VttPath).Length -gt 0)) {
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

  if (-not (Test-Path -LiteralPath $MasterPath)) { return }
  $masterText = Get-Content -LiteralPath $MasterPath -Raw
  if ($masterText -notmatch 'TYPE=SUBTITLES') {
    $media = '#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="Vietnamese",DEFAULT=YES,AUTOSELECT=YES,FORCED=NO,LANGUAGE="vi",URI="subs.vi.m3u8"'
    $masterText = $masterText -replace '(#EXTM3U\r?\n)', "`$1$media`n"
    $masterText = $masterText -replace '(#EXT-X-STREAM-INF:[^\r\n]+)', '$1,SUBTITLES="subs"'
    [System.IO.File]::WriteAllText($MasterPath, $masterText)
  }
}

if (-not (Test-Path -LiteralPath $SourceDir)) {
  throw "SourceDir not found: $SourceDir"
}
$SourceDir = (Resolve-Path -LiteralPath $SourceDir).Path
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { throw "Missing ffmpeg" }
if (-not (Get-Command mc -ErrorAction SilentlyContinue)) { throw "Missing mc" }

$videos = @(Get-ChildItem -LiteralPath $SourceDir -File -Recurse | Where-Object {
  $_.Extension -match '(?i)^\.(mp4|mkv|m4v|mov)$' -and $_.BaseName -notmatch '(?i)sample'
})

$ok = 0; $skip = 0; $fail = 0
foreach ($vid in $videos) {
  if ($vid.BaseName -notmatch '(?i)S(?<s>\d{1,2})\s*E(?<e>\d{1,3})') {
    Write-Warning "Skip (no SxxExx): $($vid.Name)"
    $skip++
    continue
  }
  $season = [int]$Matches["s"]
  $episode = [int]$Matches["e"]
  $epCode = "s{0:D2}e{1:D2}" -f $season, $episode
  $prefix = "$SeriesSlug/$epCode"
  Write-Host "---- $($vid.Name) -> $prefix"

  $srt = Join-Path $vid.DirectoryName ($vid.BaseName + ".srt")
  if (-not (Test-Path -LiteralPath $srt)) {
    Write-Warning "No .srt next to video"
    $fail++
    continue
  }

  # Only patch episodes already on MinIO
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  $null = & mc @(Get-McArgs) stat "$MinioAlias/$Bucket/$prefix/master.m3u8" 2>&1
  $hasMaster = ($LASTEXITCODE -eq 0)
  $ErrorActionPreference = $prev
  if (-not $hasMaster) {
    Write-Host "     SKIP (master.m3u8 not on MinIO yet)"
    $skip++
    continue
  }

  $work = Join-Path $env:TEMP "cinehome-subs-$SeriesSlug-$epCode"
  if (Test-Path -LiteralPath $work) { Remove-Item -LiteralPath $work -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $work | Out-Null

  $vtt = Join-Path $work "subs.vi.vtt"
  if (-not (Convert-SrtToVtt $srt $vtt)) {
    Write-Warning "srt->vtt failed"
    $fail++
    continue
  }

  # Download master, inject MEDIA line, re-upload
  $localMaster = Join-Path $work "master.m3u8"
  & mc @(Get-McArgs) cp "$MinioAlias/$Bucket/$prefix/master.m3u8" $localMaster | Out-Null
  Inject-SubsIntoMaster $localMaster $work

  & mc @(Get-McArgs) cp $vtt "$MinioAlias/$Bucket/$prefix/subs.vi.vtt" | Out-Null
  & mc @(Get-McArgs) cp (Join-Path $work "subs.vi.m3u8") "$MinioAlias/$Bucket/$prefix/subs.vi.m3u8" | Out-Null
  & mc @(Get-McArgs) cp $localMaster "$MinioAlias/$Bucket/$prefix/master.m3u8" | Out-Null

  Write-Host "     OK subs.vi.vtt + master patch"
  Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
  $ok++
}

Write-Host "Done backfill subs: ok=$ok skip=$skip fail=$fail -> $SeriesSlug"
