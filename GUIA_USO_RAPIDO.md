# 🚀 Guía de Uso Rápido - DocChat Enterprise

## ⚡ Inicio Rápido (3 pasos)

### Paso 1: Configurar API Key

**Opción A: Archivo .env (Recomendado)**

Crea un archivo `.env` en la carpeta del proyecto con:

```env
OPENAI_API_KEY=tu-clave-aqui
```

**Opción B: Variable de entorno (PowerShell)**

```powershell
$env:OPENAI_API_KEY="tu-clave-aqui"
```

**Opción C: Variable de entorno (CMD)**

```cmd
set OPENAI_API_KEY=tu-clave-aqui
```

### Paso 2: Ejecutar la aplicación

```bash
python app.py
```

### Paso 3: Abrir en el navegador

Cuando veas este mensaje:
```
🚀 Starting DocChat Enterprise on http://127.0.0.1:7860
* Running on local URL:  http://127.0.0.1:7860
```

Abre tu navegador en: **http://127.0.0.1:7860**

---

## 📋 Funcionalidades Disponibles

### 1. 🔍 Consulta RAG (Básico)
- Sube documentos (PDF, DOCX, TXT, MD)
- Haz preguntas
- Obtén respuestas verificadas

### 2. 📚 Procesamiento Masivo (NUEVO)
- Arrastra carpetas completas o selecciona múltiples archivos
- Procesa hasta 200 documentos simultáneamente
- Análisis comparativo automático

### 3. 🔥 Workflow Completo (NUEVO - LA ESTRELLA)
- Sube 100+ documentos
- Escribe: "Analiza estos PDFs y genera informe + PPT + Excel"
- El sistema genera TODO automáticamente

### 4. 🤖 Agentes Autónomos
- Ejecuta tareas completas
- Envía emails, genera reportes, etc.

### 5. 🧠 Memoria y Estadísticas
- Ver historial de consultas
- Estadísticas de uso

---

## 🎯 Ejemplo de Uso: Workflow Completo

1. Ve a la tab **"🔥 Workflow Completo"**
2. Arrastra o selecciona múltiples PDFs (puedes seleccionar 100+)
3. En el campo de texto escribe:
   ```
   Analiza estos documentos y genera informe + PPT + Excel con los hallazgos principales
   ```
4. Selecciona formato: **"all"** (genera todo)
5. Haz clic en **"🚀 Ejecutar Workflow Completo"**
6. Espera (puede tomar unos minutos con muchos documentos)
7. ¡Listo! El sistema te entregará:
   - ✅ Informe en Excel
   - ✅ Presentación PPT
   - ✅ Análisis completo

---

## 🐳 Alternativa: Docker (Opcional)

Si prefieres usar Docker:

```bash
# 1. Configurar .env con OPENAI_API_KEY
# 2. Ejecutar:
docker-compose up -d

# 3. Abrir: http://localhost:7860
```

---

## ⚠️ Solución de Problemas

### Error: "OPENAI_API_KEY no está configurada"
- Verifica que el archivo `.env` existe y tiene la clave
- O configura la variable de entorno

### Error: "Puerto 7860 en uso"
- El sistema automáticamente encuentra otro puerto
- Revisa el mensaje en la terminal para ver qué puerto usa

### La aplicación no responde
- Presiona `Ctrl+C` para detener
- Vuelve a ejecutar `python app.py`

---

## 💡 Tips

- **Primera vez**: Prueba con 1-2 documentos pequeños
- **Procesamiento masivo**: Puede tomar varios minutos con 100+ documentos
- **Workflow completo**: Es la funcionalidad más poderosa, úsala para análisis completos

---

## 🎉 ¡Listo para usar!

Tu producto está completamente funcional y listo para competir con Harvey, Glean y otros productos enterprise.



