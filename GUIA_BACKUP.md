# 🔒 Guía de Backup y Control de Versiones

## 📋 Opciones Disponibles

Tienes **3 formas** de proteger tu proyecto antes de agregar nuevas funcionalidades:

---

## 🎯 Opción 1: Backup Manual (MÁS SIMPLE)

### Crear Backup:
```powershell
.\CREAR_BACKUP.ps1
```

Esto creará una copia completa en:
`C:\Users\Random\Downloads\DocChat_Backup_YYYYMMDD_HHMMSS`

### Restaurar Backup:
```powershell
.\RESTAURAR_BACKUP.ps1
```

**Ventajas:**
- ✅ Muy simple
- ✅ No requiere Git
- ✅ Copia completa del proyecto

**Desventajas:**
- ⚠️ Ocupa más espacio
- ⚠️ No hay historial de cambios

---

## 🎯 Opción 2: Git con Ramas (RECOMENDADO)

### Inicializar Git:
```powershell
.\INICIALIZAR_GIT.ps1
```

Esto:
1. Crea un repositorio Git
2. Guarda tu versión actual como "versión estable"
3. Crea una rama "desarrollo" para nuevas funcionalidades

### Trabajar en Desarrollo:
```powershell
# Estás en la rama 'desarrollo' automáticamente
# Haz tus cambios aquí
python app.py  # Prueba tus cambios
```

### Si algo sale mal:
```powershell
# Volver a la versión estable
git checkout main

# O deshacer cambios específicos
git checkout .  # Deshace todos los cambios
```

### Guardar cambios exitosos:
```powershell
git add .
git commit -m "Nueva funcionalidad agregada"
```

**Ventajas:**
- ✅ Historial completo de cambios
- ✅ Fácil volver atrás
- ✅ Puedes trabajar en múltiples funcionalidades
- ✅ No ocupa espacio extra (solo cambios)

**Desventajas:**
- ⚠️ Requiere Git instalado

---

## 🎯 Opción 3: Copia Manual de Carpeta

### Crear copia:
1. Ve a `C:\Users\Random\Downloads\`
2. Copia la carpeta `uploaded_files`
3. Pégala y renómbrala: `uploaded_files_BACKUP`

### Restaurar:
1. Borra `uploaded_files`
2. Renombra `uploaded_files_BACKUP` a `uploaded_files`

**Ventajas:**
- ✅ Muy simple
- ✅ No requiere scripts

**Desventajas:**
- ⚠️ Ocupa mucho espacio
- ⚠️ Manual

---

## 🚀 Recomendación

**Usa la Opción 2 (Git)** porque:
- Es la forma profesional de trabajar
- Te permite experimentar sin miedo
- Puedes volver atrás fácilmente
- No ocupa espacio extra

---

## 📝 Comandos Git Útiles

```powershell
# Ver en qué rama estás
git branch

# Cambiar a versión estable
git checkout main

# Cambiar a desarrollo
git checkout desarrollo

# Ver qué archivos cambiaron
git status

# Ver diferencias
git diff

# Deshacer cambios no guardados
git checkout .

# Guardar cambios
git add .
git commit -m "Descripción de los cambios"
```

---

## ⚠️ Importante

- **Siempre** crea un backup antes de cambios grandes
- **Prueba** en la rama de desarrollo primero
- **Guarda** solo cuando funcione correctamente
- **Nunca** borres la rama `main` (versión estable)

---

## 🆘 Si Algo Sale Mal

1. **Si Git está roto:**
   ```powershell
   git checkout main  # Volver a versión estable
   ```

2. **Si necesitas restaurar todo:**
   ```powershell
   .\RESTAURAR_BACKUP.ps1
   ```

3. **Si nada funciona:**
   - Usa la copia manual de carpeta
   - Restaura desde el backup más reciente

---

¡Tu proyecto está protegido! 🛡️

