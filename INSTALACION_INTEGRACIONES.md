# 📦 Instalación de Integraciones Avanzadas

## ⚠️ Compatibilidad de Python

**Tu versión actual:** Python 3.14.0

### LangGraph ✅
- **Estado:** ✅ Compatible con Python 3.14
- **Instalación:** Ya está en requirements.txt
- **Funcionalidad:** Totalmente disponible

### CrewAI ❌
- **Estado:** ❌ Requiere Python 3.10-3.13
- **Problema:** Tu Python 3.14 no es compatible
- **Solución:** 
  - Opción 1: Usar Python 3.12 o 3.13 (recomendado)
  - Opción 2: Las funcionalidades de CrewAI estarán deshabilitadas (el sistema funcionará sin ellas)

### Composio ⚠️
- **Estado:** ⚠️ Opcional - puede funcionar sin instalación
- **Instalación:** `pip install composio-core` (opcional)
- **Funcionalidad:** Funciona en modo simulado sin instalación

---

## 🚀 Opciones de Instalación

### Opción 1: Instalar solo lo compatible (Recomendado)

```bash
# LangGraph ya está instalado
# Composio es opcional
pip install composio-core
```

**Resultado:**
- ✅ LangGraph: Funcional
- ❌ CrewAI: Deshabilitado (incompatible con Python 3.14)
- ⚠️ Composio: Funcional (modo simulado sin API key, modo real con API key)

### Opción 2: Usar Python 3.12 o 3.13 (Para tener todo)

Si quieres usar CrewAI, necesitas cambiar a Python 3.12 o 3.13:

1. **Instalar Python 3.12 o 3.13:**
   - Descarga desde: https://www.python.org/downloads/
   - Instala Python 3.12 o 3.13

2. **Crear entorno virtual:**
   ```bash
   python3.12 -m venv venv
   # o
   python3.13 -m venv venv
   ```

3. **Activar entorno:**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

4. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   pip install crewai>=0.80.0 composio-core>=0.5.0
   ```

---

## 📊 Estado Actual de Funcionalidades

Con Python 3.14:

| Herramienta | Estado | Funcionalidad |
|------------|--------|---------------|
| **LangGraph** | ✅ Disponible | Workflows avanzados funcionando |
| **CrewAI** | ❌ No disponible | Multi-agent deshabilitado |
| **Composio** | ⚠️ Opcional | Funciona en modo simulado |

---

## 💡 Recomendación

**Para desarrollo/producción:**
- Usa Python 3.12 o 3.13 para tener todas las funcionalidades
- Python 3.14 es muy nuevo y muchas librerías aún no lo soportan

**Para probar ahora:**
- El sistema funcionará perfectamente sin CrewAI
- LangGraph está disponible
- Composio funciona en modo simulado

---

## 🔧 Verificar Instalación

```bash
# Verificar LangGraph
python -c "from langgraph.graph import StateGraph; print('✅ LangGraph instalado')"

# Verificar Composio (opcional)
python -c "from composio import ComposioToolSet; print('✅ Composio instalado')" 2>/dev/null || echo "⚠️ Composio no instalado (opcional)"

# Verificar CrewAI (no funcionará con Python 3.14)
python -c "from crewai import Agent; print('✅ CrewAI instalado')" 2>/dev/null || echo "❌ CrewAI no disponible (requiere Python 3.10-3.13)"
```

---

## 🎯 Funcionalidades Disponibles

### Con Python 3.14 (tu situación actual):

✅ **LangGraph:**
- Workflows avanzados en Leads
- Workflows de campañas en Marketing
- Workflows de resolución en Atención al Cliente
- Workflows de sincronización en Integraciones

❌ **CrewAI:**
- Multi-agent collaboration deshabilitado
- Los botones de CrewAI mostrarán mensaje de no disponible

⚠️ **Composio:**
- Funciona en modo simulado
- Para modo real, instala: `pip install composio-core`
- Configura `COMPOSIO_API_KEY` para funcionalidad completa

---

## 📝 Notas

- El sistema está diseñado para funcionar sin estas integraciones
- Si CrewAI no está disponible, simplemente no se mostrarán esas opciones en la UI
- LangGraph es la integración más importante y está disponible
- Composio puede funcionar sin instalación en modo simulado

