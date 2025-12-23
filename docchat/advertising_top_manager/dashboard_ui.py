"""
UI Components para Dashboard Visual de Advertising Top Manager
Dashboard de métricas, preview de anuncios, y export CSV
"""
from __future__ import annotations

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json

import gradio as gr

from .dashboard_metrics import DashboardMetrics
from .advertising_top_manager_mode import AdvertisingTopManagerMode


def create_dashboard_visual(
    campaign_id: Optional[str],
    days: int,
    metrics_manager: DashboardMetrics
) -> Tuple[str, Dict[str, Any]]:
    """
    Crea visualización del dashboard con métricas
    
    Returns:
        Tupla con (HTML del dashboard, datos de métricas)
    """
    try:
        # Obtener métricas
        metrics = metrics_manager.get_campaign_metrics(campaign_id, days)
        
        # Crear HTML del dashboard
        dashboard_html = f"""
        <div style="padding: 20px; font-family: Arial, sans-serif;">
            <h2 style="color: #1a73e8; margin-bottom: 20px;">📊 Dashboard de Métricas</h2>
            
            <!-- Métricas principales -->
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px;">
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #1a73e8;">
                    <div style="font-size: 12px; color: #666; margin-bottom: 5px;">CTR</div>
                    <div style="font-size: 24px; font-weight: bold; color: #1a73e8;">{metrics['ctr']:.2f}%</div>
                </div>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #34a853;">
                    <div style="font-size: 12px; color: #666; margin-bottom: 5px;">CPC</div>
                    <div style="font-size: 24px; font-weight: bold; color: #34a853;">${metrics['cpc']:.2f}</div>
                </div>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #ea4335;">
                    <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Gasto Total</div>
                    <div style="font-size: 24px; font-weight: bold; color: #ea4335;">${metrics['spend']:.2f}</div>
                </div>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #fbbc04;">
                    <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Conversiones</div>
                    <div style="font-size: 24px; font-weight: bold; color: #fbbc04;">{metrics['conversions']}</div>
                </div>
            </div>
            
            <!-- Métricas adicionales -->
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 30px;">
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                    <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Impresiones</div>
                    <div style="font-size: 20px; font-weight: bold;">{metrics['impressions']:,}</div>
                </div>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                    <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Clicks</div>
                    <div style="font-size: 20px; font-weight: bold;">{metrics['clicks']:,}</div>
                </div>
            </div>
            
            <!-- Gráficos (usando datos JSON para que Gradio los renderice) -->
            <div style="margin-top: 30px;">
                <h3 style="color: #333; margin-bottom: 15px;">📈 Tendencias</h3>
                <p style="color: #666; font-size: 14px;">Los gráficos se mostrarán abajo</p>
            </div>
        </div>
        """
        
        return dashboard_html, metrics
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_html = f"""
        <div style="padding: 20px; color: #ea4335;">
            <h3>❌ Error cargando dashboard</h3>
            <p>{str(e)}</p>
        </div>
        """
        return error_html, {}


def create_charts_data(metrics: Dict[str, Any]) -> Tuple[List[List], List[List]]:
    """
    Crea datos para gráficos de línea y barras
    
    Returns:
        Tupla con (datos para gráfico de línea [gasto], datos para gráfico de barras [conversiones])
    """
    daily_data = metrics.get("daily_data", [])
    
    if not daily_data:
        # Datos dummy si no hay datos
        return (
            [[datetime.now().isoformat(), 0.0]],  # Línea: gasto por día
            [["Sin datos", 0]]  # Barras: conversiones por campaña
        )
    
    # Gráfico de línea: gasto por día
    line_data = []
    for day in daily_data:
        date_str = day.get("date", "")
        spend = day.get("spend", 0.0)
        if date_str:
            line_data.append([date_str, spend])
    
    # Gráfico de barras: conversiones por día
    bar_data = []
    for day in daily_data:
        date_str = day.get("date", "")
        conversions = day.get("conversions", 0)
        if date_str:
            # Formatear fecha para mostrar
            try:
                date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                date_display = date_obj.strftime("%Y-%m-%d")
            except:
                date_display = date_str[:10] if len(date_str) >= 10 else date_str
            bar_data.append([date_display, conversions])
    
    return line_data, bar_data


