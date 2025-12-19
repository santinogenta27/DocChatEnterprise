# Commerce Module - Sales Agent Completo

Módulo completo de Sales Agent con checkout end-to-end, integración de catálogo de productos, flujo conversacional mejorado y cross-selling automático.

## 🎯 Funcionalidades Implementadas

### ✅ 1. Checkout End-to-End en Chat
- **PaymentProcessor**: Integración real con Stripe y PayPal
- Procesa pagos dentro del chat (sin salir)
- Genera links de pago seguros
- Confirma pagos automáticamente
- Soporta múltiples métodos de pago

### ✅ 2. Integración con Catálogo de Productos
- **ProductCatalog**: Sincronización con Shopify API + catálogo local
- Búsqueda de productos en tiempo real
- Verificación de stock
- Precios actualizados
- Base de datos SQLite persistente

### ✅ 3. Flujo Conversacional Mejorado
- **ConversationalFlow**: Detección de intención del usuario
- Preguntas proactivas basadas en contexto
- Sugerencias inteligentes
- Guía el flujo de compra completo

### ✅ 4. Cross-Selling Automático
- **CrossSellingEngine**: Motor de recomendaciones
- Sugiere productos complementarios
- Recomienda productos similares
- Basado en productos del carrito
- Usa LLM para razonamiento contextual

### ✅ 5. Gestión de Carrito
- **CartManager**: Carrito persistente por sesión
- Agregar/remover items
- Actualizar cantidades
- Calcular totales automáticamente

## 📦 Módulos

```
docchat/commerce/
├── __init__.py
├── payment_processor.py    # Stripe/PayPal integration
├── product_catalog.py      # Shopify + local catalog
├── conversational_flow.py  # Proactive questions & intent detection
├── cross_selling.py        # Product recommendations
└── cart_manager.py        # Cart persistence
```

## 🔧 Configuración

### Variables de Entorno

#### Stripe
```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
```

#### PayPal
```bash
PAYPAL_CLIENT_ID=tu_client_id
PAYPAL_CLIENT_SECRET=tu_client_secret
PAYPAL_MODE=sandbox  # o "live"
```

#### Shopify
```bash
SHOPIFY_SHOP_URL=tu-tienda.myshopify.com
SHOPIFY_ACCESS_TOKEN=tu_access_token
```

## 🚀 Uso

El módulo está integrado en `Prime Agents Mode` → `COMMERCE_AGENT`.

### Crear un Commerce Agent

```python
from docchat import PrimeAgentsMode, AgentTemplate
from docchat.config import load_config

config = load_config()
prime_agents = PrimeAgentsMode(config=config)

# Crear Commerce Agent
agent_id = prime_agents.create_agent(
    name="Mi Sales Agent",
    description="Agente de ventas completo",
    system_prompt="",  # Usa el del template
    template=AgentTemplate.COMMERCE_AGENT
)

# Usar el agente
response = await prime_agents.run_agent(agent_id, "Busco un producto")
```

### Flujo Completo

1. **Usuario**: "Busco zapatos"
2. **Agente**: Usa `query_catalog` → Muestra productos
3. **Usuario**: "Muéstrame el producto X"
4. **Agente**: Usa `get_product` → Muestra detalles
5. **Agente**: Usa `get_recommendations` → Sugiere productos relacionados
6. **Usuario**: "Agrégame 2 al carrito"
7. **Agente**: Usa `add_to_cart` → Confirma agregado
8. **Usuario**: "Quiero pagar"
9. **Agente**: Usa `create_payment_intent` → Genera link de pago
10. **Usuario**: Completa pago
11. **Agente**: Usa `confirm_payment` → Confirma pago
12. **Agente**: Usa `create_order` → Crea orden
13. **Agente**: Usa `send_confirmation` → Envía confirmación

## 🛠️ Herramientas Disponibles

- `query_catalog`: Busca productos
- `get_product`: Obtiene detalles de producto
- `add_to_cart`: Agrega al carrito
- `get_cart`: Muestra carrito
- `update_cart`: Actualiza carrito
- `get_recommendations`: Obtiene recomendaciones
- `create_payment_intent`: Crea intención de pago
- `confirm_payment`: Confirma pago
- `create_order`: Crea orden
- `send_confirmation`: Envía confirmación

## 💡 Características Avanzadas

### Preguntas Proactivas
El agente hace preguntas inteligentes basadas en:
- Intención del usuario (discover, compare, buy, checkout)
- Productos vistos
- Items en el carrito
- Contexto de la conversación

### Cross-Selling Automático
Sugiere productos:
- Complementarios (usando LLM)
- Similares (mismo tipo)
- Populares (mismo tipo)
- Basados en carrito

### Detección de Intención
Detecta automáticamente:
- DISCOVER: Buscar productos
- COMPARE: Comparar productos
- BUY: Comprar
- CHECKOUT: Proceder al pago
- TRACK_ORDER: Rastrear orden

## 📊 Almacenamiento

- **Productos**: SQLite en `.docchat_memory/commerce/catalog/products.db`
- **Carritos**: SQLite en `.docchat_memory/commerce/carts/carts.db`
- **Logs**: `.docchat_memory/top_ads_logs/`

## ⚠️ Notas

- En modo desarrollo (sin API keys), se usan simulaciones
- Para producción, configura todas las variables de entorno
- El catálogo se sincroniza manualmente con `sync_from_shopify()`
- Los carritos persisten por sesión (session_id)

## 🔮 Próximas Mejoras

- [ ] Sincronización automática de catálogo (cron job)
- [ ] Integración con Meta Pay
- [ ] Widget embebible para sitios web
- [ ] Tracking de productos vistos
- [ ] Historial de compras del usuario
- [ ] Cupones y descuentos automáticos




