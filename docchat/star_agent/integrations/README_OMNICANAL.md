# IntegraciÃ³n Omnicanal - WhatsApp, Facebook, Instagram

## âœ… IntegraciÃ³n Completa Implementada

El sistema ahora tiene integraciÃ³n REAL con WhatsApp, Facebook Messenger e Instagram Direct Messages.

## ConfiguraciÃ³n en `.env`

AÃ±ade estas variables de entorno para activar cada canal:

### WhatsApp Business API

**OpciÃ³n 1: Twilio (Recomendado para empezar)**
```env
WHATSAPP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_WHATSAPP_NUMBER=+14155238886
```

**OpciÃ³n 2: Meta WhatsApp Business API**
```env
WHATSAPP_PROVIDER=meta
META_WHATSAPP_PHONE_NUMBER_ID=tu_phone_number_id
META_WHATSAPP_ACCESS_TOKEN=tu_access_token
META_WHATSAPP_VERIFY_TOKEN=tu_verify_token_customizado
```

### Facebook Messenger Platform

```env
FACEBOOK_PAGE_ACCESS_TOKEN=tu_page_access_token
FACEBOOK_VERIFY_TOKEN=tu_verify_token_customizado
```

### Instagram Direct Messages

```env
INSTAGRAM_ACCESS_TOKEN=tu_instagram_access_token
INSTAGRAM_USER_ID=tu_instagram_business_account_id
INSTAGRAM_VERIFY_TOKEN=tu_verify_token_customizado
```

## Endpoints de Webhook

### WhatsApp (Twilio)
- **URL:** `POST https://tu-servidor.com/webhook/whatsapp/twilio`
- **Configurar en:** [Twilio Console](https://console.twilio.com) â†’ WhatsApp Sandbox â†’ Webhook

### WhatsApp (Meta)
- **VerificaciÃ³n:** `GET https://tu-servidor.com/webhook/whatsapp/meta?hub.mode=subscribe&hub.verify_token=TU_TOKEN&hub.challenge=123456`
- **Mensajes:** `POST https://tu-servidor.com/webhook/whatsapp/meta`
- **Configurar en:** [Meta Developers](https://developers.facebook.com) â†’ WhatsApp Business API â†’ Webhooks

### Facebook Messenger
- **VerificaciÃ³n:** `GET https://tu-servidor.com/webhook/facebook?hub.mode=subscribe&hub.verify_token=TU_TOKEN&hub.challenge=123456`
- **Mensajes:** `POST https://tu-servidor.com/webhook/facebook`
- **Configurar en:** [Meta Developers](https://developers.facebook.com) â†’ Messenger Platform â†’ Webhooks

### Instagram Direct
- **VerificaciÃ³n:** `GET https://tu-servidor.com/webhook/instagram?hub.mode=subscribe&hub.verify_token=TU_TOKEN&hub.challenge=123456`
- **Mensajes:** `POST https://tu-servidor.com/webhook/instagram`
- **Configurar en:** [Meta Developers](https://developers.facebook.com) â†’ Instagram Messaging API â†’ Webhooks

## CÃ³mo Obtener Credenciales

### Twilio WhatsApp

1. Crea cuenta en [Twilio](https://www.twilio.com)
2. Ve a [Console](https://console.twilio.com) â†’ WhatsApp Sandbox
3. ObtÃ©n Account SID y Auth Token desde la consola
4. Usa el nÃºmero de WhatsApp Sandbox (ej: `whatsapp:+14155238886`)

### Meta WhatsApp Business API

1. Ve a [Meta Developers](https://developers.facebook.com)
2. Crea una app â†’ Selecciona "Business" â†’ WhatsApp
3. ObtÃ©n Phone Number ID desde la consola
4. Genera Access Token con permisos `whatsapp_business_messaging`
5. Configura Webhook con verify token personalizado

### Facebook Messenger

1. Ve a [Meta Developers](https://developers.facebook.com)
2. Crea una app â†’ Selecciona "Messenger"
3. ObtÃ©n Page Access Token desde la pÃ¡gina de Facebook
4. Configura Webhook con verify token personalizado

### Instagram Direct

1. Ve a [Meta Developers](https://developers.facebook.com)
2. Crea una app â†’ Selecciona "Instagram Messaging"
3. Conecta tu Instagram Business Account
4. ObtÃ©n Access Token y User ID
5. Configura Webhook con verify token personalizado

## Flujo de Funcionamiento

1. **Cliente envÃ­a mensaje** â†’ Plataforma (WhatsApp/Facebook/Instagram)
2. **Plataforma envÃ­a webhook** â†’ Tu servidor (`/webhook/{canal}`)
3. **OmnicanalBridge procesa webhook** â†’ Extrae mensaje y remitente
4. **StarAgentMode procesa mensaje** â†’ Genera respuesta con el agente
5. **OmnicanalBridge envÃ­a respuesta** â†’ Plataforma â†’ Cliente

## Funcionalidades Activas

âœ… **Tracking de Conversiones:** Todos los mensajes se registran para tracking
âœ… **Recomendaciones Inteligentes:** Funciona igual en todos los canales
âœ… **Cierre Proactivo:** Detecta seÃ±ales de compra y cierra ventas automÃ¡ticamente
âœ… **Memoria Conversacional:** Mantiene contexto entre sesiones
âœ… **RAG:** Consulta documentos subidos en el tab RAG

## Notas Importantes

- **HTTPS requerido:** Los webhooks de Meta requieren HTTPS. Usa ngrok o similar para desarrollo local.
- **Verify Token:** Ãšsalo para proteger tus webhooks. ConfigÃºralo en `.env` y en la plataforma.
- **Rate Limits:** Respeta los lÃ­mites de rate de cada plataforma (especialmente Meta).
- **Logs:** Revisa los logs del servidor para debugging: `python api_server.py`

## Testing

Para probar localmente, usa [ngrok](https://ngrok.com):
```bash
ngrok http 7864
```

Luego usa la URL de ngrok (ej: `https://abc123.ngrok.io`) para configurar los webhooks.


