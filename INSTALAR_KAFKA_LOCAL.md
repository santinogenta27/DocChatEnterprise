# 🚀 Instalar y Configurar Kafka Local (Sin Cloud)

Puedes usar **Apache Kafka local** o **Confluent Platform local** para streaming en tiempo real sin necesidad de Confluent Cloud.

## 📋 Opción 1: Apache Kafka Local (Recomendado - Más Simple)

### Windows (usando Docker - Más Fácil)

1. **Instalar Docker Desktop** (si no lo tienes):
   - Descarga: https://www.docker.com/products/docker-desktop
   - Instala y reinicia tu PC

2. **Ejecutar Kafka con Docker Compose**:

Crea un archivo `docker-compose-kafka.yml` en la raíz del proyecto:

```yaml
version: '3.8'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"

  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
```

3. **Iniciar Kafka**:

```powershell
# En la raíz del proyecto
docker-compose -f docker-compose-kafka.yml up -d
```

4. **Verificar que está corriendo**:

```powershell
docker ps
# Deberías ver zookeeper y kafka corriendo
```

### Windows (Instalación Manual - Más Complejo)

1. **Descargar Kafka**:
   - Ve a: https://kafka.apache.org/downloads
   - Descarga la última versión (ej: `kafka_2.13-3.6.1.tgz`)
   - Extrae en `C:\kafka`

2. **Instalar Java** (requerido):
   - Kafka requiere Java 8+
   - Descarga: https://adoptium.net/
   - Instala Java 17 o superior

3. **Configurar Kafka**:

Edita `C:\kafka\config\server.properties`:

```properties
# Cambiar esta línea:
listeners=PLAINTEXT://localhost:9092
advertised.listeners=PLAINTEXT://localhost:9092
```

4. **Iniciar Kafka**:

```powershell
# Terminal 1: Iniciar Zookeeper
cd C:\kafka
.\bin\windows\zookeeper-server-start.bat .\config\zookeeper.properties

# Terminal 2: Iniciar Kafka
cd C:\kafka
.\bin\windows\kafka-server-start.bat .\config\server.properties
```

---

## 📋 Opción 2: Confluent Platform Local (Más Completo)

1. **Descargar Confluent Platform**:
   - Ve a: https://www.confluent.io/download/
   - Descarga Confluent Platform Community (gratis)
   - Extrae en `C:\confluent`

2. **Iniciar Confluent Platform**:

```powershell
cd C:\confluent
.\bin\confluent local services start
```

3. **Verificar**:

```powershell
.\bin\confluent local services status
```

---

## ⚙️ Configurar DocChat para Usar Kafka Local

### Opción A: Archivo .env (Recomendado)

Crea o edita `.env` en la raíz del proyecto:

```env
# OpenAI
OPENAI_API_KEY=tu-openai-api-key

# Kafka Local (sin seguridad)
CONFLUENT_BOOTSTRAP_SERVERS=localhost:9092
```

**¡Eso es todo!** No necesitas configuración de seguridad para Kafka local.

### Opción B: PowerShell (Sesión Actual)

```powershell
$env:CONFLUENT_BOOTSTRAP_SERVERS = "localhost:9092"
```

### Opción C: Modificar INICIAR_APP.ps1

Edita `INICIAR_APP.ps1` y descomenta/agrega:

```powershell
# Kafka Local
$env:CONFLUENT_BOOTSTRAP_SERVERS = "localhost:9092"
```

---

## ✅ Verificar que Funciona

1. **Inicia Kafka** (si usas Docker):
   ```powershell
   docker-compose -f docker-compose-kafka.yml up -d
   ```

2. **Inicia DocChat**:
   ```powershell
   py -3.12 app.py
   ```

3. **Busca este mensaje**:
   ```
   ✅ [ChatPDF Mode] Confluent Streaming habilitado para streaming en tiempo real
   ```

Si ves este mensaje, ¡Kafka local está funcionando! 🎉

---

## 🔧 Solución de Problemas

### Error: "Connection refused"

- Verifica que Kafka esté corriendo:
  ```powershell
  docker ps  # Si usas Docker
  # O
  netstat -an | findstr 9092  # Debería mostrar que el puerto está en uso
  ```

### Error: "No module named 'confluent_kafka'"

- Instala la librería:
  ```powershell
  pip install confluent-kafka
  ```

### Kafka no inicia

- Verifica que Java esté instalado:
  ```powershell
  java -version
  ```

- Verifica que el puerto 9092 no esté en uso:
  ```powershell
  netstat -an | findstr 9092
  ```

---

## 🎯 Ventajas de Kafka Local

✅ **Gratis**: No hay costos
✅ **Sin límites**: Procesa todo lo que necesites
✅ **Privado**: Todo queda en tu máquina
✅ **Rápido**: Sin latencia de red
✅ **Perfecto para desarrollo**: Ideal para testing

---

## 📊 Comparación: Local vs Cloud

| Característica | Kafka Local | Confluent Cloud |
|---------------|-------------|-----------------|
| Costo | Gratis | Pago por uso |
| Setup | 5 minutos | 2 minutos |
| Límites | Ninguno | Por plan |
| Latencia | Mínima | Depende de red |
| Escalabilidad | Limitada a tu PC | Ilimitada |
| Uso | Desarrollo/Testing | Producción |

---

## 🚀 Próximos Pasos

Una vez configurado Kafka local:

1. ✅ Las respuestas aparecerán en tiempo real (token por token)
2. ✅ Streaming ultra fluido como ChatGPT
3. ✅ Sin costos adicionales
4. ✅ Todo funciona localmente

¡Disfruta del streaming en tiempo real! 🎉


