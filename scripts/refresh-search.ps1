param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

# The QMD index is shared by every wiki on this machine. Bare `qmd update`
# re-indexes all of them and `qmd embed -f` deletes all of their vectors, so
# both are scoped to this instance's own collections.
& python scripts/qmd_scope.py check-owned
if ($LASTEXITCODE -ne 0) { throw "QMD collection names collide with another wiki; see message above." }

& python scripts/qmd_scope.py update | Out-Host
if ($LASTEXITCODE -ne 0) { throw "QMD update failed." }

if ($Force) {
    & python scripts/qmd_scope.py embed --force | Out-Host
} else {
    & python scripts/qmd_scope.py embed | Out-Host
}
if ($LASTEXITCODE -ne 0) { throw "QMD embedding failed." }

& qmd status | Out-Host
if ($LASTEXITCODE -ne 0) { throw "QMD status failed." }

python scripts/validate_repo.py --full
if ($LASTEXITCODE -ne 0) { exit 1 }

python scripts/validate_content_release.py
if ($LASTEXITCODE -ne 0) { exit 2 }

Write-Host "SEARCH REFRESH PASS" -ForegroundColor Green
