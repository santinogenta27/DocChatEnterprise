# Script para restaurar la versión guardada (descarta cambios locales)
# Usa este script si quieres asegurarte de tener exactamente la versión guardada

Write-Host "🔄 Restaurando versión guardada del proyecto..." -ForegroundColor Cyan
Write-Host "⚠️  ADVERTENCIA: Esto descartará todos los cambios locales sin guardar!" -ForegroundColor Red
Write-Host ""

$response = Read-Host "¿Estás seguro? Esto descartará cambios locales. Escribe 'SI' para continuar"
if ($response -ne "SI") {
    Write-Host "❌ Cancelado." -ForegroundColor Red
    exit 1
}

# Navegar al directorio del proyecto
$projectPath = "C:\Users\Random\DocChatEnterprise"
cd $projectPath

# Branch correcto
$correctBranch = "feature/copilot-mode-production-v2-20251217"

Write-Host ""
Write-Host "📍 Cambiando al branch correcto: $correctBranch" -ForegroundColor Cyan
git checkout $correctBranch --force

Write-Host ""
Write-Host "🗑️  Descartando cambios locales..." -ForegroundColor Cyan
git restore .
git clean -fd

Write-Host ""
Write-Host "🔄 Sincronizando con GitHub..." -ForegroundColor Cyan
git pull origin $correctBranch

Write-Host ""
Write-Host "✅ Versión restaurada correctamente!" -ForegroundColor Green
Write-Host ""

# Mostrar commit actual
$currentCommit = git log --oneline -1
Write-Host "📝 Commit actual:" -ForegroundColor Cyan
Write-Host $currentCommit -ForegroundColor White
Write-Host ""

Write-Host "✅ Puedes iniciar Gradio con: py -3.12 app.py" -ForegroundColor Green
Write-Host ""












