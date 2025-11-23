# 🚀 Guía para Probar Agentic AI - Envío Automático de Emails

## Paso 1: Configurar Credenciales SMTP

Agrega estas variables a tu archivo `.env`:

```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-contraseña-de-aplicacion
```

**Para Gmail:**
1. Ve a tu cuenta de Google: https://myaccount.google.com/
2. Seguridad → Verificación en 2 pasos (debe estar activada)
3. Contraseñas de aplicaciones → Generar nueva
4. Copia la contraseña generada y úsala en `SMTP_PASSWORD`

## Paso 2: Iniciar la Aplicación

```bash
python app.py
```

## Paso 3: Probar en la Interfaz Gradio

### Opción A: Con Documentos (Recomendado)

1. **Ve al tab "🤖 Agentes Autónomos"**

2. **Sube documentos** (opcional, pero recomendado):
   - Sube algunos PDFs o documentos
   - Haz clic en **"🔍 Procesar con IDP"**
   - Espera a que termine el procesamiento

3. **Ejecuta la tarea de envío de email**:
   - **Tipo de Tarea**: Selecciona "generación" o "automatización"
   - **Descripción de la tarea**: Escribe algo como:
     ```
     Analizar los documentos procesados y enviar un email a mi-email@ejemplo.com con un resumen ejecutivo de los hallazgos principales
     ```
   - **Contexto adicional** (opcional):
     ```json
     {
       "recipient": "mi-email@ejemplo.com",
       "subject": "Resumen Ejecutivo - Análisis de Documentos",
       "priority": "high"
     }
     ```
   - Haz clic en **"🚀 Ejecutar Tarea Autónoma"**

### Opción B: Sin Documentos (Prueba Simple)

1. **Ve al tab "🤖 Agentes Autónomos"**

2. **Ejecuta la tarea directamente**:
   - **Tipo de Tarea**: "generación"
   - **Descripción de la tarea**:
     ```
     Enviar un email de prueba a mi-email@ejemplo.com con el asunto "Prueba Agentic AI" y el cuerpo "Este es un email de prueba enviado automáticamente por el Agentic AI"
     ```
   - Haz clic en **"🚀 Ejecutar Tarea Autónoma"**

## Paso 4: Verificar Resultado

El sistema mostrará:
- ✅ Si el email se envió exitosamente
- ❌ Si hubo algún error (revisa las credenciales SMTP)

## Ejemplos de Tareas para Probar

### Ejemplo 1: Email Simple
```
Enviar un email a juan@empresa.com con el asunto "Notificación" y el mensaje "Tarea completada exitosamente"
```

### Ejemplo 2: Email con Análisis
```
Analizar los documentos procesados y enviar un email a gerencia@empresa.com con un resumen de los puntos clave encontrados
```

### Ejemplo 3: Email con Reporte
```
Generar un reporte de los documentos y enviarlo por email a analista@empresa.com
```

## Solución de Problemas

### Error: "SMTP credentials not configured"
- Verifica que las variables SMTP estén en el archivo `.env`
- Reinicia la aplicación después de agregar las variables

### Error: "Authentication failed"
- Para Gmail, asegúrate de usar una **contraseña de aplicación**, no tu contraseña normal
- Verifica que la verificación en 2 pasos esté activada

### Error: "Connection refused"
- Verifica que `SMTP_SERVER` y `SMTP_PORT` sean correctos
- Para Gmail: `smtp.gmail.com:587`

## Probar por API

Si prefieres probar por API:

```bash
# 1. Iniciar servidor API
python api_server.py

# 2. Ejecutar tarea por API
curl -X POST "http://localhost:8000/api/v1/agentic-ai/execute-task" \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "Enviar un email de prueba a mi-email@ejemplo.com con el asunto Prueba y el mensaje Hola desde Agentic AI",
    "task_type": "generación"
  }'
```

