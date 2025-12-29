# Script Simple para Guardar en GitHub
# Versión simplificada sin caracteres especiales problemáticos

Write-Host "Guardando cambios en GitHub..." -ForegroundColor Green

# Buscar Git
$git = $null
$paths = @(
    "C:\Program Files\Git\cmd\git.exe",
    "C:\Program Files (x86)\Git\cmd\git.exe",
    "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe"
)

foreach($p in $paths) {
    if(Test-Path $p) {
        $git = $p
        break
    }
}

if(-not $git) {
    Write-Host "ERROR: Git no encontrado. Instala Git o usa GitHub Desktop." -ForegroundColor Red
    exit 1
}

# Funcion para ejecutar git
function git-cmd {
    param([string[]]$args)
    & $git $args
    return $LASTEXITCODE -eq 0
}

# Verificar repositorio
if(-not (Test-Path ".git")) {
    Write-Host "ERROR: No es un repositorio Git" -ForegroundColor Red
    exit 1
}

# Agregar archivos
Write-Host "Agregando archivos..." -ForegroundColor Cyan
git-cmd @("add", ".")

# Commit
Write-Host "Creando commit..." -ForegroundColor Cyan
$msg = "feat: Implementacion completa LangGraph Agent para Assistance AI"
git-cmd @("commit", "-m", $msg)

# Obtener rama
$branch = git-cmd @("branch", "--show-current") | Out-String | ForEach-Object { $_.Trim() }
if(-not $branch) { $branch = "main" }

Write-Host "Rama: $branch" -ForegroundColor Yellow

# Push
Write-Host "Subiendo a GitHub..." -ForegroundColor Cyan
if(git-cmd @("push", "origin", $branch)) {
    Write-Host "EXITO! Cambios guardados en GitHub" -ForegroundColor Green
} else {
    Write-Host "Error al hacer push. Revisa credenciales." -ForegroundColor Red
    exit 1
}

