# DocChat Enterprise - Script de inicio
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DocChat Enterprise - Iniciando..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configurar API Key
$env:OPENAI_API_KEY = "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"

Write-Host "✅ API Key configurada" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 Iniciando aplicación..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Cuando veas 'Running on local URL', abre tu navegador en:" -ForegroundColor Cyan
Write-Host "   http://127.0.0.1:7860" -ForegroundColor White
Write-Host ""
Write-Host "Presiona Ctrl+C para detener la aplicación" -ForegroundColor Yellow
Write-Host ""

python app.py



