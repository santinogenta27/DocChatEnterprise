# 🎨 CÓMO CONFIGURAR EL CHATBOT - Guía Completa para Clientes

## ✅ **ERROR CORREGIDO**

El error `'ProductSearchResult' object is not iterable` ha sido **corregido**. Ahora el chatbot debería responder correctamente a preguntas sobre productos.

---

## 🎯 **¿QUÉ PUEDE CONFIGURAR EL CLIENTE?**

Sí, **el cliente puede configurar el chatbot completamente** a través de varios métodos:

### 1. **📋 CONFIGURACIÓN BÁSICA (Widget HTML)**

Al generar el código del widget, puedes configurar:

```html
<script src="http://tu-servidor/static/business-ai-widget.js" 
        data-api-url="http://tu-servidor"
        data-widget-id="tu-widget-id"
        data-brand-name="Nombre de tu Marca"           <!-- ✨ Nombre que aparece -->
        data-primary-color="#007bff"                   <!-- 🎨 Color principal -->
        data-position="bottom-right"                   <!-- 📍 Posición del widget -->
        data-welcome-message="👋 ¡Hola! ¿En qué puedo ayudarte?"  <!-- 💬 Mensaje inicial -->
        async></script>
```

**Dónde configurarlo:**
- En Gradio: `http://localhost:7864` → "🤖 Business AI Omnicanal" → "🔧 Generar Código"

---

### 2. **⚙️ CONFIGURACIÓN AVANZADA (Código Python)**

#### **A. Nombre de la Marca**

El chatbot usa `BusinessAIConfig` para configurar el nombre de la marca:

```python
from docchat.business_ai_omnicanal.business_ai_mode import BusinessAIMode

# Al inicializar BusinessAIMode, puedes pasar configuración personalizada
business_ai = BusinessAIMode()

# El nombre de la marca se toma de:
# 1. AppConfig.app_name (si existe)
# 2. BusinessAIConfig.brand_name (por defecto: "Your Brand")
```

**Para cambiar el nombre de la marca:**

**Opción 1: Variable de entorno**
```bash
# En .env
APP_NAME=Mi Empresa
```

**Opción 2: Modificar config.py**
Edita `docchat/config.py` y cambia:
```python
app_name: str = "Tu Marca Aquí"
```

---

#### **B. Personalidad y Tono del Chatbot**

El chatbot actualmente usa un prompt del sistema que incluye el nombre de la marca. Para personalizar el **tono, personalidad y comportamiento**, puedes:

**Opción 1: Modificar el prompt del sistema (Recomendado para personalización profunda)**

Edita `docchat/business_ai_omnicanal/agents/business_ai_agent.py` y busca la función `_build_system_prompt` (aproximadamente línea 135):

```python
def _build_system_prompt(self) -> str:
    brand = self.config.brand_name if self.config else "Your Brand"
    return f"""Eres un agente de {brand}, especializado en ventas y soporte al cliente.

# AQUÍ PUEDES PERSONALIZAR:
- Tono: Amigable, profesional, casual, formal
- Personalidad: Empático, técnico, entusiasta, relajado
- Estilo de respuesta: Corto, detallado, conversacional
- Valores de la marca: Lo que tu marca representa

OBJETIVOS:
1. Ayudar al cliente a encontrar productos
2. Responder preguntas de soporte
3. Cerrar ventas de manera natural
4. Detectar cuando necesita ayuda humana

# EJEMPLO DE PERSONALIZACIÓN:
Tono: "Eres amigable y cercano, como un amigo que conoce bien los productos"
Personalidad: "Eres entusiasta sobre nuestros productos pero nunca presionador"
Valores: "Priorizas la satisfacción del cliente sobre cerrar ventas rápidas"
"""
```

---

**Opción 2: Usar variables de entorno (✅ YA IMPLEMENTADO)**

Ahora puedes agregar al archivo `.env` y funcionará automáticamente:

```env
# Personalidad del chatbot (Business AI Omnicanal)
DOCCHAT_CHATBOT_TONE=friendly                    # friendly, professional, casual, formal, enthusiastic
DOCCHAT_CHATBOT_PERSONALITY=Entusiasta pero no presionador, prioriza ayudar al cliente  # Descripción libre
DOCCHAT_CHATBOT_CUSTOM_INSTRUCTIONS=            # Instrucciones adicionales (opcional)
```

**Ejemplos de tonos:**
- `friendly`: Amigable y cercano, como un amigo
- `professional`: Profesional pero accesible
- `casual`: Relajado y conversacional
- `formal`: Formal y respetuoso
- `enthusiastic`: Entusiasta y energético

**Ejemplo de personalidad:**
```
DOCCHAT_CHATBOT_PERSONALITY=Entusiasta sobre nuestros productos pero nunca presionador. Priorizas la satisfacción del cliente sobre cerrar ventas rápidas. Eres experto pero hablas de manera simple y accesible.
```

**Ejemplo de instrucciones personalizadas:**
```
DOCCHAT_CHATBOT_CUSTOM_INSTRUCTIONS=Siempre menciona que tenemos envío gratis en compras mayores a $50. Si el cliente pregunta por devoluciones, menciona que tenemos política de devolución de 30 días sin preguntas.
```

