# 🚀 Business AI Support Widget - Widget Embeddable

Widget de chat completamente funcional y personalizable para integrar Business AI Support en cualquier sitio web.

## ✨ Características

- ✅ **Widget HTML/JS completo** - Listo para copiar/pegar
- ✅ **Código de embed simple** - Un solo `<script>` tag
- ✅ **Personalización visual** - Colores, logo, posición
- ✅ **Responsive** - Mobile-friendly automático
- ✅ **API pública** - Control programático del widget
- ✅ **Sin dependencias** - Vanilla JavaScript puro
- ✅ **Ligero** - ~15KB minificado

## 📦 Instalación

### Opción 1: Hosting Propio (Recomendado)

1. Copia `business-ai-widget.js` a tu servidor
2. Sirve el archivo desde `/widget/business-ai-widget.js`
3. Agrega el código de embed a tu sitio

### Opción 2: CDN (Próximamente)

```html
<script src="https://cdn.business-ai-support.com/widget.js"></script>
```

## 🚀 Uso Rápido

### Método 1: Integración Simple

Agrega esto antes de `</body>`:

```html
<script src="https://tu-dominio.com/widget/business-ai-widget.js"></script>
<script>
  BusinessAIWidget.init({
    apiUrl: 'https://tu-dominio.com',
    primaryColor: '#007bff',
    position: 'bottom-right',
    brandName: 'Mi Empresa'
  });
</script>
```

### Método 2: Con Atributos Data

```html
<script 
  src="https://tu-dominio.com/widget/business-ai-widget.js"
  data-business-ai-widget
  data-api-url="https://tu-dominio.com"
  data-primary-color="#007bff"
  data-position="bottom-right"
  data-brand-name="Mi Empresa"
  data-logo="https://tu-dominio.com/logo.png"
></script>
```

## 🎨 Opciones de Configuración

| Opción | Tipo | Default | Descripción |
|--------|------|---------|-------------|
| `apiUrl` | string | `window.location.origin` | URL base de tu API |
| `apiEndpoint` | string | `/business-ai-support/chat` | Endpoint del API |
| `primaryColor` | string | `'#007bff'` | Color principal (botón, header) |
| `secondaryColor` | string | `'#6c757d'` | Color secundario |
| `position` | string | `'bottom-right'` | Posición: `'bottom-right'`, `'bottom-left'`, `'top-right'`, `'top-left'` |
| `logo` | string | `null` | URL del logo (se muestra en header) |
| `brandName` | string | `'Business AI Support'` | Nombre de tu marca |
| `welcomeMessage` | string | `'¡Hola! 👋 ¿En qué puedo ayudarte hoy?'` | Mensaje de bienvenida |
| `placeholder` | string | `'Escribe tu mensaje...'` | Placeholder del input |
| `showBranding` | boolean | `true` | Mostrar branding |
| `zIndex` | number | `9999` | Z-index del widget |
| `language` | string | `'es'` | Idioma |

## 💻 API Pública

### Métodos Disponibles

```javascript
// Abrir el widget
BusinessAIWidget.open();

// Cerrar el widget
BusinessAIWidget.close();

// Enviar mensaje programáticamente
BusinessAIWidget.sendMessage('Hola, necesito ayuda');

// Obtener configuración actual
const config = BusinessAIWidget.getConfig();

// Obtener session ID
const sessionId = BusinessAIWidget.getSessionId();
```

## 📱 Responsive

El widget se adapta automáticamente:

- **Desktop**: 380px de ancho
- **Mobile**: Se adapta al ancho de la pantalla (con márgenes de 10px)
- **Altura**: Máximo `calc(100vh - 100px)` para no cubrir toda la pantalla

## 🎨 Personalización Avanzada

### Colores Personalizados

```javascript
BusinessAIWidget.init({
  apiUrl: 'https://tu-dominio.com',
  primaryColor: '#28a745',  // Verde
  secondaryColor: '#6c757d' // Gris
});
```

### Posiciones

```javascript
// Esquina inferior derecha (default)
position: 'bottom-right'

// Esquina inferior izquierda
position: 'bottom-left'

// Esquina superior derecha
position: 'top-right'

// Esquina superior izquierda
position: 'top-left'
```

### Logo Personalizado

```javascript
BusinessAIWidget.init({
  apiUrl: 'https://tu-dominio.com',
  logo: 'https://tu-dominio.com/logo.png' // URL del logo
});
```

## 🔧 Integración con FastAPI

El widget se conecta automáticamente al endpoint:

```
POST /business-ai-support/chat
```

**Payload:**
```json
{
  "session_id": "session_123",
  "user_id": "user_123",
  "message": "Hola",
  "channel": "web"
}
```

**Response:**
```json
{
  "text": "¡Hola! ¿En qué puedo ayudarte?",
  "session": {...}
}
```

## 📋 Requisitos del Backend

Asegúrate de que tu API tenga:

1. **CORS habilitado** para permitir requests desde cualquier dominio
2. **Endpoint `/business-ai-support/chat`** que acepte POST requests
3. **Response en formato JSON** con campo `text`

## 🐛 Troubleshooting

### El widget no aparece

1. Verifica que el script se carga correctamente
2. Revisa la consola del navegador por errores
3. Asegúrate de que `apiUrl` es correcta

### No se envían mensajes

1. Verifica que el endpoint `/business-ai-support/chat` existe
2. Revisa que CORS está habilitado en el backend
3. Verifica la consola del navegador por errores de red

### El widget se ve mal en mobile

El widget es responsive por defecto. Si hay problemas:
1. Verifica que no hay CSS conflictivo en tu sitio
2. Ajusta el `zIndex` si hay elementos superpuestos
3. Revisa que el viewport meta tag está presente

## 🔒 Seguridad

- El widget usa `fetch` API estándar
- No almacena datos sensibles localmente
- Session ID se genera automáticamente
- Compatible con HTTPS

## 📊 Ejemplo Completo

Ver `embed-example.html` para un ejemplo completo de integración.

## 🚀 Próximas Mejoras

- [ ] Soporte para archivos adjuntos
- [ ] Indicador de "escribiendo..."
- [ ] Emojis picker
- [ ] Temas dark/light
- [ ] Notificaciones de sonido
- [ ] Historial de conversaciones persistente

## 📝 Licencia

Incluido con Business AI Support.