def create_ad_preview(
    headline: str,
    description: str,
    cta: str,
    image_path: Optional[str] = None,
    video_path: Optional[str] = None
) -> str:
    """
    Crea preview HTML del anuncio
    
    Args:
        headline: Título del anuncio
        description: Descripción del anuncio
        cta: Call-to-action
        image_path: Ruta a imagen (opcional)
        video_path: Ruta a video (opcional)
    
    Returns:
        HTML del preview
    """
    # Determinar qué mostrar (imagen o video)
    media_html = ""
    if video_path and Path(video_path).exists():
        media_html = f'<video controls style="width: 100%; max-width: 400px; border-radius: 8px;"><source src="file/{video_path}" type="video/mp4"></video>'
    elif image_path and Path(image_path).exists():
        media_html = f'<img src="file/{image_path}" style="width: 100%; max-width: 400px; border-radius: 8px; border: 1px solid #ddd;" alt="Preview">'
    else:
        media_html = '<div style="width: 100%; max-width: 400px; height: 300px; background: #f0f0f0; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #999;">Sin imagen/video</div>'
    
    preview_html = f"""
    <div style="padding: 20px; background: #ffffff; border: 2px solid #1a73e8; border-radius: 12px; max-width: 450px; font-family: Arial, sans-serif;">
        <div style="margin-bottom: 15px;">
            {media_html}
        </div>
        
        <div style="margin-bottom: 10px;">
            <h3 style="margin: 0; font-size: 20px; font-weight: bold; color: #333;">{headline or "Sin título"}</h3>
        </div>
        
        <div style="margin-bottom: 15px; color: #666; font-size: 14px; line-height: 1.5;">
            {description or "Sin descripción"}
        </div>
        
        <div>
            <button style="background: #1a73e8; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; width: 100%;">
                {cta or "Learn More"}
            </button>
        </div>
        
        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee; font-size: 12px; color: #999; text-align: center;">
            Preview del anuncio - Vista previa
        </div>
    </div>
    """
    
    return preview_html


def generate_ad_preview_from_campaign(
    campaign_id: str,
    mode_instance: AdvertisingTopManagerMode
) -> str:
    """
    Genera preview del anuncio desde una campaña existente
    
    Args:
        campaign_id: ID de la campaña
        mode_instance: Instancia de AdvertisingTopManagerMode
    
    Returns:
        HTML del preview
    """
    try:
        # Obtener información de la campaña y creativos
        campaign = mode_instance.db_manager.get_campaign(campaign_id)
        
        if not campaign:
            return '<div style="padding: 20px; color: #ea4335;">❌ Campaña no encontrada</div>'
        
        # Obtener creativos de la campaña (necesitamos obtener los ads primero)
        # Por ahora, usar datos básicos de la campaña
        headline = campaign.get("name", "Sin título")
        description = f"Campaña: {campaign.get('name', 'N/A')}"
        cta = "Learn More"
        
        # Intentar obtener asset asociado si existe
        metadata = campaign.get("extra_metadata") or campaign.get("metadata") or {}
        asset_ids = metadata.get("asset_ids", [])
        image_path = None
        
        if asset_ids:
            # Obtener el primer asset
            try:
                asset = mode_instance.db_manager.get_asset(asset_ids[0])
                if asset:
                    image_path = asset.get("file_path")
            except Exception as e:
                print(f"⚠️ Error obteniendo asset: {e}")
        
        return create_ad_preview(headline, description, cta, image_path, None)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f'<div style="padding: 20px; color: #ea4335;">❌ Error generando preview: {str(e)}</div>'

