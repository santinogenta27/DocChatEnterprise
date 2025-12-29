# Script para instalar Git y luego guardar en GitHub

$gitInstaller = "$env:USERPROFILE\Downloads\Git-2.52.0-64-bit.exe"

Write-Host "Instalando Git..." -ForegroundColor Cyan

if (-not (Test-Path $gitInstaller)) {
    Write-Host "ERROR: Instalador de Git no encontrado en: $gitInstaller" -ForegroundColor Red
    Write-Host "Por favor descarga Git desde: https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

Write-Host "Instalando Git (esto puede tardar un minuto)..." -ForegroundColor Yellow
Write-Host "NOTA: La instalacion se hara en modo silencioso" -ForegroundColor Yellow

# Instalar Git silenciosamente en ubicacion por defecto
$installArgs = "/VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /COMPONENTS=icons,ext\shellhere,assoc,assoc_sh"
Start-Process -FilePath $gitInstaller -ArgumentList $installArgs -Wait -NoNewWindow

Write-Host "Esperando que Git se instale..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Buscar Git instalado
$gitExe = $null
$possiblePaths = @(
    "C:\Program Files\Git\cmd\git.exe",
    "C:\Program Files\Git\bin\git.exe",
    "C:\Program Files (x86)\Git\cmd\git.exe"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $gitExe = $path
        Write-Host "Git instalado encontrado: $path" -ForegroundColor Green
        break
    }
}

if (-not $gitExe) {
    Write-Host "Git no se encontro despues de instalar. Reinicia PowerShell y vuelve a intentar." -ForegroundColor Red
    exit 1
}

# Agregar Git al PATH para esta sesion
$env:PATH = "$($gitExe | Split-Path -Parent);$env:PATH"

Write-Host ""
Write-Host "Guardando cambios en GitHub..." -ForegroundColor Cyan

# Funcion para ejecutar git
function Invoke-Git {
    param([string[]]$Args)
    & $gitExe $Args
    return $LASTEXITCODE -eq 0
}

# Cambiar al directorio del proyecto
Set-Location "C:\Users\usuario\DocChatEnterprise"

# Verificar que estamos en un repositorio
if (-not (Test-Path ".git")) {
    Write-Host "Inicializando repositorio Git..." -ForegroundColor Yellow
    Invoke-Git @("init")
}

# Verificar rama
$branchOutput = Invoke-Git @("branch", "--show-current") | Out-String
$branch = $branchOutput.Trim()
if (-not $branch -or $branch -eq "") {
    $branch = "main"
    Invoke-Git @("checkout", "-b", "main") | Out-Null
}

Write-Host "Rama: $branch" -ForegroundColor Yellow

# Agregar archivos
Write-Host "Agregando archivos..." -ForegroundColor Cyan
Invoke-Git @("add", ".")

# Commit
Write-Host "Creando commit..." -ForegroundColor Cyan
$commitMsg = "feat: Implementacion completa LangGraph Agent para Assistance AI"
if (Invoke-Git @("commit", "-m", $commitMsg)) {
    Write-Host "Commit creado" -ForegroundColor Green
} else {
    Write-Host "No hay cambios nuevos para commitear" -ForegroundColor Yellow
}

# Verificar remote
$remotes = Invoke-Git @("remote", "-v") | Out-String
if (-not $remotes -or $remotes -notmatch "origin") {
    Write-Host "Agregando remote origin..." -ForegroundColor Yellow
    Invoke-Git @("remote", "add", "origin", "https://github.com/santinogenta27/DocChatEnterprise.git")
}

# Push
Write-Host "Subiendo a GitHub..." -ForegroundColor Cyan
if (Invoke-Git @("push", "-u", "origin", $branch)) {
    Write-Host ""
    Write-Host "EXITO! Cambios guardados en GitHub" -ForegroundColor Green
    Write-Host "Repositorio: https://github.com/santinogenta27/DocChatEnterprise.git" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "ERROR al hacer push. Verifica tus credenciales." -ForegroundColor Red
    Write-Host "Puede que necesites configurar Git:" -ForegroundColor Yellow
    Write-Host "  git config --global user.name 'Tu Nombre'" -ForegroundColor White
    Write-Host "  git config --global user.email 'tu@email.com'" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "Proceso completado!" -ForegroundColor Green