---

### 3. **📚 CONFIGURACIÓN DEL CATÁLOGO DE PRODUCTOS**

El cliente puede configurar qué productos aparecen:

**Archivo:** `.env`
```env
# Ruta al catálogo de productos (SQLite)
PRODUCT_CATALOG_DB=./data/products.db
```

O programáticamente cuando se inicializa `ProductCatalog`:
```python
from docchat.commerce.product_catalog import ProductCatalog

catalog = ProductCatalog(db_path="./tu-catalogo.db")
```

---

### 4. **🌐 IDIOMA DEL CHATBOT**

El chatbot detecta el idioma del mensaje, pero puedes forzar un idioma:

**En el widget:**
```html
<script ... data-language="es"></script>
```

**En la configuración:**
```python
# En BusinessAIConfig
config = BusinessAIConfig(
    brand_name="Mi Marca",
    language="es"  # es, en, pt, fr, etc.
)
```

---

### 5. **🎨 APARIENCIA DEL WIDGET**

Todas estas opciones se configuran al generar el código HTML:

- **`data-brand-name`**: Nombre que aparece en el header del chat
- **`data-primary-color`**: Color hexadecimal para botones y acentos
- **`data-position`**: `bottom-right`, `bottom-left` (donde aparece el widget)
- **`data-welcome-message`**: Mensaje que ve el usuario al abrir el chat

---

## 🔧 **IMPLEMENTACIÓN RECOMENDADA PARA CLIENTES**

### **Para Personalización Básica (Sin tocar código):**
1. Usa la UI de Gradio para generar el widget con tu marca, color y mensaje
2. Configura `APP_NAME` en `.env` para cambiar el nombre interno
3. Usa el catálogo de productos por defecto o reemplázalo

### **Para Personalización Avanzada (Requiere código):**
1. Modifica `_build_system_prompt()` en `business_ai_agent.py`
2. Agrega variables de entorno para configuración dinámica
3. Crea múltiples instancias con diferentes personalidades según necesidad

---

## 📋 **EJEMPLO COMPLETO DE CONFIGURACIÓN**

```python
# ejemplo_configurar_chatbot.py

from docchat.business_ai_omnicanal.business_ai_mode import BusinessAIMode
from docchat.business_ai_omnicanal.agents.business_ai_agent import BusinessAIConfig

# 1. Configurar personalidad
custom_config = BusinessAIConfig(
    brand_name="Mi Tienda Online",
    language="es"
)

# 2. Inicializar Business AI con configuración
business_ai = BusinessAIMode()

# 3. El sistema usará automáticamente:
# - Nombre de marca: "Mi Tienda Online"
# - Idioma: Español
# - Tono: Definido en _build_system_prompt()
```

---

## 🚀 **PRÓXIMOS PASOS SUGERIDOS**

Para hacer el chatbot **completamente configurable sin código**, podrías:

1. **Agregar UI en Gradio** para personalizar:
   - Tono (dropdown: friendly, professional, casual, formal)
   - Personalidad (texto libre)
   - Mensaje de bienvenida personalizado
   - Valores de marca

2. **Guardar configuración en .env** o base de datos

3. **Cargar configuración dinámicamente** en `BusinessAIAgent`

---

## ✅ **RESUMEN**

**Sí, el cliente puede configurar:**
- ✅ Nombre de marca (`.env` → `APP_NAME` o UI de Gradio)
- ✅ Colores y apariencia del widget (UI de Gradio)
- ✅ Mensaje de bienvenida (UI de Gradio)
- ✅ Posición del widget (UI de Gradio)
- ✅ Idioma (`.env` → `DOCCHAT_CHATBOT_LANGUAGE` o código)
- ✅ **Tono del chatbot** (`.env` → `DOCCHAT_CHATBOT_TONE`) - **✅ YA IMPLEMENTADO**
- ✅ **Personalidad del chatbot** (`.env` → `DOCCHAT_CHATBOT_PERSONALITY`) - **✅ YA IMPLEMENTADO**
- ✅ **Instrucciones personalizadas** (`.env` → `DOCCHAT_CHATBOT_CUSTOM_INSTRUCTIONS`) - **✅ YA IMPLEMENTADO**

**El error de productos está corregido.** Reinicia el servidor y prueba nuevamente.

---

## 🚀 **EJEMPLO RÁPIDO DE CONFIGURACIÓN**

1. **Edita `.env`:**
```env
APP_NAME=Mi Tienda Online
DOCCHAT_CHATBOT_TONE=enthusiastic
DOCCHAT_CHATBOT_PERSONALITY=Entusiasta pero respetuoso. Priorizas ayudar al cliente a encontrar lo mejor para ellos.
DOCCHAT_CHATBOT_CUSTOM_INSTRUCTIONS=Siempre menciona nuestros beneficios: envío gratis en compras mayores a $50 y garantía de 30 días.
```

2. **Reinicia el servidor:**
```bash
python api_server.py
```

3. **¡Listo!** El chatbot ahora usará tu personalización automáticamente.












