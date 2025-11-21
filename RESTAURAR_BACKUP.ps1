# Script para restaurar un backup del proyecto

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RESTAURAR BACKUP DEL PROYECTO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Buscar backups disponibles
$backupsPath = "C:\Users\Random\Downloads"
$backups = Get-ChildItem -Path $backupsPath -Directory | Where-Object { $_.Name -like "DocChat_Backup_*" } | Sort-Object LastWriteTime -Descending

if ($backups.Count -eq 0) {
    Write-Host "❌ No se encontraron backups" -ForegroundColor Red
    exit 1
}

Write-Host "Backups disponibles:" -ForegroundColor Yellow
Write-Host ""
for ($i = 0; $i -lt $backups.Count; $i++) {
    $backup = $backups[$i]
    $date = $backup.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
    Write-Host "  [$i] $($backup.Name) - $date" -ForegroundColor White
}
Write-Host ""

$selection = Read-Host "Selecciona el número del backup a restaurar (0-$($backups.Count-1))"

try {
    $selectedIndex = [int]$selection
    if ($selectedIndex -lt 0 -or $selectedIndex -ge $backups.Count) {
        Write-Host "❌ Selección inválida" -ForegroundColor Red
        exit 1
    }
    
    $selectedBackup = $backups[$selectedIndex]
    Write-Host ""
    Write-Host "⚠️  ADVERTENCIA: Esto sobrescribirá los archivos actuales" -ForegroundColor Yellow
    $confirm = Read-Host "¿Estás seguro? (escribe 'SI' para confirmar)"
    
    if ($confirm -ne "SI") {
        Write-Host "❌ Restauración cancelada" -ForegroundColor Red
        exit 0
    }
    
    Write-Host ""
    Write-Host "Restaurando desde: $($selectedBackup.FullName)" -ForegroundColor Cyan
    
    # Copiar archivos del backup al proyecto actual
    $currentPath = Get-Location
    $items = Get-ChildItem -Path $selectedBackup.FullName -Recurse
    
    $copied = 0
    foreach ($item in $items) {
        $relativePath = $item.FullName.Replace($selectedBackup.FullName, "").TrimStart("\")
        $destPath = Join-Path $currentPath $relativePath
        $destDir = Split-Path $destPath -Parent
        
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        
        if (-not $item.PSIsContainer) {
            Copy-Item -Path $item.FullName -Destination $destPath -Force
            $copied++
        }
    }
    
    Write-Host "✅ $copied archivos restaurados" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  BACKUP RESTAURADO EXITOSAMENTE" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    exit 1
}

