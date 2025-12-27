# 🔧 Configuración de Integraciones Opcionales

Este documento explica cómo configurar las integraciones **OPCIONALES** con Meta APIs, Website y WhatsApp.

**⚠️ IMPORTANTE:** Estas integraciones son **OPCIONALES** y se configuran **POR SEPARADO**. No afectan el funcionamiento principal del agente si no están configuradas.

---

## 📋 Tabla de Contenidos

1. [Meta API Integration (Facebook/Instagram/Meta Ads)](#meta-api-integration)
2. [Website Learner](#website-learner)
3. [WhatsApp Integration](#whatsapp-integration)

---

## 🔵 Meta API Integration

### Descripción
Permite que el agente aprenda de:
- Posts de Facebook
- Posts de Instagram
- Campañas de Meta Ads

Este conocimiento se incorpora automáticamente en el RAG del agente.

### Configuración

#### 1. Obtener Tokens de Acceso

**Facebook:**
1. Ve a [Facebook Developers](https://developers.facebook.com/)
2. Crea una App o usa una existente
3. Obtén un **Page Access Token** con permisos:
   - `pages_read_engagement`
   - `pages_read_user_content`
   - `pages_show_list`

**Instagram:**
1. En la misma App de Facebook, agrega el producto "Instagram Basic Display"
2. Obtén un **Instagram Access Token** con permisos:
   - `instagram_basic`
   - `instagram_content_publish`

**Meta Ads:**
1. En la misma App de Facebook, agrega el producto "Marketing API"
2. Obtén un **Ads Access Token** con permisos:
   - `ads_read`
   - `ads_management`

#### 2. Obtener IDs

**Facebook Page ID:**
- Ve a tu página de Facebook
- En "Acerca de" → "Información de la página", encontrarás el ID

**Instagram Business Account ID:**
- Ve a [Facebook Graph API Explorer](https://developers.facebook.com/tools/explorer/)
- Selecciona tu App y Page Access Token
- Ejecuta: `GET /me/accounts`
- Encuentra tu página y ejecuta: `GET /{page-id}?fields=instagram_business_account`
- El ID será `instagram_business_account.id`

**Meta Ads Account ID:**
- Ve a [Meta Ads Manager](https://business.facebook.com/adsmanager/)
- En la URL, encontrarás `act=XXXXX` donde `XXXXX` es tu Account ID

#### 3. Configurar Variables de Entorno

Agrega estas variables a tu archivo `.env`:

```env
# Meta API Integration (OPCIONAL)
FACEBOOK_ACCESS_TOKEN=tu_facebook_access_token
FACEBOOK_PAGE_ID=tu_facebook_page_id

INSTAGRAM_ACCESS_TOKEN=tu_instagram_access_token
INSTAGRAM_BUSINESS_ACCOUNT_ID=tu_instagram_business_account_id

META_ADS_ACCESS_TOKEN=tu_meta_ads_access_token
META_ADS_ACCOUNT_ID=tu_meta_ads_account_id
```

#### 4. Instalar Dependencias

```bash
pip install requests
```

### Uso

Una vez configurado, el agente automáticamente:
1. Obtiene posts recientes de Facebook/Instagram (máximo 30 de cada uno)
2. Obtiene campañas recientes de Meta Ads (máximo 30)
3. Extrae conocimiento de este contenido
4. Lo incorpora en el RAG del agente

**No necesitas hacer nada más.** El conocimiento se actualiza cada vez que el agente procesa un mensaje.

---

## 🌐 Website Learner

### Descripción
Permite que el agente aprenda del contenido de tu website, incluyendo:
- Página principal
- Páginas de productos
- FAQs
- Páginas "Acerca de"
- Otras páginas relevantes

### Configuración

#### 1. Configurar Variables de Entorno

Agrega estas variables a tu archivo `.env`:

```env
# Website Learner (OPCIONAL)
WEBSITE_URL=https://tu-website.com
WEBSITE_MAX_PAGES=20          # Número máximo de páginas a procesar (default: 20)
WEBSITE_MAX_DEPTH=2            # Profundidad máxima de crawling (default: 2)
```

#### 2. Instalar Dependencias

```bash
pip install requests beautifulsoup4
```

### Uso

Una vez configurado, el agente automáticamente:
1. Hace crawling de tu website (empezando desde `WEBSITE_URL`)
2. Procesa páginas importantes (home, productos, FAQs, etc.)
3. Extrae conocimiento del contenido
4. Lo incorpora en el RAG del agente

**Nota:** El crawling se ejecuta la primera vez que el agente procesa un mensaje. Puede tardar unos segundos.

---

## 📱 WhatsApp Integration

### Descripción
Permite que el agente funcione en WhatsApp Business API, recibiendo y enviando mensajes.

### Configuración

#### 1. Configurar WhatsApp Business API

1. Ve a [Meta for Developers](https://developers.facebook.com/)
2. Crea una App o usa una existente
3. Agrega el producto "WhatsApp"
4. Configura un número de teléfono de WhatsApp Business
5. Obtén:
   - **Phone Number ID**
   - **Access Token** (temporal o permanente)
   - **Verify Token** (para verificar el webhook)

#### 2. Configurar Variables de Entorno

Agrega estas variables a tu archivo `.env`:

```env
# WhatsApp Integration (OPCIONAL)
WHATSAPP_PHONE_NUMBER_ID=tu_phone_number_id
WHATSAPP_ACCESS_TOKEN=tu_whatsapp_access_token
WHATSAPP_VERIFY_TOKEN=tu_verify_token_personalizado
```

#### 3. Configurar Webhook

El webhook debe apuntar a tu servidor donde está corriendo el agente.

**URL del Webhook:**
```
https://tu-servidor.com/webhook/whatsapp
```

**Eventos a suscribir:**
- `messages`

**Verify Token:**
- Usa el mismo valor que configuraste en `WHATSAPP_VERIFY_TOKEN`

#### 4. Instalar Dependencias

```bash
pip install requests
```

### Uso

Una vez configurado, el agente puede:
1. Recibir mensajes de WhatsApp a través del webhook
2. Procesar los mensajes con el mismo agente de ventas
3. Enviar respuestas a WhatsApp

**Ejemplo de integración en tu código:**

```python
from docchat.sales_ai_agent.integrations.whatsapp_integration import WhatsAppIntegration

# En tu endpoint de webhook
@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    data = await request.json()
    
    # Verificar webhook (solo la primera vez)
    if request.query_params.get("hub.mode") == "subscribe":
        verify_token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        
        if verify_token == whatsapp_integration.verify_token:
            return Response(content=challenge)
        else:
            return Response(status_code=403)
    
    # Procesar mensaje
    whatsapp_message = whatsapp_integration.parse_webhook_message(data)
    
    if whatsapp_message:
        # Procesar con el agente
        result = sales_ai_agent_mode.process_message(
            payload={
                "session_id": whatsapp_message.from_number,
                "user_id": whatsapp_message.from_number,
                "message": whatsapp_message.message_text,
                "channel": "whatsapp"
            },
            channel="whatsapp"
        )
        
        # Enviar respuesta
        whatsapp_integration.send_message(
            to_number=whatsapp_message.from_number,
            message_text=result.get("text", "")
        )
    
    return Response(status_code=200)
```

---

## ✅ Verificar Configuración

Para verificar que las integraciones están configuradas correctamente, revisa los logs al iniciar el agente:

```
✅ Meta API Integration configurada
✅ Website Learner configurado para: https://tu-website.com
✅ WhatsApp Integration configurada
```

Si no están configuradas, verás:

```
⚠️ Meta API Integration NO configurada (opcional - no afecta funcionamiento principal)
⚠️ Website Learner NO configurado (opcional - no afecta funcionamiento principal)
⚠️ WhatsApp Integration NO configurada (opcional - no afecta funcionamiento principal)
```

**Esto es normal y no afecta el funcionamiento principal del agente.**

---

## 🔒 Seguridad

- **NUNCA** compartas tus tokens de acceso
- **NUNCA** subas tu archivo `.env` a repositorios públicos
- Usa tokens temporales para desarrollo y tokens permanentes para producción
- Rota tus tokens periódicamente

---

## 📚 Recursos Adicionales

- [Facebook Graph API Documentation](https://developers.facebook.com/docs/graph-api)
- [Instagram Basic Display API](https://developers.facebook.com/docs/instagram-basic-display-api)
- [Meta Marketing API](https://developers.facebook.com/docs/marketing-apis)
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)

---

## ❓ Preguntas Frecuentes

**P: ¿Necesito configurar todas las integraciones?**
R: No. Todas son opcionales. Configura solo las que necesites.

**P: ¿Qué pasa si no configuro ninguna integración?**
R: El agente funcionará normalmente. Solo no tendrá acceso al conocimiento de Meta/Website ni podrá usar WhatsApp.

**P: ¿Puedo configurar solo algunas integraciones?**
R: Sí. Puedes configurar solo las que necesites. Por ejemplo, solo Website Learner o solo WhatsApp.

**P: ¿Cómo actualizo el conocimiento de Meta/Website?**
R: El conocimiento se actualiza automáticamente cada vez que el agente procesa un mensaje. No necesitas hacer nada manualmente.

**P: ¿Cuánto tiempo tarda el crawling del website?**
R: Depende del tamaño de tu website y la configuración de `WEBSITE_MAX_PAGES` y `WEBSITE_MAX_DEPTH`. Generalmente tarda entre 5-30 segundos.

---

## 🆘 Soporte

Si tienes problemas con la configuración, verifica:
1. Que las variables de entorno estén correctamente configuradas
2. Que los tokens de acceso sean válidos y tengan los permisos necesarios
3. Que las dependencias estén instaladas (`requests`, `beautifulsoup4`)
4. Los logs del agente para ver mensajes de error específicos

