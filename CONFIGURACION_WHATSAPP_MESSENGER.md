# 💬 Configuración de WhatsApp y Messenger en el Widget

## ✅ Funcionalidad Implementada

Se han agregado botones de WhatsApp y Messenger **dentro del chatbot** de STAR AGENT. Los usuarios pueden elegir si prefieren continuar la conversación en WhatsApp o Messenger.

---

## 🔧 Atributos de Configuración

### Para WhatsApp:

```html
data-enable-whatsapp="true"           <!-- Activar botón de WhatsApp -->
data-whatsapp-number="+1234567890"    <!-- Tu número de WhatsApp Business (con código de país) -->
data-whatsapp-message="Hola, vi tu producto en tu website"  <!-- Mensaje predefinido (opcional) -->
```

### Para Messenger:

```html
data-enable-messenger="true"          <!-- Activar botón de Messenger -->
data-messenger-page="tu-pagina-facebook"  <!-- Nombre de tu página de Facebook (sin @ ni URL completa) -->
```

---

## 📝 Ejemplo Completo de Código

```html
<script src="http://127.0.0.1:7864/static/business-ai-widget.js?v=4" 
        data-api-url="http://127.0.0.1:7864"
        data-widget-id="tu-widget-id"
        data-brand-name="Tu Marca"
        data-primary-color="#007bff"
        data-position="bottom-right"
        data-welcome-message="👋 ¡Hola! Soy tu asistente virtual. ¿En qué puedo ayudarte hoy?"
        
        <!-- Configuración WhatsApp -->
        data-enable-whatsapp="true"
        data-whatsapp-number="+1234567890"
        data-whatsapp-message="Hola, vi tu producto en tu website y me interesa saber más"
        
        <!-- Configuración Messenger -->
        data-enable-messenger="true"
        data-messenger-page="tu-pagina-facebook"
        
        async></script>
```

---

## 📋 Guía de Configuración

### Paso 1: Configurar WhatsApp

1. **Obtén tu número de WhatsApp Business:**
   - Debe incluir código de país
   - Ejemplo: `+1234567890` (EE.UU.), `+521234567890` (México), `+34612345678` (España)

2. **Personaliza el mensaje (opcional):**
   - El mensaje se pre-llenará cuando el usuario haga click
   - Puede incluir cualquier texto personalizado
   - Se codificará automáticamente para la URL

3. **Agrega los atributos al script:**
   ```html
   data-enable-whatsapp="true"
   data-whatsapp-number="+TU_NUMERO"
   data-whatsapp-message="Tu mensaje personalizado"
   ```

### Paso 2: Configurar Messenger

1. **Obtén el nombre de tu página de Facebook:**
   - Ve a tu página de Facebook Business
   - El nombre es la parte después de `facebook.com/`
   - Ejemplo: Si tu URL es `facebook.com/mitienda`, usa `mitienda`
   - NO incluyas `@`, `facebook.com/`, ni `/` al final

2. **Agrega los atributos al script:**
   ```html
   data-enable-messenger="true"
   data-messenger-page="nombre-de-tu-pagina"
   ```

---

## 🎨 Cómo Funciona

### Experiencia del Usuario:

1. **El usuario abre el chatbot** haciendo click en el botón flotante
2. **Ve el mensaje de bienvenida** del asistente virtual
3. **Ve los botones** "Prefiero WhatsApp" y "Prefiero Messenger" (si están configurados)
4. **Si hace click en "Prefiero WhatsApp":**
   - Se abre WhatsApp (app o web)
   - Se abre un chat con tu número
   - El mensaje predefinido aparece listo para enviar
   - El usuario solo presiona "Enviar"

5. **Si hace click en "Prefiero Messenger":**
   - Se abre Messenger (app o web)
   - Se abre un chat directo con tu página de Facebook
   - El usuario puede empezar a chatear inmediatamente

---

## ⚙️ Opciones de Configuración

### Solo WhatsApp:
```html
data-enable-whatsapp="true"
data-whatsapp-number="+1234567890"
data-enable-messenger="false"
```

### Solo Messenger:
```html
data-enable-whatsapp="false"
data-enable-messenger="true"
data-messenger-page="tu-pagina"
```

### Ambos (Recomendado):
```html
data-enable-whatsapp="true"
data-whatsapp-number="+1234567890"
data-enable-messenger="true"
data-messenger-page="tu-pagina"
```

### Ninguno (Solo chat en website):
```html
data-enable-whatsapp="false"
data-enable-messenger="false"
```

---

## 🔍 Validación y Formato

### Número de WhatsApp:
- Se acepta cualquier formato, pero se limpiará automáticamente
- Ejemplos válidos:
  - `+1234567890`
  - `1234567890`
  - `+1 (234) 567-890`
- El widget extraerá solo los números para crear la URL correcta

### Página de Messenger:
- Se acepta cualquier formato, pero se limpiará automáticamente
- Ejemplos válidos:
  - `mitienda`
  - `@mitienda`
  - `facebook.com/mitienda`
  - `https://www.facebook.com/mitienda/`
- El widget extraerá solo el nombre de la página

---

## 🎯 Casos de Uso

### Caso 1: Tienda Online
```html
data-enable-whatsapp="true"
data-whatsapp-number="+1234567890"
data-whatsapp-message="Hola, vi este producto en tu website: [URL]"
```

### Caso 2: Servicios Profesionales
```html
data-enable-whatsapp="true"
data-whatsapp-number="+1234567890"
data-whatsapp-message="Hola, me interesa consultar sobre tus servicios"
```

### Caso 3: Soporte al Cliente
```html
data-enable-whatsapp="true"
data-whatsapp-number="+1234567890"
data-enable-messenger="true"
data-messenger-page="tuempresa-soporte"
```

---

## ✅ Estado Actual

- ✅ Botones agregados dentro del chatbot
- ✅ Configuración mediante atributos data-*
- ✅ Funcionalidad de redirección implementada
- ✅ Estilos CSS agregados
- ✅ Compatible con WhatsApp y Messenger
- ✅ Mensajes personalizables
- ✅ Validación y limpieza automática de formato

---

## 🚀 Próximos Pasos

1. **Configura tus números/páginas** en el código HTML
2. **Prueba los botones** haciendo click en ellos
3. **Personaliza los mensajes** según tu negocio
4. **Verifica** que las URLs se abran correctamente

---

¡Los botones están listos para usar! 🎉

