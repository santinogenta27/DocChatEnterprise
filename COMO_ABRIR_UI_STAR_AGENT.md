# 📱 CÓMO ABRIR LA UI DE STAR AGENT CON WHATSAPP E INSTAGRAM

## ⚠️ PROBLEMA IDENTIFICADO

La integración de WhatsApp e Instagram **SÍ ESTÁ IMPLEMENTADA** en la UI de Gradio, pero probablemente estás abriendo la aplicación incorrecta.

---

## ✅ SOLUCIÓN: EJECUTAR LA UI CORRECTA

### Opción 1: Usar el script dedicado (RECOMENDADO)

```bash
python run_star_agent_ui.py
```

Este script está en la raíz del proyecto y lanzará la UI completa de STAR AGENT.

### Opción 2: Ejecutar directamente desde Python

```bash
python -c "from docchat.star_agent import StarAgentMode; from docchat.config import load_config; config = load_config(); mode = StarAgentMode(config=config); iface = mode.get_gradio_interface(); iface.launch(server_name='127.0.0.1', server_port=7860)"
```

### Opción 3: Crear un script simple

Crea un archivo `start_star_agent.py` en la raíz:

```python
from docchat.star_agent import StarAgentMode
from docchat.config import load_config

if __name__ == "__main__":
    print("🚀 Iniciando STAR AGENT UI...")
    config = load_config()
    star_agent = StarAgentMode(config=config)
    iface = star_agent.get_gradio_interface()
    iface.launch(server_name="127.0.0.1", server_port=7860)
```

Luego ejecuta:
```bash
python start_star_agent.py
```

---

## ❌ NO EJECUTAR

**NO ejecutes `app.py` directamente** porque ese es el modo DocChat (documentos), no el modo STAR AGENT.

---

## 📱 QUÉ VERÁS EN LA UI

Una vez que ejecutes la UI correcta, verás estos tabs:

1. **💬 Chat** - Para probar el agente
2. **⚙️ Configuración** - Configuración básica
3. **📱 WhatsApp & Instagram** ⬅️ **ESTE ES EL TAB QUE BUSCAS**
   - Sub-tab: 💬 WhatsApp Business
   - Sub-tab: 📷 Instagram Direct
   - Sub-tab: 🌐 Estado y Webhooks
4. **📊 Métricas** - Analytics y métricas

---

## 🔍 VERIFICAR QUE ESTÁ FUNCIONANDO

Cuando abras la UI correcta:

1. Deberías ver el título: **"⭐ STAR AGENT - Asistente Virtual 24/7"**
2. Deberías ver 4 tabs principales
3. El tercer tab debería ser: **"📱 WhatsApp & Instagram"**

Si ves "DocChat 🐥" en el título, entonces estás en la aplicación incorrecta.

---

## 🐛 SI AÚN NO LO VES

1. Verifica que estás ejecutando el script correcto:
   ```bash
   python run_star_agent_ui.py
   ```

2. Verifica que el puerto sea 7860 (no 5000):
   ```
   http://127.0.0.1:7860
   ```

3. Revisa la consola para ver si hay errores al cargar la UI.

4. Si hay errores, comparte el mensaje de error para ayudarte a solucionarlo.

---

## ✅ RESUMEN

- ✅ WhatsApp e Instagram **SÍ ESTÁN IMPLEMENTADOS**
- ✅ El tab está en `star_agent_mode.py` línea 678
- ✅ Ejecuta `run_star_agent_ui.py` (NO `app.py`)
- ✅ Deberías ver el tab "📱 WhatsApp & Instagram" como tercer tab

