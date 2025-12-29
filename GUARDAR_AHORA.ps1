# Script SIMPLIFICADO - Solo guarda si Git esta disponible

Write-Host "Buscando Git..." -ForegroundColor Cyan

# Buscar Git instalado
$gitExe = $null
$paths = @(
    "C:\Program Files\Git\cmd\git.exe",
    "C:\Program Files\Git\bin\git.exe",
    "C:\Program Files (x86)\Git\cmd\git.exe",
    "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe"
)

foreach ($p in $paths) {
    if (Test-Path $p) {
        $gitExe = $p
        Write-Host "Git encontrado: $p" -ForegroundColor Green
        break
    }
}

if (-not $gitExe) {
    Write-Host ""
    Write-Host "ERROR: Git no esta instalado o no se encuentra." -ForegroundColor Red
    Write-Host ""
    Write-Host "SOLUCION RAPIDA:" -ForegroundColor Yellow
    Write-Host "1. Instala Git desde: https://git-scm.com/download/win" -ForegroundColor Cyan
    Write-Host "   O ejecuta: C:\Users\usuario\Downloads\Git-2.52.0-64-bit.exe" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "2. O usa GitHub Desktop (mas facil):" -ForegroundColor Yellow
    Write-Host "   - Abre GitHub Desktop" -ForegroundColor Cyan
    Write-Host "   - Abre este repositorio" -ForegroundColor Cyan
    Write-Host "   - Click en Commit y Push" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

# Agregar al PATH
$gitDir = Split-Path $gitExe -Parent
$env:PATH = "$gitDir;$env:PATH"

# Cambiar al directorio
Set-Location "C:\Users\usuario\DocChatEnterprise"

Write-Host ""
Write-Host "Estado del repositorio:" -ForegroundColor Cyan
& $gitExe status --short | Select-Object -First 5

# Agregar todo
Write-Host ""
Write-Host "Agregando archivos..." -ForegroundColor Cyan
& $gitExe add .

# Commit
Write-Host "Creando commit..." -ForegroundColor Cyan
$msg = "feat: Implementacion completa LangGraph Agent para Assistance AI"
$commitResult = & $gitExe commit -m $msg 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "Commit creado exitosamente" -ForegroundColor Green
} else {
    $commitOutput = $commitResult | Out-String
    if ($commitOutput -match "nothing to commit") {
        Write-Host "No hay cambios nuevos (ya esta commiteado)" -ForegroundColor Yellow
    } else {
        Write-Host "Advertencia al crear commit, pero continuando..." -ForegroundColor Yellow
    }
}

# Obtener rama
$branch = & $gitExe branch --show-current 2>&1 | Out-String | ForEach-Object { $_.Trim() }
if (-not $branch) { $branch = "main" }
Write-Host "Rama: $branch" -ForegroundColor Yellow

# Verificar remote
$remotes = & $gitExe remote -v 2>&1 | Out-String
if ($remotes -notmatch "origin") {
    Write-Host "Agregando remote origin..." -ForegroundColor Yellow
    & $gitExe remote add origin "https://github.com/santinogenta27/DocChatEnterprise.git" 2>&1 | Out-Null
}

# Push
Write-Host ""
Write-Host "Subiendo a GitHub..." -ForegroundColor Cyan
$pushResult = & $gitExe push -u origin $branch 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "EXITO! Todo guardado en GitHub" -ForegroundColor Green
    Write-Host "Repositorio: https://github.com/santinogenta27/DocChatEnterprise.git" -ForegroundColor Cyan
    Write-Host "Rama: $branch" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "ERROR al hacer push:" -ForegroundColor Red
    $pushResult | ForEach-Object { Write-Host $_ -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "Posibles soluciones:" -ForegroundColor Yellow
    Write-Host "1. Configura Git usuario:" -ForegroundColor Cyan
    Write-Host "   git config --global user.name 'Tu Nombre'" -ForegroundColor White
    Write-Host "   git config --global user.email 'tu@email.com'" -ForegroundColor White
    Write-Host ""
    Write-Host "2. O usa GitHub Desktop (mas facil)" -ForegroundColor Cyan
    exit 1
}

Write-Host ""
Write-Host "Proceso completado!" -ForegroundColor Green

