# API de Atención al Cliente Automática 24/7

Documentación completa para conectar servicios externos y recibir respuestas automáticas.

## 🚀 Endpoints Disponibles

### 1. Procesar Consulta de Cliente

**POST** `/api/v1/customer-service/inquiry`

Procesa una consulta de cliente y genera respuesta automática.

**Request:**
```json
{
  "channel": "email",
  "customer_email": "cliente@ejemplo.com",
  "message": "Hola, tengo una pregunta sobre mi pedido",
  "customer_phone": "+1234567890",
  "subject": "Consulta sobre pedido",
  "use_knowledge_base": true
}
```

**Response:**
```json
{
  "success": true,
  "inquiry_id": "INQ-1234567890-0",
  "response_text": "Hola! Gracias por contactarnos...",
  "channel": "email",
  "sent": true,
  "ticket_created": false,
  "ticket_id": null,
  "tools_used": ["email"],
  "confidence": 0.85,
  "escalated": false,
  "timestamp": "2025-01-23T10:30:00"
}
```

### 2. Webhook para Mensajes en Tiempo Real

**POST** `/api/v1/customer-service/webhook/{channel}`

Recibe mensajes de clientes desde servicios externos y responde automáticamente.

**Canales soportados:** `gmail`, `whatsapp`, `slack`, `email`, `chat`

#### Ejemplo: Gmail

**Request:**
```json
{
  "from": "cliente@ejemplo.com",
  "subject": "Consulta sobre producto",
  "body": "Hola, necesito información sobre...",
  "message_id": "gmail_message_123"
}
```

#### Ejemplo: WhatsApp Business

**Request:**
```json
{
  "from": "+1234567890",
  "message": "Hola, tengo una pregunta",
  "message_id": "whatsapp_123",
  "email": "cliente@ejemplo.com"
}
```

#### Ejemplo: Slack

**Request:**
```json
{
  "user": "U123456",
  "user_email": "usuario@empresa.com",
  "text": "Necesito ayuda con...",
  "channel": "support",
  "message_id": "slack_123"
}
```

**Headers requeridos (opcional pero recomendado):**
```
X-Webhook-Token: Bearer tu_token_secreto
```

Configura `WEBHOOK_TOKEN` en tu `.env` para seguridad.

### 3. Conectar Canal Externo

**POST** `/api/v1/customer-service/connect-channel`

Registra un canal externo para recibir mensajes automáticamente.

**Request:**
```json
{
  "channel_type": "gmail",
  "credentials": {
    "client_id": "tu_client_id",
    "client_secret": "tu_client_secret",
    "refresh_token": "tu_refresh_token"
  },
  "webhook_url": "https://tu-servidor.com/api/v1/customer-service/webhook/gmail",
  "auto_respond": true
}
```

### 4. Cargar Base de Conocimiento

**POST** `/api/v1/customer-service/load-knowledge`

Carga documentos que el AI usará para responder consultas.

**Request:** Multipart form data con archivos PDF, DOCX, TXT, MD

**Response:**
```json
{
  "success": true,
  "files_loaded": 5,
  "knowledge_base_chunks": 1234,
  "timestamp": "2025-01-23T10:30:00"
}
```

### 5. Estadísticas

**GET** `/api/v1/customer-service/stats`

Obtiene métricas del servicio de atención al cliente.

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_inquiries": 150,
    "resolved_autonomously": 120,
    "escalated": 30,
    "tickets_created": 45,
    "resolution_rate": "80.0%",
    "escalation_rate": "20.0%",
    "knowledge_base_documents": 1234
  },
  "timestamp": "2025-01-23T10:30:00"
}
```

## 🔌 Cómo Conectar Servicios Externos

### Gmail (Google Workspace)

1. **Crear proyecto en Google Cloud Console:**
   - Ve a https://console.cloud.google.com
   - Crea un nuevo proyecto
   - Habilita Gmail API

2. **Obtener credenciales:**
   - Crea OAuth 2.0 credentials
   - Obtén `client_id`, `client_secret`, y `refresh_token`

3. **Configurar webhook en Gmail:**
   - Usa Google Cloud Pub/Sub para recibir notificaciones
   - O configura un script que monitoree la bandeja de entrada

4. **Enviar mensajes al webhook:**
   ```python
   import requests
   
   webhook_url = "https://tu-servidor.com/api/v1/customer-service/webhook/gmail"
   token = "tu_webhook_token"
   
   payload = {
       "from": "cliente@ejemplo.com",
       "subject": "Consulta",
       "body": "Mensaje del cliente",
       "message_id": "gmail_123"
   }
   
   headers = {
       "X-Webhook-Token": f"Bearer {token}",
       "Content-Type": "application/json"
   }
   
   response = requests.post(webhook_url, json=payload, headers=headers)
   ```

### WhatsApp Business API

1. **Usar Twilio (Recomendado para empezar):**
   - Crea cuenta en https://www.twilio.com
   - Obtén `TWILIO_ACCOUNT_SID` y `TWILIO_AUTH_TOKEN`
   - Configura WhatsApp Sandbox

2. **Configurar webhook en Twilio:**
   - En la configuración de WhatsApp, apunta el webhook a:
     `https://tu-servidor.com/api/v1/customer-service/webhook/whatsapp`

3. **Twilio enviará automáticamente los mensajes al webhook**

