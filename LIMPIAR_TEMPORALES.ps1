# Script para limpiar archivos temporales de Gradio y Windows

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LIMPIANDO ARCHIVOS TEMPORALES" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$gradioTemp = "$env:LOCALAPPDATA\Temp\gradio"
$generalTemp = "$env:LOCALAPPDATA\Temp"
$windowsTemp = "$env:TEMP"

$totalCleaned = 0
$totalSize = 0

# Limpiar Gradio
if (Test-Path $gradioTemp) {
    Write-Host "Limpiando archivos temporales de Gradio..." -ForegroundColor Yellow
    $files = Get-ChildItem -Path $gradioTemp -Recurse -ErrorAction SilentlyContinue
    if ($files) {
        $count = $files.Count
        $size = ($files | Measure-Object -Property Length -Sum).Sum / 1MB
        Remove-Item -Path "$gradioTemp\*" -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "OK - Limpiados $count archivos ($([math]::Round($size, 2)) MB) de Gradio" -ForegroundColor Green
        $totalCleaned += $count
        $totalSize += $size
    }
}

# Limpiar archivos temporales antiguos de Windows (más de 7 días)
Write-Host "Limpiando archivos temporales antiguos de Windows..." -ForegroundColor Yellow
$oldFiles = Get-ChildItem -Path $windowsTemp -File -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) }
if ($oldFiles) {
    $count = $oldFiles.Count
    $size = ($oldFiles | Measure-Object -Property Length -Sum).Sum / 1MB
    $oldFiles | Remove-Item -Force -ErrorAction SilentlyContinue
    Write-Host "OK - Limpiados $count archivos antiguos ($([math]::Round($size, 2)) MB)" -ForegroundColor Green
    $totalCleaned += $count
    $totalSize += $size
}

# Limpiar cache de Python
$pythonCache = "$env:LOCALAPPDATA\pip\Cache"
if (Test-Path $pythonCache) {
    Write-Host "Limpiando cache de pip..." -ForegroundColor Yellow
    $files = Get-ChildItem -Path $pythonCache -Recurse -ErrorAction SilentlyContinue
    if ($files) {
        $count = $files.Count
        $size = ($files | Measure-Object -Property Length -Sum).Sum / 1MB
        Remove-Item -Path "$pythonCache\*" -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "OK - Limpiados $count archivos ($([math]::Round($size, 2)) MB) de pip cache" -ForegroundColor Green
        $totalCleaned += $count
        $totalSize += $size
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RESUMEN" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total archivos limpiados: $totalCleaned" -ForegroundColor Green
Write-Host "Espacio liberado: $([math]::Round($totalSize, 2)) MB" -ForegroundColor Green

Write-Host ""
Write-Host "Espacio en disco disponible:" -ForegroundColor Cyan
$disk = Get-PSDrive C
$freeGB = [math]::Round($disk.Free / 1GB, 2)
$usedGB = [math]::Round(($disk.Used / 1GB), 2)
$totalGB = [math]::Round(($disk.Free + $disk.Used) / 1GB, 2)

Write-Host "  Libre: $freeGB GB" -ForegroundColor $(if ($freeGB -lt 1) { "Red" } elseif ($freeGB -lt 5) { "Yellow" } else { "Green" })
Write-Host "  Usado: $usedGB GB" -ForegroundColor Yellow
Write-Host "  Total: $totalGB GB" -ForegroundColor White

if ($freeGB -lt 1) {
    Write-Host ""
    Write-Host "ADVERTENCIA: Espacio en disco muy bajo!" -ForegroundColor Red
    Write-Host "Necesitas al menos 2-3 GB libres para procesar muchos PDFs." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Opciones:" -ForegroundColor Cyan
    Write-Host "  1. Libera espacio en disco manualmente" -ForegroundColor White
    Write-Host "  2. Procesa menos archivos a la vez (20-30 en lugar de 80)" -ForegroundColor White
    Write-Host "  3. Usa la herramienta de limpieza de disco de Windows" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LIMPIEZA COMPLETADA" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

