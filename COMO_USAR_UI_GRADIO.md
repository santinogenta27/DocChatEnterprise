# 🚀 CÓMO USAR LA UI DE GRADIO DE STAR AGENT

## 📋 GUÍA RÁPIDA PARA CLIENTES

### **Paso 1: Iniciar la UI**

```bash
python run_star_agent_ui.py
```

Se abrirá automáticamente en tu navegador en: `http://127.0.0.1:7860`

---

## 🎯 CONFIGURACIÓN PASO A PASO

### **1. 🤖 Configurar Chatbot Básico**

1. Ve a la tab **"⚙️ Configuración"**
2. En **"🤖 Chatbot Básico"**:
   - **Nombre de tu Empresa/Marca**: Ej: "Mi Tienda Online"
   - **Tono de Comunicación**: Elige entre:
     - `friendly` - Amigable y cercano
     - `professional` - Profesional y formal
     - `casual` - Casual y relajado
     - `formal` - Formal y serio
     - `enthusiastic` - Entusiasta y energético
   - **Personalidad del Chatbot** (opcional): Ej: "Soy un asistente amigable que ama ayudar a los clientes..."
   - **Instrucciones Personalizadas** (opcional): Ej: "Siempre menciona que tenemos envío gratis"
   - **Idioma por Defecto**: `es` (español)
   - **Soporte Multilingüe**: Activa si quieres que responda en otros idiomas

3. Click **"💾 Guardar Configuración"**

---

### **2. 📥 Configurar Ingesta Automática**

1. Ve a la tab **"⚙️ Configuración"**
2. En **"📥 Ingesta Automática"**:

#### **🌐 Sitio Web:**
- ✅ Activa **"Habilitar Crawling Automático del Sitio Web"**
- Ingresa **"URL de tu Sitio Web"**: Ej: `https://tu-empresa.com`
- El sistema crawleará tu sitio cada 6 horas automáticamente

#### **📷 Instagram (Opcional):**
- ✅ Activa **"Habilitar Extracción de Instagram"**
- Ingresa **"Instagram Access Token"**
  - Cómo obtenerlo:
    1. Ve a https://developers.facebook.com/
    2. Crea una app
    3. Agrega "Instagram Graph API"
    4. Genera access token

#### **📘 Facebook (Opcional):**
- ✅ Activa **"Habilitar Extracción de Facebook"**
- Ingresa **"Facebook Access Token"**
- Ingresa **"Facebook Page ID"** (encuéntralo en la configuración de tu página)
- Ingresa **"Facebook Verify Token"** (para webhooks)

#### **🔍 Google Business (Opcional):**
- ✅ Activa **"Habilitar Extracción de Google Business"**
- Ingresa **"Google Business API Key"**
- Ingresa **"Google Place ID"** (encuéntralo en la URL de Google Maps)

3. Click **"💾 Guardar Configuración"**

---

### **3. 📚 Subir Documentos (Opcional)**

1. Ve a la tab **"⚙️ Configuración"**
2. En **"📚 RAG y Documentos"**:
   - ✅ Asegúrate que **"Habilitar RAG Avanzado"** esté activado
   - En **"📁 Subir Documentos Manualmente"**:
     - Selecciona archivos (PDF, Word, texto)
     - Click **"📤 Procesar y Agregar Documentos"**
   - El agente aprenderá de estos documentos

---

### **4. 💰 Configurar Sales Closer Elite**

1. Ve a la tab **"⚙️ Configuración"**
2. En **"💰 Sales Closer Elite"**:
   - ✅ Activa **"Habilitar Sales Closer Elite"**
   - Ajusta **"Agresividad de Ventas"** (1-10):
     - 1-3: Suave
     - 4-7: Balanceado (recomendado)
     - 8-10: Muy agresivo (pero ético)
   - En **"🛡️ Manejo de Objeciones"**:
     - Edita respuestas a objeciones comunes (formato JSON)
     - Ejemplo:
       ```json
       {
         "caro": "Entiendo. Justamente por eso incluye X, Y y Z que ahorran dinero a largo plazo.",
         "después": "Tiene sentido. ¿Qué tendría que pasar para que lo veas útil ahora?",
         "pensar": "Claro, es una decisión importante. ¿Hay algo específico en lo que pueda ayudarte a decidir?"
       }
       ```

