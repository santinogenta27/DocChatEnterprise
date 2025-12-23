# ADVERTISING TOP MANAGER - Advanced Features Integration

## Resumen de Funcionalidades Integradas

Este documento describe todas las funcionalidades avanzadas integradas en **ADVERTISING TOP MANAGER** basadas en investigación de vanguardia.

## 🎨 1. Content-Aware Layout Generation

**Basado en:** Content-Aware Ad Banner Layout Generation with Two-Stage Chain-of-Thought in Vision Language Models

### Características:
- Generación de layouts de banners publicitarios usando Vision-Language Models
- Dos etapas de Chain-of-Thought:
  1. **Placement Plan Generation**: El VLM analiza la imagen y genera un plan de colocación
  2. **HTML Layout Generation**: Genera código HTML basado en el plan

### Uso:
```python
layout_result = advertising_top_manager_mode.generate_content_aware_layout(
    background_image_path="path/to/image.jpg",
    element_types=["text", "logo", "underlay"],
    canvas_size=(1024, 1500)
)
```

## 📊 2. Multi-Product Influence Maximization

**Basado en:** 
- Multi-product Influence Maximization in Billboard Advertisement
- Balanced Popularity in Multi-Product Billboard Advertisement

### Características:
- Optimización de slots de billboards para múltiples productos
- Tres estrategias:
  - **Common Slots**: Un conjunto de slots para todos los productos
  - **Disjoint Slots**: Slots separados para cada producto
  - **Balanced**: Maximiza influencia manteniendo balance entre productos

### Uso:
```python
result = advertising_top_manager_mode.optimize_multi_product_influence(
    products=[
        {"product_id": "p1", "influence_demand": 1000, "budget": 1000, "target_users": ["u1", "u2"]},
        {"product_id": "p2", "influence_demand": 800, "budget": 800, "target_users": ["u3", "u4"]}
    ],
    slots=[...],
    strategy="balanced",
    budgets={"p1": 1000, "p2": 800}
)
```

## 🧠 3. MindFuse: Marketing Strategy Co-Creation

**Basado en:** MindFuse: Towards GenAI Explainability in Marketing Strategy Co-Creation

### Características:
- Extracción de Content Pillars de corpus de anuncios
- Mining de Customer Personas mediante clustering
- Identificación de Communication Themes
- Generación de Campaign Narratives

### Uso:
```python
strategy = advertising_top_manager_mode.co_create_marketing_strategy(
    ad_corpus=[...],  # Lista de anuncios para análisis
    product_info={"title": "...", "category": "...", "attributes": {...}}
)
# Retorna: personas, themes, campaign_narratives
```

## 🎯 4. CTR-Driven Image Generation

**Basado en:** CTR-Driven Advertising Image Generation with Multimodal Large Language Models

### Características:
- Generación de imágenes publicitarias optimizadas para CTR
- Uso de MLLMs para generar descripciones de fondo
- Predicción de CTR usando Reward Model
- Product-Centric Preference Optimization (PCPO)

### Uso:
```python
result = advertising_top_manager_mode.generate_ctr_optimized_image(
    product_info={
        "product_id": "prod_123",
        "title": "Wireless Earbuds",
        "category": "Electronics",
        "attributes": {"color": "black", "price": 49.99},
        "image_path": "path/to/product.jpg"
    }
)
# Retorna: image_path, background_description, predicted_ctr, product_alignment_score
```

## 📈 5. Multi-Attribution Learning

**Basado en:** See Beyond a Single View: Multi-Attribution Learning Leads to Better Conversion Rate Prediction

### Características:
- Predicción de CVR usando múltiples mecanismos de atribución:
  - Last-Click
  - First-Click
  - Linear
  - Multi-Touch Attribution (MTA)
- Attribution Knowledge Aggregator (AKA)
- Primary Target Predictor (PTP)
- CAT (Cartesian-based Auxiliary Training)

### Uso:
```python
cvr_prediction = advertising_top_manager_mode.predict_cvr_multi_attribution(
    features=[...],  # Feature vector
    touchpoints=[  # Lista de interacciones
        {"id": "tp1", "timestamp": "...", "ad_id": "ad1"},
        {"id": "tp2", "timestamp": "...", "ad_id": "ad2"}
    ]
)
```

## 🔮 6. Market Forecasting DSS

**Basado en:** AI-Integrated Decision Support System for Real-Time Market Growth Forecasting and Multi-Source Content Diffusion Analytics

### Características:
- Forecasting de crecimiento de mercado usando GNN + Temporal Transformer
- Análisis de difusión de contenido multi-fuente
- Inferencia causal para estimar efectos de intervenciones
- Recomendaciones estratégicas automáticas

### Uso:
```python
forecast = advertising_top_manager_mode.forecast_market_growth(
    nodes=[...],  # Nodos del grafo de difusión
    interactions=[("node1", "node2", 0.8), ...],  # Aristas con pesos
    metrics_history=[  # Histórico de métricas
        {"timestamp": "...", "reach": 10000, "ctr": 0.02, ...}
    ],
    forecast_horizon=7  # días
)
# Retorna: forecasted_metrics, confidence_intervals, recommendations, causal_effects
```

## 🚀 Integración Completa

Todas estas funcionalidades están integradas en el modo `AdvertisingTopManagerMode` y pueden ser accedidas directamente:

```python
from docchat.advertising_top_manager import AdvertisingTopManagerMode
from docchat.config import load_config

config = load_config()
mode = AdvertisingTopManagerMode(config=config)

# Todas las funcionalidades disponibles:
# - mode.layout_generator
# - mode.influence_optimizer
# - mode.mindfuse
# - mode.ctr_generator
# - mode.multi_attribution
# - mode.market_forecaster
```

## 📝 Notas de Implementación

- Todos los módulos están diseñados para funcionar de forma independiente
- Se manejan errores gracefully si algún módulo no está disponible
- Los módulos pueden ser inicializados opcionalmente según disponibilidad de dependencias
- La integración en Gradio UI está pendiente (se agregará en futuras actualizaciones)

## 🔧 Dependencias

- LangChain (para módulos con LLMs)
- PyTorch (para módulos de deep learning)
- NumPy (para cálculos matemáticos)
- OpenAI API Key (para modelos VLM/LLM)

