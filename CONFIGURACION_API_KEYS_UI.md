# 🔑 Configuración de API Keys desde la UI

## ✅ IMPLEMENTADO

He agregado una **sección completa de configuración de API Keys** en la UI del Enterprise Ads Manager. Los usuarios pueden configurar todas las API keys necesarias directamente desde la interfaz, sin necesidad de editar archivos o variables de entorno.

---

## 📍 Ubicación en la UI

La configuración está en el tab **"📢 Enterprise Ads Manager"**, dentro de un acordeón **"⚙️ Configurar API Keys (Requerido para Funcionalidad Completa)"**.

---

## 🔑 API Keys Configurables

### Tab 1: APIs Principales
- ✅ **OpenAI API Key**: Para generación de imágenes (DALL-E 3) y LLM
- ✅ **Meta Ads Access Token**: Token de acceso de Meta Ads API
- ✅ **Meta Ads App ID**: App ID de tu aplicación de Meta
- ✅ **Meta Ads App Secret**: App Secret de tu aplicación de Meta
- ✅ **Meta Ads Account ID**: ID de tu cuenta de anuncios (formato: act_XXXXX)
- ✅ **Meta Ads Page ID**: ID de tu página de Facebook (opcional)
- ✅ **Landing Page URL**: URL de destino para los anuncios

### Tab 2: Generación de Videos
- ✅ **Runway API Key**: Para generación de videos con Runway Gen-2
- ✅ **Pika API Key**: Para generación de videos con Pika
- ✅ **Proveedor de Video Preferido**: Dropdown para seleccionar (Runway/Pika/Sora)

### Tab 3: Base de Datos y Monitoring
- ✅ **PostgreSQL Database URL**: URL de conexión a PostgreSQL
- ✅ **Sentry DSN**: Para error tracking (opcional)

---

## 💾 Persistencia

- ✅ **Archivo de configuración**: `data/enterprise_ads_config.json`
- ✅ **Carga automática**: Las API keys se cargan automáticamente al iniciar
- ✅ **Actualización en tiempo real**: Al guardar, se actualizan las variables de entorno
- ✅ **Reinicialización automática**: El Enterprise Ads Manager se reinicializa con las nuevas configuraciones

---

## 🔄 Flujo de Configuración

1. **Usuario abre el tab "📢 Enterprise Ads Manager"**
2. **Expande el acordeón "⚙️ Configurar API Keys"**
3. **Ingresa sus API keys en los campos correspondientes**
4. **Hace clic en "💾 Guardar Configuración de API Keys"**
5. **El sistema:**
   - Guarda las keys en `data/enterprise_ads_config.json`
   - Actualiza las variables de entorno
   - Reinicializa el Enterprise Ads Manager
   - Muestra estado de configuración

---

## 📊 Estado de Configuración

El sistema muestra automáticamente el estado de cada API key:
- ✅ **Configurada**: La key está guardada y lista para usar
- ⚠️ **No configurada**: Falta configurar (funcionalidad limitada)
- ℹ️ **Opcional**: No es requerida (tiene fallback)

---

## 🔐 Seguridad

- ✅ **Campos tipo password**: Todas las API keys se muestran como campos de contraseña
- ✅ **Almacenamiento local**: Las keys se guardan en archivo local (no se envían a servidores externos)
- ✅ **Validación básica**: Se valida formato de algunas keys (ej: OpenAI debe empezar con "sk-")

---

## 🚀 Uso

1. Abre la aplicación
2. Ve al tab **"📢 Enterprise Ads Manager"**
3. Expande **"⚙️ Configurar API Keys"**
4. Ingresa tus API keys
5. Haz clic en **"💾 Guardar Configuración"**
6. ¡Listo! El sistema está configurado y listo para usar

---

## 📝 Notas

- Las API keys se guardan localmente en `data/enterprise_ads_config.json`
- Si no configuras alguna key, el sistema usará fallbacks cuando sea posible
- Meta Ads API es requerida para publicación real (sin ella, funciona en modo simulación)
- OpenAI es requerida para generación de imágenes
- Videos son opcionales (si no configuras, solo se generan imágenes)

---

**✅ Sistema completamente funcional para usuarios finales - No necesitan editar archivos o variables de entorno manualmente.**