3. Click **"💾 Guardar Configuración"**

---

### **5. 🔌 Configurar Integraciones**

1. Ve a la tab **"⚙️ Configuración"**
2. En **"🔌 Integraciones"**:

#### **💳 Stripe (Pagos):**
- ✅ Activa **"Habilitar Stripe"**
- Ingresa **"Stripe Secret Key"** (obténla en https://dashboard.stripe.com/apikeys)

#### **📊 Google Analytics (Opcional):**
- ✅ Activa **"Habilitar Google Analytics"**
- Ingresa **"Google Analytics ID"** (formato: G-XXXXXXXXXX)

#### **📱 Meta Pixel (Opcional):**
- ✅ Activa **"Habilitar Meta Pixel"**
- Ingresa **"Meta Pixel ID"**

3. Click **"💾 Guardar Configuración"**

---

### **6. 📱 Configurar Canales**

1. Ve a la tab **"⚙️ Configuración"**
2. En **"📱 Canales"**:

#### **🌐 Widget Web:**
- ✅ Activa **"Habilitar Widget Web"**
- Elige **"Posición del Widget"**:
  - `bottom-right` (recomendado)
  - `bottom-left`
  - `top-right`
  - `top-left`

#### **💬 WhatsApp (Opcional):**
- ✅ Activa **"Habilitar WhatsApp Business"**
- Ingresa **"WhatsApp Business API Key"**

#### **📘 Facebook Messenger (Opcional):**
- ✅ Activa **"Habilitar Facebook Messenger"**

#### **📷 Instagram Direct (Opcional):**
- ✅ Activa **"Habilitar Instagram Direct"**

3. Click **"💾 Guardar Configuración"**

---

## 🧪 PROBAR EL AGENTE

1. Ve a la tab **"💬 Chat"**
2. Escribe un mensaje: Ej: "¿Cuánto cuesta el producto X?"
3. El agente responderá usando toda la configuración que estableciste
4. Prueba diferentes preguntas para verificar que todo funciona

---

## 📊 VER MÉTRICAS

1. Ve a la tab **"📊 Métricas"**
2. Click **"🔄 Actualizar"**
3. Verás:
   - Total de requests
   - Conversion rate
   - Revenue total
   - Drop-off rate
   - Tiempo promedio de respuesta
   - Etapas de venta más comunes
   - Objeciones más frecuentes

---

## 💾 GUARDAR/CARGAR CONFIGURACIÓN

### **Guardar:**
- Click **"💾 Guardar Configuración"** en cualquier momento
- La configuración se guarda en `docchat/star_agent/config/star_agent_config.json`

### **Cargar:**
- Click **"📂 Cargar Configuración"** para cargar configuración guardada anteriormente

### **Restablecer:**
- Click **"🔄 Restablecer a Valores por Defecto"** para volver a valores iniciales

---

## ⚠️ NOTAS IMPORTANTES

1. **Siempre guarda** después de hacer cambios
2. **Prueba el agente** después de configurar para verificar que todo funciona
3. **Los tokens** (Instagram, Facebook, Stripe) son sensibles - no los compartas
4. **La configuración se aplica inmediatamente** después de guardar
5. **No necesitas reiniciar** el servidor después de guardar

---

## 🎯 EJEMPLO DE CONFIGURACIÓN COMPLETA

```
1. Chatbot Básico:
   - Nombre: "Mi Tienda Online"
   - Tono: "friendly"
   - Idioma: "es"

2. Ingesta Automática:
   - Web: ✅ Habilitado
   - URL: "https://mi-tienda.com"
   - Instagram: ✅ Habilitado (con token)
   - Facebook: ✅ Habilitado (con token y page ID)

3. RAG:
   - ✅ Habilitado
   - Documentos: 5 PDFs subidos

4. Sales Closer:
   - ✅ Habilitado
   - Agresividad: 5 (balanceado)

5. Integraciones:
   - Stripe: ✅ Habilitado (con secret key)

6. Canales:
   - Widget Web: ✅ Habilitado
   - Posición: "bottom-right"
```

---

*Documento generado: 2025-01-XX*  
*Versión: 1.0.0 - Guía de Uso de UI*

