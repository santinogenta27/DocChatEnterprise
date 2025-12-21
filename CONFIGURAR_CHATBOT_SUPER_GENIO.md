# 🧠 Configurar Chatbot "Super Genio" (Nivel Meta Sales Agent)

## ✅ Cómo Funciona

El chatbot del modo **Business AI Omnicanal** ahora tiene un comportamiento **"Super Genio"** inspirado en los sales agents de Meta/Mark Zuckerberg, con técnicas avanzadas de ventas, persuasión estratégica y cierre inteligente.

## 🚀 Pasos para Configurar y Probar

### 1. **Configurar el Comportamiento desde Gradio UI**

Ejecuta la UI de Gradio para configurar el chatbot:

```powershell
cd C:\Users\Random\DocChatEnterprise
py -3.12 app.py
```

Luego:

1. Ve al modo **"🤖 Business AI Omnicanal"**
2. Ve al tab **"🎨 Configuración Completa del Chatbot"**
3. Configura las siguientes características:

#### **📋 Configuraciones Recomendadas para "Super Genio":**

**Tab 1: Personalización Básica**
- **Tono:** `enthusiastic` o `professional` (según tu marca)
- **Personalidad:** Ejemplo: "Eres un asesor de ventas experto, proactivo y orientado a resultados. Haces preguntas inteligentes para entender necesidades reales y cierras ventas de forma natural."
- **Instrucciones Personalizadas:** (Opcional) Agrega instrucciones específicas de tu negocio

**Tab 2: Motor RAG Activo**
- ✅ **Habilitar RAG:** Activa esto para que el chatbot consulte documentos cuando no tenga respuesta
- **Documentos:** Sube PDFs, manuales, catálogos, etc.
- **URLs:** Agrega URLs de tu website para que el chatbot aprenda de tu contenido

**Tab 3: Lead Scoring**
- ✅ **Habilitar Lead Scoring:** Activa esto para calificar leads automáticamente
- **Preguntas de Oro:** Configura preguntas clave como:
  ```json
  [
    {"question": "¿Cuál es tu presupuesto aproximado?", "weight": 3},
    {"question": "¿Cuándo necesitas esto?", "weight": 2},
    {"question": "¿Para qué lo necesitas?", "weight": 2}
  ]
  ```
- **Threshold para Lead Caliente:** `7` (ajusta según necesites)

**Tab 4: Handoff Humano**
- **Palabras Clave:** `queja`, `fraude`, `hablar con humano`, `supervisor`
- **Threshold de Sentimiento:** `0.7`

**Tab 5: Idioma**
- **Idioma por Defecto:** `es` (español)
- ✅ **Multilingüismo:** Activa esto para que detecte y responda en el idioma del cliente

**Tab 6: Manejo de Objeciones**
- Configura respuestas personalizadas:
  ```json
  {
    "está caro": "Entiendo tu preocupación. Este producto te durará X años, lo que significa que cuesta solo Y por mes. ¿Cuál es tu presupuesto aproximado?",
    "lo voy a pensar": "Por supuesto. ¿Hay algo específico en lo que pueda ayudarte a decidir? ¿Te parece bien si te envío un resumen con las opciones que vimos?",
    "no estoy seguro": "Perfecto, déjame hacerte algunas preguntas para entender mejor qué necesitas exactamente..."
  }
  ```

**Tab 7: Agendamiento de Citas (Booking/CTA)** 🚨
- ✅ **Habilitar Agendamiento:** Activa esto para que ofrezca agendar citas cuando detecte un Lead Caliente
- **URL de Calendly:** Tu URL de Calendly (ej: `https://calendly.com/tu-usuario/demo-30min`)
- **URL de Google Calendar:** (Opcional) Tu URL de Google Calendar
- **Tipo de CRM:** Selecciona tu CRM (HubSpot, Salesforce, Pipedrive) si quieres integración automática
- **Webhook URL del CRM:** URL del webhook para enviar datos del lead
- **Mensaje Personalizado:** Personaliza el mensaje que verá el cliente

4. **💾 Guarda la Configuración:** Haz clic en **"💾 Guardar Configuración Completa"**

### 2. **Ejecutar el Servidor API**

En una **nueva terminal de PowerShell**, ejecuta:

```powershell
cd C:\Users\Random\DocChatEnterprise
python api_server.py
```

El servidor se iniciará en `http://localhost:7864` y cargará automáticamente la configuración que guardaste desde Gradio.

### 3. **Probar el Chatbot**

Puedes probar el chatbot de dos formas:

#### **Opción A: Desde el Widget Embeddable**

1. Abre `chatbot_demo.html` en tu navegador
2. El widget aparecerá en la esquina inferior derecha
3. Haz clic y empieza a chatear

#### **Opción B: Desde la API Directamente**

Puedes hacer requests POST a:
```
POST http://localhost:7864/business-ai/chat
Content-Type: application/json

{
  "session_id": "test_session_123",
  "message": "¿Tienes zapatillas Nike?",
  "user_id": "test_user"
}
```

## 🧠 Mejoras Implementadas para "Super Genio"

### **1. Descubrimiento Inteligente de Necesidades**
- El chatbot hace preguntas estratégicas para entender el contexto real del cliente
- NO asume, pregunta antes de recomendar
- Escucha activamente y profundiza en lo que el cliente menciona

