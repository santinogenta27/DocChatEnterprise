# ✅ Sistema de 3 Capas Obligatorias para Links Configurados

## 🎯 Implementación Completa

### 📋 CAPA 1: Detección de INTENCIÓN

**Archivo:** `docchat/star_agent/config/intent_link_mapper.py`

**Clase:** `IntentLinkMapper`

**Método:** `detect_intent(message, sales_stage)`

**Intenciones detectadas:**
- `browse_products` - "Quiero ver zapatillas"
- `price_inquiry` - "¿Cuánto cuestan?"
- `purchase_intent` - "Quiero comprar"
- `go_to_checkout` - "Quiero pagar ahora"
- `payment_info` - "¿Qué métodos de pago aceptan?"
- `shipping_info` - "¿Hacen envíos?"
- `returns_info` - "¿Puedo devolver?"
- `support` - "Necesito ayuda"
- `faq` - Preguntas frecuentes
- `contact` - "Quiero contactar"
- `general` - Sin intención específica

**Ejemplo:**
```python
mapper = IntentLinkMapper()
intent = mapper.detect_intent("Quiero ver zapatillas", "interest")
# Retorna: UserIntent.BROWSE_PRODUCTS
```

---

### 📋 CAPA 2: Mapeo INTENCIÓN → TIPO DE LINK

**Archivo:** `docchat/star_agent/config/intent_link_mapper.py`

**Constante:** `INTENT_TO_LINK_TYPE`

**Mapeo:**
```python
INTENT_TO_LINK_TYPE = {
    UserIntent.BROWSE_PRODUCTS: LinkType.CATALOG,
    UserIntent.PRICE_INQUIRY: LinkType.PRODUCT,  # Generado dinámicamente
    UserIntent.PURCHASE_INTENT: LinkType.PRODUCT,  # Generado dinámicamente
    UserIntent.GO_TO_CHECKOUT: LinkType.CHECKOUT,
    UserIntent.PAYMENT_INFO: LinkType.PAYMENT_METHODS,
    UserIntent.SHIPPING_INFO: LinkType.SHIPPING,
    UserIntent.RETURNS_INFO: LinkType.RETURNS,
    UserIntent.SUPPORT: LinkType.SUPPORT,
    UserIntent.FAQ: LinkType.FAQ,
    UserIntent.CONTACT: LinkType.CONTACT,
    UserIntent.GENERAL: LinkType.STORE,
}
```

**Método:** `get_link_type_for_intent(intent)`

**Ejemplo:**
```python
link_type = mapper.get_link_type_for_intent(UserIntent.BROWSE_PRODUCTS)
# Retorna: LinkType.CATALOG
```

---

### 📋 CAPA 3: Gate de CUÁNDO Enviar

**Archivo:** `docchat/star_agent/config/intent_link_mapper.py`

**Método:** `should_include_link(intent, sales_stage)`

**Reglas:**
- `GENERAL` sin intención clara → NO enviar link
- `BROWSE_PRODUCTS` → SIEMPRE enviar link al catálogo
- `READY/CLOSING` → SÍ enviar links relevantes
- Intenciones específicas (checkout, payment, shipping, etc.) → SÍ enviar

---

## 🔧 Integración en LinksManager

**Archivo:** `docchat/star_agent/config/links_manager.py`

**Métodos nuevos:**

1. **`get_link_for_intent(intent, sales_stage)`**
   - Aplica las 3 capas
   - Retorna URL del link o None

2. **`format_link_for_intent(intent, sales_stage, label)`**
   - Formatea link en Markdown
   - Retorna: `[Texto](url)`

3. **`get_relevant_links_for_query(query, sales_stage)`** (mejorado)
   - Usa sistema de 3 capas
   - Detecta intención → mapea → aplica gate

---

## 🎯 Integración en ReactSalesAgent

**Archivo:** `docchat/star_agent/agents/react_sales_agent.py`

### 1. En `_think_node()`:

```python
# CAPA 1+2+3: Detectar intención y obtener link correcto
user_intent = self.links_manager.intent_mapper.detect_intent(user_query, sales_stage)
link_for_intent = self.links_manager.format_link_for_intent(user_intent, sales_stage)

# Agregar a contexto
if link_for_intent:
    links_context = f"🔗 LINK OBLIGATORIO para incluir: {link_for_intent}"
```

### 2. En `_observe_node()`:

```python
# CAPA 1+2+3: Detectar intención y obtener link correcto
user_intent = self.links_manager.intent_mapper.detect_intent(last_user_message, sales_stage)
link_for_intent = self.links_manager.format_link_for_intent(user_intent, sales_stage)

# Agregar a contexto de observación
if link_for_intent:
    observation_context += f"\n\n🔗 LINK OBLIGATORIO: {link_for_intent}"
```

