# DocChat Enterprise - Script de inicio con entorno virtual en D:
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DocChat Enterprise - Iniciando..." -ForegroundColor Cyan
Write-Host "  (Usando entorno virtual en D:\)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Activar entorno virtual en D:
$venvPath = "D:\DocChatEnterprise_venv"
if (-not (Test-Path "$venvPath\Scripts\Activate.ps1")) {
    Write-Host "❌ Error: Entorno virtual no encontrado en $venvPath" -ForegroundColor Red
    Write-Host "Ejecuta primero: py -m venv D:\DocChatEnterprise_venv" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Activando entorno virtual..." -ForegroundColor Green
& "$venvPath\Scripts\Activate.ps1"

# Configurar variables de entorno para usar D: como temporal
$env:TMPDIR = "D:\pip_temp"
$env:TEMP = "D:\pip_temp"
$env:TMP = "D:\pip_temp"
$env:GRADIO_TEMP_DIR = "D:\gradio_temp"
New-Item -ItemType Directory -Force -Path "D:\pip_temp", "D:\gradio_temp" | Out-Null

# Configurar API Key
$env:OPENAI_API_KEY = "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"

Write-Host "✅ API Key configurada" -ForegroundColor Green
Write-Host "✅ Archivos temporales en D:\" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 Iniciando aplicación..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Cuando veas 'Running on local URL', abre tu navegador en:" -ForegroundColor Cyan
Write-Host "   http://127.0.0.1:7860" -ForegroundColor White
Write-Host ""
Write-Host "Presiona Ctrl+C para detener la aplicación" -ForegroundColor Yellow
Write-Host ""

# Ejecutar app.py con el Python del entorno virtual
python app.py

