$ErrorActionPreference = "Continue"
$logDir = Join-Path (Split-Path $PSScriptRoot -Parent) "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "upload-new-batman-series.log"
"==== START $(Get-Date -Format o) ====" | Out-File -FilePath $log -Encoding utf8

Set-Location (Split-Path $PSScriptRoot -Parent)
try {
  & ".\scripts\transcode-upload-season.ps1" `
    -SourceDir "D:\Movie\Batman.Caped.Crusader.S01.COMPLETE.1080p.AMZN.WEB.H264-SuccessfulCrab[TGx]" `
    -SeriesSlug "new-batman-series" `
    -SkipExisting `
    -SyncCatalog `
    -Insecure `
    -ApiBase "https://cinehome.automationecom.click/api" `
    2>&1 | ForEach-Object {
      $line = "$_"
      $line | Out-File -FilePath $log -Append -Encoding utf8
      $line
    }
  "EXIT=$LASTEXITCODE" | Out-File -FilePath $log -Append -Encoding utf8
} catch {
  $_ | Out-String | Out-File -FilePath $log -Append -Encoding utf8
  "EXIT=1" | Out-File -FilePath $log -Append -Encoding utf8
}
"==== END $(Get-Date -Format o) ====" | Out-File -FilePath $log -Append -Encoding utf8
