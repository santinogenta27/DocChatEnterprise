# 🌀 Configuración de ÉXTASIS Mode - Producción

Guía completa para configurar ÉXTASIS Mode para ejecutar acciones reales en sistemas empresariales.

## 🎯 Configuración desde la UI (RECOMENDADO)

**✨ TODO se puede configurar directamente desde la interfaz de Gradio.**

1. Ve al tab **"🌀 ÉXTASIS"** en la aplicación
2. Abre el accordion **"⚙️ Configurar Servicios Empresariales"**
3. Configura las credenciales de cada servicio que necesites
4. Haz clic en **"💾 Guardar Configuración de Servicios"**
5. Las credenciales se guardan automáticamente y están listas para usar

**No necesitas editar archivos `.env` manualmente.** La configuración se guarda en `data/extasis_config.json` y se aplica automáticamente a los workflows.

## 📋 Índice

1. [Configuración desde UI (Recomendado)](#configuración-desde-la-ui-recomendado)
2. [Variables de Entorno (Opcional)](#variables-de-entorno-opcional)
3. [Configuración por Servicio](#configuración-por-servicio)
4. [Modo Simulación](#modo-simulación)
5. [Ejemplos de Uso](#ejemplos-de-uso)

## 🔧 Variables de Entorno (Opcional)

Si prefieres usar variables de entorno en lugar de la UI, puedes crear un archivo `.env` en la raíz del proyecto:

### Configuración Global

```bash
# Modo Simulación (activar para pruebas sin ejecutar acciones reales)
EXTASIS_SIMULATION_MODE=false

# AI Engine (opcional, se puede cambiar en la UI)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## 🔌 Configuración por Servicio

### 1. Tickets - Jira

```bash
JIRA_API_URL=https://tu-empresa.atlassian.net
JIRA_EMAIL=tu-email@empresa.com
JIRA_API_TOKEN=tu-api-token
```

**Cómo obtener credenciales:**
1. Ve a https://id.atlassian.com/manage-profile/security/api-tokens
2. Crea un nuevo API token
3. Usa tu email y el token generado

### 2. Tickets - ServiceNow

```bash
SERVICENOW_API_URL=https://tu-instancia.service-now.com
SERVICENOW_USER=tu-usuario
SERVICENOW_PASSWORD=tu-password
```

**Cómo obtener credenciales:**
1. Ve a tu instancia de ServiceNow
2. Crea un usuario de aplicación con permisos de API
3. Usa las credenciales del usuario

### 3. Email - SMTP

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
```

**Para Gmail:**
1. Habilita verificación en 2 pasos
2. Genera una "App Password" en https://myaccount.google.com/apppasswords
3. Usa esa contraseña en `SMTP_PASSWORD`

### 4. Slack

**Opción A: Webhook (más simple)**

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/TU/WEBHOOK/URL
```

**Cómo obtener:**
1. Ve a https://api.slack.com/apps
2. Crea una nueva app o usa una existente
3. Ve a "Incoming Webhooks" y crea uno
4. Copia la URL del webhook

**Opción B: Bot Token (más funcionalidades)**

```bash
SLACK_BOT_TOKEN=xoxb-tu-bot-token
```

**Cómo obtener:**
1. Ve a https://api.slack.com/apps
2. Crea una nueva app
3. Ve a "OAuth & Permissions"
4. Instala la app a tu workspace
5. Copia el "Bot User OAuth Token"

### 5. AWS S3

```bash
AWS_ACCESS_KEY_ID=tu-access-key
AWS_SECRET_ACCESS_KEY=tu-secret-key
AWS_REGION=us-east-1
```

**Cómo obtener:**
1. Ve a AWS IAM Console
2. Crea un usuario con permisos de S3
3. Genera Access Keys
4. Usa las credenciales generadas

### 6. CRM - Salesforce

```bash
SALESFORCE_INSTANCE_URL=https://tu-instancia.salesforce.com
SALESFORCE_ACCESS_TOKEN=tu-access-token
```

**O usando Username/Password Flow:**

```bash
SALESFORCE_USERNAME=tu-usuario
SALESFORCE_PASSWORD=tu-password
SALESFORCE_SECURITY_TOKEN=tu-security-token
```

**Cómo obtener:**
1. Ve a Salesforce Setup
2. Busca "API" o "Connected Apps"
3. Crea una Connected App y obtén el token

### 7. ERP - SAP

```bash
SAP_ODATA_URL=https://tu-sap.com/sap/opu/odata
SAP_USER=tu-usuario
SAP_PASSWORD=tu-password
```

### 8. ERP - Oracle ERP Cloud

```bash
ORACLE_ERP_URL=https://tu-oracle-instance.oraclecloud.com
ORACLE_ERP_TOKEN=tu-oauth-token
```

### 9. ERP - Microsoft Dynamics 365

```bash
DYNAMICS_API_URL=https://tu-instancia.crm.dynamics.com
DYNAMICS_ACCESS_TOKEN=tu-access-token
```

### 10. SCM - SAP Ariba

```bash
SAP_ARIBA_URL=https://api.ariba.com
SAP_ARIBA_API_KEY=tu-api-key
```

### 11. SCM - Oracle SCM Cloud

```bash
ORACLE_SCM_URL=https://tu-oracle-instance.oraclecloud.com
ORACLE_SCM_TOKEN=tu-oauth-token
```

## 🧪 Modo Simulación

El modo simulación permite probar workflows sin ejecutar acciones reales en tus sistemas.

### Activar desde la UI (RECOMENDADO):

1. Ve al tab **"🌀 ÉXTASIS"** en la aplicación
2. Marca la casilla **"🧪 Simulation Mode"** 
3. El modo se activa/desactiva automáticamente y se guarda

### Activar en `.env` (Opcional):
```bash
EXTASIS_SIMULATION_MODE=true
```

### Comportamiento:

- ✅ Todos los workflows se ejecutan normalmente
- ✅ Los agentes analizan y toman decisiones
- ✅ Las herramientas devuelven respuestas simuladas
- ❌ **NO** se ejecutan acciones reales (no se crean tickets, no se envían emails, etc.)
- 📋 Se muestra qué acciones se ejecutarían

## 📚 Ejemplos de Uso

### Ejemplo 1: Auditoría de Contratos

1. Selecciona workflow: "1️⃣ Auditoría automática de contratos"
2. Sube documentos PDF de contratos
3. Opcional: Agrega contexto JSON:
   ```json
   {
     "regulation_type": "GDPR",
     "alert_priority": "high"
   }
   ```
4. Activa/desactiva modo simulación según necesites
5. Haz clic en "🚀 Ejecutar"

### Ejemplo 2: Revisión de Facturas

1. Selecciona workflow: "2️⃣ Revisión autónoma de facturas / AP Automation"
2. Sube facturas PDF
3. Contexto JSON:
   ```json
   {
     "max_auto_approval_amount": 1000,
     "approval_email": "finanzas@empresa.com"
   }
   ```
4. Ejecuta el workflow

### Ejemplo 3: Detección de Fraude

1. Selecciona workflow: "💰 Detección de fraude en facturas/pagos"
2. Sube facturas o documentos de pagos
3. El sistema detectará anomalías y bloqueará transacciones sospechosas
4. Se enviarán alertas automáticas

### Ejemplo 4: Tarea Personalizada

1. Selecciona workflow: "General / personalizado"
2. Escribe una tarea en lenguaje natural:
   ```
   Aprobar reembolso de $500 para el cliente ABC Corp en Salesforce y 
   crear orden de compra en SAP para 100 unidades del producto XYZ
   ```
3. Opcional: Agrega contexto JSON con sistemas y restricciones
4. Ejecuta

## 🔒 Seguridad

### Buenas Prácticas:

1. **Nunca commitees el archivo `.env`** - Ya está en `.gitignore`
2. **Usa variables de entorno del sistema** en producción
3. **Rota tus tokens regularmente**
4. **Usa permisos mínimos** en tus servicios (principio de menor privilegio)
5. **Prueba primero en modo simulación** antes de ejecutar en producción

### Permisos Recomendados por Servicio:

- **Jira**: Permisos de creación/actualización de tickets
- **ServiceNow**: Permisos de creación de incidentes
- **Salesforce**: Permisos específicos según acciones (reembolsos, leads, etc.)
- **S3**: Permisos de escritura en buckets específicos
- **Slack**: Permisos de envío de mensajes

## ⚠️ Solución de Problemas

### Error: "Credenciales no configuradas"

- Verifica que las variables de entorno estén correctamente configuradas
- Revisa que los nombres de las variables sean exactos (mayúsculas/minúsculas)
- Asegúrate de reiniciar la aplicación después de cambiar variables de entorno

### Error: "Connection error"

- Verifica la conectividad a internet
- Revisa que las URLs de los servicios sean correctas
- Verifica que los tokens/credenciales no hayan expirado

### Error: "Permission denied"

- Verifica que las credenciales tengan los permisos necesarios
- Revisa las políticas de acceso en los servicios (AWS IAM, Salesforce, etc.)

### Error: "CrewAI no está disponible"

- Instala CrewAI: `pip install crewai`
- Reinicia la aplicación

## 🚀 Próximos Pasos

1. Configura las variables de entorno necesarias
2. Prueba en modo simulación primero
3. Verifica que las conexiones funcionen correctamente
4. Ejecuta workflows reales con documentos de prueba
5. Monitorea los logs y resultados
6. Escala a producción cuando estés listo

## 📞 Soporte

Para problemas o preguntas, revisa:
- Los logs de la aplicación
- La documentación de cada servicio (Jira, ServiceNow, etc.)
- El código fuente en `docchat/extasis_tools.py` y `docchat/extasis_workflows.py`