### WhatsApp Business API (Directa)

1. **Obtener credenciales de Meta:**
   - Ve a https://developers.facebook.com
   - Crea una app de WhatsApp Business
   - Obtén `WHATSAPP_API_KEY` y configura `WHATSAPP_API_URL`

2. **Configurar webhook:**
   - En Meta, configura el webhook para recibir mensajes
   - El webhook debe apuntar a tu servidor

### Slack

1. **Crear Slack App:**
   - Ve a https://api.slack.com/apps
   - Crea una nueva app
   - Habilita Event Subscriptions

2. **Configurar webhook:**
   - En Event Subscriptions, configura la URL:
     `https://tu-servidor.com/api/v1/customer-service/webhook/slack`

3. **Slack enviará eventos automáticamente**

## 🔒 Seguridad

### Autenticación de Webhooks

Configura un token secreto en tu `.env`:
```
WEBHOOK_TOKEN=tu_token_secreto_muy_seguro
```

Luego, incluye este token en los headers de tus webhooks:
```
X-Webhook-Token: Bearer tu_token_secreto_muy_seguro
```

### Rate Limiting

Considera implementar rate limiting para prevenir abusos:
- Máximo 100 requests por minuto por IP
- Máximo 1000 requests por hora por canal

## 📊 Flujo de Trabajo Completo

1. **Cargar Base de Conocimiento:**
   ```bash
   curl -X POST "https://tu-servidor.com/api/v1/customer-service/load-knowledge" \
     -H "Authorization: Bearer tu_api_key" \
     -F "files=@manual.pdf" \
     -F "files=@faq.pdf"
   ```

2. **Conectar Canal (ej: Gmail):**
   ```bash
   curl -X POST "https://tu-servidor.com/api/v1/customer-service/connect-channel" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer tu_api_key" \
     -d '{
       "channel_type": "gmail",
       "credentials": {...},
       "auto_respond": true
     }'
   ```

3. **Los mensajes llegan automáticamente al webhook:**
   - Gmail/WhatsApp/Slack envía mensaje → Webhook → AI procesa → Respuesta automática

4. **Monitorear estadísticas:**
   ```bash
   curl "https://tu-servidor.com/api/v1/customer-service/stats" \
     -H "Authorization: Bearer tu_api_key"
   ```

## 🧪 Testing

### Probar con cURL

```bash
# Procesar consulta manual
curl -X POST "http://localhost:8000/api/v1/customer-service/inquiry" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "email",
    "customer_email": "test@ejemplo.com",
    "message": "Hola, tengo una pregunta",
    "use_knowledge_base": true
  }'

# Simular webhook de Gmail
curl -X POST "http://localhost:8000/api/v1/customer-service/webhook/gmail" \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Token: Bearer tu_token" \
  -d '{
    "from": "cliente@ejemplo.com",
    "subject": "Test",
    "body": "Mensaje de prueba",
    "message_id": "test_123"
  }'
```

## 💡 Ejemplos de Integración

### Python - Monitorear Gmail y enviar al webhook

```python
import imaplib
import email
import requests
import time

def check_gmail_and_forward():
    # Conectar a Gmail
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login("tu_email@gmail.com", "tu_app_password")
    mail.select("inbox")
    
    # Buscar nuevos mensajes
    status, messages = mail.search(None, "UNSEEN")
    
    for msg_num in messages[0].split():
        # Leer mensaje
        status, msg_data = mail.fetch(msg_num, "(RFC822)")
        email_body = msg_data[0][1]
        email_message = email.message_from_bytes(email_body)
        
        # Extraer información
        from_email = email_message["From"]
        subject = email_message["Subject"]
        body = email_message.get_payload()
        
        # Enviar al webhook
        webhook_url = "https://tu-servidor.com/api/v1/customer-service/webhook/gmail"
        payload = {
            "from": from_email,
            "subject": subject,
            "body": body,
            "message_id": msg_num.decode()
        }
        
        requests.post(webhook_url, json=payload, headers={
            "X-Webhook-Token": "Bearer tu_token"
        })
    
    mail.close()
    mail.logout()

# Ejecutar cada 30 segundos
while True:
    check_gmail_and_forward()
    time.sleep(30)
```

### Node.js - Webhook para WhatsApp

```javascript
const express = require('express');
const axios = require('axios');
const app = express();

app.use(express.json());

app.post('/whatsapp-webhook', async (req, res) => {
  const { from, message } = req.body;
  
  // Reenviar al Customer Service API
  try {
    const response = await axios.post(
      'https://tu-servidor.com/api/v1/customer-service/webhook/whatsapp',
      {
        from: from,
        message: message,
        message_id: req.body.id
      },
      {
        headers: {
          'X-Webhook-Token': 'Bearer tu_token',
          'Content-Type': 'application/json'
        }
      }
    );
    
    res.json({ success: true, response: response.data });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(3000, () => {
  console.log('Webhook server running on port 3000');
});
```

## 🎯 Mejores Prácticas

1. **Carga la base de conocimiento primero** antes de conectar canales
2. **Configura webhook tokens** para seguridad
3. **Monitorea las estadísticas** regularmente
4. **Revisa las escalaciones** para mejorar el AI
5. **Actualiza la base de conocimiento** periódicamente

## 📞 Soporte

Para más información, consulta la documentación completa en el repositorio.

