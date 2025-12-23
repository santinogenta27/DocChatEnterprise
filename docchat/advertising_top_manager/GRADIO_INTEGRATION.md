# 🎨 Integración de Advertising Top Manager en Gradio UI

## 📋 Resumen

He creado un módulo completo `gradio_ui.py` que proporciona una interfaz simple y visual para que personas normales puedan crear y publicar anuncios automáticamente.

## ✅ Lo que está Implementado

### 1. Módulo `gradio_ui.py` ✅
- Función `create_campaign_from_ui()`: Crea campañas desde la UI
- Función `create_gradio_interface()`: Crea la interfaz completa de Gradio
- Validación completa de inputs
- Manejo de errores robusto
- Formateo de resultados

### 2. Funcionalidades de la UI ✅
- ✅ Upload de imágenes múltiples
- ✅ Upload de videos múltiples
- ✅ Configuración de nombre de campaña
- ✅ Configuración de presupuesto diario
- ✅ Selección de objetivo (CONVERSIONS, TRAFFIC, etc.)
- ✅ Selección de plataformas (Meta, Google, Ambas)
- ✅ Checkbox para publicación automática (ACTIVE) vs PAUSED
- ✅ Input de landing page URL (opcional)
- ✅ Input de target audience JSON (opcional)
- ✅ Botón "Crear y Publicar Campaña"
- ✅ Mostrar resultado con links a campañas

## 🔧 Cómo Integrar en app.py

### Paso 1: Agregar Import (ya está hecho en app.py)

```python
from docchat.advertising_top_manager import AdvertisingTopManagerMode
from docchat.advertising_top_manager.gradio_ui import create_campaign_from_ui
```

### Paso 2: Agregar Función Helper en app.py

Agregar esta función en app.py (después de las otras funciones helper):

```python
def create_advertising_campaign_ui(
    campaign_name: str,
    daily_budget: float,
    objective: str,
    platforms: str,
    auto_publish: bool,
    image_files,
    video_files,
    landing_page_url: str = "",
    target_audience: str = ""
):
    """Helper function para crear campaña desde UI."""
    from docchat.advertising_top_manager.gradio_ui import create_campaign_from_ui
    
    return create_campaign_from_ui(
        campaign_name=campaign_name,
        daily_budget=daily_budget,
        objective=objective,
        platforms=platforms,
        auto_publish=auto_publish,
        image_files=image_files,
        video_files=video_files,
        landing_page_url=landing_page_url,
        target_audience=target_audience,
        mode_instance=advertising_top_manager_mode
    )
```

### Paso 3: Agregar Tab en la Interfaz de Gradio

Buscar donde están los tabs (probablemente cerca del final de app.py donde se crea `demo` o `interface`) y agregar:

```python
with gr.Tab("📈 Advertising Top Manager"):
    gr.Markdown("""
    # 📈 Advertising Top Manager
    
    ## 🚀 Crea y Publica Anuncios Automáticamente en Meta y Google Ads
    
    **Características:**
    - ✅ Publicación automática en Meta (Facebook/Instagram) y Google Ads
    - ✅ IA genera copy y variaciones automáticamente
    - ✅ Análisis de imágenes/videos con visión computacional
    - ✅ Optimización automática de campañas
    """)
    
    if not advertising_top_manager_mode:
        gr.Markdown("⚠️ **Advertising Top Manager no está disponible.** Verifica que las credenciales de Meta y Google Ads estén configuradas.")
    else:
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📸 Sube tus Assets")
                
                image_files = gr.File(
                    label="Imágenes",
                    file_count="multiple",
                    file_types=["image"],
                    type="filepath"
                )
                
                video_files = gr.File(
                    label="Videos",
                    file_count="multiple",
                    file_types=["video"],
                    type="filepath"
                )
            
            with gr.Column(scale=1):
                gr.Markdown("### ⚙️ Configuración de Campaña")
                
                campaign_name = gr.Textbox(
                    label="Nombre de la Campaña",
                    placeholder="Ej: Oferta Verano 2025"
                )
                
                daily_budget = gr.Number(
                    label="Presupuesto Diario (USD)",
                    value=50.0,
                    minimum=1.0,
                    maximum=10000.0
                )
                
                objective = gr.Dropdown(
                    label="Objetivo",
                    choices=[
                        ("Conversiones", "CONVERSIONS"),
                        ("Tráfico", "TRAFFIC"),
                        ("Engagement", "ENGAGEMENT"),
                        ("Alcance", "AWARENESS"),
                        ("Generación de Leads", "LEAD_GENERATION"),
                        ("Ventas", "SALES")
                    ],
                    value="CONVERSIONS"
                )
                
                platforms = gr.Dropdown(
                    label="Plataformas",
                    choices=[
                        ("Meta (Facebook/Instagram)", "meta"),
                        ("Google Ads", "google"),
                        ("Ambas", "both")
                    ],
                    value="both"
                )
                
                auto_publish = gr.Checkbox(
                    label="🚀 Publicar Automáticamente (ACTIVE)",
                    value=True,
                    info="Si está marcado, los anuncios se publicarán automáticamente"
                )
                
                landing_page_url = gr.Textbox(
                    label="URL de Página de Destino (Opcional)",
                    placeholder="https://tu-sitio.com/producto"
                )
                
                target_audience = gr.Textbox(
                    label="Audiencia Objetivo (JSON Opcional)",
                    placeholder='{"age_min": 25, "age_max": 45}',
                    lines=3
                )
        
        create_btn = gr.Button("🚀 Crear y Publicar Campaña", variant="primary", size="lg")
        
        result_output = gr.Markdown(label="Resultado")
        result_json = gr.JSON(label="Datos de la Campaña", visible=False)
        
        create_btn.click(
            fn=create_advertising_campaign_ui,
            inputs=[campaign_name, daily_budget, objective, platforms, auto_publish, image_files, video_files, landing_page_url, target_audience],
            outputs=[result_output, result_json]
        )
```

