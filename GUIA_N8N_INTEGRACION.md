# 🔗 GUÍA DE INTEGRACIÓN N8N PARA BUSINESS AI OMNICANAL

**Fecha:** 2025-12-18  
**Propósito:** Conectar WhatsApp/Instagram con tu Business AI Omnicanal vía n8n

---

## 🎯 **RESUMEN**

n8n actúa como el "puente" entre Meta (WhatsApp/Instagram) y tu Gradio. Recibe mensajes de Meta, los envía a tu API, y devuelve las respuestas.

---

## 📋 **PASO 1: INSTALAR N8N**

### **Opción A: Self-Hosted (Recomendado para producción)**

```bash
# Docker (más fácil)
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n

# O con docker-compose
```

**docker-compose.yml para n8n:**
```yaml
version: '3.8'
services:
  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    volumes:
      - ~/.n8n:/home/node/.n8n
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=tu_password_seguro
```

### **Opción B: n8n Cloud (Hosted)**

- Ve a https://n8n.io
- Crea cuenta gratuita
- Usa el workspace cloud (más fácil para empezar)

---

## 📋 **PASO 2: CONFIGURAR META (WHATSAPP/INSTAGRAM)**

### **A. Obtener Credenciales de Meta**

1. Ve a https://developers.facebook.com
2. Crea una app → Selecciona "Business"
3. Agrega producto "WhatsApp" o "Instagram Messaging"
4. Obtén:
   - **Access Token** (temporal o permanente)
   - **Phone Number ID** (para WhatsApp)
   - **App Secret** (opcional, para seguridad)

### **B. Configurar Webhook en Meta**

Meta necesita una URL pública donde enviar mensajes. Usa ngrok o tu VPS:

```bash
# Con ngrok (para desarrollo)
ngrok http 5678

# Obtendrás: https://abc123.ngrok.io
# Esta es tu URL pública para Meta
```

---

## 📋 **PASO 3: CREAR WORKFLOW EN N8N**

### **Workflow Completo:**

```
1. Webhook Trigger (Meta)
   ↓
2. HTTP Request (POST a tu API de Gradio)
   ↓
3. IF (frustración > 7) → Slack Alert
   ↓
4. IF (intención = comprar) → Consultar Inventario
   ↓
5. IF (venta completada) → Guardar en CRM
   ↓
6. Responder a Meta (WhatsApp/Instagram)
```

### **Configuración Detallada:**

#### **Nodo 1: Webhook (Trigger)**
- **Tipo:** Webhook
- **Método:** POST
- **Path:** `/meta-webhook`
- **URL generada:** `https://tu-n8n.com/webhook/meta-webhook`

**Configuración en Meta:**
- Webhook URL: `https://tu-n8n.com/webhook/meta-webhook`
- Verify Token: (el que configures en n8n)

#### **Nodo 2: Extraer Datos del Webhook**
- **Tipo:** Code (JavaScript)
- **Código:**
```javascript
// Extraer datos del webhook de Meta
const entry = $input.item.json.entry[0];
const changes = entry.changes[0];
const value = changes.value;

// Mensaje de WhatsApp
const message = value.messages?.[0];
const from_number = message?.from;
const message_text = message?.text?.body || "";

// Retornar datos limpios
return {
  from: from_number,
  message: message_text,
  channel: "whatsapp",
  timestamp: message?.timestamp
};
```

#### **Nodo 3: HTTP Request a tu API**
- **Tipo:** HTTP Request
- **Método:** POST
- **URL:** `https://tu-servidor.com/business-ai/n8n/webhook`
- **Body (JSON):**
```json
{
  "message": "{{ $json.message }}",
  "from": "{{ $json.from }}",
  "channel": "{{ $json.channel }}"
}
```

#### **Nodo 4: IF (Frustración Alta)**
- **Tipo:** IF
- **Condición:** `{{ $json.metadata.needs_handoff }} == true`
- **True:** Enviar a Slack
- **False:** Continuar

