# 🔐 Guía: Configurar OAuth para Integraciones

## 📋 Resumen

Para conectar apps con DocChat Enterprise, necesitas configurar credenciales OAuth de cada proveedor.

---

## 🔵 Google (Gmail / Google Drive)

### Paso 1: Ir a Google Cloud Console
https://console.cloud.google.com/apis/credentials

### Paso 2: Crear o Seleccionar Proyecto
- Click en "Crear proyecto" o selecciona uno existente

### Paso 3: Habilitar APIs
- **Gmail API** (para Gmail)
- **Google Drive API** (para Drive)

Busca en "APIs y servicios" → "Biblioteca" y habilita las necesarias.

### Paso 4: Crear Credenciales OAuth 2.0
1. Ve a "APIs y servicios" → "Credenciales"
2. Click en "Crear credenciales" → "ID de cliente de OAuth 2.0"
3. Tipo: **Aplicación web**
4. Nombre: "DocChat Enterprise"
5. **URI de redirección autorizada:**
   ```
   http://localhost:7860/oauth/callback?provider=google
   ```
6. Click en "Crear"

### Paso 5: Copiar Credenciales
- **ID de cliente** (Client ID)
- **Secreto de cliente** (Client Secret)

### Paso 6: Agregar a `.env`
```env
GOOGLE_CLIENT_ID=tu-client-id-aqui.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu-client-secret-aqui
```

### Paso 7: Reiniciar Aplicación
```bash
py -3.12 app.py
```

---

## 🔷 Microsoft (Teams / Outlook / OneDrive)

### Paso 1: Ir a Azure Portal
https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade

### Paso 2: Registrar Nueva Aplicación
1. Click en "Nuevo registro"
2. Nombre: "DocChat Enterprise"
3. Tipos de cuenta: "Cuentas en cualquier directorio organizativo y cuentas Microsoft personales"
4. URI de redirección:
   - Tipo: Web
   - URI: `http://localhost:7860/oauth/callback?provider=microsoft`
5. Click en "Registrar"

### Paso 3: Configurar Permisos
1. Ve a "Permisos de API"
2. Click en "Agregar un permiso"
3. Selecciona "Microsoft Graph"
4. Permisos delegados:
   - `Mail.Read` (para Outlook)
   - `Files.Read.All` (para OneDrive)
   - `ChannelMessage.Read.All` (para Teams)
5. Click en "Agregar permisos"

### Paso 4: Crear Secreto de Cliente
1. Ve a "Certificados y secretos"
2. Click en "Nuevo secreto de cliente"
3. Descripción: "DocChat Enterprise"
4. Expira: 24 meses (o el que prefieras)
5. Click en "Agregar"
6. **Copia el valor del secreto** (solo se muestra una vez)

### Paso 5: Agregar a `.env`
```env
MICROSOFT_CLIENT_ID=tu-client-id-aqui
MICROSOFT_CLIENT_SECRET=tu-client-secret-aqui
```

---

## 💬 Slack

### Paso 1: Ir a Slack API
https://api.slack.com/apps

### Paso 2: Crear Nueva App
1. Click en "Create New App"
2. "From scratch"
3. Nombre: "DocChat Enterprise"
4. Workspace: Selecciona tu workspace
5. Click en "Create App"

### Paso 3: Configurar OAuth
1. Ve a "OAuth & Permissions"
2. **Redirect URLs:**
   ```
   http://localhost:7860/oauth/callback?provider=slack
   ```
3. **Scopes (Bot Token Scopes):**
   - `channels:history`
   - `groups:history`
   - `im:history`
   - `mpim:history`
   - `search:read`

### Paso 4: Instalar App
1. Click en "Install to Workspace"
2. Autoriza los permisos

### Paso 5: Copiar Credenciales
- **Client ID** (en "App Credentials")
- **Client Secret** (en "App Credentials")

### Paso 6: Agregar a `.env`
```env
SLACK_CLIENT_ID=tu-client-id-aqui
SLACK_CLIENT_SECRET=tu-client-secret-aqui
```

---

## 📊 Salesforce

### Paso 1: Ir a Salesforce Setup
1. Ve a tu instancia de Salesforce
2. Setup → App Manager

### Paso 2: Crear Connected App
1. Click en "New Connected App"
2. Información básica:
   - Connected App Name: "DocChat Enterprise"
   - API Name: "DocChat_Enterprise"
   - Contact Email: Tu email
3. Configurar OAuth:
   - Enable OAuth Settings: ✅
   - Callback URL: `http://localhost:7860/oauth/callback?provider=salesforce`
   - Selected OAuth Scopes:
     - `Full access (full)`
     - `Perform requests on your behalf at any time (refresh_token, offline_access)`
4. Click en "Save"

### Paso 3: Copiar Credenciales
- **Consumer Key** (Client ID)
- **Consumer Secret** (Client Secret)

### Paso 4: Agregar a `.env`
```env
SALESFORCE_CLIENT_ID=tu-consumer-key-aqui
SALESFORCE_CLIENT_SECRET=tu-consumer-secret-aqui
SALESFORCE_INSTANCE_URL=https://tu-instancia.salesforce.com
```

---

## ✅ Jira

### Paso 1: Ir a Atlassian Developer
https://developer.atlassian.com/console/myapps/

