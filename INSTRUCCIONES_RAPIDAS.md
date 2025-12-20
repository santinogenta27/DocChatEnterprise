# 🚀 INSTRUCCIONES RÁPIDAS: Solucionar Error Groq 401

## ❌ PROBLEMA ACTUAL:
- Groq API Key inválida → Error 401
- CORS bloqueando desde localhost:8080

## ✅ SOLUCIÓN RÁPIDA:

### **OPCIÓN 1: Desactivar Groq (MÁS RÁPIDO)**

Edita tu archivo `.env` y cambia:
```bash
DOCCHAT_USE_GROQ=false
```

Luego reinicia:
```bash
python api_server.py
```

**Esto usará OpenAI directamente, sin intentar Groq.**

---

### **OPCIÓN 2: Configurar Groq correctamente**

1. Ve a https://console.groq.com
2. Crea cuenta (gratis)
3. Obtén API key válida
4. En `.env`:
```bash
GROQ_API_KEY=tu_key_valida_aqui
DOCCHAT_USE_GROQ=true
OPENAI_API_KEY=tu_openai_key  # Fallback si Groq falla
```

---

## 🔧 CORS YA ESTÁ CONFIGURADO

CORS ya permite `localhost:8080`. Si aún hay problemas, verifica que:
- El servidor esté corriendo en `http://localhost:7864`
- No haya otro proceso usando el puerto 7864

---

## 🚀 REINICIA Y PRUEBA:

1. **Detén api_server.py** (Ctrl+C)
2. **Edita `.env`** (pon `DOCCHAT_USE_GROQ=false` si quieres usar solo OpenAI)
3. **Reinicia:**
   ```bash
   python api_server.py
   ```
4. **Prueba el widget** en `test_widget.html`

---

**✅ RECOMENDACIÓN: Por ahora, usa `DOCCHAT_USE_GROQ=false` para que funcione inmediatamente con OpenAI.**
