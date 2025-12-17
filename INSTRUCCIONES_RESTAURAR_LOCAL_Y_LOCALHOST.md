# 🔄 INSTRUCCIONES PARA RESTAURAR: Versión Local + Localhost

## 📋 PASOS PARA RESTAURAR EL PROYECTO COMPLETO

### **1. RESTAURAR CÓDIGO DESDE GIT**

```powershell
# Navegar al directorio del proyecto
cd C:\Users\Random\DocChatEnterprise

# Verificar estado
git status

# Si hay cambios locales, guardarlos primero
git stash

# Obtener última versión
git pull origin feature/eric-schmidt-optimizations

# Si guardaste cambios, restaurarlos
git stash pop
```

### **2. RESTAURAR DEPENDENCIAS PYTHON**

```powershell
# Instalar dependencias desde backup
py -3.12 -m pip install -r requirements_backup_2025-12-16.txt

# O si no tienes el backup, instalar desde requirements.txt (si existe)
py -3.12 -m pip install -r requirements.txt
```

### **3. CONFIGURAR VARIABLES DE ENTORNO**

#### **Editar `INICIAR_APP.ps1`:**
```powershell
# Abrir el archivo
notepad INICIAR_APP.ps1

# Verificar que la API key esté configurada:
$env:OPENAI_API_KEY = "tu-api-key-aqui"
```

#### **O configurar manualmente:**
```powershell
# En PowerShell
$env:OPENAI_API_KEY = "sk-proj-..."
```

### **4. VERIFICAR CONFIGURACIÓN LOCALHOST**

#### **Verificar puertos disponibles:**
```powershell
# Verificar si el puerto 7860 está libre
netstat -ano | findstr :7860

# Verificar si el puerto 8000 está libre
netstat -ano | findstr :8000
```

#### **Si los puertos están ocupados:**
```powershell
# Ver qué proceso está usando el puerto
netstat -ano | findstr :7860
# Anotar el PID y matar el proceso:
taskkill /PID [PID] /F
```

### **5. INICIAR LA APLICACIÓN**

#### **Opción A: Usar Script PowerShell (Recomendado)**
```powershell
.\INICIAR_APP.ps1
```

#### **Opción B: Iniciar Manualmente**
```powershell
# Configurar API key
$env:OPENAI_API_KEY = "tu-api-key"

# Iniciar app
py -3.12 app.py
```

#### **Opción C: Iniciar API Server**
```powershell
.\INICIAR_API.ps1
# O manualmente:
py -3.12 api_server.py
```

### **6. VERIFICAR QUE FUNCIONA**

1. **Abrir navegador:**
   - App Principal: http://127.0.0.1:7860
   - API Docs: http://127.0.0.1:8000/docs

2. **Probar Multi-Agent Platform:**
   - Ir al tab "🚀 Autonomous Multi-Agent Workflows"
   - Crear un workflow desde template
   - Ejecutar workflow

3. **Verificar logs:**
   - Deberías ver: "✅ Iniciando interfaz Gradio..."
   - Y luego: "Running on local URL: http://127.0.0.1:7860"

---

## 🔧 SOLUCIÓN DE PROBLEMAS

### **Error: Puerto ya en uso**
```powershell
# Encontrar proceso
netstat -ano | findstr :7860

# Matar proceso (reemplazar [PID])
taskkill /PID [PID] /F

# O cambiar puerto en app.py
# Buscar: find_free_port(start_port=7860)
# Cambiar a: find_free_port(start_port=7861)
```

### **Error: Módulo no encontrado**
```powershell
# Instalar módulo faltante
py -3.12 -m pip install [nombre-modulo]

# O reinstalar todas las dependencias
py -3.12 -m pip install -r requirements_backup_2025-12-16.txt
```

### **Error: API Key no configurada**
```powershell
# Verificar variable de entorno
echo $env:OPENAI_API_KEY

# Si está vacía, configurarla:
$env:OPENAI_API_KEY = "tu-api-key-aqui"
```

### **Error: Python 3.12 no encontrado**
```powershell
# Verificar versión de Python
py --version

# Si no tienes 3.12, instalar desde python.org
# O usar la versión que tengas:
python app.py
```

---

## 📁 ARCHIVOS IMPORTANTES A VERIFICAR

### **Antes de restaurar, verificar que existan:**
- [ ] `app.py` - Aplicación principal
- [ ] `api_server.py` - Servidor API
- [ ] `INICIAR_APP.ps1` - Script de inicio
- [ ] `docchat/config.py` - Configuración
- [ ] `docchat/autonomous_multi_agent_platform.py` - Multi-Agent Platform
- [ ] `requirements_backup_*.txt` - Dependencias

### **Si falta algún archivo:**
```powershell
# Restaurar desde Git
git checkout HEAD -- [nombre-archivo]

# O restaurar todo
git reset --hard HEAD
```

---

## 🎯 CHECKLIST DE RESTAURACIÓN

- [ ] Código restaurado desde Git
- [ ] Dependencias Python instaladas
- [ ] Variables de entorno configuradas
- [ ] Puertos verificados (7860, 8000)
- [ ] Aplicación inicia correctamente
- [ ] Multi-Agent Platform funciona
- [ ] URLs accesibles en navegador

---

## 📞 SI ALGO FALLA

1. **Revisar logs:**
   - Los errores aparecen en la consola de PowerShell
   - Buscar líneas que empiecen con "❌" o "ERROR"

2. **Verificar documentación:**
   - `BACKUP_COMPLETO_PROYECTO_LOCAL_Y_LOCALHOST.md`
   - `AUTONOMOUS_MULTI_AGENT_PLATFORM_COMPLETE.md`

3. **Restaurar desde backup completo:**
   ```powershell
   # Si tienes un ZIP del backup
   Expand-Archive -Path "DocChatEnterprise_BACKUP_2025-12-16.zip" -DestinationPath "C:\Users\Random\" -Force
   ```

---

**✅ SIGUIENDO ESTOS PASOS, DEBERÍAS TENER EL PROYECTO FUNCIONANDO EN LOCAL Y LOCALHOST**

