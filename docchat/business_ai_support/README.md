# Business AI Support

Agente oficial de soporte al cliente **24/7** en todos los canales.

## Rol del producto

- Un único agente que:
  - Conoce el catálogo y stock en tiempo real
  - Arma el carrito y cobra en el chat (Stripe/PayPal vía `PaymentProcessor`)
  - Da estado de pedidos y gestiona devoluciones
  - Escala a un humano cuando detecta frustración o el usuario lo pide

## Arquitectura

- `business_ai_mode.py`: modo principal (`BusinessAISupportMode`)
- `agents/business_ai_agent.py`: orquestador de ventas + soporte
- `state/customer_session.py`: estado unificado de cliente
- `sentiment/sentiment_analyzer.py`: detección de sentimiento y frustración
- `tools/`: wrappers hacia catálogo, carrito, pagos, pedidos, tickets
- `channels/base.py`: adaptadores de canal (web, WhatsApp, IG, Messenger)

## Uso básico

```python
from docchat.business_ai_support import BusinessAISupportMode
from docchat.config import load_config

config = load_config()
mode = BusinessAISupportMode(config=config)

# Mensaje desde webchat
payload = {
    "session_id": "user-123",
    "user_id": "user-123",
    "message": "¿Tienen zapatillas talla 42 en negro?",
    "channel": "web",
}

response = mode.process_message(payload, channel="web")
print(response["text"])
```

## API HTTP (FastAPI)

```python
from fastapi import FastAPI
from docchat.business_ai_support import BusinessAISupportMode
from docchat.config import load_config

app = FastAPI()
mode = BusinessAISupportMode(config=load_config())
app.include_router(mode.get_api_router())
```

## Gradio Demo

```python
mode = BusinessAISupportMode(config=load_config())
iface = mode.get_gradio_interface()
iface.launch()
```

## Widget Embeddable

Business AI Support incluye un **widget embeddable** listo para integrar en cualquier sitio web:

```html
<!-- Agregar antes de </body> -->
<script src="https://tu-dominio.com/business-ai-support/widget.js"></script>
<script>
  BusinessAIWidget.init({
    apiUrl: 'https://tu-dominio.com',
    primaryColor: '#007bff',
    position: 'bottom-right',
    brandName: 'Mi Empresa'
  });
</script>
```

**Características del Widget:**
- ✅ HTML/JS completo y funcional
- ✅ Código de embed simple (un solo `<script>` tag)
- ✅ Personalización visual (colores, logo, posición)
- ✅ Responsive y mobile-friendly
- ✅ API pública para control programático

Ver `widget/README.md` para documentación completa del widget.

## Integraciones Disponibles

### CRM (Integración Profunda)
- ✅ **Salesforce** - Create/update cases, contacts, accounts
- ✅ **HubSpot** - Create/update contacts, deals, tickets
- ✅ **Zendesk** - Create/update tickets, users, organizations

### E-commerce
- ✅ **Shopify** - Catálogo en tiempo real
- ✅ **WooCommerce** - Catálogo en tiempo real

### Canales Omnicanales
- ✅ **Web** - Widget embeddable
- ✅ **WhatsApp** - Via Twilio o Meta Business API
- ✅ **Instagram DM** - Via Meta API
- ✅ **Facebook Messenger** - Via Meta Platform

## Nota

Este modo es **independiente** de `PrimeAgentsMode`, `COMMERCE_AGENT` y `customer_service_24_7`,
pero reutiliza internamente módulos de comercio (catálogo, carrito, pagos) y deja hooks/listos
para conectar con sistemas de soporte y pedidos externos.


































