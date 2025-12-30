# Integración WhatsApp e Instagram en Interfaz Gradio

## Resumen

Se ha agregado un nuevo tab "📱 WhatsApp & Instagram" en la interfaz Gradio de STAR AGENT que permite configurar y gestionar la integración con WhatsApp Business e Instagram Direct Messages.

---

## ✅ Cambios Realizados

### Nuevo Tab en la Interfaz Gradio

Se agregó un nuevo tab después del tab de "Configuración" y antes de "Métricas" con tres sub-tabs:

1. **💬 WhatsApp Business**
2. **📷 Instagram Direct**
3. **🌐 Estado y Webhooks**

---

## 📋 Funcionalidades Implementadas

### 1. WhatsApp Business Tab

**Campos de configuración:**
- ✅ Checkbox para habilitar/deshabilitar WhatsApp
- ✅ **Phone Number ID** - ID del número de teléfono de WhatsApp Business
- ✅ **Access Token** - Token de acceso de WhatsApp Business API
- ✅ **Verify Token** - Token personalizado para verificar webhooks
- ✅ **Webhook URL** - URL generada automáticamente (no editable)

**Funciones:**
- ✅ **Guardar Configuración** - Guarda credenciales y inicializa adapter
- ✅ **Probar Conexión** - Verifica que las credenciales sean válidas

**Características:**
- Guarda credenciales en variables de entorno
- Inicializa `WhatsAppBusinessAdapter` cuando se guarda
- Muestra estado de configuración
- Genera URL de webhook automáticamente

---

### 2. Instagram Direct Tab

**Campos de configuración:**
- ✅ Checkbox para habilitar/deshabilitar Instagram
- ✅ **Page ID** - ID de la página de Facebook conectada a Instagram
- ✅ **Page Access Token** - Token de acceso con permisos de Instagram
- ✅ **Verify Token** - Token personalizado para verificar webhooks
- ✅ **Webhook URL** - URL generada automáticamente

**Funciones:**
- ✅ **Guardar Configuración** - Guarda credenciales y inicializa adapter
- ✅ **Probar Conexión** - Verifica conexión con Instagram Graph API

**Características:**
- Usa `MessengerAdapter` para Instagram (Instagram usa la misma API que Messenger)
- Guarda credenciales en variables de entorno
- Verifica que la página esté conectada a Instagram Business Account
- Genera URL de webhook automáticamente

---

### 3. Estado y Webhooks Tab

**Funcionalidades:**
- ✅ **Estado de Conexiones** - Muestra estado actual de WhatsApp e Instagram
- ✅ **Botón Actualizar** - Refresca el estado de conexiones
- ✅ **URLs de Webhooks** - Muestra las URLs que deben configurarse en Meta

**Información mostrada:**
- Estado JSON con información de cada canal (enabled, configured, connected)
- URLs de webhooks generadas automáticamente
- Instrucciones de configuración detalladas

---

## 🔧 Integración Técnica

### Variables de Entorno Configuradas

**WhatsApp:**
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_VERIFY_TOKEN`

**Instagram:**
- `INSTAGRAM_PAGE_ID`
- `INSTAGRAM_ACCESS_TOKEN`
- `INSTAGRAM_VERIFY_TOKEN`

### Adapters Inicializados

Cuando se guarda la configuración, se inicializan los adapters:

```python
# WhatsApp
self.whatsapp_adapter = WhatsAppBusinessAdapter(
    phone_number_id=phone_id,
    access_token=access_token,
    verify_token=verify_token
)

# Instagram (usa MessengerAdapter)
self.instagram_adapter = MessengerAdapter(
    page_id=page_id,
    access_token=access_token,
    verify_token=verify_token
)
```

---

## 📝 Uso

### Configurar WhatsApp

1. Ve al tab "📱 WhatsApp & Instagram"
2. Selecciona el sub-tab "💬 WhatsApp Business"
3. Marca "✅ Habilitar WhatsApp Business"
4. Ingresa:
   - Phone Number ID
   - Access Token
   - Verify Token (opcional, tiene un valor por defecto)
5. Haz clic en "💾 Guardar Configuración WhatsApp"
6. Opcionalmente, haz clic en "🧪 Probar Conexión" para verificar
7. Copia la Webhook URL mostrada
8. Configura el webhook en Meta Business Suite

### Configurar Instagram

1. Ve al tab "📱 WhatsApp & Instagram"
2. Selecciona el sub-tab "📷 Instagram Direct"
3. Marca "✅ Habilitar Instagram Direct"
4. Ingresa:
   - Page ID
   - Page Access Token
   - Verify Token (opcional)
5. Haz clic en "💾 Guardar Configuración Instagram"
6. Opcionalmente, haz clic en "🧪 Probar Conexión"
7. Copia la Webhook URL mostrada
8. Configura el webhook en Meta for Developers

### Verificar Estado

1. Ve al tab "📱 WhatsApp & Instagram"
2. Selecciona el sub-tab "🌐 Estado y Webhooks"
3. Haz clic en "🔄 Actualizar Estado"
4. Revisa el JSON de estado para verificar configuración

---

## ⚠️ Notas Importantes

1. **Webhook URLs:** Las URLs se generan automáticamente usando `WEBHOOK_BASE_URL` del entorno. Si no está configurado, usa `https://tu-dominio.com` como placeholder.

2. **Para desarrollo local:** Necesitas usar ngrok o similar para exponer tu servidor local:
   ```bash
   ngrok http 7860
   ```
   Luego configura `WEBHOOK_BASE_URL=https://tu-ngrok-url.ngrok.io`

3. **Permisos requeridos:**
   - WhatsApp: Requiere WhatsApp Business API activada
   - Instagram: Requiere permisos `instagram_basic`, `instagram_manage_messages`, `pages_messaging`

4. **Verificación de webhooks:** Meta requiere verificar los webhooks antes de enviar mensajes. El Verify Token debe coincidir con el configurado en Meta.

---

## 🔗 Integración con el Agente

Una vez configurados los adapters, los mensajes recibidos en WhatsApp e Instagram se procesarán automáticamente usando `ReactSalesAgent`:

1. Mensaje recibido → Webhook
2. Webhook → Adapter (`to_internal()`)
3. Adapter → `star_agent_mode.process_message()`
4. Process Message → `ReactSalesAgent`
5. Respuesta → Adapter (`send_message()`)
6. Adapter → WhatsApp/Instagram

---

## 📚 Archivos Modificados

- `docchat/star_agent/star_agent_mode.py` - Método `get_gradio_interface()` actualizado con nuevo tab

---

## ✅ Estado

✅ **COMPLETADO** - La integración está lista para usar. Solo falta configurar los webhooks en Meta para que los mensajes se reciban automáticamente.

