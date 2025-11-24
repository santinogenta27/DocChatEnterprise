# Guía Completa: Agentes Autónomos para Ads/Sales/Marketing

Esta guía explica cómo configurar y usar el modo **Agentes Autónomos** para automatizar completamente la creación y gestión de ads, sales y marketing en múltiples plataformas.

## 🎯 ¿Qué Puede Hacer el Agentic AI?

El Agentic AI puede automatizar:

### 📢 **Publicidad (Ads)**
- ✅ Crear campañas en Meta (Facebook/Instagram)
- ✅ Crear campañas en TikTok
- ✅ Crear campañas en Google Ads
- ✅ Crear campañas en LinkedIn Ads
- ✅ Optimizar campañas en tiempo real
- ✅ Generar creativos automáticamente
- ✅ Segmentar audiencias
- ✅ Ajustar presupuestos y pujas

### 💼 **CRM y Ventas (Sales)**
- ✅ Gestionar leads y contactos
- ✅ Crear oportunidades de venta
- ✅ Automatizar seguimiento
- ✅ Integrar con Salesforce, Pipedrive, Zoho CRM
- ✅ Gestionar pipeline de ventas

### 📧 **Email Marketing**
- ✅ Crear campañas de email
- ✅ Automatizar flujos de trabajo
- ✅ Segmentar audiencias
- ✅ Analizar performance
- ✅ Integrar con Mailchimp, HubSpot, ActiveCampaign

### 📊 **Analytics**
- ✅ Analizar tráfico web
- ✅ Analizar comportamiento de usuarios
- ✅ Optimizar campañas basadas en datos
- ✅ Generar insights automáticos
- ✅ Integrar con Google Analytics, Hotjar

## 🔧 Configuración de APIs

### 1. Meta (Facebook/Instagram) Ads

1. **Crear App en Facebook Developers:**
   - Ve a https://developers.facebook.com
   - Crea una nueva app
   - Agrega "Marketing API" como producto

2. **Obtener credenciales:**
   - Ve a "Settings" > "Basic"
   - Copia `App ID` y `App Secret`
   - Genera un Access Token con permisos `ads_management`

3. **Obtener Ad Account ID:**
   - Ve a https://business.facebook.com/ads/manager
   - En la URL verás: `act=123456789` (ese número es tu Ad Account ID)

4. **Agregar al `.env`:**
```env
META_ACCESS_TOKEN=tu_access_token_aqui
META_AD_ACCOUNT_ID=tu_ad_account_id_aqui
```

### 2. TikTok Ads

1. **Crear cuenta en TikTok for Business:**
   - Ve a https://ads.tiktok.com
   - Crea una cuenta de anunciante

2. **Obtener credenciales:**
   - Ve a "Tools" > "API"
   - Crea una app y obtén `Access Token`
   - Copia tu `Advertiser ID`

3. **Agregar al `.env`:**
```env
TIKTOK_ACCESS_TOKEN=tu_access_token_aqui
TIKTOK_ADVERTISER_ID=tu_advertiser_id_aqui
```

### 3. Google Ads

1. **Crear proyecto en Google Cloud:**
   - Ve a https://console.cloud.google.com
   - Crea un nuevo proyecto
   - Habilita "Google Ads API"

2. **Obtener Developer Token:**
   - Ve a https://ads.google.com
   - Ve a "Tools & Settings" > "API Center"
   - Solicita un Developer Token (puede tardar días)

3. **Configurar OAuth2:**
   - En Google Cloud Console, crea credenciales OAuth2
   - Obtén `Client ID`, `Client Secret`, y `Refresh Token`

4. **Obtener Customer ID:**
   - En Google Ads, ve a "Settings" > "Account Settings"
   - Copia tu "Customer ID" (formato: 123-456-7890)

5. **Agregar al `.env`:**
```env
GOOGLE_ADS_CUSTOMER_ID=123-456-7890
GOOGLE_ADS_DEVELOPER_TOKEN=tu_developer_token
GOOGLE_ADS_CLIENT_ID=tu_client_id
GOOGLE_ADS_CLIENT_SECRET=tu_client_secret
GOOGLE_ADS_REFRESH_TOKEN=tu_refresh_token
```

