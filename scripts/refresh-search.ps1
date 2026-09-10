param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

& qmd update | Out-Host
if ($LASTEXITCODE -ne 0) { throw "QMD update failed." }

if ($Force) {
    & qmd embed -f | Out-Host
} else {
    & qmd embed | Out-Host
}
if ($LASTEXITCODE -ne 0) { throw "QMD embedding failed." }

& qmd status | Out-Host
if ($LASTEXITCODE -ne 0) { throw "QMD status failed." }

python scripts/validate_repo.py --full
if ($LASTEXITCODE -ne 0) { exit 1 }

python scripts/validate_content_release.py
if ($LASTEXITCODE -ne 0) { exit 2 }

Write-Host "SEARCH REFRESH PASS" -ForegroundColor Green
