# Script para configurar variables de entorno en PowerShell

Write-Host "🔧 Configurando variables de entorno para DocChat Enterprise..." -ForegroundColor Cyan

# Solicitar API Key
$apiKey = Read-Host "Ingresa tu OPENAI_API_KEY (o presiona Enter para usar la del .env)"

if ($apiKey) {
    $env:OPENAI_API_KEY = $apiKey
    Write-Host "✅ OPENAI_API_KEY configurada" -ForegroundColor Green
} else {
    Write-Host "📝 Usando OPENAI_API_KEY del archivo .env" -ForegroundColor Yellow
}

# Verificar si existe .env
$envFile = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "📝 Creando archivo .env..." -ForegroundColor Yellow
    if ($apiKey) {
        "OPENAI_API_KEY=$apiKey" | Out-File -FilePath $envFile -Encoding utf8
        Write-Host "✅ Archivo .env creado con OPENAI_API_KEY" -ForegroundColor Green
    } else {
        "OPENAI_API_KEY=tu-clave-aqui" | Out-File -FilePath $envFile -Encoding utf8
        Write-Host "⚠️  Archivo .env creado. Edítalo y agrega tu OPENAI_API_KEY" -ForegroundColor Yellow
    }
}

Write-Host "`n🚀 Para ejecutar la aplicación:" -ForegroundColor Cyan
Write-Host "   python app.py" -ForegroundColor White
Write-Host "`n📖 O ejecuta este script cada vez que abras PowerShell:" -ForegroundColor Cyan
Write-Host "   .\setup_env.ps1" -ForegroundColor White



