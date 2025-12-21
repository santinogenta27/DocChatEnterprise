# 🔐 Guía: Configurar Credenciales para ADS WORKER

## 📍 Ubicación en Gradio

1. Ve al tab **"📢 ADS WORKER"** en la interfaz principal
2. Dentro de ADS WORKER, ve al tab **"⚙️ Configurar Credenciales"**
3. Ahí encontrarás dos sub-tabs:
   - **📘 Meta Ads (Facebook/Instagram)**
   - **🔍 Google Ads**

---

## 📘 Configurar Credenciales de Meta Ads

### Campos Requeridos:

1. **🔑 Access Token** (Requerido)
   - Token de acceso de Meta Marketing API
   - Cómo obtenerlo: [Facebook Developers](https://developers.facebook.com)

2. **🆔 App ID** (Requerido)
   - ID de tu aplicación de Facebook
   - Lo encuentras en tu app en Facebook Developers

3. **🔐 App Secret** (Requerido)
   - Secret de tu aplicación de Facebook
   - Lo encuentras en Configuración de tu app

4. **💼 Ad Account ID** (Requerido)
   - ID de tu cuenta publicitaria
   - **IMPORTANTE:** Ingresa solo el número, sin el prefijo `act_`
   - Ejemplo: Si tu ID es `act_123456789`, ingresa solo `123456789`

5. **📄 Page ID** (Opcional pero recomendado)
   - ID de tu página de Facebook
   - Útil para publicaciones en páginas

### Cómo Obtener las Credenciales:

#### 1. Crear una App en Facebook Developers:

1. Ve a https://developers.facebook.com
2. Click en "My Apps" → "Create App"
3. Selecciona tipo "Business"
4. Completa el formulario
5. Tu **App ID** y **App Secret** estarán en el Dashboard

#### 2. Obtener Access Token:

**Opción A: Token de Prueba (Rápido para testing)**
1. En tu app, ve a "Tools" → "Graph API Explorer"
2. Selecciona tu app en el dropdown
3. Genera token con permisos: `ads_read`, `ads_management`, `business_management`
4. Copia el token generado

**Opción B: Token de Larga Duración (Producción)**
1. Usa el Graph API Explorer para obtener token corto
2. Intercambia el token corto por uno de larga duración usando:
   ```
   GET /oauth/access_token?grant_type=fb_exchange_token&
   client_id={app-id}&client_secret={app-secret}&
   fb_exchange_token={short-lived-token}
   ```

#### 3. Obtener Ad Account ID:

1. Ve a https://business.facebook.com/adsmanager
2. Selecciona tu cuenta publicitaria
3. En la URL verás algo como: `act_123456789`
4. El ID es el número después de `act_` (en este caso: `123456789`)

#### 4. Obtener Page ID:

1. Ve a tu página de Facebook
2. Click en "About" en el menú izquierdo
3. Scroll hasta "Page ID"
4. O usa el Graph API Explorer con `me?fields=id`

---

## 🔍 Configurar Credenciales de Google Ads

### Campos Requeridos:

1. **Customer ID** (Requerido)
   - ID de tu cuenta de Google Ads
   - Formato: `123-456-7890` (con guiones)
   - Lo encuentras en la parte superior derecha de Google Ads

2. **Developer Token** (Opcional pero recomendado)
   - Token de desarrollador de Google Ads API
   - Necesario para usar la API completa

### Cómo Obtener las Credenciales:

#### 1. Obtener Customer ID:

1. Inicia sesión en https://ads.google.com
2. En la parte superior derecha verás tu Customer ID
3. Formato: `123-456-7890`

#### 2. Obtener Developer Token:

1. Ve a https://ads.google.com/aw/apicenter
2. Solicita acceso al API Center
3. Una vez aprobado, verás tu Developer Token
4. Copia el token (puede tardar días en ser aprobado)

---

## 💾 Cómo Guardar las Credenciales

### En Gradio:

1. Llena todos los campos requeridos
2. Opcional: Haz click en **"🧪 Probar Conexión"** para verificar que funcionan
3. Haz click en **"💾 Guardar Credenciales"**
4. Verás un mensaje de confirmación si se guardaron correctamente

### Verificar que se Guardaron:

1. Click en el botón **"📥 Cargar Credenciales"** (si está disponible)
2. Deberías ver tus credenciales cargadas en los campos
3. El estado mostrará si la conexión es exitosa

---

## 🔒 Seguridad

### Dónde se Guardan:

Las credenciales se guardan en:
- **Archivo local:** `.docchat_memory/ads_credentials/meta_credentials.json`
- **Variables de entorno:** Se actualizan automáticamente

### ⚠️ Importante:

- **NO compartas** tus credenciales
- **NO subas** estos archivos a GitHub
- Los archivos de credenciales están en `.gitignore`
- Usa tokens con permisos mínimos necesarios

---

## 🧪 Probar la Conexión

Después de guardar las credenciales:

1. Click en **"🧪 Probar Conexión"**
2. Verás un mensaje indicando si la conexión fue exitosa
3. Si hay errores, verifica:
   - Que los tokens sean válidos
   - Que tengan los permisos correctos
   - Que el Ad Account ID esté correcto (sin `act_`)

---

## ⚠️ Solución de Problemas

### Error: "Invalid Access Token"
- Verifica que el token no haya expirado
- Genera un nuevo token si es necesario
- Asegúrate de tener los permisos correctos

### Error: "Invalid Ad Account ID"
- Verifica que ingresaste solo el número (sin `act_`)
- Asegúrate de que el ID sea correcto
- Verifica que tengas acceso a esa cuenta publicitaria

### Error: "App ID or Secret Invalid"
- Verifica que copiaste correctamente App ID y App Secret
- Asegúrate de que no haya espacios adicionales
- Verifica que la app esté activa en Facebook Developers

### Error: "Connection Timeout"
- Verifica tu conexión a internet
- Asegúrate de que Facebook/Google no estén bloqueados
- Intenta de nuevo más tarde

---

## 📝 Notas Adicionales

- **Meta Ads:** Puedes configurar credenciales sin LangChain instalado
- **Google Ads:** Developer Token puede tardar días en ser aprobado
- **Testing:** Puedes usar tokens de prueba para desarrollo
- **Producción:** Usa tokens de larga duración para producción

---

## ✅ Checklist de Configuración

- [ ] Creé una app en Facebook Developers
- [ ] Obtuve Access Token de Meta
- [ ] Tengo App ID y App Secret
- [ ] Tengo Ad Account ID (sin `act_`)
- [ ] (Opcional) Tengo Page ID
- [ ] Guardé las credenciales en Gradio
- [ ] Probé la conexión exitosamente
- [ ] (Opcional) Configuré credenciales de Google Ads

---

## 🚀 Después de Configurar

Una vez que tengas las credenciales configuradas:

1. **ADS WORKER estará completamente habilitado**
2. Podrás crear campañas automáticamente
3. Podrás procesar assets creativos
4. Podrás optimizar campañas existentes
5. Podrás analizar métricas en tiempo real

---

## 📚 Enlaces Útiles

- **Facebook Developers:** https://developers.facebook.com
- **Meta Marketing API Docs:** https://developers.facebook.com/docs/marketing-apis
- **Google Ads API:** https://developers.google.com/google-ads/api/docs/start
- **Graph API Explorer:** https://developers.facebook.com/tools/explorer/








