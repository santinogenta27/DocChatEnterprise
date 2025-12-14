# 🔧 Configurar Variables de Entorno para Confluent

Hay **3 formas** de configurar las variables de entorno para Confluent:

## 📋 Opción 1: Archivo .env (RECOMENDADO)

Crea un archivo `.env` en la raíz del proyecto (`C:\Users\Random\DocChatEnterprise\.env`) con este contenido:

```env
# OpenAI API Key (ya deberías tenerla)
OPENAI_API_KEY=tu-openai-api-key

# Confluent Kafka Configuration
CONFLUENT_BOOTSTRAP_SERVERS=pkc-xxxxx.us-east-1.aws.confluent.cloud:9092

# Opcional: Configuración de seguridad para Confluent
# CONFLUENT_SECURITY_PROTOCOL=SASL_SSL
# CONFLUENT_SASL_MECHANISM=PLAIN
# CONFLUENT_SASL_USERNAME=tu-username
# CONFLUENT_SASL_PASSWORD=tu-password
```

**Ejemplo completo para Confluent Cloud:**
```env
OPENAI_API_KEY=sk-proj-...

# Confluent Cloud (ejemplo)
CONFLUENT_BOOTSTRAP_SERVERS=pkc-xxxxx.us-east-1.aws.confluent.cloud:9092
CONFLUENT_SECURITY_PROTOCOL=SASL_SSL
CONFLUENT_SASL_MECHANISM=PLAIN
CONFLUENT_SASL_USERNAME=TU_API_KEY
CONFLUENT_SASL_PASSWORD=TU_API_SECRET
```

La aplicación cargará automáticamente estas variables al iniciar.

---

## 📋 Opción 2: PowerShell (Sesión Actual)

Ejecuta estos comandos en PowerShell **antes** de iniciar la aplicación:

```powershell
# Configurar Confluent Bootstrap Servers
$env:CONFLUENT_BOOTSTRAP_SERVERS = "pkc-xxxxx.us-east-1.aws.confluent.cloud:9092"

# Opcional: Configuración de seguridad
$env:CONFLUENT_SECURITY_PROTOCOL = "SASL_SSL"
$env:CONFLUENT_SASL_MECHANISM = "PLAIN"
$env:CONFLUENT_SASL_USERNAME = "tu-username"
$env:CONFLUENT_SASL_PASSWORD = "tu-password"

# Verificar que se configuraron
echo $env:CONFLUENT_BOOTSTRAP_SERVERS
```

**Nota:** Estas variables solo duran mientras la sesión de PowerShell esté abierta.

---

## 📋 Opción 3: Modificar INICIAR_APP.ps1

Agrega las variables al script de inicio. Ya lo hice por ti, solo necesitas agregar tus valores.

---

## 🔍 Cómo Obtener las Credenciales de Confluent

### Si usas Confluent Cloud:

1. Ve a https://confluent.cloud
2. Inicia sesión en tu cuenta
3. Selecciona tu cluster
4. Ve a **Clients** → **Create new API key**
5. Copia:
   - **Bootstrap servers** (ej: `pkc-xxxxx.us-east-1.aws.confluent.cloud:9092`)
   - **API Key** (username)
   - **API Secret** (password)

### Si usas Kafka local (SIN CLOUD - GRATIS):

**Opción A: Docker (Recomendado - Más Fácil)**

1. Instala Docker Desktop: https://www.docker.com/products/docker-desktop
2. En la raíz del proyecto, ejecuta:
   ```powershell
   docker-compose -f docker-compose-kafka.yml up -d
   ```
3. Configura en `.env`:
   ```env
   CONFLUENT_BOOTSTRAP_SERVERS=localhost:9092
   # No necesitas seguridad para Kafka local
   ```

**Opción B: Instalación Manual**

Ver guía completa en `INSTALAR_KAFKA_LOCAL.md`

**Configuración mínima para Kafka local:**
```env
CONFLUENT_BOOTSTRAP_SERVERS=localhost:9092
# No necesitas seguridad para Kafka local
```

---

## ✅ Verificar Configuración

Después de configurar, inicia la aplicación y verás:

```
✅ [Event Bus Mode] Confluent Streaming habilitado para streaming en tiempo real
```

Si no ves este mensaje, significa que:
- Confluent no está configurado (usa Event Bus interno - funciona igual)
- O hay un error en la configuración (revisa los logs)

---

## 🚀 Uso sin Confluent (Opcional)

Si NO configuras Confluent, el Event Bus Mode funciona perfectamente usando su sistema interno de eventos. Confluent solo mejora el performance para casos de uso enterprise.

---

## 📝 Ejemplo Completo de .env

```env
# OpenAI
OPENAI_API_KEY=sk-proj-...

# Confluent Cloud
CONFLUENT_BOOTSTRAP_SERVERS=pkc-xxxxx.us-east-1.aws.confluent.cloud:9092
CONFLUENT_SECURITY_PROTOCOL=SASL_SSL
CONFLUENT_SASL_MECHANISM=PLAIN
CONFLUENT_SASL_USERNAME=TU_API_KEY_AQUI
CONFLUENT_SASL_PASSWORD=TU_API_SECRET_AQUI
```


