"""
Ads Optimization Mode - Interfaz Gradio para el Ads Optimization Engine
"""

from __future__ import annotations

import json
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

import gradio as gr

from .config import AppConfig
from .ads_optimization_engine import (
    CreativeType,
    CampaignObjective,
    Platform,
    PerformanceMetrics
)
from .ads_optimization.engine_production import ProductionAdsOptimizationEngine
from .utils.llm_factory import create_llm


class AdsOptimizationMode:
    """Modo de optimización de anuncios con interfaz Gradio"""
    
    def __init__(self, config: AppConfig, tenant_id: Optional[str] = None):
        self.config = config
        self.llm = create_llm(config, provider="openai")
        # Usar engine de producción
        self.engine = ProductionAdsOptimizationEngine(config, self.llm, tenant_id=tenant_id or "default")
    
    def create_interface(self) -> gr.Blocks:
        """Crea la interfaz Gradio"""
        with gr.Blocks(title="🚀 Ads Optimization Engine", theme=gr.themes.Soft()) as interface:
            gr.Markdown("""
            # 🚀 Ads Optimization Engine
            ## Motor completo de optimización de anuncios similar a Meta's Advantage+ / Google Performance Max
            
            ### Características:
            - ✅ Subida de assets creativos (texto, imágenes, videos)
            - ✅ Generación de múltiples variaciones usando AI generativa
            - ✅ Predicción de CTR / CPC / Probabilidad de conversión antes de gastar dinero
            - ✅ Selección automática de los mejores creativos
            - ✅ Generación y lanzamiento de campañas a través de Meta/Google/TikTok APIs
            - ✅ Auto-optimización diaria usando RL (reinforcement learning bidding)
            - ✅ Pausar anuncios malos + escalar buenos automáticamente
            """)
            
            with gr.Tabs():
                # TAB 1: Upload Creative Assets
                with gr.Tab("📤 Subir Assets Creativos"):
                    gr.Markdown("### Sube tus assets creativos (texto, imágenes, videos)")
                    
                    with gr.Row():
                        asset_type = gr.Dropdown(
                            choices=["text", "image", "video"],
                            value="text",
                            label="Tipo de Asset",
                            info="Selecciona el tipo de asset que vas a subir"
                        )
                    
                    with gr.Row():
                        text_input = gr.Textbox(
                            label="Contenido de Texto",
                            placeholder="Escribe el texto de tu anuncio aquí...",
                            lines=5,
                            visible=True
                        )
                        image_input = gr.Image(
                            label="Imagen",
                            type="filepath",
                            visible=False
                        )
                        video_input = gr.Video(
                            label="Video",
                            visible=False
                        )
                    
                    asset_metadata = gr.JSON(
                        label="Metadata (opcional)",
                        value={},
                        visible=False
                    )
                    
                    upload_btn = gr.Button("📤 Subir Asset", variant="primary")
                    upload_output = gr.JSON(label="Resultado")
                    
                    def toggle_asset_input(asset_type_val):
                        if asset_type_val == "text":
                            return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)
                        elif asset_type_val == "image":
                            return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)
                        else:  # video
                            return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)
                    
                    asset_type.change(
                        fn=toggle_asset_input,
                        inputs=[asset_type],
                        outputs=[text_input, image_input, video_input]
                    )
                    
                    def upload_asset_async(asset_type_val, text_val, image_val, video_val, metadata_val):
                        try:
                            creative_type = CreativeType(asset_type_val)
                            
                            if asset_type_val == "text":
                                content = text_val
                            elif asset_type_val == "image":
                                content = Path(image_val) if image_val else None
                            else:  # video
                                content = Path(video_val) if video_val else None
                            
                            if content is None:
                                return {"success": False, "error": "No se proporcionó contenido"}
                            
                            asset = asyncio.run(
                                self.engine.upload_creative_asset(
                                    creative_type,
                                    content,
                                    metadata_val if metadata_val else None
                                )
                            )
                            
                            return {
                                "success": True,
                                "asset_id": asset.asset_id,
                                "asset_type": asset.asset_type.value,
                                "file_path": asset.file_path,
                                "created_at": asset.created_at
                            }
                        except Exception as e:
                            return {"success": False, "error": str(e)}
                    
                    upload_btn.click(
                        fn=upload_asset_async,
                        inputs=[asset_type, text_input, image_input, video_input, asset_metadata],
                        outputs=upload_output
                    )
                
                # TAB 2: Generate Ad Variations
                with gr.Tab("🎨 Generar Variaciones"):
                    gr.Markdown("### Genera múltiples variaciones de tus anuncios usando AI")
                    
                    asset_id_input = gr.Textbox(
                        label="Asset ID",
                        placeholder="Ingresa el ID del asset (del paso anterior)",
                        info="ID del asset que quieres usar como base"
                    )
                    
                    num_variations = gr.Slider(
                        minimum=1,
                        maximum=10,
                        value=5,
                        step=1,
                        label="Número de Variaciones",
                        info="Cuántas variaciones quieres generar"
                    )
                    
                    objective = gr.Dropdown(
                        choices=[obj.value for obj in CampaignObjective],
                        value=CampaignObjective.AWARENESS.value,
                        label="Objetivo de Campaña"
                    )
                    
                    target_audience = gr.JSON(
                        label="Audiencia Objetivo (opcional)",
                        value={},
                        info='Ejemplo: {"age_range": "25-45", "interests": ["technology", "business"]}'
                    )
                    
                    generate_btn = gr.Button("🎨 Generar Variaciones", variant="primary")
                    variations_output = gr.JSON(label="Variaciones Generadas")
                    
                    def generate_variations_async(asset_id, num_var, obj_val, audience_val):
                        try:
                            obj = CampaignObjective(obj_val)
                            variations = asyncio.run(
                                self.engine.generate_ad_variations(
                                    asset_id,
                                    int(num_var),
                                    obj,
                                    audience_val if audience_val else None
                                )
                            )
                            
                            return {
                                "success": True,
                                "num_variations": len(variations),
                                "variations": [
                                    {
                                        "variation_id": v.variation_id,
                                        "headline": v.headline,
                                        "description": v.description,
                                        "metadata": v.metadata
                                    }
                                    for v in variations
                                ]
                            }
                        except Exception as e:
                            return {"success": False, "error": str(e)}
                    
                    generate_btn.click(
                        fn=generate_variations_async,
                        inputs=[asset_id_input, num_variations, objective, target_audience],
                        outputs=variations_output
                    )
                
                # TAB 3: Predict Performance
                with gr.Tab("🔮 Predecir Performance"):
                    gr.Markdown("### Predice CTR, CPC y probabilidad de conversión antes de gastar dinero")
                    
                    variation_ids_input = gr.Textbox(
                        label="Variation IDs (separados por comas)",
                        placeholder="var_123, var_456, var_789",
                        info="IDs de las variaciones que quieres evaluar"
                    )
                    
                    platform_pred = gr.Dropdown(
                        choices=[p.value for p in Platform],
                        value=Platform.META.value,
                        label="Plataforma"
                    )
                    
                    objective_pred = gr.Dropdown(
                        choices=[obj.value for obj in CampaignObjective],
                        value=CampaignObjective.AWARENESS.value,
                        label="Objetivo"
                    )
                    
                    predict_btn = gr.Button("🔮 Predecir Performance", variant="primary")
                    predictions_output = gr.JSON(label="Predicciones")
                    
                    def predict_performance_async(var_ids_str, platform_val, obj_val):
                        try:
                            var_ids = [v.strip() for v in var_ids_str.split(",")]
                            platform = Platform(platform_val)
                            obj = CampaignObjective(obj_val)
                            
                            # Obtener variaciones (simplificado - en producción se cargarían desde DB)
                            # Por ahora, crear variaciones dummy para demostración
                            from .ads_optimization_engine import AdVariation
                            variations = []
                            for var_id in var_ids:
                                variation = AdVariation(
                                    variation_id=var_id,
                                    original_asset_id="dummy",
                                    headline=f"Headline para {var_id}",
                                    description=f"Description para {var_id}"
                                )
                                variations.append(variation)
                            
                            variations = asyncio.run(
                                self.engine.predict_performance(variations, platform, obj)
                            )
                            
                            return {
                                "success": True,
                                "predictions": [
                                    {
                                        "variation_id": v.variation_id,
                                        "predicted_ctr": round(v.predicted_ctr, 4),
                                        "predicted_cpc": round(v.predicted_cpc, 2),
                                        "predicted_conversion_prob": round(v.predicted_conversion_prob, 4)
                                    }
                                    for v in variations
                                ]
                            }
                        except Exception as e:
                            return {"success": False, "error": str(e)}
                    
                    predict_btn.click(
                        fn=predict_performance_async,
                        inputs=[variation_ids_input, platform_pred, objective_pred],
                        outputs=predictions_output
                    )
                
                # TAB 4: Create & Launch Campaign
                with gr.Tab("🚀 Crear y Lanzar Campaña"):
                    gr.Markdown("### Crea y lanza una campaña completa automáticamente")
                    
                    campaign_name = gr.Textbox(
                        label="Nombre de Campaña",
                        placeholder="Mi Campaña de Verano 2025"
                    )
                    
                    platform_launch = gr.Dropdown(
                        choices=[p.value for p in Platform],
                        value=Platform.META.value,
                        label="Plataforma"
                    )
                    
                    objective_launch = gr.Dropdown(
                        choices=[obj.value for obj in CampaignObjective],
                        value=CampaignObjective.AWARENESS.value,
                        label="Objetivo"
                    )
                    
                    budget = gr.Number(
                        label="Presupuesto Total",
                        value=1000.0,
                        minimum=10.0,
                        info="Presupuesto total de la campaña en USD"
                    )
                    
                    asset_id_launch = gr.Textbox(
                        label="Asset ID",
                        placeholder="asset_1234567890",
                        info="ID del asset base para la campaña"
                    )
                    
                    num_variations_launch = gr.Slider(
                        minimum=1,
                        maximum=10,
                        value=5,
                        step=1,
                        label="Número de Variaciones a Generar"
                    )
                    
                    auto_select = gr.Checkbox(
                        label="Seleccionar Automáticamente los Mejores",
                        value=True,
                        info="Si está marcado, solo se usarán las mejores variaciones"
                    )
                    
                    top_k = gr.Slider(
                        minimum=1,
                        maximum=5,
                        value=3,
                        step=1,
                        label="Top K Creativos a Usar",
                        visible=True
                    )
                    
                    target_audience_launch = gr.JSON(
                        label="Audiencia Objetivo",
                        value={},
                        info='Ejemplo: {"age_range": "25-45", "interests": ["technology"]}'
                    )
                    
                    launch_btn = gr.Button("🚀 Crear y Lanzar Campaña", variant="primary")
                    launch_output = gr.JSON(label="Resultado de Lanzamiento")
                    
                    def launch_campaign_async(
                        name, platform_val, obj_val, budget_val,
                        asset_id, num_var, auto_sel, top_k_val, audience_val
                    ):
                        try:
                            platform = Platform(platform_val)
                            obj = CampaignObjective(obj_val)
                            
                            result = asyncio.run(
                                self.engine.create_and_launch_campaign(
                                    name=name,
                                    platform=platform,
                                    objective=obj,
                                    budget=float(budget_val),
                                    asset_id=asset_id,
                                    num_variations=int(num_var),
                                    target_audience=audience_val if audience_val else None,
                                    auto_select_best=auto_sel,
                                    top_k=int(top_k_val)
                                )
                            )
                            
                            return {
                                "success": True,
                                "campaign_id": result["campaign"].campaign_id,
                                "campaign_name": result["campaign"].name,
                                "platform": result["campaign"].platform.value,
                                "status": result["campaign"].status,
                                "launch_result": result["launch_result"],
                                "predictions": result["predictions"],
                                "num_variations_used": len(result["variations"])
                            }
                        except Exception as e:
                            return {"success": False, "error": str(e)}
                    
                    launch_btn.click(
                        fn=launch_campaign_async,
                        inputs=[
                            campaign_name, platform_launch, objective_launch, budget,
                            asset_id_launch, num_variations_launch, auto_select, top_k,
                            target_audience_launch
                        ],
                        outputs=launch_output
                    )
                
                # TAB 5: Auto-Optimize
                with gr.Tab("⚙️ Auto-Optimizar"):
                    gr.Markdown("### Auto-optimización diaria usando RL y auto-scaling")
                    
                    campaign_id_optimize = gr.Textbox(
                        label="Campaign ID",
                        placeholder="campaign_1234567890",
                        info="ID de la campaña a optimizar"
                    )
                    
                    # Simular métricas de performance (en producción vendrían de APIs)
                    impressions = gr.Number(label="Impressions", value=10000)
                    clicks = gr.Number(label="Clicks", value=200)
                    conversions = gr.Number(label="Conversions", value=10)
                    spend = gr.Number(label="Spend (USD)", value=500.0)
                    
                    update_metrics_btn = gr.Button("📊 Actualizar Métricas", variant="secondary")
                    optimize_btn = gr.Button("⚙️ Auto-Optimizar", variant="primary")
                    
                    metrics_output = gr.JSON(label="Métricas Actualizadas")
                    optimization_output = gr.JSON(label="Resultado de Optimización")
                    
                    def update_metrics_async(campaign_id, imp, clk, conv, spd):
                        try:
                            ctr = (clk / imp) if imp > 0 else 0.0
                            cpc = (spd / clk) if clk > 0 else 0.0
                            cpm = (spd / imp * 1000) if imp > 0 else 0.0
                            cpa = (spd / conv) if conv > 0 else 0.0
                            conversion_rate = (conv / clk) if clk > 0 else 0.0
                            roas = (conv * 50.0 / spd) if spd > 0 else 0.0  # Asumiendo $50 por conversión
                            
                            metrics = PerformanceMetrics(
                                ad_id=campaign_id,
                                impressions=int(imp),
                                clicks=int(clk),
                                conversions=int(conv),
                                spend=float(spd),
                                ctr=ctr,
                                cpc=cpc,
                                cpm=cpm,
                                cpa=cpa,
                                roas=roas,
                                conversion_rate=conversion_rate
                            )
                            
                            self.engine.update_performance(campaign_id, metrics)
                            
                            return {
                                "success": True,
                                "metrics": {
                                    "ctr": round(ctr, 4),
                                    "cpc": round(cpc, 2),
                                    "cpm": round(cpm, 2),
                                    "cpa": round(cpa, 2),
                                    "roas": round(roas, 2),
                                    "conversion_rate": round(conversion_rate, 4)
                                }
                            }
                        except Exception as e:
                            return {"success": False, "error": str(e)}
                    
                    def optimize_campaign_async(campaign_id):
                        try:
                            result = asyncio.run(
                                self.engine.auto_optimize_campaign(campaign_id)
                            )
                            return result
                        except Exception as e:
                            return {"success": False, "error": str(e)}
                    
                    update_metrics_btn.click(
                        fn=update_metrics_async,
                        inputs=[campaign_id_optimize, impressions, clicks, conversions, spend],
                        outputs=metrics_output
                    )
                    
                    optimize_btn.click(
                        fn=optimize_campaign_async,
                        inputs=[campaign_id_optimize],
                        outputs=optimization_output
                    )
                
                # TAB 6: Analytics & Reports
                with gr.Tab("📊 Analytics"):
                    gr.Markdown("### Analytics y reportes de performance")
                    
                    campaign_id_analytics = gr.Textbox(
                        label="Campaign ID",
                        placeholder="campaign_1234567890"
                    )
                    
                    view_analytics_btn = gr.Button("📊 Ver Analytics", variant="primary")
                    analytics_output = gr.JSON(label="Analytics")
                    
                    def get_analytics(campaign_id):
                        try:
                            performance = self.engine.get_campaign_performance(campaign_id)
                            optimization_summary = self.engine.get_optimization_summary(campaign_id)
                            
                            return {
                                "success": True,
                                "performance_history": [
                                    {
                                        "timestamp": m.timestamp,
                                        "impressions": m.impressions,
                                        "clicks": m.clicks,
                                        "conversions": m.conversions,
                                        "spend": round(m.spend, 2),
                                        "ctr": round(m.ctr, 4),
                                        "cpc": round(m.cpc, 2),
                                        "roas": round(m.roas, 2)
                                    }
                                    for m in performance[-10:]  # Últimas 10 métricas
                                ],
                                "optimization_summary": optimization_summary
                            }
                        except Exception as e:
                            return {"success": False, "error": str(e)}
                    
                    view_analytics_btn.click(
                        fn=get_analytics,
                        inputs=[campaign_id_analytics],
                        outputs=analytics_output
                    )
        
        return interface


def get_ads_optimization_mode(config: AppConfig) -> AdsOptimizationMode:
    """Factory function para obtener instancia del modo"""
    return AdsOptimizationMode(config)


def run_ads_optimization_mode(config: AppConfig):
    """Ejecuta el modo de optimización de anuncios"""
    mode = AdsOptimizationMode(config)
    interface = mode.create_interface()
    interface.launch(share=False, server_name="0.0.0.0", server_port=7860)

