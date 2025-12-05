# Guía de Integraciones Reales - Enterprise Autonomous Workflows

Este documento explica cómo configurar las integraciones reales para que los agentes ejecuten acciones de forma autónoma.

## 🚀 Configuración Rápida

### 1. Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables según los servicios que quieras usar:

```bash
# Jira
JIRA_API_URL=https://tu-empresa.atlassian.net
JIRA_EMAIL=tu-email@empresa.com
JIRA_API_TOKEN=tu-api-token

# ServiceNow
SERVICENOW_API_URL=https://tu-instancia.service-now.com
SERVICENOW_USER=tu-usuario
SERVICENOW_PASSWORD=tu-password

# Email SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/TU/WEBHOOK/URL

# Microsoft Teams
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/TU/WEBHOOK/URL

# Salesforce
SALESFORCE_INSTANCE_URL=https://tu-instancia.salesforce.com
SALESFORCE_ACCESS_TOKEN=tu-access-token

# AWS S3
AWS_ACCESS_KEY_ID=tu-access-key
AWS_SECRET_ACCESS_KEY=tu-secret-key
AWS_REGION=us-east-1

# ERP (Odoo)
ERP_TYPE=odoo
ODOO_URL=https://tu-odoo.com
ODOO_DB=tu-base-de-datos
ODOO_USER=tu-usuario
ODOO_PASSWORD=tu-password

# ERP (SAP)
ERP_TYPE=sap
SAP_ODATA_URL=https://tu-sap.com/sap/opu/odata
SAP_USER=tu-usuario
SAP_PASSWORD=tu-password

# ERP (Dynamics 365)
ERP_TYPE=dynamics
DYNAMICS_API_URL=https://tu-instancia.crm.dynamics.com
DYNAMICS_ACCESS_TOKEN=tu-access-token

# Base de Datos SQL
DATABASE_URL=postgresql://usuario:password@host:5432/database
```

## 📋 Cómo Obtener Credenciales

### Jira
1. Ve a https://id.atlassian.com/manage-profile/security/api-tokens
2. Crea un nuevo API token
3. Usa tu email y el token generado

### ServiceNow
1. Ve a tu instancia de ServiceNow
2. Crea un usuario de aplicación con permisos de API
3. Usa las credenciales del usuario

### Slack Webhook
1. Ve a https://api.slack.com/apps
2. Crea una nueva app
3. Activa "Incoming Webhooks"
4. Crea un webhook para tu canal
5. Copia la URL del webhook

### Microsoft Teams Webhook
1. En Teams, ve al canal donde quieres recibir notificaciones
2. Click en "..." → "Connectors"
3. Busca "Incoming Webhook" y configúralo
4. Copia la URL generada

### Salesforce
1. Ve a Setup → App Manager → New Connected App
2. Configura OAuth y obtén el Access Token
3. O usa OAuth2 flow para obtener tokens automáticamente

### AWS S3
1. Ve a AWS Console → IAM
2. Crea un usuario con permisos S3
3. Genera Access Key ID y Secret Access Key

## ✅ Verificación

Una vez configuradas las variables, el sistema automáticamente:
- ✅ Se conectará a los servicios cuando `auto_execute_actions=True`
- ✅ Ejecutará acciones reales (crear tickets, enviar emails, etc.)
- ✅ Registrará todas las acciones en el audit log
- ✅ Respetará las políticas del Enterprise Policy Engine

## 🧪 Modo Simulación

Para probar sin ejecutar acciones reales:
- Activa `simulation_mode=True` en la UI
- El sistema mostrará qué acciones ejecutaría sin hacerlo realmente

## 🔒 Seguridad

- **NUNCA** subas el archivo `.env` a Git
- Usa variables de entorno del sistema en producción
- Rota las credenciales regularmente
- Usa permisos mínimos necesarios en cada servicio

