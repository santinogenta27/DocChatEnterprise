# Script PowerShell para detener proceso en puerto 7864

Write-Host "🔍 Buscando proceso en puerto 7864..." -ForegroundColor Yellow

$port = 7864
$connections = netstat -ano | findstr ":$port"

if ($connections) {
    Write-Host "✅ Proceso encontrado:" -ForegroundColor Green
    Write-Host $connections
    
    # Extraer PID
    $pid = ($connections | Select-String -Pattern "LISTENING\s+(\d+)" | ForEach-Object { $_.Matches.Groups[1].Value }) | Select-Object -First 1
    
    if ($pid) {
        Write-Host "`n🛑 Deteniendo proceso PID: $pid" -ForegroundColor Red
        
        try {
            Stop-Process -Id $pid -Force
            Write-Host "✅ Proceso detenido exitosamente" -ForegroundColor Green
            Write-Host "`n🚀 Ahora puedes ejecutar: python api_server.py" -ForegroundColor Cyan
        } catch {
            Write-Host "❌ Error al detener proceso: $_" -ForegroundColor Red
            Write-Host "`n💡 Intenta manualmente con:" -ForegroundColor Yellow
            Write-Host "   taskkill /PID $pid /F" -ForegroundColor Yellow
        }
    } else {
        Write-Host "⚠️ No se pudo extraer el PID. Intenta manualmente:" -ForegroundColor Yellow
        Write-Host "   taskkill /PID <PID_NUMBER> /F" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ No hay proceso usando el puerto 7864" -ForegroundColor Green
    Write-Host "🚀 Puedes ejecutar: python api_server.py" -ForegroundColor Cyan
}

Write-Host "`nPresiona cualquier tecla para continuar..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