#### **Nodo 5: Responder a Meta**
- **Tipo:** HTTP Request
- **Método:** POST
- **URL:** `https://graph.facebook.com/v18.0/{{ PHONE_NUMBER_ID }}/messages`
- **Headers:**
  - `Authorization: Bearer {{ ACCESS_TOKEN }}`
- **Body:**
```json
{
  "messaging_product": "whatsapp",
  "to": "{{ $('Nodo 2').item.json.from }}",
  "type": "text",
  "text": {
    "body": "{{ $json.response }}"
  }
}
```

---

## 📋 **PASO 4: CONFIGURAR TU API DE GRADIO**

### **A. Asegurar que tu API esté accesible:**

```python
# En api_server.py ya está configurado:
# - CORS habilitado
# - Endpoint /business-ai/n8n/webhook
# - Endpoint /business-ai/chat
```

### **B. Variables de Entorno:**

```bash
# .env
GROQ_API_KEY=tu_groq_api_key
DOCCHAT_USE_GROQ=true
DOCCHAT_GROQ_MODEL=llama-3.3-70b-versatile

# PostgreSQL (memoria de largo plazo)
DATABASE_URL=postgresql://user:pass@host:port/db
DOCCHAT_POSTGRESQL_ENABLED=true

# n8n
N8N_WEBHOOK_URL=https://tu-n8n.com/webhook
DOCCHAT_N8N_ENABLED=true
```

---

## 📋 **PASO 5: PROBAR EL FLUJO**

### **Test Manual:**

1. Envía mensaje de WhatsApp a tu número de Meta
2. Meta → Webhook a n8n
3. n8n → POST a `https://tu-servidor.com/business-ai/n8n/webhook`
4. Tu API procesa con Groq (<0.5 seg)
5. Respuesta → n8n → Meta → WhatsApp del cliente

### **Verificar Logs:**

- n8n: Ve a "Executions" para ver el flujo
- Tu API: Revisa logs de `api_server.py`
- Meta: Revisa webhooks en Facebook Developer Console

---

## 🎯 **CONFIGURACIÓN AVANZADA**

### **A. Consultar Inventario Antes de Responder:**

En n8n, entre el nodo de webhook y el de tu API:

**Nodo: Consultar Google Sheets**
- Tipo: Google Sheets
- Operación: Read
- Spreadsheet ID: (tu ID)
- Range: `Inventario!A:D`
- Filtrar: Producto disponible

**Nodo: Agregar al Payload**
- Agregar `inventory_data` al payload antes de llamar a tu API

### **B. Guardar en CRM Automáticamente:**

Después de recibir respuesta de tu API:

**Nodo: IF (intención = comprar)**
- Condición: `{{ $json.metadata.intent }} == "sales"`

**Nodo: HubSpot/Salesforce**
- Tipo: HubSpot Create Contact
- Datos: Usuario, productos de interés, score de sentimiento

### **C. Alertas a Slack:**

**Nodo: IF (frustración > 7)**
- Condición: `{{ $json.metadata.frustration_score }} > 7`

**Nodo: Slack**
- Tipo: Slack Send Message
- Canal: #customer-support
- Mensaje: "⚠️ Cliente frustrado detectado: {{ $json.metadata }}"

---

## ✅ **RESULTADO FINAL**

Con esta configuración:

1. ✅ Cliente escribe en WhatsApp
2. ✅ n8n recibe webhook de Meta
3. ✅ n8n llama a tu API (Groq <0.5 seg)
4. ✅ Tu agente procesa (con memoria PostgreSQL)
5. ✅ n8n ejecuta acciones (CRM, alertas, inventario)
6. ✅ n8n responde a WhatsApp
7. ✅ **Todo automático, <1 segundo total**

---

## 🚀 **PRÓXIMOS PASOS**

1. Configurar n8n en VPS ($10-20/mes)
2. Conectar con Meta (WhatsApp Business API)
3. Probar flujo completo
4. Agregar más integraciones (CRM, inventario, etc.)

---

**✅ GUÍA COMPLETA - LISTO PARA IMPLEMENTAR**
