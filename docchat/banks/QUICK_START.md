# 🚀 Quick Start - Modo BANKS

## ⚡ Inicio Rápido (5 minutos)

### 1. Instalar Dependencias

```bash
# Dependencias básicas
pip install langgraph langchain-anthropic langchain-openai
pip install unstructured[all-docs] rapidfuzz
pip install fastapi uvicorn

# Dependencias opcionales (para integraciones)
pip install simple-salesforce atlassian-python-api
pip install boto3  # Para AWS Rekognition
```

### 2. Configurar Variables de Entorno

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-...
# O
OPENAI_API_KEY=sk-...

# Opcionales
WORLDCHECK_API_KEY=...
SALESFORCE_USERNAME=...
SALESFORCE_PASSWORD=...
SALESFORCE_SECURITY_TOKEN=...
JIRA_URL=...
JIRA_USERNAME=...
JIRA_API_TOKEN=...
SLACK_WEBHOOK_URL=...
```

### 3. Ejecutar la Aplicación

```bash
python app.py
```

### 4. Usar el Modo BANKS

1. Abre la pestaña **"🏦 BANKS - Compliance KYC/AML"**
2. Haz clic en **"🎬 Crear Demo con Datos de Ejemplo"**
3. Copia la ruta generada
4. Pega la ruta en **"📂 Ruta de Documentos"**
5. Selecciona jurisdicción (ej: "US")
6. Haz clic en **"🚀 Ejecutar Compliance Check"**
7. ¡Listo! Verás los resultados con risk scores y reportes

## 📡 Usar la API REST

### Iniciar Servidor API

```python
from docchat.banks import BanksAPI
from docchat import load_config

config = load_config()
api = BanksAPI(config)
api.run(host="0.0.0.0", port=8000)
```

### Ejemplo de Uso

```bash
# Health check
curl http://localhost:8000/health

# Compliance check
curl -X POST http://localhost:8000/api/v1/compliance/check \
  -H "Content-Type: application/json" \
  -d '{
    "input_path": "/path/to/documents",
    "jurisdiction": "US",
    "steering_commands": ["Ignora PEP level 1 para España"]
  }'
```

## 🎯 Casos de Uso Rápidos

### Caso 1: Onboarding Nuevo Cliente
```python
from docchat.banks import BanksMode
from docchat import load_config

config = load_config()
banks = BanksMode(config)

result = banks.process_compliance_check(
    input_path="/path/to/client_docs",
    jurisdiction="US",
    action_config={
        "update_salesforce": True,
        "salesforce_opportunity_id": "006XX000004ABCD",
        "create_jira_ticket": True,
        "jira_threshold": 70
    }
)
```

### Caso 2: Batch Processing
```python
clients = [
    {"client_id": "CLIENT_001", "input_path": "/path/to/client1"},
    {"client_id": "CLIENT_002", "input_path": "/path/to/client2"}
]

result = banks.process_batch_compliance(
    clients=clients,
    jurisdiction="US"
)
```

### Caso 3: Configurar Reglas
```python
from docchat.banks import BanksConfigManager
from docchat import load_config

config = load_config()
config_manager = BanksConfigManager(config)

# Actualizar pesos de risk scoring
config_manager.update_risk_weights({
    "country_risk": 0.4,
    "pep_risk": 0.25,
    "adverse_media_risk": 0.2,
    "transaction_risk": 0.1,
    "ubo_risk": 0.05
})

# Añadir a whitelist
config_manager.add_to_whitelist("Banco Central de España", "Institución gubernamental")
```

## 📊 Ver Dashboard

1. Ve a la pestaña **"📊 Dashboard Ejecutivo"**
2. Selecciona período (ej: 30 días)
3. Haz clic en **"🔄 Actualizar Dashboard"**
4. Verás métricas, ROI, y tendencias

## ⚙️ Configurar Reglas

1. Ve a la pestaña **"⚙️ Configuración de Reglas"**
2. Ajusta pesos de risk scoring
3. Configura thresholds
4. Añade países de alto riesgo
5. Gestiona whitelist/blacklist

## 🔗 Integraciones

### Salesforce
```python
action_config = {
    "update_salesforce": True,
    "salesforce_opportunity_id": "006XX000004ABCD"
}
```

### Jira
```python
action_config = {
    "create_jira_ticket": True,
    "jira_threshold": 70,
    "jira_project_key": "AML"
}
```

### Slack
```python
action_config = {
    "send_notifications": True,
    "notify_slack": True
}
```

## 🆘 Troubleshooting

### Error: "No module named 'docling'"
**Solución:** No es crítico. El modo BANKS funciona sin docling.

### Error: "World-Check API falló"
**Solución:** Usa fallbacks gratuitos (OFAC, EU, UN). World-Check es opcional.

### Error: "No se procesaron documentos"
**Solución:** Verifica la ruta y permisos de lectura.

## 📚 Documentación Completa

- **README.md** - Guía general
- **TECHNICAL_DOCS.md** - Documentación técnica
- **SELLING_GUIDE.md** - Guía de venta
- **ROI_CALCULATOR.md** - Cálculo de ROI

## ✅ Checklist de Verificación

- [ ] Dependencias instaladas
- [ ] Variables de entorno configuradas
- [ ] Aplicación ejecutándose
- [ ] Demo creada y probada
- [ ] Dashboard funcionando
- [ ] Configuración de reglas probada

## 🎯 Siguiente Paso

**¡Empieza a vender!**

1. Prepara demo con datos reales anonimizados
2. Crea pitch deck
3. Contacta 50 directores de compliance
4. Ofrece PoC gratis de 3 meses
5. Cierra tu primer contrato

**¡Éxito! 🚀**