### 3. En `_close_node()`:

```python
# CAPA 1+2+3: Detectar intención y obtener link correcto
user_intent = self.links_manager.intent_mapper.detect_intent(last_user_message, sales_stage)
link_for_intent = self.links_manager.format_link_for_intent(user_intent, sales_stage)

# Agregar a prompt
if link_for_intent:
    links_context = f"🔗 LINK OBLIGATORIO: {link_for_intent}"
```

### 4. En `_act_node()` (search_products):

```python
# IMPORTANTE: Si pregunta por productos, también incluir link al catálogo
if user_intent == UserIntent.BROWSE_PRODUCTS:
    catalog_link = self.links_manager.get_link(LinkType.CATALOG.value)
    if catalog_link:
        executed_tools["catalog_link"] = catalog_link
```

---

## 📊 Ejemplos de Uso

### Ejemplo 1: Usuario pregunta por productos

**Usuario:** "Quiero ver zapatillas"

**CAPA 1:** Detecta `BROWSE_PRODUCTS`

**CAPA 2:** Mapea a `LinkType.CATALOG`

**CAPA 3:** `should_include_link()` → `True`

**Resultado:**
- Agente busca productos
- Encuentra zapatillas
- **INCLUYE link al catálogo**: `[Ver catálogo](https://tu-tienda.com/productos)`

**Respuesta:**
```
Tenemos estas zapatillas:
- Zapatilla X - $99
- Zapatilla Y - $129

[Ver catálogo completo](https://tu-tienda.com/productos)
```

---

### Ejemplo 2: Usuario quiere pagar

**Usuario:** "Quiero pagar ahora"

**CAPA 1:** Detecta `GO_TO_CHECKOUT`

**CAPA 2:** Mapea a `LinkType.CHECKOUT`

**CAPA 3:** `should_include_link()` → `True`

**Resultado:**
- **INCLUYE link al checkout**: `[Ir al checkout](https://tu-tienda.com/checkout)`

**Respuesta:**
```
Perfecto, puedes proceder al pago.

[Ir al checkout](https://tu-tienda.com/checkout)
```

---

### Ejemplo 3: Usuario pregunta por envíos

**Usuario:** "¿Hacen envíos?"

**CAPA 1:** Detecta `SHIPPING_INFO`

**CAPA 2:** Mapea a `LinkType.SHIPPING`

**CAPA 3:** `should_include_link()` → `True`

**Resultado:**
- **INCLUYE link de info de envíos**: `[Ver info de envíos](https://tu-tienda.com/envios)`

**Respuesta:**
```
Sí, hacemos envíos a todo el país.

[Ver información completa de envíos](https://tu-tienda.com/envios)
```

---

## ✅ Instrucciones en Prompts

**Agregadas en TODOS los prompts:**

```
**Instrucciones CRÍTICAS sobre LINKS (OBLIGATORIO):**
- Si hay "🔗 LINK OBLIGATORIO" en el contexto, DEBES incluirlo en tu respuesta.
- Los links son el 90% del producto - SIEMPRE inclúyelos cuando están disponibles.
- Formato: [Texto del link](url) en Markdown.
- NO elijas links al azar - usa SOLO los links proporcionados.
```

---

## 🎯 Casos Especiales

### Cuando pregunta por productos específicos:

**Usuario:** "¿Cuánto cuesta la zapatilla X?"

**CAPA 1:** Detecta `PRICE_INQUIRY`

**CAPA 2:** Mapea a `LinkType.PRODUCT` (generado dinámicamente)

**CAPA 3:** `should_include_link()` → `True`

**Resultado:**
- Agente busca producto
- Genera link dinámico: `https://tu-tienda.com/products/zapatilla-x`
- **INCLUYE link al producto**

**Respuesta:**
```
La Zapatilla X cuesta $99.

[Ver producto](https://tu-tienda.com/products/zapatilla-x)
```

---

## ✅ Estado Final

**TODO IMPLEMENTADO:**

✅ CAPA 1: Detección de intención (IntentLinkMapper)  
✅ CAPA 2: Mapeo INTENCIÓN → TIPO DE LINK  
✅ CAPA 3: Gate de CUÁNDO enviar  
✅ LinksManager integrado con sistema de 3 capas  
✅ ReactSalesAgent usa sistema en todos los nodos  
✅ Links se incluyen como "🔗 LINK OBLIGATORIO" en prompts  
✅ Cuando pregunta por productos, también recibe link al catálogo  
✅ Instrucciones claras: "Los links son el 90% del producto"  

**El sistema está completo y funcional.** 🚀

