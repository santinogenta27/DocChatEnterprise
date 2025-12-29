# 🚀 Guía para Configurar y Ejecutar DocChat Enterprise en Localhost

## 📋 Estado Actual del Proyecto

✅ **Proyecto descargado:** `C:\Users\usuario\DocChatEnterprise`
✅ **Archivo principal:** `app.py` (Aplicación Gradio)
✅ **Script de inicio:** `INICIAR_APP.ps1`
✅ **Dependencias:** `requirements.txt`

## ⚠️ Requisitos Previos

### 1. Instalar Python 3.12

Descarga e instala Python 3.12 desde:
- **Opcional 1:** Microsoft Store (busca "Python 3.12")
- **Opcional 2:** https://www.python.org/downloads/

**Importante:** Durante la instalación, marca la opción **"Add Python to PATH"**

### 2. Verificar Instalación de Python

Abre PowerShell y ejecuta:
```powershell
python --version
# Debe mostrar: Python 3.12.x

# O alternativamente:
py -3.12 --version
```

## 🔧 Configuración del Proyecto

### Paso 1: Navegar al Directorio del Proyecto

```powershell
cd C:\Users\usuario\DocChatEnterprise
```

### Paso 2: Crear Entorno Virtual (Recomendado)

```powershell
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
.\venv\Scripts\Activate.ps1
```

**Nota:** Si recibes un error sobre ejecución de scripts, ejecuta primero:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Paso 3: Instalar Dependencias

```powershell
# Asegúrate de que el entorno virtual esté activado
pip install --upgrade pip
pip install -r requirements.txt
```

**Nota:** La instalación puede tomar varios minutos debido a las muchas dependencias.

### Paso 4: Configurar Variables de Entorno

Crea un archivo `.env` en el directorio del proyecto:

```powershell
# Crear archivo .env
New-Item -Path .env -ItemType File -Force
```

Edita el archivo `.env` y agrega tus API keys:

```env
# API Key de OpenAI (requerida para algunas funciones)
OPENAI_API_KEY=tu-clave-openai-aqui

# API Key de Groq (requerida para los agentes)
GROQ_API_KEY=tu-clave-groq-aqui

# Opcional: Configuración de Confluent/Kafka
# CONFLUENT_BOOTSTRAP_SERVERS=localhost:9092
```

## 🚀 Ejecutar la Aplicación

### Opción 1: Usar el Script de Inicio (Recomendado)

```powershell
cd C:\Users\usuario\DocChatEnterprise
.\INICIAR_APP.ps1
```

### Opción 2: Ejecutar Directamente con Python

```powershell
cd C:\Users\usuario\DocChatEnterprise

# Si usas entorno virtual, actívalo primero:
.\venv\Scripts\Activate.ps1

# Ejecutar la aplicación
python app.py
```

### Opción 3: Ejecutar con Python 3.12 Específico

```powershell
py -3.12 app.py
```

## 🌐 Acceder a la Aplicación

Una vez que la aplicación inicie, verás un mensaje como:

```
Running on local URL:  http://127.0.0.1:7860
```

**Abre tu navegador en:** http://127.0.0.1:7860

## 📝 Modificar el Código

Para hacer modificaciones:

1. **Edita el archivo principal:**
   - `app.py` - Aplicación principal de Gradio (34,755 líneas)

2. **Archivos de módulos importantes:**
   - `docchat/` - Módulos principales del proyecto
   - `agentic_system/` - Sistema de agentes
   - `api/` - API endpoints

3. **Después de modificar:**
   - Guarda los cambios
   - La aplicación Gradio se recarga automáticamente (hot reload)
   - O reinicia la aplicación presionando `Ctrl+C` y ejecutando nuevamente

## 🛑 Detener la Aplicación

Presiona `Ctrl+C` en la terminal donde se está ejecutando la aplicación.

## ❓ Solución de Problemas

### Error: "Python no se reconoce"
- Instala Python 3.12 y asegúrate de agregarlo al PATH
- Reinicia PowerShell después de instalar Python

### Error: "Module not found"
- Asegúrate de haber instalado todas las dependencias: `pip install -r requirements.txt`
- Verifica que el entorno virtual esté activado

### Error: "Port 7860 already in use"
- Cierra otras instancias de la aplicación
- O detén el proceso en el puerto 7860:
```powershell
# Encontrar proceso en el puerto 7860
netstat -ano | findstr :7860

# Terminar proceso (reemplaza PID con el número del proceso)
taskkill /PID <PID> /F
```

### Error: "API Key not found"
- Crea el archivo `.env` en el directorio del proyecto
- Agrega las API keys necesarias (OPENAI_API_KEY, GROQ_API_KEY)

## 📚 Recursos Adicionales

- **README.md** - Documentación general del proyecto
- **VERIFICACION_AGENTES_GRADIO.md** - Información sobre los agentes disponibles
- **INICIAR_APP.ps1** - Script de inicio con configuración preestablecida

## 🎯 Agentes Disponibles en Gradio

El proyecto incluye 3 agentes principales:

1. **🎯 STEM Customer Care** - Atención al cliente STEM
2. **💼 Customer Business Agent** - Agente de negocios
3. **💰 Sales AI Agent** - Agente de ventas

Todos están integrados en la interfaz de Gradio y estarán disponibles una vez que inicies la aplicación.

