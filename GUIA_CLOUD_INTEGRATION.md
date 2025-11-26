# ☁️ Guía de Integración con Cloud Storage

## 🎯 ¿Qué hace esto?

Permite que las empresas conecten sus datos en **S3, Google Cloud Storage o Azure Blob** y se procesen **automáticamente** sin intervención manual.

---

## 🚀 Configuración Rápida

### Opción 1: Conectar Bucket Completo (Procesamiento Inmediato)

```bash
# Conectar S3
curl -X POST "http://localhost:8000/api/v1/cloud/connect/s3" \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "mi-bucket-empresa",
    "access_key": "AKIAIOSFODNN7EXAMPLE",
    "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "region": "us-east-1",
    "prefix": "documentos/",
    "auto_process": true
  }'
```

**Resultado**: Todos los PDFs, DOCX, TXT, MD en el bucket se procesan automáticamente.

### Opción 2: Webhooks (Procesamiento Automático en Tiempo Real)

Configura webhooks en tu cloud storage para que notifique cuando se suban archivos nuevos.

#### Para AWS S3:

1. **Configura S3 Event Notifications**:
   - Ve a tu bucket en AWS Console
   - Properties → Event notifications
   - Crea una nueva notificación
   - Event type: `s3:ObjectCreated:*`
   - Destination: HTTP/HTTPS endpoint
   - URL: `http://tu-servidor:8000/api/v1/cloud/webhook/s3`

2. **Cuando se suba un archivo**:
   - S3 envía webhook automáticamente
   - Tu API procesa el archivo
   - Genera resumen, detecta problemas, etc.

#### Para Google Cloud Storage:

1. **Configura Pub/Sub Notifications**:
```bash
gsutil notification create -t docchat-notifications \
  -f json -e OBJECT_FINALIZE \
  gs://mi-bucket
```

2. **Crea un Cloud Function** que envíe al webhook:
```python
def process_gcs_event(event, context):
    import requests
    requests.post(
        'http://tu-servidor:8000/api/v1/cloud/webhook/gcs',
        json=event
    )
```

#### Para Azure Blob Storage:

1. **Configura Event Grid**:
   - Crea un Event Grid subscription
   - Event type: `Blob Created`
   - Endpoint: `http://tu-servidor:8000/api/v1/cloud/webhook/azure`

---

## 📋 Ejemplos Completos

### Python - Conectar S3 y Procesar Automáticamente

```python
import requests

# Conectar bucket
response = requests.post(
    'http://localhost:8000/api/v1/cloud/connect/s3',
    json={
        "bucket_name": "mi-bucket",
        "access_key": "TU_ACCESS_KEY",
        "secret_key": "TU_SECRET_KEY",
        "region": "us-east-1",
        "auto_process": True  # Procesa todos los archivos automáticamente
    }
)

print(response.json())
# {
#   "status": "connected",
#   "bucket": "mi-bucket",
#   "files_found": 150,
#   "files_processed": 150,
#   "auto_processing": true
# }
```

### JavaScript/Node.js - Webhook Handler

```javascript
// Endpoint para recibir webhooks de S3
app.post('/api/v1/cloud/webhook/s3', async (req, res) => {
  const webhookData = req.body;
  
  // Reenviar a DocChat Enterprise API
  const response = await fetch('http://tu-servidor:8000/api/v1/cloud/webhook/s3', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(webhookData)
  });
  
  const result = await response.json();
  console.log('Archivos procesados:', result.files_processed);
  
  res.json(result);
});
```

---

## 🔄 Flujo Automático Completo

```
1. Empresa sube PDF a S3/GCS/Azure
   ↓
2. Cloud Storage envía webhook automáticamente
   ↓
3. DocChat Enterprise API recibe webhook
   ↓
4. Descarga y procesa el archivo automáticamente
   ↓
5. Genera resumen, detecta problemas/oportunidades
   ↓
6. Ejecuta reglas y automatizaciones
   ↓
7. Guarda resultados en memoria para aprendizaje
   ↓
8. Notifica a la empresa (opcional)
```

---

## 🎛️ Configuración Avanzada

### Procesar Solo Archivos Nuevos

```json
{
  "bucket_name": "mi-bucket",
  "prefix": "documentos/2025/",
  "auto_process": true
}
```

### Filtrar por Tipo de Archivo

El sistema automáticamente procesa solo:
- `.pdf`
- `.docx`
- `.txt`
- `.md`

### Procesamiento en Lotes

Si hay muchos archivos, el sistema procesa en lotes de 100 para optimizar rendimiento.

---

## 🔐 Seguridad

### Credenciales

**⚠️ IMPORTANTE**: Nunca expongas credenciales en código.

**Mejores prácticas**:
1. Usa variables de entorno
2. Usa IAM roles (AWS) o Service Accounts (GCS)
3. Rota credenciales regularmente
4. Usa API keys para autenticación

### Ejemplo Seguro:

```python
import os

response = requests.post(
    'http://localhost:8000/api/v1/cloud/connect/s3',
    json={
        "bucket_name": os.getenv("S3_BUCKET"),
        "access_key": os.getenv("AWS_ACCESS_KEY"),
        "secret_key": os.getenv("AWS_SECRET_KEY"),
        "region": os.getenv("AWS_REGION", "us-east-1"),
        "auto_process": True
    },
    headers={"X-API-Key": os.getenv("DOCCHAT_API_KEY")}
)
```

---

## 📊 Monitoreo

### Verificar Estado de Conexión

```bash
curl http://localhost:8000/api/v1/stats
```

### Ver Logs de Procesamiento

Los logs se guardan automáticamente en:
- Auditoría: `docchat_audit/`
- Memoria: `docchat_memory/`

---

## 🆘 Troubleshooting

### Error: "boto3 no está instalado"

```bash
pip install boto3
```

### Error: "google-cloud-storage no está instalado"

```bash
pip install google-cloud-storage
```

### Error: "azure-storage-blob no está instalado"

```bash
pip install azure-storage-blob
```

### Webhook no se recibe

1. Verifica que el endpoint sea accesible públicamente
2. Verifica firewall/security groups
3. Usa HTTPS (recomendado para producción)
4. Verifica logs del cloud storage

---

## 🎯 Casos de Uso Empresariales

### 1. Procesamiento Masivo de Contratos

```
Empresa → Sube 1000 contratos a S3
         ↓
S3 → Webhook → DocChat API
         ↓
Procesa automáticamente todos
         ↓
Detecta cláusulas problemáticas
         ↓
Genera reporte ejecutivo
```

### 2. Análisis Continuo de Documentos

```
Equipo Legal → Sube documentos diariamente
              ↓
GCS → Webhook automático
              ↓
DocChat procesa en tiempo real
              ↓
Notifica problemas críticos
```

### 3. Due Diligence Automatizado

```
M&A Team → Sube documentos de empresa objetivo
          ↓
Azure Blob → Procesamiento automático
          ↓
Detecta riesgos y oportunidades
          ↓
Genera informe para decisión
```

---

## 📞 Soporte

Para más información:
- Documentación API: http://localhost:8000/docs
- `ENTERPRISE_API_README.md` - Guía completa de Enterprise API
- `README_ENTERPRISE.md` - Documentación general

---

**¡Tu empresa ahora puede conectar su cloud storage y procesar documentos automáticamente!** 🚀

