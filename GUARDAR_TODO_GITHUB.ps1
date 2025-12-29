# Script para Guardar TODO en GitHub
# Busca Git automáticamente y ejecuta commit + push

Write-Host "=== GUARDANDO TODO EN GITHUB ===" -ForegroundColor Green
Write-Host ""

# Buscar Git en múltiples ubicaciones
$gitExe = $null

# Buscar en PATH primero
try {
    $gitCmd = Get-Command git -ErrorAction SilentlyContinue
    if ($gitCmd) {
        $gitExe = $gitCmd.Source
        Write-Host "✅ Git encontrado en PATH: $gitExe" -ForegroundColor Green
    }
} catch {}

# Si no está en PATH, buscar en ubicaciones comunes
if (-not $gitExe) {
    $searchPaths = @(
        "$env:USERPROFILE\Downloads\Git\cmd\git.exe",
        "$env:USERPROFILE\Downloads\PortableGit\cmd\git.exe",
        "$env:USERPROFILE\Downloads\git.exe",
        "C:\Program Files\Git\cmd\git.exe",
        "C:\Program Files (x86)\Git\cmd\git.exe",
        "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe"
    )
    
    foreach ($path in $searchPaths) {
        if (Test-Path $path) {
            $gitExe = $path
            Write-Host "✅ Git encontrado: $gitExe" -ForegroundColor Green
            break
        }
    }
}

# Si aún no se encuentra, buscar en Descargas recursivamente
if (-not $gitExe) {
    Write-Host "🔍 Buscando Git en Descargas..." -ForegroundColor Yellow
    $foundGit = Get-ChildItem -Path "$env:USERPROFILE\Downloads" -Recurse -Filter "git.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($foundGit) {
        $gitExe = $foundGit.FullName
        Write-Host "✅ Git encontrado: $gitExe" -ForegroundColor Green
    }
}

# Si no se encuentra, error
if (-not $gitExe) {
    Write-Host "❌ ERROR: Git no encontrado." -ForegroundColor Red
    Write-Host ""
    Write-Host "Por favor, asegúrate de que Git esté instalado o descargado." -ForegroundColor Yellow
    Write-Host "Si Git está en Descargas, dime la ruta exacta." -ForegroundColor Yellow
    exit 1
}

# Función para ejecutar git
function Invoke-Git {
    param([string[]]$Args)
    if ($gitExe) {
        & $gitExe $Args
        return $LASTEXITCODE -eq 0
    }
    return $false
}

# Verificar que estamos en un repo Git
if (-not (Test-Path ".git")) {
    Write-Host "❌ ERROR: No es un repositorio Git" -ForegroundColor Red
    exit 1
}

# Ver estado actual
Write-Host ""
Write-Host "📋 Estado del repositorio:" -ForegroundColor Cyan
Invoke-Git @("status", "--short") | Select-Object -First 30

# Agregar TODOS los archivos
Write-Host ""
Write-Host "📦 Agregando TODOS los archivos..." -ForegroundColor Cyan
Invoke-Git @("add", ".") | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Archivos agregados" -ForegroundColor Green
} else {
    Write-Host "⚠️ Advertencia al agregar archivos" -ForegroundColor Yellow
}

# Crear commit
Write-Host ""
Write-Host "💾 Creando commit..." -ForegroundColor Cyan

$commitMessage = @"
feat: Implementacion completa LangGraph Agent para Assistance AI

Arquitectura Enterprise-grade con:
- LangGraph completo con 13 nodos
- Decision Policy explicita
- Intent Routing con 8 intenciones
- RAG Engine optimizado
- ReAct Agent completo
- Memory Management
- Response Validator
- Escalation System
- Tools Registry
- Integracion completa
- LangGraph SIEMPRE activado

Archivos nuevos: 15 archivos Python/MD
Archivos modificados: 5 archivos
Total: 3500+ lineas de codigo nuevo
"@

# Guardar mensaje en archivo temporal para evitar problemas de encoding
$tempMsgFile = [System.IO.Path]::GetTempFileName()
$commitMessage | Out-File -FilePath $tempMsgFile -Encoding UTF8

try {
    Invoke-Git @("commit", "-F", $tempMsgFile) | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Commit creado exitosamente" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Puede que no haya cambios nuevos o el commit falló" -ForegroundColor Yellow
        # Verificar si hay cambios
        $status = Invoke-Git @("status", "--porcelain")
        if ($status) {
            Write-Host "❌ Hay cambios pero commit falló. Revisa errores arriba." -ForegroundColor Red
            exit 1
        } else {
            Write-Host "ℹ️ No hay cambios nuevos (todo ya está commiteado)" -ForegroundColor Cyan
        }
    }
} finally {
    Remove-Item $tempMsgFile -ErrorAction SilentlyContinue
}

# Obtener rama actual
Write-Host ""
Write-Host "📍 Verificando rama..." -ForegroundColor Cyan
$branchOutput = Invoke-Git @("branch", "--show-current")
$branch = ($branchOutput | Out-String).Trim()
if (-not $branch -or $branch -eq "") {
    $branch = "main"
}
Write-Host "Rama actual: $branch" -ForegroundColor Yellow

# Verificar remotes
Write-Host ""
Write-Host "🔍 Verificando remotes..." -ForegroundColor Cyan
$remotes = Invoke-Git @("remote", "-v")
if (-not $remotes) {
    Write-Host "⚠️ No hay remotes. Agregando origin..." -ForegroundColor Yellow
    Invoke-Git @("remote", "add", "origin", "https://github.com/santinogenta27/DocChatEnterprise.git")
}

# Push a GitHub
Write-Host ""
Write-Host "⬆️ Subiendo a GitHub (rama: $branch)..." -ForegroundColor Cyan
if (Invoke-Git @("push", "origin", $branch)) {
    Write-Host ""
    Write-Host "✅ ¡ÉXITO! TODO guardado en GitHub" -ForegroundColor Green
    Write-Host "🔗 https://github.com/santinogenta27/DocChatEnterprise" -ForegroundColor Cyan
    Write-Host "📌 Rama: $branch" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "❌ Error al hacer push. Verifica:" -ForegroundColor Red
    Write-Host "   1. Credenciales de GitHub configuradas" -ForegroundColor Yellow
    Write-Host "   2. Permisos de escritura en el repositorio" -ForegroundColor Yellow
    Write-Host "   3. Conexión a internet" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "🎉 Proceso completado exitosamente" -ForegroundColor Green

