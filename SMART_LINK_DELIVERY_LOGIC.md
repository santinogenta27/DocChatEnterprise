# Smart Link Delivery Logic (Sales AI Agent)

## 🎯 Principio Clave

**Los links aparecen solo cuando el usuario está listo para actuar.**

---

## ✅ Cuándo Se Incluyen Links

### 1. Intención de Compra Detectada
- Palabras clave: `"quiero"`, `"comprar"`, `"me interesa"`, `"dame"`, `"necesito comprar"`
- Frases: `"precio de"`, `"cuánto cuesta"`, `"agregar al carrito"`, `"añadir"`

### 2. Etapas READY o CLOSING
- Usuario está listo para comprar
- Muestra intención clara de transacción
- Etapa del funnel indica decisión inminente

### 3. Preguntas Específicas de Producto en CONSIDERATION
- Usuario pregunta específicamente por un producto: `"este producto"`, `"ese producto"`
- Está evaluando características de un producto específico
- Muestra interés focalizado

---

## ❌ Cuándo NO Se Incluyen Links

### 1. Exploración Temprana (INTEREST)
- Usuario solo está viendo opciones
- No muestra intención de compra clara
- Etapa inicial del funnel

### 2. Consultas Generales Sin Intención de Compra
- Palabras clave: `"qué tienen"`, `"qué venden"`, `"muéstrame"`, `"catálogo"`, `"listado"`
- Preguntas exploratorias sin intención de acción
- Solo busca información general

---

## 🔧 Cómo Funciona

### 1. Detección de Intención Basada en Contexto y Señales Lingüísticas

```python
def _should_include_product_links(self, sales_stage: str, intent: str, state: Dict[str, Any]) -> bool:
    """
    Determina si debe incluir links de productos en la respuesta.
    
    Analiza:
    - Etapa de venta (INTEREST, CONSIDERATION, READY, CLOSING)
    - Último mensaje del usuario para palabras clave
    - Intención detectada
    """
    # Etapas donde SIEMPRE incluir links
    if sales_stage in ["ready", "closing"]:
        return True
    
    # Analizar mensaje del usuario
    last_user_message = get_last_user_message(state)
    
    # Palabras que indican intención de compra -> INCLUIR LINKS
    purchase_keywords = ["quiero", "comprar", "me interesa", "dame", "necesito comprar", ...]
    if any(keyword in last_user_message for keyword in purchase_keywords):
        return True
    
    # Palabras que indican solo exploración -> NO INCLUIR LINKS
    exploration_keywords = ["qué tienen", "qué venden", "muéstrame", "catálogo", ...]
    if any(keyword in last_user_message for keyword in exploration_keywords):
        return False
    
    # CONSIDERATION: Solo si pregunta específicamente por un producto
    if sales_stage == "consideration":
        if any(word in last_user_message for word in ["este", "ese", "ese producto"]):
            return True
        return False
    
    # INTEREST: NO incluir links por defecto
    return False
```

---

### 2. Evaluación de Etapa de Venta

El sistema detecta la etapa de venta usando `Sales Closer Elite`:

- **INTEREST**: Exploración inicial
- **CONSIDERATION**: Evaluando opciones
- **READY**: Listo para comprar
- **CLOSING**: Proceso de compra activo

---

### 3. Decisión Centralizada vía `_should_include_product_links()`

Función única que centraliza toda la lógica de decisión:

```python
should_include_links = self._should_include_product_links(
    sales_stage=sales_stage,
    intent=intent,
    state=state
)
```

Esta decisión se usa consistentemente en todos los nodos.

---

### 4. Integración Consistente en Todos los Nodos de Respuesta

#### Nodo de Observación (`_observe_node`)
```python
should_include_links = self._should_include_product_links(sales_stage, intent, state)
observation_context = self._build_observation_context(tool_results, include_links=should_include_links)
```

#### Nodo de Cierre (`_close_node`)
```python
should_include_links = self._should_include_product_links(sales_stage, intent, state)
close_prompt = self._build_close_prompt(..., state=state)
```

#### Prompt de Pensamiento (`_think_node`)
```python
# Instrucciones preventivas sobre cuándo NO incluir links
"NO incluyas links cuando el usuario solo está explorando..."
```

---

## 📊 Impacto

### ✅ Menos Fricción
- Usuario no se siente presionado cuando solo explora
- Links aparecen cuando realmente los necesita
- Experiencia más natural y menos intrusiva

### ✅ Mayor Conversión
- Links aparecen en el momento óptimo (cuando está listo para comprar)
- Reduce fricción en el proceso de compra
- Aumenta la probabilidad de click-through

### ✅ Experiencia Natural Tipo Vendedor Humano
- Actúa como un vendedor experimentado
- Primero muestra opciones, luego links cuando hay interés
- Respeta el ritmo natural del cliente

### ✅ Links Solo Cuando Aportan Valor
- No satura con información innecesaria
- Cada link tiene propósito claro
- Aumenta la confianza del usuario

---

## 📋 Flujo de Decisión

```
Usuario envía mensaje
    ↓
Detectar etapa de venta (INTEREST/CONSIDERATION/READY/CLOSING)
    ↓
Analizar palabras clave del mensaje
    ↓
Determinar intención (compra vs exploración)
    ↓
_should_include_product_links() → True/False
    ↓
Generar respuesta con o sin links
```

---

## 🎯 Ejemplos Prácticos

### Ejemplo 1: Exploración (NO incluye links)
**Usuario:** "¿Qué tienen?"
**Etapa:** INTEREST
**Decisión:** ❌ NO incluir links
**Respuesta:**
```
Tenemos zapatillas deportivas, ropa, accesorios...
- Zapatilla X - $99
- Zapatilla Y - $129
¿Te interesa alguna en particular?
```

---

### Ejemplo 2: Intención de Compra (SÍ incluye links)
**Usuario:** "Quiero comprar zapatillas deportivas"
**Etapa:** READY
**Decisión:** ✅ SÍ incluir links
**Respuesta:**
```
¡Perfecto! Te muestro nuestras zapatillas:

- Zapatilla Deportiva X - $99 [Ver producto](https://tienda.com/products/x)
- Zapatilla Running Y - $129 [Ver producto](https://tienda.com/products/y)

¿Cuál te interesa más?
```

---

### Ejemplo 3: Pregunta Específica (SÍ incluye links)
**Usuario:** "¿Cuánto cuesta la zapatilla X?"
**Etapa:** READY
**Decisión:** ✅ SÍ incluir links
**Respuesta:**
```
La Zapatilla X cuesta $99.

[Ver producto](https://tienda.com/products/x)

¿Te gustaría agregarla al carrito?
```

---

## ✅ Estado de Implementación

**COMPLETAMENTE IMPLEMENTADO:**

✅ Función `_should_include_product_links()` con lógica completa  
✅ Detección de intención basada en palabras clave  
✅ Evaluación de etapa de venta integrada  
✅ Integración en `_observe_node()`  
✅ Integración en `_close_node()`  
✅ Instrucciones preventivas en `_think_node()`  
✅ Prompts optimizados con instrucciones claras  
✅ Respeta todas las etapas del funnel  

---

## 🚀 Resultado Final

El agente ahora implementa **Smart Link Delivery Logic** de forma completa y consistente:

- 🎯 Links solo cuando el usuario está listo para actuar
- 🧠 Decisión inteligente basada en contexto y señales
- 📈 Mayor conversión con menor fricción
- 🤝 Experiencia natural tipo vendedor humano

**El mejor producto del mundo está listo.** ⭐

