# 🧠 Guía Completa: Cómo Hacer que el Chatbot Use Datos Privados (RAG)

## ✅ RESPUESTA DIRECTA A TUS PREGUNTAS

### 1. ¿Estoy configurando correctamente desde Gradio?

**SÍ, estás configurando correctamente.** La forma correcta es:

1. **Configurar desde Gradio UI** (`app.py`) → Guarda la configuración en JSON
2. **Ejecutar el servidor** (`api_server.py`) → Carga automáticamente la configuración guardada

**NO necesitas ejecutar desde Gradio para que funcione.** La configuración se guarda en `docchat/business_ai_omnicanal/config/chatbot_config.json` y `api_server.py` la carga automáticamente en cada mensaje.

### 2. ¿Cómo lo hacen los profesionales?

Según las mejores prácticas de 2025 para RAG en empresas:

**Profesionales hacen:**
1. **Preparan documentos de calidad**: Catálogos, manuales, políticas, FAQs
2. **Los suben al sistema**: El sistema procesa (vectoriza) los documentos
3. **Configuran el agente**: Definen personalidad, tono, comportamientos
4. **Testean y ajustan**: Prueban con preguntas reales y refinan

**Tu sistema ya tiene esto implementado correctamente.**

### 3. ¿Cómo hacer que el chatbot use datos privados?

**PASO A PASO DETALLADO:**

## 📚 CÓMO CARGAR TUS DATOS PRIVADOS (RAG)

### **Paso 1: Preparar tus Documentos**

Prepara los documentos de tu empresa/persona:

**Tipos de documentos recomendados:**
- 📄 **Catálogo de productos** (PDF, DOCX)
- 📋 **Manuales de producto** (PDF)
- 📖 **Preguntas Frecuentes (FAQ)** (PDF, TXT, DOCX)
- 📝 **Políticas de devolución/garantía** (PDF, DOCX)
- 🎯 **Guía de objeciones y respuestas** (PDF, DOCX, TXT)
- 💼 **Manuales de ventas** (PDF)
- 🌐 **Contenido de tu website** (URLs)

**Ejemplos reales:**
- `catalogo-productos-2025.pdf`
- `politicas-devolucion.pdf`
- `manual-ventas-b2b.pdf`
- `faq-clientes.txt`
- `guia-objeciones-comunes.docx`

### **Paso 2: Configurar desde Gradio UI**

1. **Abre Gradio UI:**
   ```powershell
   py -3.12 app.py
   ```

2. **Ve al modo Business AI Omnicanal:**
   - Tab: "🤖 Business AI Omnicanal"
   - Sub-tab: "🎨 Configuración Completa del Chatbot"

3. **Ve al Tab "📚 RAG - Conocimiento del Negocio":**

   **a) Activa RAG:**
   - ✅ Marca el checkbox: "✅ Habilitar RAG (Retrieval-Augmented Generation)"

   **b) Sube tus documentos:**
   - Haz clic en "📄 Subir Documentos"
   - Selecciona tus archivos (PDF, DOCX, TXT, MD)
   - Puedes subir múltiples archivos a la vez

   **c) (Opcional) Agrega URLs:**
   - Si quieres que el chatbot aprenda de tu website
   - Pega URLs (una por línea):
     ```
     https://tu-empresa.com/manual-ventas
     https://tu-empresa.com/catalogo
     https://tu-empresa.com/politicas
     ```

   **d) Procesa los documentos:**
   - Haz clic en "🔄 Procesar Documentos y URLs"
   - Espera a que termine el procesamiento
   - Verás el estado: "✅ Documentos procesados correctamente"

4. **Configura las demás características:**
   - Tab 1: Personalización (Tono, Personalidad)
   - Tab 3: Lead Scoring
   - Tab 4: Handoff Humano
   - Tab 5: Idioma
   - Tab 6: Manejo de Objeciones
   - Tab 7: Agendamiento de Citas

5. **💾 GUARDA TODO:**
   - Haz clic en "💾 Guardar Configuración Completa"
   - Verás: "✅ Configuración guardada en: ..."

### **Paso 3: Ejecutar el Servidor API**

**Cierra Gradio** (opcional, no es necesario tenerlo abierto) y ejecuta:

```powershell
py -3.12 api_server.py
```

El servidor:
- ✅ Carga automáticamente la configuración guardada desde Gradio
- ✅ Carga los documentos procesados
- ✅ El chatbot recarga la configuración en cada mensaje

### **Paso 4: Probar el Chatbot**

Ahora el chatbot puede responder usando tus datos privados:

**Ejemplo de preguntas que puede responder:**
- "¿Cuál es tu política de devoluciones?" → Consulta tu PDF de políticas
- "¿Qué productos tienes disponibles?" → Consulta tu catálogo
- "¿Cómo funciona la garantía?" → Consulta tus manuales
- "¿Qué hago si el producto llega dañado?" → Consulta tus FAQs

## 🔄 CÓMO FUNCIONA EL "CEREBRO" DEL AGENTE (RAG)

### **Alimentación de Datos (Paso 1)**
```
Tus Documentos → Procesamiento → Base Vectorizada
```

**Lo que pasa internamente:**
1. El sistema lee tus documentos (PDFs, DOCX, TXT, etc.)
2. Divide los documentos en "chunks" (fragmentos) de 300-500 palabras
3. Convierte cada chunk en "embeddings" (vectores numéricos que representan el significado)
4. Guarda todo en una "base vectorizada" (base de datos de conocimientos)

**Ejemplo:**
- Tu PDF tiene 10 páginas
- Se divide en ~50 chunks
- Cada chunk se convierte en un vector
- Se guardan 50 vectores en la base

### **Procesamiento (Paso 2)**
Cuando un cliente hace una pregunta:

```
Pregunta del Cliente → Buscar en Base Vectorizada → Encontrar Chunks Relevantes → Generar Respuesta
```

**Lo que pasa internamente:**
1. El cliente pregunta: "¿Cuál es la política de devoluciones?"
2. El sistema convierte la pregunta en un vector
3. Busca en la base vectorizada los chunks más similares (más relevantes)
4. Encuentra 3-5 chunks que hablan de devoluciones
5. El LLM (Groq/OpenAI) lee esos chunks y genera una respuesta basada SOLO en esa información
6. El chatbot responde: "Según nuestros documentos, nuestra política de devoluciones permite..."

### **Ventajas del RAG:**
✅ **No alucina**: Solo usa información de tus documentos
✅ **Actualizable**: Puedes agregar nuevos documentos cuando quieras
✅ **Contextual**: Entiende el contexto de la conversación
✅ **Preciso**: Combina búsqueda semántica + keywords para mejor precisión

## 🎯 EJEMPLO REAL COMPLETO

### **Escenario: Tienda de Ropa**

**1. Documentos que subes:**
- `catalogo-ropa-2025.pdf` (500 productos con precios, tallas, colores)
- `politicas-devolucion.pdf` (30 días, condiciones, pasos)
- `guia-tallas.pdf` (cómo elegir talla correcta)
- `faq-pedidos.txt` (preguntas sobre envíos, tiempos, etc.)

**2. Configuración en Gradio:**
- Personalización: "Eres un asesor de moda experto..."
- RAG: ✅ Habilitado + 4 documentos subidos
- Lead Scoring: ✅ Habilitado
- Objeciones: Configuradas

**3. Cliente pregunta:**
> "¿Puedo devolver una camisa si no me queda bien?"

**4. El chatbot:**
1. Busca en la base vectorizada: encuentra información sobre devoluciones
2. Lee tus políticas: "30 días, sin usar, con etiqueta"
3. Genera respuesta: "Sí, puedes devolverla. Según nuestras políticas, tienes 30 días desde la compra. La prenda debe estar sin usar y con etiqueta. ¿Quieres que te ayude con el proceso?"

**5. El chatbot es proactivo:**
> "También tengo una guía de tallas. ¿Quieres que te ayude a elegir la talla correcta la próxima vez?"

## ✅ CHECKLIST COMPLETO

**Para que el chatbot use tus datos privados:**

- [ ] **Preparar documentos** (catálogo, políticas, FAQs, manuales)
- [ ] **Abrir Gradio** (`py -3.12 app.py`)
- [ ] **Ir a "🎨 Configuración Completa del Chatbot"**
- [ ] **Tab "📚 RAG":**
  - [ ] ✅ Activar checkbox "Habilitar RAG"
  - [ ] 📄 Subir documentos
  - [ ] 🔄 Hacer clic en "Procesar Documentos y URLs"
  - [ ] ✅ Verificar estado: "Documentos procesados correctamente"
- [ ] **Configurar otros tabs** (Personalización, Lead Scoring, etc.)
- [ ] **💾 Guardar configuración completa**
- [ ] **Cerrar Gradio** (opcional)
- [ ] **Ejecutar `api_server.py`** (`py -3.12 api_server.py`)
- [ ] **Probar el chatbot** con preguntas sobre tus documentos

## 🚀 CONFIGURACIÓN PROFESIONAL (Lo que hacen las empresas grandes)

Según las mejores prácticas de 2025:

### **1. Curar Documentos de Calidad**
- ✅ Documentos autorizados y actualizados
- ✅ Evitar información obsoleta o irrelevante
- ✅ Organizar por categorías (ventas, soporte, productos)

### **2. Procesamiento Inteligente**
- ✅ Chunking optimizado (300-500 tokens)
- ✅ Overlap entre chunks (para no perder contexto)
- ✅ Metadata (fuente, fecha, categoría)

### **3. Retrieval Híbrido**
- ✅ Búsqueda semántica (entender significado)
- ✅ Búsqueda por keywords (encontrar términos exactos)
- ✅ Reranking (ordenar resultados por relevancia)

### **4. Prompting Estratégico**
- ✅ Instrucciones claras: "Solo usa información de los documentos"
- ✅ Evitar alucinaciones
- ✅ Citar fuentes cuando sea necesario

### **5. Monitoreo y Mejora**
- ✅ Revisar respuestas incorrectas
- ✅ Agregar documentos faltantes
- ✅ Ajustar configuración según feedback

**Tu sistema ya tiene todo esto implementado.** Solo necesitas:
1. Subir tus documentos
2. Configurar desde Gradio
3. Ejecutar api_server.py
4. ¡Listo!

## 💡 TIPS PROFESIONALES

1. **Empieza con 2-3 documentos esenciales**
   - Catálogo de productos
   - FAQs básicas
   - Políticas principales

2. **Agrega documentos gradualmente**
   - Prueba el chatbot
   - Identifica qué falta
   - Agrega documentos según necesites

3. **Mantén documentos actualizados**
   - Si cambias políticas, actualiza el PDF
   - Reprocesa documentos cuando actualices

4. **Combina documentos + configuración**
   - Documentos = Conocimiento
   - Configuración = Personalidad y comportamiento
   - Ambos son importantes

5. **No necesitas ejecutar Gradio para usar el chatbot**
   - Configura desde Gradio
   - Guarda la configuración
   - Ejecuta solo api_server.py para servir el chatbot

## ❓ PREGUNTAS FRECUENTES

### ¿Tengo que ejecutar Gradio y api_server.py al mismo tiempo?

**NO.** 
- Gradio es solo para **configurar**
- api_server.py es para **servir el chatbot**
- Configuras una vez en Gradio, guardas, y luego usas api_server.py

### ¿La configuración se guarda automáticamente?

**Sí, cuando haces clic en "💾 Guardar Configuración Completa"**
- Se guarda en `docchat/business_ai_omnicanal/config/chatbot_config.json`
- `api_server.py` carga esta configuración automáticamente
- El chatbot recarga la configuración en cada mensaje (cambios son inmediatos)

### ¿Cómo sé si los documentos se procesaron correctamente?

Después de hacer clic en "🔄 Procesar Documentos y URLs", verás:
- ✅ "Documentos procesados correctamente" o
- ❌ Un error con detalles

### ¿Puedo agregar más documentos después?

**Sí, en cualquier momento:**
1. Abre Gradio
2. Ve al tab "📚 RAG"
3. Sube más documentos
4. Haz clic en "🔄 Procesar Documentos y URLs"
5. Guarda la configuración
6. El chatbot usará los nuevos documentos automáticamente

### ¿Los documentos se comparten entre diferentes usuarios del chatbot?

**No, cada configuración es independiente.**
- Si tienes múltiples clientes/empresas, cada uno tiene su propia configuración
- Los documentos están asociados a la configuración guardada
- Puedes tener múltiples configuraciones (guardadas en JSON diferentes)

## 🎉 RESUMEN FINAL

**Para que el chatbot use tus datos privados:**

1. ✅ **Prepara documentos** (PDFs, DOCX, TXT, MD)
2. ✅ **Configura desde Gradio** → Tab "📚 RAG" → Sube documentos → Procesa
3. ✅ **Guarda la configuración**
4. ✅ **Ejecuta api_server.py** (no necesitas Gradio corriendo)
5. ✅ **El chatbot ahora usa tus datos privados automáticamente**

**¡Es así de fácil!** 🚀


