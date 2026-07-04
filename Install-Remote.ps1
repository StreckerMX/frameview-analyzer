#Requires -Version 5.1
<#
.SYNOPSIS
    Instala o actualiza FrameView Analyzer desde GitHub y abre la interfaz gráfica.
.EXAMPLE
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; irm https://raw.githubusercontent.com/StreckerMX/frameview-analyzer/main/Install-Remote.ps1 | iex
#>

$ErrorActionPreference = "Stop"

$RepoOwner = "StreckerMX"
$RepoName = "frameview-analyzer"
$InstallDir = Join-Path $env:LOCALAPPDATA "FrameViewAnalyzer"
$ZipUrl = "https://github.com/$RepoOwner/$RepoName/archive/refs/heads/main.zip"
$RequirementsFile = "FrameViewAnalyzer.Requirements.txt"
$EntryPoint = "Start-FrameViewAnalyzer.py"
$ShortcutName = "FrameView Analyzer"

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

    if (-not (Test-Path $TargetDir)) {
        New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    }

    Get-ChildItem -LiteralPath $TargetDir -Force | Where-Object {
        $_.Name -notin @("venv")
    } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

    Copy-Item -Path (Join-Path $sourceDir.FullName "*") -Destination $TargetDir -Recurse -Force
    Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}

function Update-FromGit([string]$TargetDir) {
    if (-not (Test-Path (Join-Path $TargetDir ".git"))) {
        throw "No es un repositorio git."
    }
    git -C $TargetDir pull --ff-only
}

function New-DesktopShortcut([string]$ProjectRoot) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktop "$ShortcutName.lnk"
    $launcher = Join-Path $ProjectRoot "Start-FrameViewAnalyzer.ps1"
    try {
        $wsh = New-Object -ComObject WScript.Shell
        $shortcut = $wsh.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = "powershell.exe"
        $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$launcher`""
        $shortcut.WorkingDirectory = $ProjectRoot
        $shortcut.Description = "Analizador de metricas NVIDIA FrameView"
        $shortcut.Save()
        return $true
    } catch {
        return $false
    }
}

Clear-Host
Write-Host "`n  FrameView Analyzer - Instalacion remota`n" -ForegroundColor Green

Write-Step "1/4  Verificando Python..."
$pythonCmd = Get-PythonCmd
if (-not $pythonCmd) {
    Write-Host "  Se requiere Python 3.10 o superior." -ForegroundColor Red
    Write-Host "  Descarga: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}
Write-Ok "$(& $pythonCmd --version 2>&1)"

Write-Step "2/4  Actualizando aplicacion en $InstallDir"
$updatedWithGit = $false
if ((Get-Command git -ErrorAction SilentlyContinue) -and (Test-Path (Join-Path $InstallDir ".git"))) {
    try {
        Update-FromGit $InstallDir
        $updatedWithGit = $true
        Write-Ok "Codigo actualizado con git pull"
    } catch {
        Write-Host "  git pull fallo, usando descarga ZIP..." -ForegroundColor Yellow
    }
}
if (-not $updatedWithGit) {
    Update-FromZip $InstallDir
    Write-Ok "Codigo actualizado desde GitHub"
}

Write-Step "3/4  Preparando entorno..."
$venvPath = Join-Path $InstallDir "venv"
if (-not (Test-Path (Join-Path $venvPath "Scripts\python.exe"))) {
    & $pythonCmd -m venv $venvPath
}
$venvPython = Join-Path $venvPath "Scripts\python.exe"
& $venvPython -m pip install --upgrade pip -q
& $venvPython -m pip install -r (Join-Path $InstallDir $RequirementsFile) -q
Write-Ok "Dependencias instaladas en venv"

if (New-DesktopShortcut $InstallDir) {
    Write-Ok "Acceso directo: $ShortcutName"
}

Write-Step "4/4  Abriendo FrameView Analyzer..."
Write-Host "`n  Listo. Se abrira la aplicacion.`n" -ForegroundColor Green
Set-Location $InstallDir
& $venvPython (Join-Path $InstallDir $EntryPoint)