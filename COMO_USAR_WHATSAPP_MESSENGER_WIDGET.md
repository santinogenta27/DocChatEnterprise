# 💬 Cómo Configurar WhatsApp y Messenger en el Widget

## ✅ Funcionalidad Implementada

Los botones de WhatsApp y Messenger ahora están completamente integrados en el chatbot de STAR AGENT. Aparecen **dentro del chat** después del mensaje de bienvenida.

---

## 🚀 Cómo Configurarlo desde la UI

### Paso 1: Abrir la UI de Gradio

1. Ejecuta: `py -3.12 run_star_agent_ui.py`
2. Espera a que cargue la UI
3. Ve a la pestaña **"🔧 Generar Código"**

### Paso 2: Configurar WhatsApp

1. **Marca el checkbox:** ✅ Activar Botón de WhatsApp
2. **Ingresa tu número:** En "Número de WhatsApp Business"
   - Formato: `+1234567890` (con código de país)
   - Ejemplo: `+1234567890` (EE.UU.), `+521234567890` (México)
3. **Personaliza el mensaje (opcional):** En "Mensaje Predefinido WhatsApp"
   - Este mensaje aparecerá pre-llenado cuando el usuario haga click
   - Ejemplo: `Hola, vi tu producto en tu website y me interesa saber más`

### Paso 3: Configurar Messenger (Opcional)

1. **Marca el checkbox:** ✅ Activar Botón de Messenger
2. **Ingresa tu página:** En "Página de Facebook"
   - Solo el nombre de la página (sin @ ni facebook.com)
   - Ejemplo: Si tu URL es `facebook.com/mitienda`, escribe: `mitienda`

### Paso 4: Generar el Código

1. Haz click en **"📋 Generar Código"**
2. El código generado incluirá automáticamente todos los atributos de WhatsApp y Messenger
3. Copia el código y pégalo en tu website

---

## 📋 Ejemplo de Código Generado

```html
<!-- STAR AGENT Widget -->
<!-- Copia y pega este código antes de </body> en tu website -->
<script src="http://127.0.0.1:7864/static/business-ai-widget.js" 
        data-api-url="http://127.0.0.1:7864"
        data-widget-id="widget_abc123"
        data-brand-name="Mi Empresa"
        data-primary-color="#007bff"
        data-position="bottom-right"
        data-welcome-message="👋 ¡Hola! Soy tu asistente virtual. ¿En qué puedo ayudarte hoy?"
        data-enable-whatsapp="true"
        data-whatsapp-number="+1234567890"
        data-whatsapp-message="Hola, vi tu producto en tu website"
        data-enable-messenger="true"
        data-messenger-page="mi-pagina-facebook"
        async></script>
```

---

## 🎨 Cómo Funciona

### Experiencia del Usuario:

1. **Usuario visita tu website**
2. **Hace click en el botón del chatbot** (esquina inferior derecha)
3. **Ve el mensaje de bienvenida** del asistente
4. **Ve los botones** (si están configurados):
   - 💬 **"Prefiero WhatsApp"** (verde)
   - 💙 **"Prefiero Messenger"** (azul)
5. **Si hace click en "Prefiero WhatsApp":**
   - Se abre WhatsApp (app o web)
   - Se abre un chat con tu número
   - El mensaje predefinido aparece listo para enviar
6. **Si hace click en "Prefiero Messenger":**
   - Se abre Messenger (app o web)
   - Se abre un chat directo con tu página de Facebook

---

## ⚙️ Opciones de Configuración

### Solo WhatsApp:
- ✅ Activar Botón de WhatsApp: **Marcado**
- 📱 Número de WhatsApp: **Tu número**
- 💬 Mensaje: **Tu mensaje** (opcional)
- ✅ Activar Botón de Messenger: **Sin marcar**

### Solo Messenger:
- ✅ Activar Botón de WhatsApp: **Sin marcar**
- ✅ Activar Botón de Messenger: **Marcado**
- 📘 Página de Facebook: **Tu página**

### Ambos (Recomendado):
- ✅ Activar Botón de WhatsApp: **Marcado**
- ✅ Activar Botón de Messenger: **Marcado**
- Configura ambos números/páginas

### Ninguno (Solo chat en website):
- ✅ Activar Botón de WhatsApp: **Sin marcar**
- ✅ Activar Botón de Messenger: **Sin marcar**
- El chatbot funcionará solo en el website

---

## 📝 Notas Importantes

1. **Los botones aparecen dentro del chat**, no como botones flotantes separados
2. **Se muestran después del mensaje de bienvenida**
3. **Solo aparecen si están configurados correctamente** (checkbox marcado + número/página ingresado)
4. **El formato del número se limpia automáticamente** (puedes escribir con espacios, guiones, etc.)
5. **El mensaje de WhatsApp es opcional**, si no lo configuras, se usará un mensaje por defecto

---

## ✅ Verificación

Después de configurar y generar el código:

1. **Pega el código en tu website**
2. **Abre el website** en el navegador
3. **Haz click en el botón del chatbot**
4. **Verifica que los botones aparezcan** después del mensaje de bienvenida
5. **Haz click en los botones** para verificar que abran WhatsApp/Messenger correctamente

---

## 🎉 ¡Listo!

Los botones de WhatsApp y Messenger están completamente integrados y funcionando. Solo necesitas configurarlos desde la UI y generar el código nuevo.

¡Disfruta de la funcionalidad completa! 🚀

