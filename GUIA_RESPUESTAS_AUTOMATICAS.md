# 🤖 Guía: Respuestas Automáticas en Tiempo Real

Esta guía explica cómo configurar respuestas automáticas que se ejecutan **instantáneamente** cuando llegan mensajes a WhatsApp, Email, Chat, etc.

## 🎯 ¿Qué Hace Este Sistema?

Permite programar respuestas automáticas que se ejecutan **sin intervención humana** cuando llegan mensajes:

- ✅ **Respuesta Fija**: Siempre responde lo mismo (ej: "Gracias por contactarnos")
- ✅ **Por Palabra Clave**: Responde cuando el mensaje contiene ciertas palabras
- ✅ **Por Patrón**: Responde cuando el mensaje coincide con un patrón (regex)
- ✅ **Siempre**: Responde automáticamente a todos los mensajes

## 🚀 Cómo Funciona

1. **Configuras una regla** en la UI de Gradio
2. **Cuando llega un mensaje** (vía webhook o API), el sistema:
   - Evalúa el mensaje contra todas las reglas activas
   - Si encuentra una regla que coincide, **ejecuta la respuesta automáticamente**
   - Envía la respuesta por el mismo canal (WhatsApp, Email, etc.)
3. **Todo sucede en tiempo real**, sin que tengas que hacer nada

## 📝 Ejemplos de Uso

### Ejemplo 1: Saludo Automático en WhatsApp

**Configuración:**
- **Nombre:** "Saludo automático WhatsApp"
- **Canal:** whatsapp
- **Trigger:** keyword
- **Valor:** hola,hola,buenos días,buenas tardes
- **Respuesta:** fixed
- **Contenido:** "¡Hola! Gracias por contactarnos. ¿En qué puedo ayudarte hoy?"

**Resultado:** Cada vez que alguien escriba "hola" en WhatsApp, recibirá automáticamente esa respuesta.

### Ejemplo 2: Respuesta a Consultas de Horarios

**Configuración:**
- **Nombre:** "Horarios de atención"
- **Canal:** all (todos los canales)
- **Trigger:** keyword
- **Valor:** horario,horarios,abierto,cierra,atencion
- **Respuesta:** fixed
- **Contenido:** "Nuestro horario de atención es de Lunes a Viernes de 9:00 AM a 6:00 PM. ¿Necesitas algo más?"

### Ejemplo 3: Respuesta Automática a Todos los Emails

**Configuración:**
- **Nombre:** "Confirmación de recepción"
- **Canal:** email
- **Trigger:** always
- **Valor:** (no necesario)
- **Respuesta:** template
- **Contenido:** "Hola {nombre}, hemos recibido tu mensaje del {fecha} a las {hora}. Te responderemos pronto."

### Ejemplo 4: Respuesta por Patrón (Regex)

**Configuración:**
- **Nombre:** "Consultas de pedidos"
- **Canal:** whatsapp
- **Trigger:** pattern
- **Valor:** `pedido|orden|#\d+`
- **Respuesta:** fixed
- **Contenido:** "Para consultar tu pedido, por favor proporciona el número de orden."

## 🔧 Configuración Paso a Paso

### Paso 1: Acceder a la UI

1. Abre la aplicación Gradio
2. Ve al tab **"🎧 Atención al Cliente 24/7"**
3. Haz clic en el sub-tab **"🤖 Reglas Automáticas"**

### Paso 2: Crear una Regla

1. **Nombre de la Regla:** Un nombre descriptivo (ej: "Saludo WhatsApp")
2. **Canal:** Selecciona el canal (whatsapp, email, chat, all)
3. **Tipo de Trigger:**
   - **Siempre**: Se ejecuta para todos los mensajes
   - **Palabra Clave**: Se ejecuta si el mensaje contiene ciertas palabras
   - **Patrón**: Se ejecuta si el mensaje coincide con un patrón regex
4. **Valor del Trigger:**
   - Para keyword: palabras separadas por comas (ej: `hola,hola,buenos días`)
   - Para pattern: expresión regular (ej: `pedido|orden`)
5. **Tipo de Respuesta:**
   - **Fija**: Respuesta exacta siempre igual
   - **Template**: Respuesta con variables (ej: `{nombre}`, `{fecha}`)
   - **AI Generated**: Respuesta mejorada por AI
6. **Contenido:** El texto de la respuesta
7. **Prioridad:** Número del 0-10 (mayor = se ejecuta primero)

### Paso 3: Guardar y Activar

1. Haz clic en **"✅ Crear Regla"**
2. La regla se guarda automáticamente
3. Se activa inmediatamente (estado: ✅ Activa)

