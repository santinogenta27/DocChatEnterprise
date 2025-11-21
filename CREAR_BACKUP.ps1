# Script de Backup para DocChat Enterprise
# Crea una copia completa del proyecto antes de hacer cambios

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupName = "DocChat_Backup_$timestamp"
$backupPath = "C:\Users\Random\Downloads\$backupName"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CREANDO BACKUP DEL PROYECTO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Crear directorio de backup
New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
Write-Host "✅ Directorio de backup creado: $backupPath" -ForegroundColor Green

# Copiar todos los archivos (excluyendo cache y archivos temporales)
$excludePatterns = @(
    "__pycache__",
    "*.pyc",
    ".docchat_cache",
    ".docchat_vectordb",
    ".docchat_memory",
    ".docchat_audit",
    "cache",
    "uploaded_files",
    ".env"
)

$sourcePath = Get-Location
$items = Get-ChildItem -Path $sourcePath -Recurse | Where-Object {
    $item = $_
    $relativePath = $item.FullName.Replace($sourcePath, "").TrimStart("\")
    $shouldExclude = $false
    foreach ($pattern in $excludePatterns) {
        if ($relativePath -like "*$pattern*") {
            $shouldExclude = $true
            break
        }
    }
    return -not $shouldExclude
}

$copied = 0
foreach ($item in $items) {
    $relativePath = $item.FullName.Replace($sourcePath, "").TrimStart("\")
    $destPath = Join-Path $backupPath $relativePath
    $destDir = Split-Path $destPath -Parent
    
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
    
    if (-not $item.PSIsContainer) {
        Copy-Item -Path $item.FullName -Destination $destPath -Force
        $copied++
    }
}

Write-Host "✅ $copied archivos copiados" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  BACKUP COMPLETADO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Ubicación: $backupPath" -ForegroundColor Yellow
Write-Host ""
Write-Host "Para restaurar:" -ForegroundColor Cyan
Write-Host "  1. Copia el contenido de $backupPath" -ForegroundColor White
Write-Host "  2. Pégalo en tu carpeta del proyecto" -ForegroundColor White
Write-Host ""

