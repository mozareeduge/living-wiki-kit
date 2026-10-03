param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Question,

    [ValidateSet("canonical", "source-records", "derivatives", "evidence")]
    [string]$Scope = "canonical",

    [int]$Limit = 10
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

# The QMD index is machine-wide; every query is scoped to this instance's own
# collections (from 00-system/configuration/qmd-collections-v1.1.0.json).
function Own-Collections([string]$Which) {
    $Out = (& python scripts/qmd_scope.py names @($Which.Split(" ")) | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $Out) { throw "No QMD collections configured for this instance." }
    return @($Out -split "\r?\n")
}

function Run-Query([string]$Heading, [string]$Which) {
    Write-Host ""
    Write-Host "=== $Heading ===" -ForegroundColor Cyan
    $Scope = @()
    foreach ($Name in (Own-Collections $Which)) { $Scope += @("-c", $Name) }
    & qmd query "$Question" @Scope --json -n $Limit
    if ($LASTEXITCODE -ne 0) { throw "QMD query failed for $Heading." }
}

switch ($Scope) {
    "canonical" {
        Run-Query "Canonical records" "--default"
    }
    "source-records" {
        Run-Query "Source records" "--role source-records"
    }
    "derivatives" {
        Run-Query "Extracted derivatives" "--role derivatives"
    }
    "evidence" {
        Run-Query "1. Canonical records" "--default"
        Run-Query "2. Source records" "--role source-records"
        Run-Query "3. Extracted derivatives" "--role derivatives"
        Write-Host ""
        Write-Host "Open the immutable original when exact wording, layout, image, or version identity matters." -ForegroundColor Yellow
    }
}
