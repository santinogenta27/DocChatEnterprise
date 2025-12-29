# Script para guardar cambios en GitHub
# Ejecutar en PowerShell: .\GUARDAR_EN_GITHUB.ps1

Write-Host "🚀 Guardando cambios en GitHub..." -ForegroundColor Green
Write-Host ""

# Buscar Git en ubicaciones comunes
$gitPath = $null
$possiblePaths = @(
    "C:\Program Files\Git\cmd\git.exe",
    "C:\Program Files (x86)\Git\cmd\git.exe",
    "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $gitPath = $path
        break
    }
}

# Si no se encuentra Git, intentar usar 'git' directamente
if (-not $gitPath) {
    $gitPath = "git"
}

# Función para ejecutar git
function Invoke-Git {
    param([string[]]$Arguments)
    try {
        & $gitPath $Arguments
    } catch {
        Write-Host "❌ Error ejecutando Git. Por favor, instala Git o agrégalo al PATH." -ForegroundColor Red
        Write-Host "Descarga Git desde: https://git-scm.com/download/win" -ForegroundColor Yellow
        exit 1
    }
}

# Verificar que estamos en un repositorio Git
if (-not (Test-Path ".git")) {
    Write-Host "❌ Este directorio no es un repositorio Git." -ForegroundColor Red
    exit 1
}

# Mostrar estado actual
Write-Host "📋 Estado actual del repositorio:" -ForegroundColor Cyan
Invoke-Git @("status")

Write-Host ""
Write-Host "📦 Agregando todos los archivos..." -ForegroundColor Cyan
Invoke-Git @("add", ".")

Write-Host ""
Write-Host "💾 Creando commit..." -ForegroundColor Cyan
$commitMessage = @"
feat: Implementación completa de LangGraph Agent para Assistance AI

- ✅ Arquitectura LangGraph completa con 13 nodos
- ✅ Decision Policy explícita (respond, ask_clarification, escalate, reject)
- ✅ Intent Routing con 8 intenciones mapeadas
- ✅ RAG Engine optimizado por intención
- ✅ ReAct Agent completo (Reasoning + Acting)
- ✅ Memory Management con resumen automático
- ✅ Response Validator para evitar alucinaciones
- ✅ Escalation System con contexto para humanos
- ✅ Tools Registry con 5 herramientas integradas
- ✅ Integración completa con AssistanceAIAgent
- ✅ LangGraph SIEMPRE activado por defecto

Componentes agregados:
- docchat/assistance_ai/graph/agent_graph.py (grafo principal)
- docchat/assistance_ai/graph/state.py (estado tipado)
- docchat/assistance_ai/graph/intent_classifier.py
- docchat/assistance_ai/graph/decision_policy.py
- docchat/assistance_ai/graph/rag_retriever.py
- docchat/assistance_ai/graph/react_agent.py
- docchat/assistance_ai/graph/memory_manager.py
- docchat/assistance_ai/graph/response_validator.py
- docchat/assistance_ai/graph/tools_registry.py
- docchat/assistance_ai/graph/langgraph_integration.py
- docchat/assistance_ai/graph/langgraph_agent_wrapper.py
- docchat/assistance_ai/graph/__init__.py
- docchat/assistance_ai/agents/langgraph_integration.py (actualizado)

Arquitectura Enterprise-grade lista para producción.
"@

Invoke-Git @("commit", "-m", $commitMessage)

Write-Host ""
Write-Host "🔍 Verificando rama actual..." -ForegroundColor Cyan
$currentBranch = Invoke-Git @("branch", "--show-current") | Out-String | ForEach-Object { $_.Trim() }

Write-Host "📍 Rama actual: $currentBranch" -ForegroundColor Yellow

# Verificar si hay cambios remotos
Write-Host ""
Write-Host "🔄 Verificando cambios remotos..." -ForegroundColor Cyan
Invoke-Git @("fetch", "origin")

# Push a GitHub
Write-Host ""
Write-Host "⬆️ Subiendo cambios a GitHub (rama: $currentBranch)..." -ForegroundColor Cyan
Invoke-Git @("push", "origin", $currentBranch)

Write-Host ""
Write-Host "✅ ¡Cambios guardados exitosamente en GitHub!" -ForegroundColor Green
Write-Host "🔗 Repositorio: https://github.com/santinogenta27/DocChatEnterprise.git" -ForegroundColor Cyan
Write-Host "📌 Rama: $currentBranch" -ForegroundColor Cyan

