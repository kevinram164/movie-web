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
  [switch]$WhatIf,
  # Include Extra/Extras folders (default: skip documentaries/bonus)
  [switch]$IncludeExtras,
  # Default season when filename uses "Ep. 01" (TNBA / Beware the Batman)
  [int]$DefaultSeason = 1,
  # Skip relative paths matching this regex (e.g. 'Volume 4' when uploading BTAS only)
  [string]$ExcludePathPattern = "",
  # Movie packs: "01. Title\" folders -> S01E01.. (Justice League movies, etc.)
  [switch]$NumberedFolders
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

function Clean-EpisodeTitle([string]$title) {
  $t = ($title -replace '\s+', ' ').Trim()
  $t = $t -replace '(?i)\s*,\s*with Commentary\s*', ' '
  $t = $t -replace '(?i)\s*\((?:480p|720p|1080p|2160p)[^)]*\)\s*$', ''
  $t = $t -replace '\s*\(\d{4}(?:\s*[-–]\s*[^)]+)?\)\s*$', ''
  return ($t -replace '\s+', ' ').Trim()
}

function Get-EpisodeTitle([string]$baseName) {
  if ($baseName -match '(?i)S\d{1,2}\s*E\d{1,3}\s*[-.]\s*(.+)$') {
    return (Clean-EpisodeTitle $Matches[1])
  }
  if ($baseName -match '(?i)Ep\.?\s*\d{1,3}\s*[-.]\s*(.+)$') {
    return (Clean-EpisodeTitle $Matches[1])
  }
  if ($baseName -match '(?i)^\d{1,2}x\d{1,3}\s*[-.]?\s*(.+)$') {
    return (Clean-EpisodeTitle $Matches[1])
  }
  # "01. Justice League - The New Frontier (2008)" or file without Ep code
  if ($baseName -match '^\d{1,2}\.\s*(.+)$') {
    return (Clean-EpisodeTitle $Matches[1])
  }
  return (Clean-EpisodeTitle $baseName)
}

function Get-EpisodeInfoFromPath([System.IO.FileInfo]$file) {
  $info = Get-EpisodeInfo $file.BaseName
  if ($info) { return $info }
  if (-not $NumberedFolders) { return $null }
  # Walk up from file: "01. Movie Title\file.mp4"
  $dir = $file.Directory
  $rootPath = (Resolve-Path -LiteralPath $SourceDir).Path
  while ($dir -and ($dir.FullName.Length -ge $rootPath.Length)) {
    if ($dir.Name -match '^(?<n>\d{1,2})\.\s*(?<title>.+)$') {
      return [pscustomobject]@{
        Season  = $DefaultSeason
        Episode = [int]$Matches["n"]
        Title   = (Clean-EpisodeTitle $Matches["title"])
      }
    }
    if ($dir.FullName -eq $rootPath) { break }
    $dir = $dir.Parent
  }
  # Single-film SourceDir (e.g. Return of the Joker) — one episode
  return [pscustomobject]@{
    Season  = $DefaultSeason
    Episode = 1
    Title   = (Get-EpisodeTitle $file.BaseName)
  }
}

function Get-EpisodeInfo([string]$baseName) {
  # Skip bonus tracks named "S01 Extra 01" (not real episodes)
  if ($baseName -match '(?i)S\d{1,2}\s+Extra\s+\d') {
    return $null
  }
  if ($baseName -match '(?i)S(?<season>\d{1,2})\s*E(?<episode>\d{1,3})') {
    return [pscustomobject]@{
      Season  = [int]$Matches["season"]
      Episode = [int]$Matches["episode"]
    }
  }
  if ($baseName -match '(?i)(?<season>\d{1,2})x(?<episode>\d{1,3})') {
    return [pscustomobject]@{
      Season  = [int]$Matches["season"]
      Episode = [int]$Matches["episode"]
    }
  }
  # "The New Batman Adventures - Ep. 01 - Title" / "Beware the Batman - Ep. 01 - Title"
  if ($baseName -match '(?i)Ep\.?\s*(?<episode>\d{1,3})') {
    return [pscustomobject]@{
      Season  = $DefaultSeason
      Episode = [int]$Matches["episode"]
    }
  }
  # Flat movie packs: "1. Batman - Mask of The Phantasm (1993 - 480p DVDRip).mp4"
  if ($NumberedFolders -and ($baseName -match '^(?<n>\d{1,2})\.\s*(?<title>.+)$')) {
    return [pscustomobject]@{
      Season  = $DefaultSeason
      Episode = [int]$Matches["n"]
      Title   = (Clean-EpisodeTitle $Matches["title"])
    }
  }
  return $null
}

