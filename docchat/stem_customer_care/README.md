# STEM Customer Care

Agente oficial de la empresa para **ventas + soporte + postventa 24/7** en todos los canales.

## Rol del producto

- Un único agente que:
  - Conoce el catálogo y stock en tiempo real
  - Arma el carrito y cobra en el chat (Stripe/PayPal vía `PaymentProcessor`)
  - Da estado de pedidos y gestiona devoluciones
  - Escala a un humano cuando detecta frustración o el usuario lo pide

## Arquitectura

- `stem_customer_care_mode.py`: modo principal (`StemCustomerCareMode`)
- `agents/stem_customer_care_agent.py`: orquestador de ventas + soporte
- `state/customer_session.py`: estado unificado de cliente
- `sentiment/sentiment_analyzer.py`: detección de sentimiento y frustración
- `tools/`: wrappers hacia catálogo, carrito, pagos, pedidos, tickets
- `channels/base.py`: adaptadores de canal (web, WhatsApp, IG, Messenger)

## Uso básico

```python
from docchat.stem_customer_care import StemCustomerCareMode
from docchat.config import load_config

config = load_config()
mode = StemCustomerCareMode(config=config)

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
from docchat.stem_customer_care import StemCustomerCareMode
from docchat.config import load_config

app = FastAPI()
mode = StemCustomerCareMode(config=load_config())
app.include_router(mode.get_api_router())
```

## Gradio Demo

```python
mode = StemCustomerCareMode(config=load_config())
iface = mode.get_gradio_interface()
iface.launch()
```

## Nota

Este modo es **independiente** de `PrimeAgentsMode`, `COMMERCE_AGENT` y `customer_service_24_7`,
pero reutiliza internamente módulos de comercio (catálogo, carrito, pagos) y deja hooks/listos
para conectar con sistemas de soporte y pedidos externos.
