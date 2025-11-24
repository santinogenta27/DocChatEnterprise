# 🔌 Guía Práctica: Cómo Conectar APIs de Ads

Esta guía te muestra **paso a paso** cómo obtener y configurar las credenciales para cada plataforma de ads.

## 📋 Resumen Rápido

Todas las APIs se conectan mediante **credenciales almacenadas en el archivo `.env`**. El sistema las lee automáticamente cuando ejecutas tareas.

---

## 1️⃣ Meta (Facebook/Instagram) Ads

### Paso 1: Crear App en Facebook Developers

1. Ve a **https://developers.facebook.com**
2. Haz clic en **"My Apps"** > **"Create App"**
3. Selecciona **"Business"** como tipo de app
4. Completa el nombre y email de contacto

### Paso 2: Agregar Marketing API

1. En tu app, ve a **"Add Product"**
2. Busca **"Marketing API"** y haz clic en **"Set Up"**
3. Acepta los términos y condiciones

### Paso 3: Obtener Access Token

**Opción A: Access Token de Prueba (Rápido)**
1. Ve a **"Tools"** > **"Graph API Explorer"**
2. Selecciona tu app en el dropdown
3. Haz clic en **"Generate Access Token"**
4. Selecciona estos permisos:
   - `ads_management`
   - `ads_read`
   - `business_management`
5. Copia el token generado

**Opción B: Access Token Permanente (Producción)**
1. Ve a **"Settings"** > **"Basic"**
2. Copia tu **App ID** y **App Secret**
3. Genera un token de larga duración usando:
   ```
   https://graph.facebook.com/oauth/access_token?
     client_id=TU_APP_ID&
     client_secret=TU_APP_SECRET&
     grant_type=client_credentials
   ```

### Paso 4: Obtener Ad Account ID

1. Ve a **https://business.facebook.com/ads/manager**
2. En la URL verás algo como: `act=123456789`
3. Ese número es tu **Ad Account ID**

### Paso 5: Agregar al `.env`

Crea o edita el archivo `.env` en la raíz del proyecto:

```env
META_ACCESS_TOKEN=tu_access_token_aqui
META_AD_ACCOUNT_ID=123456789
```

---

## 2️⃣ TikTok Ads

### Paso 1: Crear Cuenta en TikTok for Business

1. Ve a **https://ads.tiktok.com**
2. Crea una cuenta de anunciante
3. Completa la verificación de identidad

### Paso 2: Obtener Credenciales

1. Ve a **"Tools"** > **"API"**
2. Haz clic en **"Create App"**
3. Completa la información de la app
4. Una vez creada, obtén:
   - **Access Token**: Se genera automáticamente
   - **Advertiser ID**: Lo encuentras en **"Advertiser Account"** > **"Settings"**

### Paso 3: Agregar al `.env`

```env
TIKTOK_ACCESS_TOKEN=tu_access_token_aqui
TIKTOK_ADVERTISER_ID=tu_advertiser_id_aqui
```

---

## 3️⃣ Google Ads

### Paso 1: Crear Proyecto en Google Cloud

1. Ve a **https://console.cloud.google.com**
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita la **"Google Ads API"**:
   - Ve a **"APIs & Services"** > **"Library"**
   - Busca "Google Ads API"
   - Haz clic en **"Enable"**

### Paso 2: Obtener Developer Token

1. Ve a **https://ads.google.com**
2. Inicia sesión con tu cuenta de Google Ads
3. Ve a **"Tools & Settings"** (icono de llave inglesa) > **"API Center"**
4. Haz clic en **"Apply for API access"**
5. Completa el formulario (puede tardar varios días en aprobarse)
6. Una vez aprobado, copia tu **Developer Token**

### Paso 3: Configurar OAuth2

1. En Google Cloud Console, ve a **"APIs & Services"** > **"Credentials"**
2. Haz clic en **"Create Credentials"** > **"OAuth client ID"**
3. Selecciona **"Desktop app"** como tipo
4. Descarga el archivo JSON de credenciales
5. Guarda el archivo en tu proyecto (ej: `google_ads_credentials.json`)

