# DocChat Enterprise - Script de inicio
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DocChat Enterprise - Iniciando..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configurar API Key
$env:OPENAI_API_KEY = "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"

# Configurar Confluent/Kafka (Opcional - para streaming en tiempo real mejorado)
# 
# OPCIÓN 1: Kafka Local (GRATIS - Recomendado para desarrollo)
# 1. Instala Docker Desktop: https://www.docker.com/products/docker-desktop
# 2. Ejecuta: docker-compose -f docker-compose-kafka.yml up -d
# 3. Descomenta la línea de abajo:
# $env:CONFLUENT_BOOTSTRAP_SERVERS = "localhost:9092"
#
# OPCIÓN 2: Confluent Cloud (Pago - Para producción)
# Descomenta y configura con tus credenciales:
# $env:CONFLUENT_BOOTSTRAP_SERVERS = "pkc-xxxxx.us-east-1.aws.confluent.cloud:9092"
# $env:CONFLUENT_SECURITY_PROTOCOL = "SASL_SSL"
# $env:CONFLUENT_SASL_MECHANISM = "PLAIN"
# $env:CONFLUENT_SASL_USERNAME = "tu-api-key"
# $env:CONFLUENT_SASL_PASSWORD = "tu-api-secret"
#
# Ver guías completas:
# - INSTALAR_KAFKA_LOCAL.md (para Kafka local)
# - CONFIGURAR_CONFLUENT.md (para Confluent Cloud)

Write-Host "✅ API Key configurada" -ForegroundColor Green
if ($env:CONFLUENT_BOOTSTRAP_SERVERS) {
    Write-Host "✅ Confluent configurado: $env:CONFLUENT_BOOTSTRAP_SERVERS" -ForegroundColor Green
} else {
    Write-Host "ℹ️  Confluent no configurado (usando Event Bus interno)" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "🚀 Iniciando aplicación..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Cuando veas 'Running on local URL', abre tu navegador en:" -ForegroundColor Cyan
Write-Host "   http://127.0.0.1:7860" -ForegroundColor White
Write-Host ""
Write-Host "Presiona Ctrl+C para detener la aplicación" -ForegroundColor Yellow
Write-Host ""

# Usar Python 3.12 para compatibilidad con Gradio y CrewAI
py -3.12 app.py



