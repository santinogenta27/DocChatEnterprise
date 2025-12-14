# Script para verificar si la aplicación está corriendo

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Verificando estado de la aplicación" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar procesos de Python
Write-Host "1. Verificando procesos de Python..." -ForegroundColor Yellow
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "   ✅ Se encontraron procesos de Python:" -ForegroundColor Green
    $pythonProcesses | ForEach-Object {
        Write-Host "      - PID: $($_.Id) | Inicio: $($_.StartTime)" -ForegroundColor White
    }
} else {
    Write-Host "   ❌ No se encontraron procesos de Python ejecutándose" -ForegroundColor Red
}

Write-Host ""

# Verificar puerto 7860
Write-Host "2. Verificando puerto 7860..." -ForegroundColor Yellow
try {
    $connection = Test-NetConnection -ComputerName 127.0.0.1 -Port 7860 -WarningAction SilentlyContinue -InformationLevel Quiet
    if ($connection) {
        Write-Host "   ✅ Puerto 7860 está activo - La aplicación está corriendo" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Puerto 7860 no está activo" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ Error verificando puerto: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Intentar hacer una petición HTTP
Write-Host "3. Intentando conectar a http://127.0.0.1:7860..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:7860" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
    Write-Host "   ✅ Aplicación respondiendo correctamente" -ForegroundColor Green
    Write-Host "      Status Code: $($response.StatusCode)" -ForegroundColor White
    Write-Host "      URL disponible: http://127.0.0.1:7860" -ForegroundColor Cyan
} catch {
    Write-Host "   ⚠️  No se pudo conectar a la aplicación" -ForegroundColor Yellow
    Write-Host "      $($_.Exception.Message)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan


