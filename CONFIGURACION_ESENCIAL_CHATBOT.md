# 🎯 Configuración Esencial del Chatbot - Guía Priorizada

## ✅ LO MÁS IMPORTANTE (Configuración Mínima para que Funcione Bien)

### 1. 🎭 Personalización (OBLIGATORIO - Mínimo Básico)

**¿Por qué es esencial?**
- Define la identidad y personalidad del chatbot
- Sin esto, el chatbot será genérico y poco efectivo

**Configuración mínima:**
- **Tono:** Elige uno (`friendly`, `professional`, `enthusiastic`, `casual`, `formal`)
  - Recomendado: `enthusiastic` o `professional` para ventas
- **Personalidad:** Define cómo quieres que sea el chatbot
  - Ejemplo mínimo: "Eres un asesor de ventas experto y proactivo"
  - Ejemplo completo: "Eres un asesor de ventas experto, proactivo y orientado a resultados. Haces preguntas inteligentes para entender necesidades reales y cierras ventas de forma natural. Eres amigable pero profesional."

**⏱️ Tiempo:** 2 minutos

---

### 2. 🌍 Idioma (OBLIGATORIO)

**¿Por qué es esencial?**
- Sin esto, el chatbot puede responder en el idioma incorrecto

**Configuración mínima:**
- **Idioma por Defecto:** `es` (español) o el idioma principal de tus clientes
- **Multilingüismo:** ✅ Actívalo si tienes clientes en múltiples idiomas
  - Si solo hablas español, puedes dejarlo desactivado

**⏱️ Tiempo:** 30 segundos

---

## 🚀 MUY IMPORTANTE (Mejora Significativamente el Comportamiento)

### 3. 📚 RAG - Conocimiento del Negocio (MUY RECOMENDADO)

**¿Por qué es muy importante?**
- Sin RAG, el chatbot solo sabe lo que está en el catálogo de productos
- Con RAG, puede responder sobre políticas, garantías, procesos, etc.
- Evita que el chatbot "alucine" información incorrecta

**Configuración mínima:**
- ✅ **Habilitar RAG:** Activa el checkbox
- **Documentos:** Sube al menos:
  - Catálogo de productos (PDF)
  - Políticas de devolución/garantía
  - Preguntas frecuentes (FAQ)
  - Manuales o guías de productos

**⏱️ Tiempo:** 5-10 minutos (depende de cuántos documentos tengas)

**💡 Tip:** Empieza con 2-3 documentos esenciales. Puedes agregar más después.

---

### 4. 💬 Manejo de Objeciones (MUY RECOMENDADO)

**¿Por qué es muy importante?**
- Los clientes siempre tienen objeciones ("está caro", "lo voy a pensar")
- Sin esto, el chatbot no sabrá cómo responder a objeciones comunes
- Mejora significativamente la tasa de conversión

**Configuración mínima:**
Agrega al menos estas 3 objeciones comunes:

```json
{
  "está caro": "Entiendo tu preocupación. Este producto te durará X años, lo que significa que cuesta solo Y por mes. ¿Cuál es tu presupuesto aproximado?",
  "lo voy a pensar": "Por supuesto. ¿Hay algo específico en lo que pueda ayudarte a decidir? ¿Te parece bien si te envío un resumen con las opciones que vimos?",
  "no estoy seguro": "Perfecto, déjame hacerte algunas preguntas para entender mejor qué necesitas exactamente..."
}
```

**⏱️ Tiempo:** 5 minutos

---

### 5. 🎯 Lead Scoring (RECOMENDADO para Ventas)

**¿Por qué es importante?**
- Detecta automáticamente cuando un cliente está "caliente" (listo para comprar)
- Permite que el chatbot sea más proactivo con leads calientes
- Mejora el cierre de ventas

**Configuración mínima:**
- ✅ **Habilitar Lead Scoring:** Activa el checkbox
- **Preguntas de Oro:** Agrega al menos 2-3 preguntas clave:
  ```json
  [
    {"question": "¿Cuál es tu presupuesto aproximado?", "weight": 3},
    {"question": "¿Cuándo necesitas esto?", "weight": 2}
  ]
  ```
- **Threshold para Lead Caliente:** Deja el valor por defecto (`7`) o ajústalo según necesites

**⏱️ Tiempo:** 3-5 minutos

---

## 🎁 OPCIONAL PERO ÚTIL (Mejora la Experiencia)

### 6. 📅 Agendamiento de Citas (OPCIONAL pero Muy Útil)

**¿Por qué es útil?**
- Cierra ventas automáticamente cuando detecta un Lead Caliente
- Ofrece agendar citas/demos para leads que necesitan más información
- Integración con CRM para seguimiento automático

**Configuración mínima:**
- ✅ **Habilitar Agendamiento:** Activa el checkbox
- **URL de Calendly:** Tu URL de Calendly (ej: `https://calendly.com/tu-usuario/demo-30min`)
- **Mensaje Personalizado:** Personaliza el mensaje (o deja el por defecto)

**⏱️ Tiempo:** 2 minutos

**💡 Tip:** Solo configúralo si realmente quieres que el chatbot ofrezca agendar citas. Si no, puedes dejarlo desactivado.

---

### 7. 👤 Handoff Humano (OPCIONAL)

**¿Por qué es opcional?**
- Solo necesario si quieres transferir conversaciones a agentes humanos
- Útil para casos complejos o cuando el chatbot no puede resolver algo

**Configuración mínima:**
- **Palabras Clave:** Deja las por defecto (`queja`, `fraude`, `hablar con humano`, `supervisor`)
- **Threshold de Sentimiento:** Deja el valor por defecto (`0.7`)

**⏱️ Tiempo:** 1 minuto

**💡 Tip:** Si no tienes un sistema de tickets o agentes humanos, puedes dejarlo desactivado o con valores por defecto.

---

## 📋 RESUMEN: Configuración por Prioridad

### ✅ **Configuración Mínima (5 minutos):**
1. ✅ Personalización (Tono + Personalidad básica)
2. ✅ Idioma (Idioma por defecto)

### 🚀 **Configuración Recomendada (15-20 minutos):**
1. ✅ Personalización (Tono + Personalidad completa)
2. ✅ Idioma (Idioma por defecto + Multilingüismo si es necesario)
3. ✅ RAG (Habilitar + Subir 2-3 documentos esenciales)
4. ✅ Manejo de Objeciones (Agregar 3-5 objeciones comunes)
5. ✅ Lead Scoring (Habilitar + Agregar 2-3 preguntas de oro)

### 🎁 **Configuración Completa (25-30 minutos):**
Todo lo anterior +:
6. ✅ Agendamiento de Citas (Si quieres cerrar ventas automáticamente)
7. ✅ Handoff Humano (Si tienes agentes humanos)

---

## 🎯 CONFIGURACIÓN RÁPIDA PARA EMPEZAR (5 minutos)

Si tienes prisa y solo quieres que funcione básicamente:

1. **🎭 Personalización:**
   - Tono: `enthusiastic`
   - Personalidad: "Eres un asesor de ventas experto y proactivo"

2. **🌍 Idioma:**
   - Idioma por Defecto: `es`
   - Multilingüismo: ✅ (si tienes clientes en otros idiomas)

3. **💬 Manejo de Objeciones:**
   - Agrega al menos: `"está caro"` y `"lo voy a pensar"`

**Con esto mínimo, el chatbot funcionará y responderá correctamente.** Puedes agregar más configuraciones después según veas qué necesita tu negocio.

---

## 💡 Consejos Finales

1. **Empieza simple:** Configura lo mínimo primero, prueba el chatbot, y luego agrega más características según veas qué funciona mejor.

2. **RAG es muy importante:** Si tienes documentos (catálogos, FAQs, políticas), súbelos. El chatbot será mucho más útil.

3. **Las objeciones son clave:** Invierte tiempo en configurar bien las objeciones comunes. Esto mejora significativamente la conversión.

4. **Lead Scoring ayuda mucho:** Si vendes productos/servicios, activa Lead Scoring. El chatbot será más inteligente detectando clientes listos para comprar.

5. **Puedes cambiar después:** Todas las configuraciones se pueden modificar en cualquier momento. No necesitas reiniciar el servidor.

---

## ✅ Checklist Rápido

- [ ] Personalización: Tono configurado
- [ ] Personalización: Personalidad definida
- [ ] Idioma: Idioma por defecto configurado
- [ ] Idioma: Multilingüismo activado (si es necesario)
- [ ] RAG: Habilitado y documentos subidos
- [ ] Objeciones: Al menos 3 objeciones comunes configuradas
- [ ] Lead Scoring: Habilitado (si vendes productos/servicios)
- [ ] Agendamiento: Configurado (si quieres cerrar ventas automáticamente)
- [ ] Handoff: Configurado (si tienes agentes humanos)

**¡Guarda la configuración y prueba el chatbot!** 🚀






