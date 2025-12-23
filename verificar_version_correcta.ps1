# Script para verificar y asegurar que estás en la versión correcta del proyecto
# Ejecuta este script antes de iniciar Gradio para asegurarte de que tienes la versión guardada

Write-Host "🔍 Verificando versión del proyecto..." -ForegroundColor Cyan
Write-Host ""

# Navegar al directorio del proyecto
$projectPath = "C:\Users\Random\DocChatEnterprise"
cd $projectPath

# Verificar branch actual
$currentBranch = git branch --show-current
Write-Host "📍 Branch actual: $currentBranch" -ForegroundColor Yellow

# Branch correcto que queremos usar
$correctBranch = "feature/copilot-mode-production-v2-20251217"

if ($currentBranch -ne $correctBranch) {
    Write-Host "⚠️  ADVERTENCIA: No estás en el branch correcto!" -ForegroundColor Red
    Write-Host "   Branch actual: $currentBranch" -ForegroundColor Red
    Write-Host "   Branch esperado: $correctBranch" -ForegroundColor Green
    Write-Host ""
    $response = Read-Host "¿Quieres cambiar al branch correcto? (S/N)"
    if ($response -eq "S" -or $response -eq "s") {
        git checkout $correctBranch
        $currentBranch = git branch --show-current
        Write-Host "✅ Cambiado a branch: $currentBranch" -ForegroundColor Green
    } else {
        Write-Host "❌ Cancelado. Asegúrate de estar en el branch correcto antes de continuar." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ Estás en el branch correcto: $correctBranch" -ForegroundColor Green
}

Write-Host ""

# Verificar si hay cambios sin commitear
$status = git status --porcelain
if ($status) {
    Write-Host "⚠️  HAY CAMBIOS SIN GUARDAR:" -ForegroundColor Red
    git status
    Write-Host ""
    Write-Host "💡 SUGERENCIA: Si quieres mantener estos cambios, haz commit primero." -ForegroundColor Yellow
    Write-Host "   Si quieres descartarlos y usar la versión guardada, ejecuta:" -ForegroundColor Yellow
    Write-Host "   git restore ." -ForegroundColor White
    Write-Host ""
    $response = Read-Host "¿Quieres continuar de todas formas? (S/N)"
    if ($response -ne "S" -and $response -ne "s") {
        Write-Host "❌ Cancelado." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ No hay cambios sin guardar" -ForegroundColor Green
}

Write-Host ""

# Sincronizar con remoto (pull)
Write-Host "🔄 Sincronizando con GitHub..." -ForegroundColor Cyan
$pullOutput = git pull origin $correctBranch 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Sincronizado con GitHub correctamente" -ForegroundColor Green
} else {
    Write-Host "⚠️  Problema al sincronizar (puede ser normal si ya estás actualizado)" -ForegroundColor Yellow
}

Write-Host ""

# Mostrar commit actual
$currentCommit = git log --oneline -1
Write-Host "📝 Commit actual:" -ForegroundColor Cyan
Write-Host $currentCommit -ForegroundColor White
Write-Host ""

# Verificar que el commit coincide con el guardado
$expectedCommit = "261b793"
if ($currentCommit -match $expectedCommit) {
    Write-Host "✅ Versión verificada: Commit $expectedCommit encontrado" -ForegroundColor Green
} else {
    Write-Host "⚠️  El commit actual no coincide con el esperado" -ForegroundColor Yellow
    Write-Host "   Commit esperado: $expectedCommit" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Verificación completada. Puedes iniciar Gradio con: py -3.12 app.py" -ForegroundColor Green
Write-Host ""












