# 🌐 Website Demo con Widget STAR AGENT

## ✅ Archivo Creado

Se ha creado el archivo: **`star_agent_widget_demo.html`**

Este es un website completo y funcional que incluye el chatbot STAR AGENT en la esquina inferior derecha.

---

## 📋 Características del Website

- ✅ **Diseño moderno y atractivo** con gradientes y efectos glassmorphism
- ✅ **Responsive** - Se adapta a móviles y tablets
- ✅ **Chatbot integrado** - Widget flotante en esquina inferior derecha
- ✅ **Información clara** - Explica cómo usar el chatbot
- ✅ **Características destacadas** - Muestra todas las funcionalidades del chatbot

---

## 🚀 Cómo Abrirlo

### Opción 1: Doble Click
1. Navega a: `C:\Users\usuario\DocChatEnterprise`
2. Busca el archivo: `star_agent_widget_demo.html`
3. Haz doble click en el archivo
4. Se abrirá en tu navegador predeterminado

### Opción 2: Arrastrar y Soltar
1. Abre tu navegador (Chrome, Firefox, Edge, etc.)
2. Arrastra el archivo `star_agent_widget_demo.html` a la ventana del navegador
3. El website se cargará automáticamente

### Opción 3: Abrir desde el Navegador
1. Abre tu navegador
2. Presiona `Ctrl + O` (o `Cmd + O` en Mac)
3. Navega a: `C:\Users\usuario\DocChatEnterprise`
4. Selecciona: `star_agent_widget_demo.html`
5. Haz click en "Abrir"

---

## 💬 Cómo Usar el Chatbot

1. **Abre el website** usando cualquiera de las opciones anteriores
2. **Busca el botón de chat** en la esquina inferior derecha de la página
3. **Haz click en el botón** para abrir la ventana de chat
4. **Escribe tu mensaje** en el cuadro de texto
5. **Presiona Enter** o haz click en "Enviar"
6. **El chatbot responderá** usando STAR AGENT

---

## 🔧 Configuración del Widget

El código del widget está configurado con:

```html
<script src="http://127.0.0.1:7864/static/business-ai-widget.js" 
        data-api-url="http://127.0.0.1:7864"
        data-widget-id="star_agent_widget_demo_001"
        data-brand-name="STAR AGENT"
        data-primary-color="#007bff"
        data-position="bottom-right"
        data-welcome-message="👋 ¡Hola! Soy tu asistente virtual. ¿En qué puedo ayudarte hoy?"
        async></script>
```

**Parámetros:**
- `data-widget-id`: ID único del widget (requerido, no puede estar vacío)
- `data-brand-name`: Nombre de la marca que aparece en el widget
- `data-primary-color`: Color principal del widget (#007bff = azul)
- `data-position`: Posición del widget (bottom-right o bottom-left)
- `data-welcome-message`: Mensaje de bienvenida cuando se abre el chat

---

## ⚠️ Requisitos

1. **Servidor API debe estar corriendo:**
   - Puerto: 7864
   - URL: http://127.0.0.1:7864
   - Verifica en la UI de Gradio → Pestaña "🚀 Servidor API"

2. **El archivo JS debe ser accesible:**
   - URL: http://127.0.0.1:7864/static/business-ai-widget.js
   - Debe retornar código JavaScript (no "Not Found")

---

## 🐛 Si el Chatbot No Aparece

### 1. Verifica el Servidor API
- Abre: http://127.0.0.1:7864/api/widget/health
- Debe retornar: `{"status": "healthy", ...}`

### 2. Abre la Consola del Navegador
- Presiona `F12` en el navegador
- Ve a la pestaña "Console"
- Busca errores relacionados con:
  - `business-ai-widget.js`
  - `widget-id`
  - `CORS`

### 3. Verifica el Network
- Presiona `F12` → Pestaña "Network"
- Recarga la página
- Busca `business-ai-widget.js`
- Status debe ser: `200 OK`

### 4. Verifica los Valores
- El `data-widget-id` NO puede estar vacío o ser "X" o "F"
- Debe ser un valor válido como: `star_agent_widget_demo_001`

---

## 📝 Personalización

Si quieres personalizar el widget, modifica estos valores en el código:

```html
data-widget-id="tu_widget_id_aqui"          <!-- Cambia el ID -->
data-brand-name="Tu Marca"                  <!-- Cambia el nombre -->
data-primary-color="#ff6b6b"                <!-- Cambia el color -->
data-position="bottom-left"                 <!-- Cambia la posición -->
data-welcome-message="Tu mensaje aquí"      <!-- Cambia el mensaje -->
```

---

## ✅ Estado Actual

- ✅ Website creado: `star_agent_widget_demo.html`
- ✅ Widget configurado con valores válidos
- ✅ Diseño moderno y responsive
- ✅ Instrucciones incluidas
- ⚠️ Verifica que el servidor API esté corriendo

---

¡Abre el archivo y prueba el chatbot! 🚀

