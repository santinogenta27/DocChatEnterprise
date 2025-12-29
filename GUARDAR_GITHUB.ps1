# Script para Guardar TODO en GitHub

Write-Host "=== GUARDANDO TODO EN GITHUB ===" -ForegroundColor Green

# Buscar Git
$gitExe = $null

# Buscar en PATH
try {
    $gitCmd = Get-Command git -ErrorAction SilentlyContinue
    if ($gitCmd) {
        $gitExe = $gitCmd.Source
        Write-Host "Git encontrado: $gitExe" -ForegroundColor Green
    }
} catch {}

# Buscar en ubicaciones comunes
if (-not $gitExe) {
    $paths = @(
        "$env:USERPROFILE\Downloads\Git\cmd\git.exe",
        "$env:USERPROFILE\Downloads\PortableGit\cmd\git.exe",
        "$env:USERPROFILE\Downloads\git.exe",
        "C:\Program Files\Git\cmd\git.exe",
        "C:\Program Files (x86)\Git\cmd\git.exe"
    )
    
    foreach ($path in $paths) {
        if (Test-Path $path) {
            $gitExe = $path
            Write-Host "Git encontrado: $gitExe" -ForegroundColor Green
            break
        }
    }
}

# Buscar en Descargas recursivamente
if (-not $gitExe) {
    $foundGit = Get-ChildItem -Path "$env:USERPROFILE\Downloads" -Recurse -Filter "git.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($foundGit) {
        $gitExe = $foundGit.FullName
        Write-Host "Git encontrado: $gitExe" -ForegroundColor Green
        # Agregar al PATH
        $gitDir = Split-Path (Split-Path $gitExe -Parent) -Parent
        $env:PATH = "$gitDir\cmd;$env:PATH"
    }
}

if (-not $gitExe) {
    Write-Host "ERROR: Git no encontrado" -ForegroundColor Red
    Write-Host "Por favor, proporciona la ruta exacta a git.exe" -ForegroundColor Yellow
    exit 1
}

# Funcion git
function git-cmd {
    param([string[]]$args)
    if ($gitExe) {
        & $gitExe $args
        return $LASTEXITCODE -eq 0
    }
    return $false
}

# Verificar repo
if (-not (Test-Path ".git")) {
    Write-Host "ERROR: No es un repositorio Git" -ForegroundColor Red
    exit 1
}

# Agregar todos los archivos
Write-Host ""
Write-Host "Agregando todos los archivos..." -ForegroundColor Cyan
git-cmd @("add", ".") | Out-Null

# Commit
Write-Host "Creando commit..." -ForegroundColor Cyan
$msg = "feat: Implementacion completa LangGraph Agent para Assistance AI - Arquitectura Enterprise con 13 nodos, Decision Policy, Intent Routing, RAG Engine, ReAct Agent, Memory Management, Response Validator, Escalation System, Tools Registry. Total: 15 archivos nuevos, 3500+ lineas de codigo."
git-cmd @("commit", "-m", $msg) | Out-Null

# Rama
$branch = git-cmd @("branch", "--show-current") | Out-String | ForEach-Object { $_.Trim() }
if (-not $branch) { $branch = "main" }
Write-Host "Rama: $branch" -ForegroundColor Yellow

# Remote
$remotes = git-cmd @("remote", "-v")
if (-not $remotes) {
    Write-Host "Agregando remote origin..." -ForegroundColor Yellow
    git-cmd @("remote", "add", "origin", "https://github.com/santinogenta27/DocChatEnterprise.git") | Out-Null
}

# Push
Write-Host ""
Write-Host "Subiendo a GitHub..." -ForegroundColor Cyan
if (git-cmd @("push", "origin", $branch)) {
    Write-Host ""
    Write-Host "EXITO! TODO guardado en GitHub" -ForegroundColor Green
    Write-Host "Repositorio: https://github.com/santinogenta27/DocChatEnterprise" -ForegroundColor Cyan
    Write-Host "Rama: $branch" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "ERROR al hacer push. Verifica credenciales." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Proceso completado" -ForegroundColor Green

