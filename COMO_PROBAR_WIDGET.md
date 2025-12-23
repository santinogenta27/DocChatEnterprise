# 🚀 CÓMO PROBAR EL WIDGET EN TU WEBSITE

**Fecha:** 2025-12-18  
**Guía rápida para probar el Business AI Widget**

---

## ✅ **PASO 1: INICIAR EL SERVIDOR**

Asegúrate de que tu servidor esté corriendo:

```bash
# Opción 1: Con app.py (Gradio completo)
python app.py

# Opción 2: Con api_server.py (Solo API)
python api_server.py
```

El servidor debe estar en: `http://localhost:7864`

**Verifica que funcione:**
- Abre: http://localhost:7864
- Debe mostrar la interfaz de Gradio o la API funcionando

---

## ✅ **PASO 2: ABRIR EL ARCHIVO HTML DE PRUEBA**

### **Opción A: Usar el archivo de prueba (MÁS FÁCIL)**

1. He creado `test_widget.html` en la raíz del proyecto
2. Abre este archivo en tu navegador:
   - Doble click en `test_widget.html`
   - O arrastra el archivo a tu navegador
   - O click derecho → "Abrir con" → Navegador

3. El widget debería aparecer automáticamente en la esquina inferior derecha

### **Opción B: Crear tu propio HTML**

Crea un archivo HTML con este contenido mínimo:

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Mi Website con Chatbot</title>
</head>
<body>
    <h1>Mi Website</h1>
    <p>El widget aparecerá automáticamente en la esquina.</p>

    <!-- WIDGET CODE - Pega aquí el código que generaste -->
    <script src="http://localhost:7864/static/business-ai-widget.js" 
            data-api-url="http://localhost:7864"
            data-widget-id="alien"
            data-brand-name="x"
            data-primary-color="#007bff"
            data-position="bottom-right"
            data-welcome-message="👋 ¡Hola! Soy tu asistente virtual. ¿En qué puedo ayudarte hoy?"
            async></script>
</body>
</html>
```

Guarda como `mi_website.html` y ábrelo en tu navegador.

---

## ✅ **PASO 3: VERIFICAR QUE EL WIDGET FUNCIONE**

### **Lo que deberías ver:**

1. ✅ Un botón flotante en la esquina inferior derecha (o izquierda, según configuraste)
2. ✅ El color que configuraste (#007bff por defecto = azul)
3. ✅ Al hacer click, se abre una ventana de chat

### **Si NO aparece el widget:**

1. **Abre la consola del navegador (F12)**
   - Ve a la pestaña "Console"
   - Busca errores en rojo
   
2. **Verifica que el servidor esté corriendo:**
   ```bash
   # Abre en el navegador:
   http://localhost:7864/static/business-ai-widget.js
   
   # Debe mostrar código JavaScript (no error 404)
   ```

3. **Verifica CORS (si usas una URL diferente a localhost):**
   - El servidor ya tiene CORS habilitado en `api_server.py`
   - Si aún hay problemas, revisa la consola

4. **Verifica que el archivo JS exista:**
   - Debe estar en: `docchat/static/business-ai-widget.js`
   - Si no existe, verifica la estructura de carpetas

---

## 🧪 **PROBAR EL CHATBOT**

Una vez que el widget aparezca, prueba estos mensajes:

### **Mensajes de Prueba:**

1. **Búsqueda de productos:**
   ```
   ¿Tienen zapatillas Nike talla 42?
   ```

2. **Recomendaciones:**
   ```
   ¿Qué productos me recomiendan para hacer ejercicio?
   ```

3. **Carrito:**
   ```
   Agrega las Nike al carrito
   ```

4. **Soporte:**
   ```
   ¿Cómo puedo hacer una devolución?
   ```

5. **Imágenes:**
   - Haz click en el botón de adjuntar (si está disponible)
   - O pega una imagen en el chat

---

## 📋 **PARA USAR EN PRODUCCIÓN (Website Real)**

Cuando quieras ponerlo en tu website real:

### **1. Cambia la URL:**

En lugar de `http://localhost:7864`, usa tu URL pública:

```html
<script src="https://tu-servidor.com/static/business-ai-widget.js" 
        data-api-url="https://tu-servidor.com"
        ...>
</script>
```

### **2. Pega el código antes de `</body>`:**

```html
<!DOCTYPE html>
<html>
<head>
    <!-- Tu head -->
</head>
<body>
    <!-- Tu contenido -->
    
    <!-- WIDGET - Siempre antes de </body> -->
    <script src="https://tu-servidor.com/static/business-ai-widget.js" 
            data-api-url="https://tu-servidor.com"
            data-widget-id="tu_widget_id"
            data-brand-name="Tu Marca"
            data-primary-color="#007bff"
            data-position="bottom-right"
            data-welcome-message="👋 ¡Hola! ¿En qué puedo ayudarte?"
            async></script>
</body>
</html>
```

### **3. Requisitos para Producción:**

- ✅ Servidor corriendo 24/7 (VPS o Cloud Hosting)
- ✅ URL pública con HTTPS (recomendado)
- ✅ CORS configurado (ya está hecho)
- ✅ API Keys configuradas (OPENAI_API_KEY o GROQ_API_KEY)

---

## 🐛 **SOLUCIÓN DE PROBLEMAS**

### **Problema: Widget no aparece**

**Solución:**
1. Verifica que el servidor esté corriendo
2. Abre la consola del navegador (F12) y busca errores
3. Verifica que `http://localhost:7864/static/business-ai-widget.js` sea accesible
4. Asegúrate de que el código esté antes de `</body>`

### **Problema: Error 404 en widget.js**

**Solución:**
- Verifica que el archivo exista: `docchat/static/business-ai-widget.js`
- Si no existe, verifica que se haya creado correctamente

### **Problema: CORS Error**

**Solución:**
- El servidor ya tiene CORS habilitado
- Si usas `localhost`, no debería haber problemas
- Si usas otra URL, verifica que esté en los orígenes permitidos

### **Problema: El chat no responde**

**Solución:**
1. Verifica que la API esté funcionando:
   ```
   POST http://localhost:7864/business-ai/chat
   ```
2. Verifica que tengas API keys configuradas (OPENAI_API_KEY o GROQ_API_KEY)
3. Revisa los logs del servidor para ver errores

---

## ✅ **VERIFICACIÓN RÁPIDA**

Checklist para asegurar que todo funciona:

- [ ] Servidor corriendo en `http://localhost:7864`
- [ ] `test_widget.html` abierto en el navegador
- [ ] Widget aparece como botón flotante
- [ ] Al hacer click, se abre el chat
- [ ] Puedo escribir mensajes
- [ ] El chatbot responde
- [ ] No hay errores en la consola (F12)

---

## 🎉 **¡LISTO!**

Si todo funciona, ya puedes usar el widget en cualquier website simplemente pegando el código antes de `</body>`.

---

**✅ GUÍA COMPLETA - LISTO PARA PROBAR**
