### **2. Persuasión Estratégica y Cierre Avanzado**
- Usa técnicas de cierre suave: "¿Te parece bien si te muestro 3 opciones que encajan perfecto?"
- Crea urgencia cuando es apropiado: "Solo quedan 2 unidades en tu talla"
- Resuelve objeciones proactivamente explicando el valor, no solo el costo
- Usa prueba social: "Este producto es muy popular entre clientes como tú"

### **3. Cross-Selling y Up-Selling Inteligente**
- Sugiere complementos lógicos automáticamente
- Up-selling natural: "Para un uso intensivo, te recomendaría la versión Pro que dura 3x más"
- NO es agresivo, es útil y natural

### **4. Personalización Extrema**
- Adapta el tono al perfil del usuario (formal para B2B, entusiasta para lifestyle)
- Usa el historial de conversación para personalizar recomendaciones
- Se refiere a cosas que el cliente mencionó antes: "Como mencionaste que buscas algo cómodo..."

### **5. Proactividad y Anticipación**
- Después de resolver una pregunta, pregunta proactivamente: "¿Hay algo más en lo que pueda ayudarte?"
- Anticipa necesidades: Si alguien compra un producto, ofrece información sobre garantía, envío, o cuidado
- Si el cliente muestra interés pero no compra, pregunta qué le falta

### **6. Manejo de Objeciones Avanzado**
- Si el cliente dice "está caro", pregunta: "¿Comparado con qué?" o "¿Cuál es tu presupuesto?"
- Si dice "lo voy a pensar", pregunta: "¿Hay algo específico en lo que pueda ayudarte a decidir?"
- Usa técnicas de cierre suave: "¿Te parece bien si te envío un resumen con las opciones que vimos?"

### **7. Técnicas de Cierre de Ventas (cuando es Lead Caliente)**
- Usa el método de "asumir la venta": "Perfecto, ¿qué talla necesitas?" en lugar de "¿Te gustaría comprarlo?"
- Crea escasez cuando sea real: "Solo quedan X unidades"
- Ofrece alternativas: "Si este no encaja, tengo otras 2 opciones que podrían funcionar mejor"
- Cierra con un siguiente paso claro: "¿Te parece bien si te muestro el carrito para que revises?"

### **8. Agendamiento Automático de Citas**
- Cuando detecta un Lead Caliente, ofrece agendar una cita automáticamente
- Integración con Calendly o Google Calendar
- Envío automático de datos al CRM (HubSpot, Salesforce, Pipedrive)

## ⚙️ Configuración Dinámica

**IMPORTANTE:** La configuración se recarga automáticamente en cada mensaje, así que:

1. Puedes cambiar la configuración en Gradio mientras `api_server.py` está corriendo
2. Los cambios se aplicarán en el siguiente mensaje del chatbot
3. NO necesitas reiniciar `api_server.py` para aplicar cambios de configuración

## 🎯 Ejemplo de Conversación "Super Genio"

**Cliente:** "¿Tienes zapatillas?"

**Chatbot (Super Genio):**
"¡Por supuesto! Tenemos varias opciones de zapatillas. Para recomendarte las mejores, déjame hacerte algunas preguntas:

1. ¿Para qué actividad las necesitas? (running, gimnasio, casual, etc.)
2. ¿Qué talla usas?
3. ¿Tienes alguna marca preferida o presupuesto aproximado?

Con esa información, te mostraré las opciones que mejor encajan contigo. 😊"

**Cliente:** "Para running, talla 42, presupuesto hasta 100€"

**Chatbot (Super Genio):**
"Perfecto, tengo 3 opciones excelentes para running en tu talla y presupuesto:

1. **Nike Air Zoom Pegasus 40** - 89€
   - Ideal para running diario, muy cómodas y duraderas
   - ⭐⭐⭐⭐⭐ (4.8/5 de 1,200+ reseñas)
   - Solo quedan 2 unidades en talla 42

2. **Adidas Ultraboost 22** - 95€
   - Máxima amortiguación, perfectas para distancias largas
   - ⭐⭐⭐⭐⭐ (4.9/5 de 800+ reseñas)

3. **Asics Gel-Nimbus 25** - 99€
   - Tecnología de gel avanzada, muy populares entre runners
   - ⭐⭐⭐⭐⭐ (4.7/5 de 600+ reseñas)

**Recomendación personal:** Para running, te recomendaría las Nike Air Zoom Pegasus 40. Son las más populares entre runners como tú y están en tu presupuesto.

¿Te parece bien si te muestro más detalles de alguna de estas? También tenemos calcetines técnicos y plantillas que van perfecto con estas zapatillas. 🏃‍♂️"

## 📝 Notas Importantes

1. **La configuración se guarda en JSON** (`docchat/business_ai_omnicanal/config/chatbot_config.json`)
2. **Los cambios son inmediatos** - no necesitas reiniciar el servidor
3. **El chatbot recarga la configuración en cada mensaje**
4. **Puedes tener Gradio abierto para ajustar la configuración mientras pruebas**

## 🎉 ¡Listo!

Ahora tienes un chatbot "Super Genio" con comportamiento de nivel Meta Sales Agent. El chatbot:

- ✅ Hace preguntas inteligentes para descubrir necesidades
- ✅ Usa técnicas de cierre avanzadas
- ✅ Es proactivo y anticipa necesidades
- ✅ Personaliza extremadamente las respuestas
- ✅ Maneja objeciones de forma estratégica
- ✅ Ofrece agendar citas cuando detecta Leads Calientes
- ✅ Integra con CRM automáticamente

¡Disfruta tu chatbot de nivel enterprise! 🚀
