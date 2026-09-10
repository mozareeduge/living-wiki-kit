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

function Run-Query([string]$Heading, [string]$Collection) {
    Write-Host ""
    Write-Host "=== $Heading ===" -ForegroundColor Cyan
    if ($Collection) {
        & qmd query "$Question" -c $Collection --json -n $Limit
    } else {
        & qmd query "$Question" --json -n $Limit
    }
    if ($LASTEXITCODE -ne 0) { throw "QMD query failed for $Heading." }
}

switch ($Scope) {
    "canonical" {
        Run-Query "Canonical records" ""
    }
    "source-records" {
        Run-Query "Source records" "wiki-source-records"
    }
    "derivatives" {
        Run-Query "Extracted derivatives" "wiki-derivatives"
    }
    "evidence" {
        Run-Query "1. Canonical records" ""
        Run-Query "2. Source records" "wiki-source-records"
        Run-Query "3. Extracted derivatives" "wiki-derivatives"
        Write-Host ""
        Write-Host "Open the immutable original when exact wording, layout, image, or version identity matters." -ForegroundColor Yellow
    }
}
