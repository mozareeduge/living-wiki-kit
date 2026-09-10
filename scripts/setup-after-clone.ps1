param(
    [switch]$SkipQmd,
    [switch]$SkipObsidianPlugin
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

function Step($Text) {
    Write-Host ""
    Write-Host "=== $Text ===" -ForegroundColor Cyan
}

function Has-Command($Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

Step "Confirm repository root"
if (-not (Test-Path "SYSTEM_DESIGN.md") -or -not (Test-Path "_originals")) {
    throw "This script must run inside the This Wiki Git root."
}
Write-Host "Repository: $RepoRoot"

Step "Python dependencies and static validation"
if (-not (Has-Command "python")) {
    throw "Python is not available in PATH. Install Python 3.12, restart Claude Desktop or PowerShell, and run again."
}
python --version
python -m pip install --user -r requirements.txt
python scripts/validate_repo.py --full
python scripts/validate_content_release.py

if (-not $SkipQmd) {
    Step "Authority-aware QMD search"
    if (-not (Has-Command "npm")) {
        throw "npm is not available. Install Node.js 22 or newer, restart Claude Desktop or PowerShell, and run again."
    }
    node --version
    npm --version
    powershell -ExecutionPolicy Bypass -File scripts/configure-search.ps1
    powershell -ExecutionPolicy Bypass -File scripts/refresh-search.ps1
}

if (-not $SkipObsidianPlugin) {
    Step "Obsidian CLI and optional Git plugin"
    if (Has-Command "obsidian") {
        & obsidian version | Out-Host
        & obsidian vault info=path | Out-Host
        Write-Host "Attempting to install and enable the optional Obsidian Git plugin."
        & obsidian plugin:install id=obsidian-git enable | Out-Host
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Automatic plugin installation failed. GitHub Desktop remains the supported fallback."
        }
    } else {
        Write-Warning "Obsidian CLI is not visible in this process. Enable it in Obsidian Settings > General and restart Claude Desktop or PowerShell."
    }
}

Step "Claude Code or Claude Desktop"
Write-Host "The project MCP configuration is in .mcp.json. Approve only the qmd server."
Write-Host "Claude must treat GPT-authored bundles as bounded patches and must not rewrite the corpus autonomously."

Step "Final local verification"
python scripts/validate_repo.py --full
python scripts/validate_content_release.py
Write-Host ""
Write-Host "LOCAL STATIC SETUP PASS" -ForegroundColor Green
Write-Host "Next: run scripts/verify-install.ps1 and the semantic benchmark, then inspect 09-indexes/release-dashboard.md in Obsidian."
