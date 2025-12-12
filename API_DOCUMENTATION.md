# 📚 API Documentation - Ads Optimization Engine

## 🔐 Autenticación

### JWT Token
```bash
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password"
}

Response:
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "user_id": "user_123",
    "tenant_id": "tenant_456",
    "role": "user"
  }
}
```

### API Key
```bash
Authorization: Bearer YOUR_API_KEY
```

## 📤 Endpoints

### 1. Upload Creative Asset
```http
POST /api/v1/assets
Authorization: Bearer {token}
Content-Type: multipart/form-data

{
  "asset_type": "text|image|video",
  "content": "file or text",
  "metadata": {}
}

Response:
{
  "success": true,
  "asset_id": "asset_1234567890",
  "asset_type": "text",
  "file_path": "/path/to/asset",
  "created_at": "2025-01-15T10:30:00"
}
```

### 2. Generate Ad Variations
```http
POST /api/v1/variations/generate
Authorization: Bearer {token}
Content-Type: application/json

{
  "asset_id": "asset_123",
  "num_variations": 5,
  "objective": "awareness",
  "target_audience": {
    "age_range": "25-45",
    "interests": ["technology"]
  }
}

Response:
{
  "success": true,
  "variations": [
    {
      "variation_id": "var_123",
      "headline": "Amazing Product!",
      "description": "Buy now and save!",
      "predicted_ctr": 0.025,
      "predicted_cpc": 2.5,
      "predicted_conversion_prob": 0.15
    }
  ]
}
```

### 3. Predict Performance
```http
POST /api/v1/predictions
Authorization: Bearer {token}
Content-Type: application/json

{
  "variation_ids": ["var_123", "var_456"],
  "platform": "meta",
  "objective": "awareness"
}

Response:
{
  "success": true,
  "predictions": [
    {
      "variation_id": "var_123",
      "predicted_ctr": 0.025,
      "predicted_cpc": 2.5,
      "predicted_conversion_prob": 0.15,
      "quality_score": 0.85
    }
  ]
}
```

### 4. Create and Launch Campaign
```http
POST /api/v1/campaigns
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Summer Sale 2025",
  "platform": "meta",
  "objective": "awareness",
  "budget": 1000.0,
  "asset_id": "asset_123",
  "num_variations": 5,
  "target_audience": {},
  "auto_select_best": true,
  "top_k": 3
}

Response:
{
  "success": true,
  "campaign_id": "campaign_1234567890",
  "campaign_name": "Summer Sale 2025",
  "platform": "meta",
  "status": "active",
  "launch_result": {
    "success": true,
    "platform_id": "123456789"
  },
  "predictions": {
    "avg_predicted_ctr": 0.025,
    "avg_predicted_cpc": 2.5,
    "avg_predicted_conversion_prob": 0.15
  },
  "variations_used": 3
}
```

### 5. Update Performance Metrics
```http
POST /api/v1/campaigns/{campaign_id}/metrics
Authorization: Bearer {token}
Content-Type: application/json

{
  "impressions": 10000,
  "clicks": 200,
  "conversions": 10,
  "spend": 500.0
}

Response:
{
  "success": true,
  "metrics": {
    "ctr": 0.02,
    "cpc": 2.5,
    "cpm": 50.0,
    "cpa": 50.0,
    "roas": 2.0,
    "conversion_rate": 0.05
  }
}
```

### 6. Auto-Optimize Campaign
```http
POST /api/v1/campaigns/{campaign_id}/optimize
Authorization: Bearer {token}

Response:
{
  "success": true,
  "rl_optimization": {
    "bid_multiplier": 1.15,
    "reward": 0.25,
    "action": "increase"
  },
  "scaling_decision": {
    "should_pause": false,
    "should_scale": true,
    "actions": [
      {
        "action": "scale",
        "new_budget": 1500.0
      }
    ]
  },
  "actions_taken": ["Budget aumentado a $1500.00"]
}
```

### 7. Get Campaign Performance
```http
GET /api/v1/campaigns/{campaign_id}/performance
Authorization: Bearer {token}

Response:
{
  "success": true,
  "performance_history": [
    {
      "timestamp": "2025-01-15T10:30:00",
      "impressions": 10000,
      "clicks": 200,
      "conversions": 10,
      "spend": 500.0,
      "ctr": 0.02,
      "cpc": 2.5,
      "roas": 2.0
    }
  ],
  "optimization_summary": {
    "rl_optimizations": 5,
    "scaling_actions": 2,
    "current_bid_multiplier": 1.15
  }
}
```

### 8. Get Billing Summary
```http
GET /api/v1/billing/summary
Authorization: Bearer {token}

Response:
{
  "tenant_id": "tenant_123",
  "plan": "pro",
  "usage": {
    "campaigns": 15,
    "assets": 50,
    "api_calls": 500,
    "predictions": 200
  },
  "quotas": {
    "max_campaigns": 50,
    "max_assets": 500,
    "max_variations": 10,
    "max_api_calls": 1000,
    "max_budget": 10000.0
  },
  "current_usage": {
    "campaigns": 15,
    "assets": 50,
    "api_calls_today": 50
  }
}
```

### 9. Generate Bill
```http
POST /api/v1/billing/generate
Authorization: Bearer {token}

Response:
{
  "billing_id": "bill_tenant_123_202501",
  "tenant_id": "tenant_123",
  "period_start": "2025-01-01T00:00:00",
  "period_end": "2025-01-31T23:59:59",
  "total_amount": 149.50,
  "currency": "USD",
  "items": [
    {
      "description": "Plan pro - Base mensual",
      "quantity": 1,
      "unit_price": 99.0,
      "total": 99.0
    },
    {
      "description": "campaigns usage",
      "quantity": 15,
      "unit_price": 0.10,
      "total": 1.50
    }
  ],
  "status": "pending"
}
```

### 10. Get Alerts
```http
GET /api/v1/alerts
Authorization: Bearer {token}
Query params: ?campaign_id={id}&level={level}

Response:
{
  "success": true,
  "alerts": [
    {
      "alert_id": "alert_123",
      "level": "warning",
      "title": "low_ctr",
      "message": "CTR muy bajo (< 1%)",
      "campaign_id": "campaign_123",
      "timestamp": "2025-01-15T10:30:00",
      "resolved": false
    }
  ]
}
```

## 🔒 Permisos Requeridos

- `CREATE_CAMPAIGN`: Crear campañas
- `EDIT_CAMPAIGN`: Editar campañas
- `DELETE_CAMPAIGN`: Eliminar campañas
- `VIEW_CAMPAIGN`: Ver campañas
- `UPLOAD_ASSET`: Subir assets
- `GENERATE_VARIATIONS`: Generar variaciones
- `LAUNCH_CAMPAIGN`: Lanzar campañas
- `VIEW_BILLING`: Ver facturación
- `MANAGE_TENANT`: Gestionar tenant

## 📊 Rate Limits

- **Meta API**: 200 requests/hora
- **Google Ads**: 100 requests/hora
- **TikTok**: 300 requests/hora
- **Default**: 100 requests/hora

## 🐛 Error Codes

- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden (sin permisos)
- `404`: Not Found
- `429`: Rate Limit Exceeded
- `500`: Internal Server Error
- `503`: Service Unavailable (circuit breaker open)

## 📝 Notas

- Todos los endpoints requieren autenticación
- Rate limits se aplican por tenant
- Las predicciones se cachean por 24 horas
- Las respuestas de APIs se cachean por 5 minutos

