# 🚀 Guía de API de Integraciones

## Endpoints Disponibles

### 1. Listar Integraciones Conectadas

```bash
GET /api/v1/integrations/?user_id=user123
```

**Respuesta:**
```json
{
  "connections": [
    {
      "integration_id": "abc123",
      "integration_type": "gmail",
      "status": "active",
      "connected_at": "2025-11-29 20:00:00"
    }
  ],
  "total": 1
}
```

### 2. Buscar en Todas las Integraciones

```bash
POST /api/v1/integrations/search
Content-Type: application/json

{
  "query": "emails de hoy",
  "max_results": 10,
  "user_id": "user123"
}
```

**Respuesta:**
```json
{
  "query": "emails de hoy",
  "total_results": 5,
  "integrations_searched": 2,
  "results": {
    "gmail": {
      "documents": [...],
      "count": 3
    },
    "slack": {
      "documents": [...],
      "count": 2
    }
  }
}
```

### 3. Buscar en una Integración Específica

```bash
GET /api/v1/integrations/gmail/search?query=emails%20de%20hoy&max_results=5
```

### 4. Estado de Sincronización

```bash
GET /api/v1/integrations/sync/status
```

**Respuesta:**
```json
{
  "status": "running",
  "sync_interval_minutes": 15,
  "stats": {
    "last_sync": "2025-11-29T20:15:00",
    "total_syncs": 10,
    "last_sync_results": {
      "gmail": 5,
      "slack": 3
    }
  }
}
```

### 5. Disparar Sincronización Manual

```bash
POST /api/v1/integrations/sync/trigger
```

### 6. Obtener Datos del Caché

```bash
GET /api/v1/integrations/cache/gmail?query=emails
```

## Ejemplos de Uso

### Python

```python
import requests

# Buscar en todas las integraciones
response = requests.post(
    "http://localhost:8000/api/v1/integrations/search",
    json={
        "query": "emails de hoy",
        "max_results": 10
    }
)
results = response.json()
print(f"Encontrados {results['total_results']} resultados")
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

// Buscar en Gmail específicamente
const response = await axios.get(
  'http://localhost:8000/api/v1/integrations/gmail/search',
  {
    params: {
      query: 'emails de hoy',
      max_results: 5
    }
  }
);

console.log(`Encontrados ${response.data.count} emails`);
```

### cURL

```bash
# Listar integraciones
curl http://localhost:8000/api/v1/integrations/

# Buscar
curl -X POST http://localhost:8000/api/v1/integrations/search \
  -H "Content-Type: application/json" \
  -d '{"query": "emails de hoy", "max_results": 5}'

# Estado de sincronización
curl http://localhost:8000/api/v1/integrations/sync/status
```

## Características

✅ **Sincronización Automática**: Los datos se sincronizan cada 15 minutos automáticamente
✅ **Caché Inteligente**: Respuestas rápidas usando datos en caché
✅ **Búsqueda en Tiempo Real**: Si no hay caché, busca en tiempo real
✅ **API RESTful**: Endpoints estándar y fáciles de usar
✅ **Documentación Automática**: Disponible en `/docs` cuando corras el servidor


