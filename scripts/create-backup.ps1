param(
    [string]$Destination = "$env:USERPROFILE\Documents\Wiki-Wiki-Backups"
)
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$ZipPath = Join-Path $Destination "$($RepoName)_$Timestamp.zip"
$Temp = Join-Path $env:TEMP "wiki-backup-$Timestamp"
New-Item -ItemType Directory -Force -Path $Temp | Out-Null

Get-ChildItem -LiteralPath $RepoRoot -Force | Where-Object {
    $_.Name -notin @(".git", "_search", ".venv", "node_modules")
} | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $Temp -Recurse -Force
}

Compress-Archive -LiteralPath (Join-Path $Temp "*") -DestinationPath $ZipPath -CompressionLevel Optimal
Remove-Item -LiteralPath $Temp -Recurse -Force
Write-Host "Backup created: $ZipPath"