## 🧪 Testing

### Testing Manual

1. **Iniciar la aplicación:**
   ```bash
   python app.py
   ```

2. **Acceder al tab "📈 Advertising Top Manager"**

3. **Crear una campaña de prueba:**
   - Subir una imagen
   - Configurar nombre: "Test Campaign"
   - Presupuesto: $50
   - Objetivo: CONVERSIONS
   - Plataformas: Meta
   - Marcar "Publicar Automáticamente"
   - Click en "Crear y Publicar Campaña"

4. **Verificar resultado:**
   - Debe mostrar mensaje de éxito
   - Debe mostrar campaign_id
   - Debe mostrar links a campañas de Meta
   - Si auto_publish=True, los anuncios deben estar ACTIVE

### Testing con Credenciales Reales

**Requisitos:**
- Meta Ads credentials configuradas en .env
- Google Ads credentials configuradas (opcional)
- META_PAGE_ID configurado

**Pasos:**
1. Configurar credenciales en `.env`:
   ```
   META_ACCESS_TOKEN=tu_token
   META_APP_ID=tu_app_id
   META_APP_SECRET=tu_secret
   META_AD_ACCOUNT_ID=tu_ad_account_id
   META_PAGE_ID=tu_page_id
   ```

2. Crear campaña desde UI

3. Verificar en Meta Ads Manager:
   - La campaña debe existir
   - Los anuncios deben estar ACTIVE (si auto_publish=True)
   - Los anuncios deben tener copy generado automáticamente

## 🐛 Solución de Problemas

### Error: "Advertising Top Manager no está inicializado"
- Verificar que las credenciales estén configuradas
- Verificar que `advertising_top_manager_mode` no sea None

### Error: "No se pudieron crear campañas"
- Verificar credenciales de Meta/Google
- Verificar que META_PAGE_ID esté configurado
- Verificar logs para detalles del error

### Los anuncios se crean como PAUSED aunque auto_publish=True
- Verificar que el bug fix esté aplicado en `ads_agent.py` línea 535
- Verificar que `auto_activate=True` se pase correctamente a `CampaignRequest`

## ✅ Checklist de Implementación

- [x] Crear módulo `gradio_ui.py`
- [x] Implementar función `create_campaign_from_ui()`
- [x] Implementar función `create_gradio_interface()`
- [ ] Agregar función helper en app.py
- [ ] Agregar tab en interfaz de Gradio
- [ ] Testing manual
- [ ] Testing con credenciales reales

## 📝 Notas

- La UI es simple e intuitiva para personas normales (no técnicos)
- El sistema genera copy y variaciones automáticamente
- Los anuncios se publican automáticamente si `auto_publish=True`
- Se puede usar con Meta, Google, o ambas plataformas
- Todos los inputs tienen validación y manejo de errores