function Test-IsExtraPath([string]$fullPath) {
  if ($IncludeExtras) { return $false }
  return ($fullPath -match '(?i)[\\/]Extras?[\\/]' -or $fullPath -match '(?i)S\d{1,2}\s+Extra\s+\d')
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
    $known = @{
      "x-men-97"                      = "X-Men '97"
      "batman-animated"               = "Batman: The Animated Series"
      "batman-new-adventures"         = "The New Batman Adventures"
      "the-batman-2004"               = "The Batman (2004)"
      "batman-phantasm"               = "Batman: Mask of the Phantasm"
      "batman-subzero"                = "Batman & Mr. Freeze: SubZero"
      "batman-tas-movies"             = "Batman TAS Movies"
      "batman-return-of-the-joker"    = "Batman Beyond: Return of the Joker"
      "justice-league-movies"         = "Justice League Animated Movies"
      "spiderman-animated"            = "Spider-Man: The Animated Series"
    }
    if ($known.ContainsKey($Slug)) { $Title = $known[$Slug] }
    else { $Title = ($Slug -replace '-', ' ') }
  }
  $artwork = @{
    "batman-animated"            = @("/movies/batman-tas-poster.jpg", "/movies/batman-tas-backdrop.jpg")
    "batman-new-adventures"      = @("/movies/batman-tnba-poster.jpg", "/movies/batman-tnba-backdrop.jpg")
    "the-batman-2004"            = @("/movies/the-batman-2004-poster.jpg", "/movies/the-batman-2004-backdrop.jpg")
    "batman-phantasm"            = @("/movies/batman-phantasm-poster.jpg", "/movies/batman-phantasm-backdrop.jpg")
    "batman-subzero"             = @("/movies/batman-subzero-poster.jpg", "/movies/batman-subzero-backdrop.jpg")
    "batman-tas-movies"          = @("/movies/batman-tas-movies-poster.jpg", "/movies/batman-tas-movies-backdrop.jpg")
    "batman-return-of-the-joker" = @("/movies/batman-rotoj-poster.jpg", "/movies/batman-rotoj-backdrop.jpg")
    "justice-league-movies"      = @("/movies/justice-league-movies-poster.jpg", "/movies/justice-league-movies-backdrop.jpg")
    "spiderman-animated"         = @("/movies/spiderman-tas-poster.jpg", "/movies/spiderman-tas-backdrop.jpg")
    "x-men-97"                   = @("/movies/x-men-97-poster.webp", "/movies/x-men-97-backdrop.webp")
  }
  $posterKey = "/movies/poster-1.png"
  $backdropKey = "/movies/hero-backdrop.png"
  if ($artwork.ContainsKey($Slug)) {
    $posterKey = $artwork[$Slug][0]
    $backdropKey = $artwork[$Slug][1]
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
  elseif ($Slug -match '(?i)justice') { $franchise = "justice-league" }
  $yearStart = 2024
  if ($Slug -eq "batman-animated") { $yearStart = 1992 }
  elseif ($Slug -eq "batman-new-adventures") { $yearStart = 1997 }
  elseif ($Slug -eq "the-batman-2004") { $yearStart = 2004 }
  elseif ($Slug -eq "batman-phantasm") { $yearStart = 1993 }
  elseif ($Slug -eq "batman-subzero") { $yearStart = 1998 }
  elseif ($Slug -eq "batman-return-of-the-joker") { $yearStart = 2000 }
  elseif ($Slug -eq "spiderman-animated") { $yearStart = 1994 }
  elseif ($Slug -eq "justice-league-movies") { $yearStart = 2008 }
  elseif ($Slug -eq "batman-tas-movies") { $yearStart = 1993 }
  $body = @{
    slug          = $Slug
    title         = $Title
    english_title = $Title
    franchise     = $franchise
    year_start    = $yearStart
    poster_key    = $posterKey
    backdrop_key  = $backdropKey
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

$candidates = @(Get-ChildItem -Path $SourceDir -File -Recurse | Where-Object {
  if ($_.Extension -notmatch '(?i)^\.(mp4|mkv|m4v|mov)$') { return $false }
  if ($_.BaseName -match '(?i)^sample$|\bsample\b') { return $false }
  if (Test-IsExtraPath $_.FullName) { return $false }
  if ($ExcludePathPattern -and ($_.FullName -match $ExcludePathPattern)) { return $false }
  $true
})
if (-not $candidates) {
  throw "No video files (.mp4/.mkv) in: $SourceDir"
}

# One source per episode. Prefer MP4 when both MP4 and MKV exist.
# Remap absolute episode numbers per season (BTAS Vol2 S02E29 -> S02E01).
$parsed = @()
foreach ($f in $candidates) {
  $info = Get-EpisodeInfoFromPath $f
  if (-not $info) {
    Write-Warning "Skip (cannot parse SxxExx / 01x01 / Ep.NN / numbered folder): $($f.Name)"
    continue
  }
  $title = $null
  if ($info.PSObject.Properties.Name -contains "Title" -and $info.Title) {
    $title = $info.Title
  } else {
    $title = Get-EpisodeTitle $f.BaseName
  }
  $parsed += [pscustomobject]@{
    File    = $f
    Season  = $info.Season
    Episode = $info.Episode
    Title   = $title
  }
}

$videos = @(
  $parsed |
    Group-Object Season |
    ForEach-Object {
      $seasonNum = [int]$_.Name
      $minEp = [int](($_.Group | Measure-Object -Property Episode -Minimum).Minimum)
      $offset = 0
      if ($minEp -gt 1) {
        $offset = $minEp - 1
        Write-Host "==> Remap S$seasonNum absolute eps: E$minEp+ -> E1+ (offset -$offset)"
      }
      $_.Group | ForEach-Object {
        [pscustomobject]@{
          File    = $_.File
          Season  = $seasonNum
          Episode = [int]($_.Episode - $offset)
          Title   = $_.Title
        }
      }
    } |
    Group-Object { "{0:D2}x{1:D3}" -f ([int]$_.Season), ([int]$_.Episode) } |
    ForEach-Object {
      $_.Group |
        Sort-Object @{
          Expression = {
            if ($_.File.Extension -ieq ".mp4") { 0 }
            elseif ($_.File.Extension -ieq ".mkv") { 1 }
            else { 2 }
          }
        }, { $_.File.Length } |
        Select-Object -First 1
    }
)

Write-Host "==> $($candidates.Count) source file(s), $($videos.Count) unique episode(s) in $SourceDir"
Write-Host "==> Series: $SeriesSlug -> $Bucket/<slug>/sXXeYY/"

$ok = 0
$skip = 0
$fail = 0

foreach ($item in $videos | Sort-Object Season, Episode) {
  $vid = $item.File
  $season = $item.Season
  $episode = $item.Episode
  $epCode = "s{0:D2}e{1:D2}" -f $season, $episode
  $objectPrefix = "$SeriesSlug/$epCode"
  $masterKey = "$objectPrefix/master.m3u8"
  $work = Join-Path $env:TEMP "cinehome-hls-$SeriesSlug-$epCode"
  $title = $item.Title

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

  # -ac 2: browser khong phat duoc AAC 5.1 (nguon web-dl DDP) -> ep stereo
  & ffmpeg -hide_banner -loglevel error -y -i $vid.FullName `
    -c:v libx264 -preset veryfast -crf 22 `
    -c:a aac -b:a 160k -ac 2 `
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
