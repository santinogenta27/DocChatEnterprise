# Script para guardar en GitHub usando Git desde cualquier ubicacion

Write-Host "Buscando Git..." -ForegroundColor Cyan

# Buscar Git en ubicaciones comunes
$gitExe = $null
$searchPaths = @(
    "C:\Program Files\Git\cmd\git.exe",
    "C:\Program Files\Git\bin\git.exe",
    "C:\Program Files (x86)\Git\cmd\git.exe",
    "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe",
    "$env:ProgramFiles\Git\cmd\git.exe"
)

foreach ($path in $searchPaths) {
    if (Test-Path $path) {
        $gitExe = $path
        Write-Host "Git encontrado: $path" -ForegroundColor Green
        break
    }
}

# Si no se encuentra, intentar usar git del PATH
if (-not $gitExe) {
    try {
        $gitCmd = Get-Command git -ErrorAction SilentlyContinue
        if ($gitCmd) {
            $gitExe = "git"
            Write-Host "Git encontrado en PATH" -ForegroundColor Green
        }
    } catch {
        # Continuar
    }
}

if (-not $gitExe) {
    Write-Host ""
    Write-Host "ERROR: Git no encontrado." -ForegroundColor Red
    Write-Host "Por favor instala Git primero ejecutando:" -ForegroundColor Yellow
    Write-Host "  C:\Users\usuario\Downloads\Git-2.52.0-64-bit.exe" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "O usa GitHub Desktop para hacer commit y push." -ForegroundColor Yellow
    exit 1
}

# Funcion para ejecutar git
function Invoke-Git {
    param([string[]]$Args)
    if ($gitExe -eq "git") {
        & git $Args
    } else {
        & $gitExe $Args
    }
    return $LASTEXITCODE -eq 0
}

# Verificar que estamos en un repositorio
if (-not (Test-Path ".git")) {
    Write-Host "ERROR: No es un repositorio Git. Inicializando..." -ForegroundColor Yellow
    Invoke-Git @("init")
    Invoke-Git @("remote", "add", "origin", "https://github.com/santinogenta27/DocChatEnterprise.git")
}

# Verificar rama
Write-Host ""
Write-Host "Verificando rama..." -ForegroundColor Cyan
$branchOutput = Invoke-Git @("branch", "--show-current") | Out-String
$branch = $branchOutput.Trim()
if (-not $branch -or $branch -eq "") {
    $branch = "main"
    # Intentar crear rama main si no existe
    Invoke-Git @("checkout", "-b", "main") | Out-Null
}
Write-Host "Rama: $branch" -ForegroundColor Yellow

# Agregar archivos
Write-Host ""
Write-Host "Agregando archivos..." -ForegroundColor Cyan
Invoke-Git @("add", ".")

# Estado
Write-Host "Estado:" -ForegroundColor Cyan
Invoke-Git @("status", "--short") | Select-Object -First 10

# Commit
Write-Host ""
Write-Host "Creando commit..." -ForegroundColor Cyan
$commitMsg = "feat: Implementacion completa LangGraph Agent para Assistance AI"
if (-not (Invoke-Git @("commit", "-m", $commitMsg))) {
    $status = Invoke-Git @("status", "--porcelain")
    if (-not $status) {
        Write-Host "No hay cambios para commitear (ya esta commiteado)" -ForegroundColor Yellow
    } else {
        Write-Host "ERROR creando commit" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Commit creado exitosamente" -ForegroundColor Green
}

# Verificar remote
Write-Host ""
Write-Host "Verificando remoto..." -ForegroundColor Cyan
$remotes = Invoke-Git @("remote", "-v") | Out-String
if (-not $remotes -or $remotes -notmatch "origin") {
    Write-Host "Agregando remote origin..." -ForegroundColor Yellow
    Invoke-Git @("remote", "add", "origin", "https://github.com/santinogenta27/DocChatEnterprise.git")
}

# Push
Write-Host ""
Write-Host "Subiendo a GitHub..." -ForegroundColor Cyan
if (Invoke-Git @("push", "-u", "origin", $branch)) {
    Write-Host ""
    Write-Host "EXITO! Cambios guardados en GitHub" -ForegroundColor Green
    Write-Host "Repositorio: https://github.com/santinogenta27/DocChatEnterprise.git" -ForegroundColor Cyan
    Write-Host "Rama: $branch" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "ERROR al hacer push" -ForegroundColor Red
    Write-Host "Verifica tus credenciales de GitHub" -ForegroundColor Yellow
    Write-Host "Puedes intentar manualmente:" -ForegroundColor Cyan
    Write-Host "  git push -u origin $branch" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "Proceso completado!" -ForegroundColor Green

