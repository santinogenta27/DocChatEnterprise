# Script para inicializar Git y crear una rama de desarrollo
# Esto te permite trabajar en nuevas funcionalidades sin afectar la versión estable

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  INICIALIZANDO GIT PARA EL PROYECTO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si Git está instalado
try {
    $gitVersion = git --version
    Write-Host "✅ Git encontrado: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Git no está instalado" -ForegroundColor Red
    Write-Host "   Descarga Git desde: https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

# Verificar si ya existe un repositorio Git
if (Test-Path .git) {
    Write-Host "⚠️  Ya existe un repositorio Git" -ForegroundColor Yellow
    Write-Host "   Creando nueva rama para desarrollo..." -ForegroundColor Yellow
} else {
    Write-Host "Inicializando repositorio Git..." -ForegroundColor Cyan
    git init
    Write-Host "✅ Repositorio Git inicializado" -ForegroundColor Green
}

# Crear .gitignore si no existe
if (-not (Test-Path .gitignore)) {
    Write-Host "Creando .gitignore..." -ForegroundColor Cyan
    @"
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/

# DocChat específico
.docchat_cache/
.docchat_vectordb/
.docchat_memory/
.docchat_audit/
cache/
uploaded_files/

# Variables de entorno
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log

# OS
.DS_Store
Thumbs.db
"@ | Out-File -FilePath .gitignore -Encoding UTF8
    Write-Host "✅ .gitignore creado" -ForegroundColor Green
}

# Hacer commit inicial de la versión estable
Write-Host ""
Write-Host "Creando commit inicial de la versión estable..." -ForegroundColor Cyan
git add .
git commit -m "Versión estable - DocChat Enterprise funcionando (1000 docs, optimizado)"
Write-Host "✅ Versión estable guardada en Git" -ForegroundColor Green

# Crear rama de desarrollo
Write-Host ""
Write-Host "Creando rama 'desarrollo' para nuevas funcionalidades..." -ForegroundColor Cyan
git checkout -b desarrollo
Write-Host "✅ Rama 'desarrollo' creada" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  GIT CONFIGURADO CORRECTAMENTE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📌 Comandos útiles:" -ForegroundColor Yellow
Write-Host "   Ver ramas: git branch" -ForegroundColor White
Write-Host "   Cambiar a versión estable: git checkout main" -ForegroundColor White
Write-Host "   Cambiar a desarrollo: git checkout desarrollo" -ForegroundColor White
Write-Host "   Ver cambios: git status" -ForegroundColor White
Write-Host "   Deshacer cambios: git checkout ." -ForegroundColor White
Write-Host "   Guardar cambios: git add . && git commit -m 'mensaje'" -ForegroundColor White
Write-Host ""

