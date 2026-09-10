param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ConfigPath = Join-Path $RepoRoot "00-system/configuration/qmd-collections-v1.1.0.json"
Set-Location $RepoRoot

function Has-Command($Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Has-Command "qmd")) {
    if ($SkipInstall) {
        throw "QMD is not installed or not visible in PATH."
    }
    if (-not (Has-Command "npm")) {
        throw "npm is required to install QMD. Install Node.js 22 or newer, restart Claude Desktop or PowerShell, and run again."
    }
    npm install -g @tobilu/qmd
    if ($LASTEXITCODE -ne 0) { throw "QMD installation failed." }
}

$Config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$Existing = (& qmd collection list 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0) { throw "qmd collection list failed." }

$ManagedNames = @("wiki") + @($Config.collections | ForEach-Object { $_.name })
foreach ($Name in $ManagedNames) {
    if ($Existing -match "(?m)(^|\s)$([regex]::Escape($Name))(\s|$)") {
        Write-Host "Removing rebuildable collection registration: $Name"
        & qmd collection remove $Name | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "Failed to remove QMD collection $Name." }
    }
}

foreach ($Spec in $Config.collections) {
    $CollectionPath = (Resolve-Path (Join-Path $RepoRoot $Spec.path)).Path
    Write-Host "Adding $($Spec.name) from $CollectionPath"
    & qmd collection add "$CollectionPath" --name $Spec.name --mask $Spec.mask | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Failed to add QMD collection $($Spec.name)." }

    & qmd context add "qmd://$($Spec.name)" $Spec.context | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Failed to add QMD context for $($Spec.name)." }

    if ($Spec.include_by_default) {
        & qmd collection include $Spec.name | Out-Host
    } else {
        & qmd collection exclude $Spec.name | Out-Host
    }
    if ($LASTEXITCODE -ne 0) { throw "Failed to set default inclusion for $($Spec.name)." }
}

& qmd update | Out-Host
if ($LASTEXITCODE -ne 0) { throw "QMD update failed." }

Write-Host ""
Write-Host "AUTHORITY-AWARE QMD COLLECTIONS CONFIGURED" -ForegroundColor Green
& qmd collection list | Out-Host
& qmd context list | Out-Host
