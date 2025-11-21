# Script para conectar tu proyecto con GitHub

param(
    [Parameter(Mandatory=$true)]
    [string]$GitHubUser,
    
    [Parameter(Mandatory=$false)]
    [string]$RepoName = "DocChat-Enterprise"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CONFIGURANDO GITHUB" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si ya existe un remote
$existingRemote = git remote -v
if ($existingRemote) {
    Write-Host "⚠️  Ya existe un repositorio remoto:" -ForegroundColor Yellow
    Write-Host $existingRemote -ForegroundColor White
    $overwrite = Read-Host "¿Sobrescribir? (S/N)"
    if ($overwrite -ne "S") {
        Write-Host "❌ Cancelado" -ForegroundColor Red
        exit 0
    }
    git remote remove origin
}

# URL del repositorio
$repoUrl = "https://github.com/$GitHubUser/$RepoName.git"

Write-Host "Configurando repositorio remoto..." -ForegroundColor Cyan
Write-Host "Usuario: $GitHubUser" -ForegroundColor White
Write-Host "Repositorio: $RepoName" -ForegroundColor White
Write-Host "URL: $repoUrl" -ForegroundColor White
Write-Host ""

# Agregar remote
git remote add origin $repoUrl

Write-Host "✅ Repositorio remoto configurado" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PRÓXIMOS PASOS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Crea el repositorio en GitHub:" -ForegroundColor Yellow
Write-Host "   - Ve a: https://github.com/new" -ForegroundColor White
Write-Host "   - Nombre: $RepoName" -ForegroundColor White
Write-Host "   - NO inicialices con README (ya tienes archivos)" -ForegroundColor White
Write-Host ""
Write-Host "2. Luego ejecuta:" -ForegroundColor Yellow
Write-Host "   git push -u origin main" -ForegroundColor White
Write-Host "   git push -u origin desarrollo" -ForegroundColor White
Write-Host ""