## 🔄 Cómo Funciona en Tiempo Real

### Flujo Automático:

```
1. Cliente envía mensaje → WhatsApp/Email/Chat
2. Webhook recibe mensaje → Tu servidor
3. Sistema evalúa mensaje → Busca reglas que coincidan
4. Si encuentra regla → Genera respuesta automática
5. Envía respuesta → Por el mismo canal
6. Cliente recibe respuesta → En segundos
```

### Ejemplo Real:

**Cliente escribe en WhatsApp:** "Hola, tengo una pregunta"

**Sistema:**
1. Recibe el mensaje vía webhook
2. Evalúa: ¿Hay alguna regla que coincida?
3. Encuentra regla "Saludo automático" (trigger: "hola")
4. Genera respuesta: "¡Hola! Gracias por contactarnos..."
5. Envía automáticamente por WhatsApp
6. Cliente recibe respuesta en 2-3 segundos

## 🔌 Conectar APIs de Mensajería

### WhatsApp (Twilio)

1. Crea cuenta en https://www.twilio.com
2. Configura WhatsApp Sandbox
3. Obtén `TWILIO_ACCOUNT_SID` y `TWILIO_AUTH_TOKEN`
4. Configura webhook en Twilio apuntando a:
   ```
   https://tu-servidor.com/api/v1/customer-service/webhook/whatsapp
   ```
5. Agrega al `.env`:
   ```env
   TWILIO_ACCOUNT_SID=tu_account_sid
   TWILIO_AUTH_TOKEN=tu_auth_token
   WHATSAPP_FROM=whatsapp:+14155238886
   ```

### Email (Gmail)

1. Configura Gmail API (ver `CONECTAR_APIS_ADS.md`)
2. Configura webhook para recibir emails
3. Cuando llegue un email, envía al webhook:
   ```
   POST /api/v1/customer-service/webhook/gmail
   ```

## 📊 Estadísticas

El sistema rastrea:
- **Total de reglas:** Cuántas reglas tienes configuradas
- **Reglas activas:** Cuántas están habilitadas
- **Total de usos:** Cuántas veces se han ejecutado las reglas
- **Uso por regla:** Cuántas veces se usó cada regla

## ⚙️ Tipos de Respuesta

### 1. Respuesta Fija (Fixed)
```
Contenido: "Gracias por contactarnos. Te responderemos pronto."
```
- Siempre responde exactamente lo mismo
- Más rápido
- Ideal para respuestas simples

### 2. Template con Variables
```
Contenido: "Hola {nombre}, tu consulta del {fecha} está siendo procesada."
```
- Variables disponibles:
  - `{nombre}`: Nombre del cliente
  - `{email}`: Email del cliente
  - `{fecha}`: Fecha actual
  - `{hora}`: Hora actual

### 3. AI Generated
```
Contenido: "Responde de forma amigable y profesional"
```
- El AI mejora la respuesta
- Más personalizada
- Usa la base de conocimiento si está disponible

## 🎯 Mejores Prácticas

1. **Usa prioridades:** Reglas más específicas con mayor prioridad
2. **Prueba primero:** Crea reglas de prueba antes de activar en producción
3. **Monitorea uso:** Revisa qué reglas se usan más
4. **Actualiza regularmente:** Mejora las respuestas basándote en feedback
5. **Combina con base de conocimiento:** Las reglas funcionan mejor con KB cargada

## 🚨 Troubleshooting

### La regla no se ejecuta
- Verifica que esté **activa** (✅ Activa)
- Verifica que el **trigger** coincida exactamente
- Revisa la **prioridad** (otras reglas pueden tener mayor prioridad)

### La respuesta no se envía
- Verifica que las credenciales de la API estén configuradas
- Revisa los logs del servidor
- Verifica que el webhook esté recibiendo mensajes

### Múltiples reglas se ejecutan
- Ajusta las **prioridades** (mayor = primero)
- Haz los triggers más específicos
- Usa condiciones adicionales

## 💡 Ejemplos Avanzados

### Regla con Múltiples Palabras Clave
```
Trigger: keyword
Valor: pedido,orden,compra,factura
```
Se ejecuta si el mensaje contiene cualquiera de estas palabras.

### Regla con Regex para Números
```
Trigger: pattern
Valor: \d{4,}
```
Se ejecuta si el mensaje contiene un número de 4 o más dígitos.

### Regla Solo para Horario Laboral
```
Trigger: always
Condiciones: {"hour": "9-18", "day": "mon-fri"}
```
Se ejecuta solo en horario laboral (requiere configuración adicional).

---

**¡Listo!** Ahora puedes automatizar completamente las respuestas a tus clientes. 🚀

