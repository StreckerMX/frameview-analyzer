#Requires -Version 5.1
<#
.SYNOPSIS
    Instala o actualiza FrameView Analyzer desde GitHub y abre la interfaz gráfica.
.EXAMPLE
    irm https://raw.githubusercontent.com/StreckerMX/frameview-analyzer/main/Install-Remote.ps1 | iex
#>

$ErrorActionPreference = "Stop"

$RepoOwner = "StreckerMX"
$RepoName = "frameview-analyzer"
$InstallDir = Join-Path $env:LOCALAPPDATA "FrameViewAnalyzer"
$ZipUrl = "https://github.com/$RepoOwner/$RepoName/archive/refs/heads/main.zip"
$RequirementsFile = "FrameViewAnalyzer.Requirements.txt"
$EntryPoint = "Start-FrameViewAnalyzer.py"

function Write-Step([string]$Text) { Write-Host "`n$Text" -ForegroundColor Cyan }
function Write-Ok([string]$Text) { Write-Host "  $Text" -ForegroundColor Green }

function Get-PythonCmd {
    foreach ($cmd in @("python", "python3", "py")) {
        try {
            $ver = & $cmd --version 2>&1
            if ($ver -match "Python (\d+)\.(\d+)" -and ([int]$Matches[1] -gt 3 -or ([int]$Matches[1] -eq 3 -and [int]$Matches[2] -ge 10))) {
                return $cmd
            }
        } catch {}
    }
    return $null
}

function Update-FromZip([string]$TargetDir) {
    $tempRoot = Join-Path $env:TEMP "fva-install-$([guid]::NewGuid().ToString('N'))"
    $zipPath = Join-Path $tempRoot "repo.zip"
    $extractDir = Join-Path $tempRoot "extract"
    New-Item -ItemType Directory -Path $extractDir -Force | Out-Null

    Write-Host "  Descargando ultima version..." -ForegroundColor DarkGray
    Invoke-WebRequest -Uri $ZipUrl -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force

    $sourceDir = Get-ChildItem $extractDir -Directory | Select-Object -First 1
    if (-not $sourceDir) { throw "No se pudo extraer el repositorio." }

    if (Test-Path $TargetDir) {
        Remove-Item $TargetDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    Copy-Item -Path (Join-Path $sourceDir.FullName "*") -Destination $TargetDir -Recurse -Force
    Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Step "FrameView Analyzer - Instalacion remota"
$python = Get-PythonCmd
if (-not $python) {
    Write-Host "Python 3.10+ no encontrado. Instala Python desde https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
Write-Ok "Python: $(& $python --version 2>&1)"

Write-Step "Descargando proyecto en $InstallDir"
Update-FromZip $InstallDir
Write-Ok "Archivos instalados"

Write-Step "Instalando dependencias"
& $python -m pip install --upgrade pip | Out-Null
& $python -m pip install -r (Join-Path $InstallDir $RequirementsFile)
Write-Ok "Dependencias listas"

Write-Step "Iniciando FrameView Analyzer"
Set-Location $InstallDir
& $python (Join-Path $InstallDir $EntryPoint)