### Paso 4: Obtener Refresh Token

Usa este script Python para obtener el Refresh Token:

```python
from google_auth_oauthlib.flow import InstalledAppFlow
from google.ads.googleads.client import GoogleAdsClient

# Configuración
SCOPES = ['https://www.googleapis.com/auth/adwords']
CLIENT_SECRETS_FILE = 'google_ads_credentials.json'

# Ejecutar flujo OAuth
flow = InstalledAppFlow.from_client_secrets_file(
    CLIENT_SECRETS_FILE, SCOPES)
credentials = flow.run_console()

# El refresh_token está en credentials.refresh_token
print(f"Refresh Token: {credentials.refresh_token}")
```

### Paso 5: Obtener Customer ID

1. En Google Ads, ve a **"Settings"** > **"Account Settings"**
2. Copia tu **Customer ID** (formato: `123-456-7890`)

### Paso 6: Agregar al `.env`

```env
GOOGLE_ADS_CUSTOMER_ID=123-456-7890
GOOGLE_ADS_DEVELOPER_TOKEN=tu_developer_token
GOOGLE_ADS_CLIENT_ID=tu_client_id_del_json
GOOGLE_ADS_CLIENT_SECRET=tu_client_secret_del_json
GOOGLE_ADS_REFRESH_TOKEN=tu_refresh_token
```

**Nota:** También necesitas instalar la librería:
```bash
pip install google-ads
```

---

## 4️⃣ LinkedIn Ads

### Paso 1: Crear App en LinkedIn

1. Ve a **https://www.linkedin.com/developers/apps**
2. Haz clic en **"Create app"**
3. Completa la información:
   - App name
   - Company LinkedIn Page
   - Privacy policy URL
   - App logo

### Paso 2: Solicitar Acceso a Marketing API

1. En tu app, ve a **"Products"**
2. Busca **"Marketing Developer Platform"**
3. Haz clic en **"Request access"**
4. Completa el formulario (puede tardar días en aprobarse)

### Paso 3: Obtener Access Token

1. Ve a **"Auth"** en tu app
2. Copia tu **Client ID** y **Client Secret**
3. Genera un Access Token usando OAuth2:

**Opción A: Usando OAuth Playground**
1. Ve a **https://www.linkedin.com/oauth/v2/authorization**
2. Usa estos parámetros:
   ```
   response_type=code
   client_id=TU_CLIENT_ID
   redirect_uri=https://www.linkedin.com/developers/tools/oauth/redirect
   scope=r_ads w_ads
   ```
3. Autoriza y copia el código
4. Intercambia el código por un token

**Opción B: Usando Python**
```python
import requests

CLIENT_ID = "tu_client_id"
CLIENT_SECRET = "tu_client_secret"
REDIRECT_URI = "https://www.linkedin.com/developers/tools/oauth/redirect"

# Paso 1: Obtener código de autorización
auth_url = f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=r_ads%20w_ads"
print(f"Visita: {auth_url}")
code = input("Pega el código aquí: ")

# Paso 2: Intercambiar código por token
token_url = "https://www.linkedin.com/oauth/v2/accessToken"
data = {
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": REDIRECT_URI,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET
}
response = requests.post(token_url, data=data)
access_token = response.json()["access_token"]
print(f"Access Token: {access_token}")
```

### Paso 4: Obtener Account ID

1. Ve a **https://www.linkedin.com/campaignmanager**
2. En la URL o en la configuración, encontrarás tu **Account ID**

### Paso 5: Agregar al `.env`

```env
LINKEDIN_ACCESS_TOKEN=tu_access_token_aqui
LINKEDIN_ACCOUNT_ID=tu_account_id_aqui
```

---

## ✅ Verificar Conexión

Después de configurar las credenciales, puedes verificar que funcionan:

### Script de Verificación

Crea un archivo `verificar_apis.py`:

```python
import os
from dotenv import load_dotenv
import requests

load_dotenv()

print("🔍 Verificando conexiones de APIs...\n")

# Meta
if os.getenv("META_ACCESS_TOKEN"):
    try:
        url = f"https://graph.facebook.com/v18.0/me?access_token={os.getenv('META_ACCESS_TOKEN')}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print("✅ Meta API: Conectado")
        else:
            print("❌ Meta API: Error -", response.text)
    except Exception as e:
        print("❌ Meta API: Error -", str(e))
else:
    print("⚠️ Meta API: No configurado")

# TikTok
if os.getenv("TIKTOK_ACCESS_TOKEN"):
    try:
        url = "https://business-api.tiktok.com/open_api/v1.3/advertiser/info/"
        headers = {"Access-Token": os.getenv("TIKTOK_ACCESS_TOKEN")}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            print("✅ TikTok API: Conectado")
        else:
            print("❌ TikTok API: Error -", response.text)
    except Exception as e:
        print("❌ TikTok API: Error -", str(e))
else:
    print("⚠️ TikTok API: No configurado")

# LinkedIn
if os.getenv("LINKEDIN_ACCESS_TOKEN"):
    try:
        url = "https://api.linkedin.com/v2/me"
        headers = {"Authorization": f"Bearer {os.getenv('LINKEDIN_ACCESS_TOKEN')}"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            print("✅ LinkedIn API: Conectado")
        else:
            print("❌ LinkedIn API: Error -", response.text)
    except Exception as e:
        print("❌ LinkedIn API: Error -", str(e))
else:
    print("⚠️ LinkedIn API: No configurado")

# Google Ads (requiere librería especial)
if os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"):
    print("⚠️ Google Ads API: Requiere verificación manual (usa google-ads library)")
else:
    print("⚠️ Google Ads API: No configurado")

print("\n✅ Verificación completada")
```

Ejecuta:
```bash
python verificar_apis.py
```

---

## 📝 Ejemplo de `.env` Completo

```env
# Meta (Facebook/Instagram) Ads
META_ACCESS_TOKEN=EAABwzLix...
META_AD_ACCOUNT_ID=123456789

# TikTok Ads
TIKTOK_ACCESS_TOKEN=abc123def456...
TIKTOK_ADVERTISER_ID=1234567890123456789

# Google Ads
GOOGLE_ADS_CUSTOMER_ID=123-456-7890
GOOGLE_ADS_DEVELOPER_TOKEN=tu_developer_token
GOOGLE_ADS_CLIENT_ID=123456789-abc.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=GOCSPX-abc123def456
GOOGLE_ADS_REFRESH_TOKEN=1//abc123def456...

# LinkedIn Ads
LINKEDIN_ACCESS_TOKEN=AQUabc123def456...
LINKEDIN_ACCOUNT_ID=123456789
```

---

## 🚨 Problemas Comunes

### "Invalid access token"
- **Solución:** El token expiró. Genera uno nuevo.

### "Insufficient permissions"
- **Solución:** Asegúrate de tener los permisos correctos en la app.

### "Rate limit exceeded"
- **Solución:** Espera unos minutos o reduce la frecuencia de requests.

### "Account not found"
- **Solución:** Verifica que el Account ID sea correcto.

---

## 🔒 Seguridad

⚠️ **IMPORTANTE:**
- **NUNCA** subas el archivo `.env` a GitHub
- Agrega `.env` a `.gitignore`
- Usa tokens de prueba para desarrollo
- Rota los tokens periódicamente

---

## 📚 Recursos Oficiales

- **Meta Marketing API:** https://developers.facebook.com/docs/marketing-apis
- **TikTok Ads API:** https://ads.tiktok.com/help/article?aid=9577
- **Google Ads API:** https://developers.google.com/google-ads/api/docs/start
- **LinkedIn Marketing API:** https://docs.microsoft.com/en-us/linkedin/marketing/

---

**¡Listo!** Una vez configuradas las credenciales, el Agentic AI podrá crear y gestionar campañas automáticamente. 🚀