**Nota:** Google Ads requiere la librería `google-ads`:
```bash
pip install google-ads
```

### 4. LinkedIn Ads

1. **Crear app en LinkedIn:**
   - Ve a https://www.linkedin.com/developers/apps
   - Crea una nueva app
   - Solicita acceso a "Marketing Developer Platform"

2. **Obtener credenciales:**
   - Genera un Access Token con permisos `r_ads`, `w_ads`
   - Obtén tu `Account ID` desde LinkedIn Campaign Manager

3. **Agregar al `.env`:**
```env
LINKEDIN_ACCESS_TOKEN=tu_access_token_aqui
LINKEDIN_ACCOUNT_ID=tu_account_id_aqui
```

### 5. Salesforce CRM

1. **Crear Connected App:**
   - Ve a Setup > App Manager > New Connected App
   - Habilita OAuth Settings
   - Obtén `Consumer Key` y `Consumer Secret`

2. **Obtener Access Token:**
   - Usa OAuth2 flow para obtener Access Token
   - Obtén tu `Instance URL` (ej: https://yourinstance.salesforce.com)

3. **Agregar al `.env`:**
```env
SALESFORCE_INSTANCE_URL=https://yourinstance.salesforce.com
SALESFORCE_ACCESS_TOKEN=tu_access_token_aqui
```

### 6. Pipedrive CRM

1. **Obtener API Token:**
   - Ve a Settings > Personal > API
   - Genera un API Token
   - Copia tu Company Domain (ej: `mycompany`)

2. **Agregar al `.env`:**
```env
PIPEDRIVE_API_TOKEN=tu_api_token_aqui
PIPEDRIVE_COMPANY_DOMAIN=mycompany
```

### 7. Zoho CRM

1. **Crear app en Zoho:**
   - Ve a https://api-console.zoho.com
   - Crea una nueva app
   - Obtén `Client ID`, `Client Secret`, y genera `Refresh Token`

2. **Obtener Org ID:**
   - En Zoho CRM, ve a Settings > Organization
   - Copia tu Organization ID

3. **Agregar al `.env`:**
```env
ZOHO_API_TOKEN=tu_access_token_aqui
ZOHO_ORG_ID=tu_org_id_aqui
```

### 8. Mailchimp

1. **Obtener API Key:**
   - Ve a Account > Extras > API keys
   - Genera una nueva API key
   - Identifica tu server prefix (ej: `us1`, `us2`)

2. **Agregar al `.env`:**
```env
MAILCHIMP_API_KEY=tu_api_key_aqui
MAILCHIMP_SERVER=us1
```

### 9. HubSpot

1. **Obtener API Key:**
   - Ve a Settings > Integrations > Private Apps
   - Crea una nueva Private App
   - Obtén el API Key

2. **Agregar al `.env`:**
```env
HUBSPOT_API_KEY=tu_api_key_aqui
```

### 10. ActiveCampaign

1. **Obtener credenciales:**
   - Ve a Settings > Developer
   - Obtén `API URL` y `API Key`

2. **Agregar al `.env`:**
```env
ACTIVECAMPAIGN_API_KEY=tu_api_key_aqui
ACTIVECAMPAIGN_API_URL=https://youraccount.api-us1.com
```

### 11. Google Analytics

1. **Crear proyecto en Google Cloud:**
   - Ve a https://console.cloud.google.com
   - Crea un proyecto
   - Habilita "Google Analytics Reporting API"

2. **Obtener Property ID:**
   - En Google Analytics, ve a Admin > Property Settings
   - Copia tu Property ID

3. **Configurar OAuth2:**
   - Crea credenciales OAuth2 en Google Cloud
   - Descarga el JSON de credenciales

4. **Agregar al `.env`:**
```env
GOOGLE_ANALYTICS_PROPERTY_ID=123456789
GOOGLE_ANALYTICS_CREDENTIALS=ruta/al/credenciales.json
```

### 12. Hotjar

1. **Obtener credenciales:**
   - Ve a Settings > Sites & Organizations
   - Copia tu Site ID
   - Genera un API Key

2. **Agregar al `.env`:**
```env
HOTJAR_SITE_ID=tu_site_id_aqui
HOTJAR_API_KEY=tu_api_key_aqui
```

## 🚀 Uso del Modo Agentes Autónomos

### Paso 1: Cargar Datos

1. Ve al tab **"🤖 Agentes Autónomos"**
2. Sube documentos con información de tu empresa/productos
3. Haz clic en **"Procesar con IDP"**

### Paso 2: Ejecutar Tareas Autónomas

El Agentic AI puede ejecutar tareas como:

**Crear Campaña de Ads:**
```
"Crea una campaña en Meta para promocionar nuestro nuevo producto. 
Presupuesto: $500, objetivo: conversiones, audiencia: 25-45 años, 
interesados en tecnología"
```

**Gestionar Leads:**
```
"Agrega este nuevo lead al CRM: Juan Pérez, juan@ejemplo.com, 
empresa: TechCorp, teléfono: +1234567890"
```

**Crear Campaña de Email:**
```
"Crea una campaña de email para nuestra lista de suscriptores 
anunciando el lanzamiento del nuevo producto"
```

**Analizar Performance:**
```
"Analiza el tráfico web de los últimos 30 días y genera 
recomendaciones para optimizar nuestras campañas"
```

## 📝 Ejemplos de Tareas

### Ejemplo 1: Campaña Completa de Marketing

```
"Usando los datos de nuestros productos, crea una campaña completa:
1. Crea una campaña en Meta Ads con presupuesto de $1000
2. Crea una campaña en TikTok con presupuesto de $500
3. Crea una campaña de email marketing para nuestra lista
4. Analiza el performance después de 7 días y optimiza"
```

### Ejemplo 2: Automatización de Ventas

```
"Automatiza el proceso de ventas:
1. Crea un lead en el CRM para cada nuevo contacto del sitio web
2. Envía un email de bienvenida automático
3. Programa seguimiento después de 3 días
4. Crea una oportunidad si el lead muestra interés"
```

### Ejemplo 3: Optimización Basada en Datos

```
"Analiza nuestros datos de analytics y optimiza las campañas:
1. Identifica las mejores audiencias
2. Ajusta los presupuestos de las campañas según performance
3. Pausa las campañas con bajo ROI
4. Genera nuevos creativos para las campañas exitosas"
```

## 🔍 Herramientas Disponibles

El Agentic AI tiene acceso a estas herramientas:

- **`advertising`**: Crear y gestionar campañas de ads
- **`crm`**: Gestionar leads, contactos y oportunidades
- **`email_marketing`**: Crear campañas de email
- **`analytics`**: Analizar datos y generar insights
- **`email`**: Enviar emails personalizados
- **`report`**: Generar reportes
- **`scheduler`**: Programar tareas

## ⚠️ Notas Importantes

1. **Límites de APIs:** Cada plataforma tiene límites de rate. El sistema maneja esto automáticamente.

2. **Costos:** Las campañas creadas gastarán presupuesto real. Asegúrate de revisar antes de activar.

3. **Privacidad:** Todas las credenciales se almacenan en `.env` y nunca se exponen.

4. **Testing:** Usa cuentas de prueba primero antes de usar en producción.

## 🆘 Troubleshooting

### Error: "API credentials not found"
- Verifica que las credenciales estén en `.env`
- Reinicia la aplicación después de agregar credenciales

### Error: "Rate limit exceeded"
- El sistema esperará automáticamente
- Reduce la frecuencia de requests

### Error: "Campaign creation failed"
- Verifica que las credenciales sean válidas
- Revisa los logs para más detalles

## 📚 Recursos Adicionales

- **Meta Marketing API:** https://developers.facebook.com/docs/marketing-apis
- **TikTok Ads API:** https://ads.tiktok.com/help/article?aid=9577
- **Google Ads API:** https://developers.google.com/google-ads/api/docs/start
- **LinkedIn Marketing API:** https://docs.microsoft.com/en-us/linkedin/marketing/

---

**¡Listo!** Ahora puedes automatizar completamente tus ads, sales y marketing con Agentic AI. 🚀

