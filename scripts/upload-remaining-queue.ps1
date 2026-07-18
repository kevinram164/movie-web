<#
.SYNOPSIS
  Queue remaining CineHome uploads after current job (TNBA / etc.).
  Kong/Kafka later — focus on finishing media first.

.EXAMPLE
  .\scripts\upload-remaining-queue.ps1 -SkipExisting -SyncCatalog -Insecure
#>
param(
  [switch]$SkipExisting,
  [switch]$SyncCatalog,
  [switch]$Insecure,
  [switch]$WhatIf,
  [switch]$SkipBatman2004,
  [switch]$SkipBatmanMovies,
  [switch]$SkipJusticeLeague
)

$ErrorActionPreference = "Stop"
$season = Join-Path $PSScriptRoot "transcode-upload-season.ps1"
$batmanRoot = "D:\Movie\BATMAN Cartoons (1992-2015) - The FIVE Complete Animated Series - 480p-720p x264"
$jlRoot = "D:\Movie\JUSTICE LEAGUE (2008-2016) - Cartoon MOVIES Pack - 720p BrRip x264"

function Invoke-Season {
  param(
    [Parameter(Mandatory = $true)]
    [string]$SourceDir,
    [Parameter(Mandatory = $true)]
    [string]$SeriesSlug,
    [switch]$NumberedFolders,
    [string]$ExcludePathPattern = ""
  )
  Write-Host ""
  Write-Host "############################################################"
  Write-Host " $SeriesSlug <- $SourceDir"
  Write-Host "############################################################"
  $splat = @{
    SourceDir    = $SourceDir
    SeriesSlug   = $SeriesSlug
    SkipExisting = $SkipExisting
    SyncCatalog  = $SyncCatalog
    Insecure     = $Insecure
    WhatIf       = $WhatIf
  }
  if ($NumberedFolders) { $splat.NumberedFolders = $true }
  if ($ExcludePathPattern) { $splat.ExcludePathPattern = $ExcludePathPattern }
  & $season @splat
}

# 1) The Batman (2004)
if (-not $SkipBatman2004) {
  Invoke-Season `
    -SourceDir (Join-Path $batmanRoot "3a. The Batman (2004-08)") `
    -SeriesSlug "the-batman-2004"
}

# 2) BTAS movies + Return of the Joker
if (-not $SkipBatmanMovies) {
  Invoke-Season `
    -SourceDir (Join-Path $batmanRoot "1b. T.A.S. Movies (1993-98)") `
    -SeriesSlug "batman-tas-movies" `
    -NumberedFolders

  Invoke-Season `
    -SourceDir (Join-Path $batmanRoot "2b. BB - Return of the Joker (2000)") `
    -SeriesSlug "batman-return-of-the-joker" `
    -NumberedFolders `
    -ExcludePathPattern '(?i)[\\/]Extras?[\\/]|sample'
}

# 3) Justice League animated movies
if (-not $SkipJusticeLeague) {
  if (-not (Test-Path -LiteralPath $jlRoot)) {
    Write-Warning "JL pack not found: $jlRoot"
  } else {
    Invoke-Season `
      -SourceDir $jlRoot `
      -SeriesSlug "justice-league-movies" `
      -NumberedFolders `
      -ExcludePathPattern '(?i)Torrent'
  }
}

Write-Host ""
Write-Host "All queued uploads finished."
