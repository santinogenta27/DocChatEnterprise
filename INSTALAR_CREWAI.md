# 🚀 Instalar CrewAI con Python 3.12

## ⚠️ Problema

Cuando ejecutas `pip install crewai`, está usando el Python por defecto (probablemente 3.14), pero necesitas usar Python 3.12.

## ✅ Solución

Usa `py -3.12 -m pip` en lugar de solo `pip`:

### Paso 1: Instalar CrewAI

```powershell
py -3.12 -m pip install crewai
```

Esto instalará la última versión compatible con Python 3.12.

### Paso 2: Instalar Composio (Opcional)

```powershell
py -3.12 -m pip install composio-core
```

### Paso 3: Verificar Instalación

```powershell
py -3.12 -c "from crewai import Agent; print('✅ CrewAI instalado correctamente')"
```

## 📋 Comandos Completos

Ejecuta estos comandos en PowerShell:

```powershell
# Navegar al directorio del proyecto
cd C:\Users\Random\Downloads\uploaded_files

# Instalar CrewAI
py -3.12 -m pip install crewai

# Instalar Composio (opcional)
py -3.12 -m pip install composio-core

# Verificar
py -3.12 -c "from crewai import Agent; print('✅ CrewAI OK')"
```

## 🔍 Verificar Versión de Python

Para asegurarte de que estás usando Python 3.12:

```powershell
py -3.12 --version
```

Debería mostrar: `Python 3.12.x`

## ⚠️ Si Aún Hay Problemas

Si sigue sin funcionar, verifica que Python 3.12 esté instalado:

```powershell
py -0
```

Esto mostrará todas las versiones de Python instaladas. Asegúrate de que 3.12 esté en la lista.

## 📝 Nota sobre Versiones

- CrewAI requiere Python 3.10-3.13
- Python 3.12 es perfecto ✅
- La versión de CrewAI se instalará automáticamente (la última compatible)

