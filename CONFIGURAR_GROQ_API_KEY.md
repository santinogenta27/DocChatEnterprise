# 🔑 CONFIGURAR GROQ API KEY

## ✅ TU API KEY DE GROQ:
```
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
```

## 📋 OPCIÓN 1: Configurar en archivo .env (RECOMENDADO)

1. **Abre o crea el archivo `.env` en la raíz del proyecto**

2. **Agrega estas líneas:**
```env
GROQ_API_KEY=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
DOCCHAT_USE_GROQ=true
DOCCHAT_GROQ_MODEL=llama-3.3-70b-versatile
```

3. **Guarda el archivo**

4. **Reinicia el servidor:**
   ```bash
   python api_server.py
   ```

5. **Deberías ver:**
   ```
   ✅ Business AI usando Groq (Llama 3.3 70B) - Velocidad <0.5 seg
   ```

---

## 📋 OPCIÓN 2: Configurar en Gradio UI

1. **Abre Gradio:** `http://localhost:7864` (si estás usando app.py)

2. **Ve a:** "🤖 Business AI Omnicanal" → "⚙️ Configuración Enterprise"

3. **En la sección "🔥 Groq Cloud":**
   - Pega tu API Key: `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`
   - Activa: "✅ Usar Groq (Llama 3.3 70B)"
   - Click: "💾 Guardar Configuración Groq"

4. **Reinicia el servidor**

---

## ✅ VERIFICACIÓN:

Después de configurar, cuando envíes un mensaje al chatbot:

- **Si Groq funciona:** Verás respuesta en <0.5 segundos
- **Si Groq falla:** El sistema automáticamente usará OpenAI como fallback

---

**✅ CONFIGURA LA API KEY Y REINICIA EL SERVIDOR**
















