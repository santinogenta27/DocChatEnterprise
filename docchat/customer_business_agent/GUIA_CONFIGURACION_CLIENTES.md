# 📖 Guía de Configuración para Clientes - Customer Business Agent

## 🚀 Configuración Rápida (5 minutos)

### Paso 1: Configuración Básica (OBLIGATORIO)

1. **Obtén tu API Key de Groq:**
   - Ve a https://console.groq.com
   - Crea una cuenta (gratis)
   - Genera una API Key

2. **Configura en tu archivo `.env`:**
   ```env
   GROQ_API_KEY=tu-clave-groq-aqui
   ```

3. **¡Listo!** El agente ya funciona básico.

### Paso 2: Personalización (OPCIONAL pero Recomendado)

Edita `docchat/customer_business_agent/config/chatbot_config.json`:

```json
{
  "tone": "friendly",
  "personality": "Eres un experto en atención al cliente",
  "custom_instructions": "Siempre prioriza la satisfacción del cliente",
  "brand_name": "Tu Marca"
}
```

### Paso 3: Integración con CRM (OPCIONAL)

Si usas HubSpot, Salesforce o Pipedrive:

1. **Obtén tu API Key del CRM**

2. **Configura en `.env`:**
   ```env
   # Para HubSpot
   HUBSPOT_API_KEY=tu-api-key
   
   # Para Salesforce
   SALESFORCE_INSTANCE_URL=https://tu-instancia.salesforce.com
   SALESFORCE_ACCESS_TOKEN=tu-access-token
   ```

3. **Configura en `chatbot_config.json`:**
   ```json
   {
     "crm_type": "hubspot",
     "crm_webhook_url": "https://tu-crm.com/webhook"
   }
   ```

### Paso 4: Integración con E-commerce (OPCIONAL)

Si usas Shopify o WooCommerce:

**Shopify:**
1. Crea una App Private en Shopify
2. Obtén el Access Token
3. Configura en `chatbot_config.json`:
   ```json
   {
     "ecommerce_enabled": true,
     "ecommerce_platform": "shopify",
     "shopify_shop_name": "tu-tienda",
     "shopify_api_key": "tu-access-token"
   }
   ```

**WooCommerce:**
1. Ve a WooCommerce > Settings > Advanced > REST API
2. Crea una nueva API Key
3. Configura en `chatbot_config.json`:
   ```json
   {
     "ecommerce_enabled": true,
     "ecommerce_platform": "woocommerce",
     "woocommerce_url": "https://tu-tienda.com",
     "woocommerce_consumer_key": "ck_...",
     "woocommerce_consumer_secret": "cs_..."
   }
   ```

### Paso 5: Knowledge Base (OPCIONAL)

1. Ve al tab "Configuración RAG" en la interfaz
2. Sube tus documentos (PDF, DOCX, TXT)
3. Haz click en "Procesar Documentos"
4. El agente usará esta información para responder

## ✅ Verificación

Después de configurar, prueba:

1. Abre el tab "💼 Customer Business Agent"
2. Escribe: "Hola, ¿qué productos tienen?"
3. El agente debe responder de forma natural

## 🆘 Troubleshooting

### Error: "GROQ_API_KEY requerida"
- **Solución:** Agrega `GROQ_API_KEY=tu-clave` en tu archivo `.env`

### Error: "Error inicializando CRM"
- **Solución:** Verifica que tu API Key sea correcta y tenga permisos

### Error: "No hay documentos RAG procesados"
- **Solución:** Sube y procesa documentos en el tab "Configuración RAG"

### El agente no responde bien
- **Solución:** Verifica que `GROQ_API_KEY` sea válida y tenga créditos

## 📞 Soporte

Si tienes problemas:
1. Revisa los logs en la consola
2. Verifica que todas las API Keys sean válidas
3. Contacta con soporte técnico

