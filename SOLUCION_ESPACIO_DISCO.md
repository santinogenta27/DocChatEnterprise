# ⚠️ SOLUCIÓN: Error "No space left on device"

## 🔍 Problema

El error `OSError: [Errno 28] No space left on device` ocurre porque:
- Tu disco tiene **muy poco espacio libre** (0.05 GB = 50 MB)
- Gradio guarda todos los archivos subidos en `C:\Users\Random\AppData\Local\Temp\gradio\`
- Con 80 PDFs, esto puede ocupar varios GB

## ✅ SOLUCIONES

### Opción 1: Limpiar Archivos Temporales (RÁPIDO)

Ejecuta el script de limpieza:
```powershell
.\LIMPIAR_TEMPORALES.ps1
```

Este script limpia:
- Archivos temporales de Gradio
- Archivos temporales antiguos de Windows (más de 7 días)
- Cache de pip

### Opción 2: Limpiar Manualmente

1. **Limpiar Gradio:**
```powershell
Remove-Item -Path "$env:LOCALAPPDATA\Temp\gradio\*" -Recurse -Force
```

2. **Limpiar Windows Temp:**
```powershell
Remove-Item -Path "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue
```

3. **Usar Limpieza de Disco de Windows:**
   - Presiona `Win + R`
   - Escribe: `cleanmgr`
   - Selecciona la unidad C:
   - Marca todas las opciones
   - Click en "Limpiar archivos del sistema"

### Opción 3: Procesar en Lotes Más Pequeños

En lugar de 80 PDFs de una vez:
- **Prueba con 20-30 PDFs primero**
- Si funciona, procesa otro lote
- Repite hasta procesar todos

### Opción 4: Liberar Espacio en Disco

1. **Eliminar archivos grandes:**
   - Descargas antiguas
   - Videos/imágenes duplicados
   - Programas no usados

2. **Mover archivos a otro disco:**
   - Si tienes otro disco, mueve archivos grandes allí

3. **Usar herramienta de Windows:**
   - Configuración → Sistema → Almacenamiento
   - Click en "Archivos temporales"
   - Elimina todo lo que puedas

## 📊 Verificar Espacio Disponible

```powershell
Get-PSDrive C | Select-Object Used, Free, @{Name="FreeGB";Expression={[math]::Round($_.Free/1GB,2)}}
```

## 💡 Recomendación

**Para procesar 80 PDFs necesitas al menos 2-3 GB libres.**

1. Ejecuta `.\LIMPIAR_TEMPORALES.ps1`
2. Si aún no tienes espacio, libera más archivos
3. Procesa en lotes de 20-30 PDFs
4. Una vez procesados, los archivos se limpian automáticamente

## 🚀 Después de Limpiar

1. Verifica que tengas al menos 2 GB libres
2. Reinicia la app: `python app.py`
3. Prueba con 20-30 PDFs primero
4. Si funciona, aumenta gradualmente

---

**El problema NO es de tu PC, es simplemente falta de espacio en disco. Una vez liberes espacio, funcionará perfectamente.**

