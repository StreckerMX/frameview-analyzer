#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)" -and ([int]$Matches[1] -gt 3 -or ([int]$Matches[1] -eq 3 -and [int]$Matches[2] -ge 10))) {
            $python = $cmd
            break
        }
    } catch {}
}

if (-not $python) {
    Write-Host "Python 3.10+ no encontrado." -ForegroundColor Red
    exit 1
}

& $python (Join-Path $Root "Start-FrameViewAnalyzer.py")