### Paso 2: Crear App
1. Click en "Create"
2. Tipo: "OAuth 2.0 (3LO)"
3. Nombre: "DocChat Enterprise"
4. Callback URL: `http://localhost:7860/oauth/callback?provider=jira`

### Paso 3: Configurar Permisos
- `read:jira-work`
- `read:jira-user`

### Paso 4: Copiar Credenciales
- **Client ID**
- **Client Secret**

### Paso 5: Agregar a `.env`
```env
JIRA_CLIENT_ID=tu-client-id-aqui
JIRA_CLIENT_SECRET=tu-client-secret-aqui
JIRA_URL=https://tu-dominio.atlassian.net
```

---

## 💻 GitHub

### Paso 1: Ir a GitHub Settings
https://github.com/settings/developers

### Paso 2: Crear OAuth App
1. Click en "New OAuth App"
2. Application name: "DocChat Enterprise"
3. Homepage URL: `http://localhost:7860`
4. Authorization callback URL: `http://localhost:7860/oauth/callback?provider=github`

### Paso 3: Copiar Credenciales
- **Client ID**
- **Client Secret**

### Paso 4: Agregar a `.env`
```env
GITHUB_CLIENT_ID=tu-client-id-aqui
GITHUB_CLIENT_SECRET=tu-client-secret-aqui
```

---

## 📝 Notion

### Paso 1: Ir a Notion Integrations
https://www.notion.so/my-integrations

### Paso 2: Crear Integración
1. Click en "New integration"
2. Nombre: "DocChat Enterprise"
3. Tipo: "Internal"
4. Copia el **Internal Integration Token**

### Paso 3: Agregar a `.env`
```env
NOTION_CLIENT_ID=tu-integration-id-aqui
NOTION_CLIENT_SECRET=tu-integration-token-aqui
```

---

## 📚 Confluence

Similar a Jira (ambos son Atlassian). Usa las mismas credenciales de Atlassian.

---

## 🎫 Zendesk

### Paso 1: Ir a Zendesk Admin
1. Admin → Apps → APIs → OAuth Clients
2. Click en "Add OAuth Client"

### Paso 2: Configurar
- Name: "DocChat Enterprise"
- Redirect URI: `http://localhost:7860/oauth/callback?provider=zendesk`

### Paso 3: Copiar Credenciales
- **Client ID**
- **Client Secret**

### Paso 4: Agregar a `.env`
```env
ZENDESK_CLIENT_ID=tu-client-id-aqui
ZENDESK_CLIENT_SECRET=tu-client-secret-aqui
ZENDESK_URL=https://tu-dominio.zendesk.com
```

---

## 🔧 ServiceNow

### Paso 1: Ir a ServiceNow
1. System OAuth → Application Registry
2. Click en "New"

### Paso 2: Configurar
- Name: "DocChat Enterprise"
- Redirect URL: `http://localhost:7860/oauth/callback?provider=servicenow`

### Paso 3: Copiar Credenciales
- **Client ID**
- **Client Secret**

### Paso 4: Agregar a `.env`
```env
SERVICENOW_CLIENT_ID=tu-client-id-aqui
SERVICENOW_CLIENT_SECRET=tu-client-secret-aqui
SERVICENOW_INSTANCE_URL=https://tu-instancia.service-now.com
```

---

## 📝 Ejemplo de Archivo `.env` Completo

```env
# Google
GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abc123

# Microsoft
MICROSOFT_CLIENT_ID=abc123-def456
MICROSOFT_CLIENT_SECRET=xyz789

# Slack
SLACK_CLIENT_ID=123456789.123456789
SLACK_CLIENT_SECRET=abc123def456

# Salesforce
SALESFORCE_CLIENT_ID=3MVG9abc123
SALESFORCE_CLIENT_SECRET=abc123def456
SALESFORCE_INSTANCE_URL=https://your-instance.salesforce.com

# Jira
JIRA_CLIENT_ID=abc123def456
JIRA_CLIENT_SECRET=xyz789
JIRA_URL=https://your-domain.atlassian.net

# GitHub
GITHUB_CLIENT_ID=abc123def456
GITHUB_CLIENT_SECRET=xyz789

# Notion
NOTION_CLIENT_ID=abc123def456
NOTION_CLIENT_SECRET=secret_xyz789

# Zendesk
ZENDESK_CLIENT_ID=abc123def456
ZENDESK_CLIENT_SECRET=xyz789
ZENDESK_URL=https://your-domain.zendesk.com

# ServiceNow
SERVICENOW_CLIENT_ID=abc123def456
SERVICENOW_CLIENT_SECRET=xyz789
SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com
```

---

## ⚠️ Importante

1. **Nunca compartas tus credenciales** - Son secretas
2. **No subas `.env` a Git** - Agrégalo a `.gitignore`
3. **Usa diferentes credenciales** para desarrollo y producción
4. **Reinicia la aplicación** después de cambiar `.env`

---

## 🆘 Problemas Comunes

**Error: "Missing required parameter: client_id"**
- Verifica que agregaste las credenciales en `.env`
- Verifica que reiniciaste la aplicación

**Error: "redirect_uri_mismatch"**
- Verifica que la URL de redirección en `.env` coincide con la configurada en el proveedor
- Debe ser exactamente: `http://localhost:7860/oauth/callback?provider=google`

**Error: "invalid_client"**
- Verifica que el Client ID y Secret son correctos
- Verifica que no hay espacios extra en `.env`


