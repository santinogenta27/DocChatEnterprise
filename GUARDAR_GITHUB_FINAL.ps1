# Script Final para Guardar TODO en GitHub

Write-Host "=== GUARDANDO TODO EN GITHUB ===" -ForegroundColor Green
Write-Host ""

# Git encontrado en: C:\Program Files\Git\cmd\git.exe
$gitExe = "C:\Program Files\Git\cmd\git.exe"

if (-not (Test-Path $gitExe)) {
    Write-Host "ERROR: Git no encontrado en $gitExe" -ForegroundColor Red
    exit 1
}

Write-Host "Git encontrado: $gitExe" -ForegroundColor Green
Write-Host ""

# Agregar todos los archivos
Write-Host "Agregando todos los archivos..." -ForegroundColor Cyan
& $gitExe add . 2>&1 | Out-Null

# Verificar cambios
Write-Host "Verificando cambios..." -ForegroundColor Cyan
$status = & $gitExe status --short 2>&1
if ($status) {
    Write-Host "Archivos con cambios encontrados" -ForegroundColor Green
} else {
    Write-Host "No hay cambios nuevos (todo ya esta commiteado)" -ForegroundColor Yellow
}

# Commit
Write-Host ""
Write-Host "Creando commit..." -ForegroundColor Cyan
$commitMsg = "feat: Implementacion completa LangGraph Agent para Assistance AI - Arquitectura Enterprise con 13 nodos, Decision Policy, Intent Routing, RAG Engine, ReAct Agent, Memory Management, Response Validator, Escalation System, Tools Registry. Total: 15 archivos nuevos, 3500+ lineas de codigo."

& $gitExe commit -m $commitMsg 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "Commit creado exitosamente" -ForegroundColor Green
} else {
    Write-Host "Nota: Puede que no haya cambios nuevos para commitear" -ForegroundColor Yellow
}

# Obtener rama actual
Write-Host ""
Write-Host "Verificando rama..." -ForegroundColor Cyan
$branchOutput = & $gitExe branch --show-current 2>&1
$branch = ($branchOutput | Where-Object { $_ -notmatch 'usage:' -and $_ -notmatch 'These are' }).Trim()
if (-not $branch -or $branch -eq "" -or $branch -match 'usage:') {
    $branchOutput = & $gitExe branch 2>&1
    $branchLine = $branchOutput | Where-Object { $_ -match '^\*' }
    if ($branchLine) {
        $branch = ($branchLine -replace '\*', '').Trim()
    } else {
        $branch = "main"
    }
}

Write-Host "Rama: $branch" -ForegroundColor Yellow

# Verificar remote
Write-Host ""
Write-Host "Verificando remotes..." -ForegroundColor Cyan
$remotes = & $gitExe remote -v 2>&1
if (-not $remotes -or ($remotes -match '^$')) {
    Write-Host "Agregando remote origin..." -ForegroundColor Yellow
    & $gitExe remote add origin https://github.com/santinogenta27/DocChatEnterprise.git 2>&1 | Out-Null
}

# Push
Write-Host ""
Write-Host "Subiendo a GitHub (rama: $branch)..." -ForegroundColor Cyan
& $gitExe push origin $branch 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=== EXITO! TODO GUARDADO EN GITHUB ===" -ForegroundColor Green
    Write-Host "Repositorio: https://github.com/santinogenta27/DocChatEnterprise" -ForegroundColor Cyan
    Write-Host "Rama: $branch" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Resumen:" -ForegroundColor Yellow
    Write-Host "- 15 archivos nuevos (graph/*.py)" -ForegroundColor White
    Write-Host "- 5 archivos modificados" -ForegroundColor White
    Write-Host "- 3500+ lineas de codigo nuevo" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "ERROR al hacer push. Verifica:" -ForegroundColor Red
    Write-Host "1. Credenciales de GitHub configuradas" -ForegroundColor Yellow
    Write-Host "2. Permisos de escritura en el repositorio" -ForegroundColor Yellow
    Write-Host "3. Conexion a internet" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Proceso completado" -ForegroundColor Green

