# 📘 Guía de Integración - Business AI Support Widget

## 🎯 Resumen

El widget de Business AI Support es un componente embeddable que puedes agregar a cualquier sitio web con solo unas líneas de código. Es completamente personalizable, responsive y listo para producción.

## ✅ Lo que Incluye

- ✅ Widget HTML/JS completo y funcional
- ✅ Código de embed simple (un solo `<script>` tag)
- ✅ Personalización visual (colores, logo, posición)
- ✅ Widget responsive y mobile-friendly
- ✅ API pública para control programático
- ✅ Sin dependencias externas
- ✅ ~15KB de tamaño

## 🚀 Instalación Rápida (3 Pasos)

### Paso 1: Sube el archivo JavaScript

Sube `business-ai-widget.js` a tu servidor web, por ejemplo:
- `https://tu-dominio.com/widget/business-ai-widget.js`
- O usa un CDN

### Paso 2: Agrega el código de embed

Antes de cerrar el tag `</body>` en tu HTML, agrega:

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

### Paso 3: ¡Listo!

El widget aparecerá automáticamente en tu sitio. Los usuarios pueden hacer clic en el botón flotante para abrir el chat.

## 📋 Configuración Completa

### Opciones Disponibles

```javascript
BusinessAIWidget.init({
  // REQUERIDO: URL de tu API
  apiUrl: 'https://tu-dominio.com',
  
  // OPCIONAL: Personalización
  primaryColor: '#007bff',        // Color principal
  secondaryColor: '#6c757d',      // Color secundario
  position: 'bottom-right',        // Posición del widget
  logo: 'https://.../logo.png',    // URL del logo
  brandName: 'Mi Empresa',         // Nombre de la marca
  welcomeMessage: '¡Hola! 👋',     // Mensaje de bienvenida
  placeholder: 'Escribe...',       // Placeholder del input
  zIndex: 9999,                    // Z-index del widget
  language: 'es'                   // Idioma
});
```

### Posiciones Disponibles

- `'bottom-right'` - Esquina inferior derecha (default)
- `'bottom-left'` - Esquina inferior izquierda
- `'top-right'` - Esquina superior derecha
- `'top-left'` - Esquina superior izquierda

## 🎨 Ejemplos de Personalización

### Ejemplo 1: Verde con Logo

```javascript
BusinessAIWidget.init({
  apiUrl: 'https://tu-dominio.com',
  primaryColor: '#28a745',
  logo: 'https://tu-dominio.com/logo.png',
  brandName: 'Mi Tienda',
  position: 'bottom-right'
});
```

### Ejemplo 2: Rojo, Esquina Izquierda

```javascript
BusinessAIWidget.init({
  apiUrl: 'https://tu-dominio.com',
  primaryColor: '#dc3545',
  position: 'bottom-left',
  brandName: 'Soporte Técnico'
});
```

### Ejemplo 3: Con Atributos Data (Sin JavaScript)

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

## 💻 API Pública

### Controlar el Widget Programáticamente

```javascript
// Abrir el widget
BusinessAIWidget.open();

// Cerrar el widget
BusinessAIWidget.close();

// Enviar mensaje
BusinessAIWidget.sendMessage('Hola, necesito ayuda');

// Obtener configuración
const config = BusinessAIWidget.getConfig();

// Obtener session ID
const sessionId = BusinessAIWidget.getSessionId();
```

### Ejemplo: Abrir Widget al Hacer Clic en Botón

```html
<button onclick="BusinessAIWidget.open()">
  Abrir Chat
</button>
```

## 🔧 Integración con Backend

El widget se conecta automáticamente al endpoint:

```
POST /business-ai-support/chat
```

**Request:**
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

### Requisitos del Backend

1. **CORS habilitado** - El widget necesita hacer requests cross-origin
2. **Endpoint correcto** - Debe estar en `/business-ai-support/chat`
3. **Response JSON** - Debe incluir campo `text` con la respuesta

## 📱 Responsive Design

El widget es completamente responsive:

- **Desktop**: 380px de ancho, 600px de alto
- **Mobile**: Se adapta al ancho de la pantalla
- **Tablet**: Tamaño intermedio optimizado

No necesitas hacer nada especial, el widget se adapta automáticamente.

## 🐛 Troubleshooting

### El widget no aparece

1. Verifica que el script se carga: Abre DevTools → Network → busca `business-ai-widget.js`
2. Revisa la consola por errores JavaScript
3. Verifica que `apiUrl` es correcta y accesible

### No se envían mensajes

1. Verifica que el endpoint existe: `https://tu-dominio.com/business-ai-support/chat`
2. Revisa CORS en el backend (debe permitir requests desde tu dominio)
3. Abre DevTools → Network → busca el request POST y revisa la respuesta

### El widget se ve mal

1. Verifica que no hay CSS conflictivo en tu sitio
2. Ajusta el `zIndex` si hay elementos superpuestos
3. Revisa que el viewport meta tag está presente: `<meta name="viewport" content="width=device-width, initial-scale=1.0">`

## 🔒 Seguridad

- ✅ Compatible con HTTPS
- ✅ No almacena datos sensibles
- ✅ Session ID se genera automáticamente
- ✅ Usa fetch API estándar (sin jQuery ni otras dependencias)

## 📊 Testing

### Probar Localmente

1. Inicia tu servidor de Business AI Support en `http://localhost:7864`
2. Abre `quick-start.html` en tu navegador
3. El widget debería aparecer y funcionar

### Probar en Producción

1. Sube `business-ai-widget.js` a tu servidor
2. Agrega el código de embed a tu sitio
3. Verifica que el widget aparece y funciona

## 📝 Checklist de Integración

- [ ] Archivo `business-ai-widget.js` subido al servidor
- [ ] Código de embed agregado al HTML
- [ ] `apiUrl` configurada correctamente
- [ ] Backend con CORS habilitado
- [ ] Endpoint `/business-ai-support/chat` funcionando
- [ ] Widget probado en desktop
- [ ] Widget probado en mobile
- [ ] Personalización aplicada (colores, logo, etc.)

## 🚀 Próximos Pasos

Una vez integrado:

1. **Personaliza** los colores y logo para que coincida con tu marca
2. **Prueba** en diferentes dispositivos
3. **Monitorea** las conversaciones desde el dashboard
4. **Optimiza** el mensaje de bienvenida según tu audiencia

## 📞 Soporte

Si tienes problemas con la integración:

1. Revisa esta guía completa
2. Revisa `embed-example.html` para ver un ejemplo funcional
3. Revisa la consola del navegador por errores
4. Verifica que el backend está funcionando correctamente

---

**¡Listo para vender!** 🎉 El widget está completamente funcional y listo para producción.

