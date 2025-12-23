"""
Gradio UI para Advertising Top Manager
Interfaz simple para que personas normales puedan crear y publicar anuncios
"""
from __future__ import annotations

import os
import uuid
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import tempfile

import gradio as gr

from .models.schemas import (
    AssetUpload,
    AssetType,
    CampaignRequest,
    CampaignObjective,
    Platform
)
from .advertising_top_manager_mode import AdvertisingTopManagerMode


def create_campaign_from_ui(
    campaign_name: str,
    daily_budget: float,
    objective: str,
    platforms: str,
    auto_publish: bool,
    image_files: Optional[List] = None,
    video_files: Optional[List] = None,
    landing_page_url: Optional[str] = None,
    target_audience: Optional[str] = None,
    mode_instance: Optional[AdvertisingTopManagerMode] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Crea y publica una campaña desde la UI de Gradio.
    
    Args:
        campaign_name: Nombre de la campaña
        daily_budget: Presupuesto diario en USD
        objective: Objetivo de la campaña (CONVERSIONS, TRAFFIC, etc.)
        platforms: Plataformas donde publicar (meta, google, both)
        auto_publish: Si True, publica automáticamente (ACTIVE), si False, crea en PAUSED
        image_files: Lista de archivos de imagen
        video_files: Lista de archivos de video
        landing_page_url: URL de la página de destino
        target_audience: Audiencia objetivo (JSON string)
        mode_instance: Instancia de AdvertisingTopManagerMode
        
    Returns:
        Tupla con (mensaje de resultado, datos de la campaña)
    """
    if not mode_instance:
        return "❌ Error: Advertising Top Manager no está inicializado", {}
    
    try:
        # Validar inputs
        if not campaign_name or not campaign_name.strip():
            return "❌ Error: El nombre de la campaña es requerido", {}
        
        if daily_budget <= 0:
            return "❌ Error: El presupuesto diario debe ser mayor a 0", {}
        
        if daily_budget > 10000:
            return "❌ Error: El presupuesto diario no puede exceder $10,000 por día", {}
        
        # Validar que haya al menos un asset
        all_files = []
        if image_files:
            all_files.extend([(f, AssetType.IMAGE) for f in image_files if f])
        if video_files:
            all_files.extend([(f, AssetType.VIDEO) for f in video_files if f])
        
        if not all_files:
            return "❌ Error: Debes subir al menos una imagen o video", {}
        
        # Convertir objective string a enum
        try:
            objective_enum = CampaignObjective(objective.upper())
        except ValueError:
            return f"❌ Error: Objetivo inválido '{objective}'. Opciones: CONVERSIONS, TRAFFIC, ENGAGEMENT, AWARENESS, LEAD_GENERATION, SALES", {}
        
        # Convertir platforms string a enum
        platforms_lower = platforms.lower()
        if platforms_lower == "meta":
            platform_enum = Platform.META
        elif platforms_lower == "google":
            platform_enum = Platform.GOOGLE
        elif platforms_lower == "ambas" or platforms_lower == "both":
            platform_enum = Platform.BOTH
        else:
            return f"❌ Error: Plataforma inválida '{platforms}'. Opciones: meta, google, ambas", {}
        
        # Parsear target_audience si está disponible
        audience_dict = None
        if target_audience and target_audience.strip():
            try:
                import json
                audience_dict = json.loads(target_audience)
            except json.JSONDecodeError:
                pass  # Si no es JSON válido, usar None
        
        # Crear assets desde archivos subidos
        assets = []
        user_id = "gradio_user"
        
        # Guardar archivos temporalmente y crear AssetUpload
        temp_dir = Path(tempfile.gettempdir()) / "advertising_top_manager_uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path, asset_type in all_files:
            if file_path:
                # Copiar archivo a directorio temporal
                src_path = Path(file_path)
                if src_path.exists():
                    dst_path = temp_dir / f"{uuid.uuid4()}_{src_path.name}"
                    import shutil
                    shutil.copy2(src_path, dst_path)
                    
                    asset = AssetUpload(
                        asset_type=asset_type,
                        file_path=str(dst_path),
                        metadata={
                            "original_filename": src_path.name,
                            "landing_page_url": landing_page_url,
                            "target_audience": audience_dict
                        }
                    )
                    assets.append(asset)
        
        if not assets:
            return "❌ Error: No se pudieron procesar los archivos subidos", {}
        
        # Procesar assets primero
        print(f"📦 Procesando {len(assets)} assets...")
        processed_assets = mode_instance.process_assets(assets, user_id=user_id)
        
        if not processed_assets:
            return "❌ Error: No se pudieron procesar los assets. Verifica que sean imágenes o videos válidos.", {}
        
        # Obtener asset_ids de los assets procesados
        asset_ids = [asset.get("asset_id") for asset in processed_assets if asset.get("asset_id")]
        
        if not asset_ids:
            return "❌ Error: No se generaron asset IDs. Verifica que los archivos sean válidos.", {}
        
        # Crear CampaignRequest
        campaign_request = CampaignRequest(
            name=campaign_name.strip(),
            objective=objective_enum,
            budget_daily=daily_budget,
            asset_ids=asset_ids,
            platforms=platform_enum,
            auto_activate=auto_publish,  # CRÍTICO: Esto controla si se publica automáticamente
            metadata={
                "landing_page_url": landing_page_url,
                "target_audience": audience_dict,
                "created_from": "gradio_ui",
                "created_at": datetime.now().isoformat()
            }
        )
        
        # Lanzar campaña
        print(f"🚀 Lanzando campaña: {campaign_name} (${daily_budget}/día, {platforms}, auto_publish={auto_publish})")
        campaign_response = mode_instance.launch_campaign(campaign_request, user_id=user_id)
        
        # Formatear respuesta
        status_emoji = "🟢" if campaign_response.status == "active" else "⏸️"
        platforms_list = ", ".join(campaign_response.platforms)
        
        result_message = f"""
## ✅ Campaña Creada Exitosamente

**Nombre:** {campaign_response.name}
**ID:** {campaign_response.campaign_id}
**Estado:** {status_emoji} {campaign_response.status.upper()}

**Presupuesto:**
- Diario: ${campaign_response.budget_daily:.2f}
- Total estimado (30 días): ${campaign_response.budget_daily * 30:.2f}

**Plataformas:** {platforms_list}

**Anuncios Creados:** {campaign_response.ads_count}

**Links a Campañas:**
"""
        
        # Agregar links a campañas de plataformas
        for platform, campaign_id in campaign_response.platform_campaign_ids.items():
            if platform == "meta":
                result_message += f"- **Meta Ads:** https://business.facebook.com/adsmanager/manage/campaigns?act={campaign_id.split('_')[-1] if '_' in campaign_id else campaign_id}\n"
            elif platform == "google":
                result_message += f"- **Google Ads:** Campaign ID: {campaign_id}\n"
        
        result_message += f"""
**💡 Nota:** {'Los anuncios están ACTIVOS y comenzarán a publicarse automáticamente.' if auto_publish else 'Los anuncios están PAUSADOS. Actívalos manualmente desde Meta Ads Manager o Google Ads.'}
"""
        
        return result_message, {
            "campaign_id": campaign_response.campaign_id,
            "status": campaign_response.status,
            "platforms": campaign_response.platforms,
            "ads_count": campaign_response.ads_count,
            "platform_campaign_ids": campaign_response.platform_campaign_ids
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Error creando campaña: {e}")
        print(error_details)
        return f"❌ Error creando campaña: {str(e)}", {}


def create_gradio_interface(mode_instance: Optional[AdvertisingTopManagerMode] = None):
    """
    Crea la interfaz de Gradio para Advertising Top Manager.
    
    Returns:
        Gradio Blocks interface
    """
    with gr.Blocks(title="Advertising Top Manager", theme=gr.themes.Soft()) as interface:
        gr.Markdown("""
        # 📈 Advertising Top Manager
        
        ## 🚀 Crea y Publica Anuncios Automáticamente en Meta y Google Ads
        
        **Características:**
        - ✅ Publicación automática en Meta (Facebook/Instagram) y Google Ads
        - ✅ IA genera copy y variaciones automáticamente
        - ✅ Análisis de imágenes/videos con visión computacional
        - ✅ Optimización automática de campañas
        
        **Para usar:**
        1. Sube imágenes o videos de tu producto
        2. Configura nombre, presupuesto y objetivo
        3. Selecciona plataformas (Meta, Google, o ambas)
        4. Click en "🚀 Crear y Publicar Campaña"
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                # Upload de archivos
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
                
                gr.Markdown("""
                **💡 Tip:** Puedes subir múltiples imágenes o videos. 
                El sistema generará variaciones automáticamente.
                """)
            
            with gr.Column(scale=1):
                # Configuración de campaña
                gr.Markdown("### ⚙️ Configuración de Campaña")
                
                campaign_name = gr.Textbox(
                    label="Nombre de la Campaña",
                    placeholder="Ej: Oferta Verano 2025",
                    value=""
                )
                
                daily_budget = gr.Number(
                    label="Presupuesto Diario (USD)",
                    value=50.0,
                    minimum=1.0,
                    maximum=10000.0,
                    step=1.0
                )
                
                objective = gr.Dropdown(
                    label="Objetivo de la Campaña",
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
                    info="Si está marcado, los anuncios se publicarán automáticamente. Si no, se crearán en PAUSED."
                )
                
                landing_page_url = gr.Textbox(
                    label="URL de Página de Destino (Opcional)",
                    placeholder="https://tu-sitio.com/producto",
                    value=""
                )
                
                target_audience = gr.Textbox(
                    label="Audiencia Objetivo (JSON Opcional)",
                    placeholder='{"age_min": 25, "age_max": 45, "genders": [1, 2], "interests": ["technology"]}',
                    value="",
                    lines=3
                )
        
        # Botón de acción
        create_btn = gr.Button("🚀 Crear y Publicar Campaña", variant="primary", size="lg")
        
        # Output
        result_output = gr.Markdown(label="Resultado")
        result_json = gr.JSON(label="Datos de la Campaña", visible=False)
        
        # Handler
        def handle_create_campaign(
            name, budget, obj, plat, auto, images, videos, url, audience
        ):
            return create_campaign_from_ui(
                campaign_name=name,
                daily_budget=budget,
                objective=obj,
                platforms=plat,
                auto_publish=auto,
                image_files=images,
                video_files=videos,
                landing_page_url=url,
                target_audience=audience,
                mode_instance=mode_instance
            )
        
        create_btn.click(
            fn=handle_create_campaign,
            inputs=[campaign_name, daily_budget, objective, platforms, auto_publish, image_files, video_files, landing_page_url, target_audience],
            outputs=[result_output, result_json]
        )
        
        # Información adicional
        with gr.Accordion("ℹ️ Información Adicional", open=False):
            gr.Markdown("""
            ### 🔑 Configuración Requerida
            
            Para usar Advertising Top Manager, necesitas configurar credenciales:
            
            **Meta Ads:**
            - `META_ACCESS_TOKEN`
            - `META_APP_ID`
            - `META_APP_SECRET`
            - `META_AD_ACCOUNT_ID`
            - `META_PAGE_ID`
            
            **Google Ads:**
            - `GOOGLE_ADS_CUSTOMER_ID`
            - `GOOGLE_ADS_CONFIG_PATH` (ruta a google-ads.yaml)
            
            ### 📊 Después de Crear la Campaña
            
            - Los anuncios se procesarán y publicarán automáticamente
            - Puedes ver las métricas en Meta Ads Manager y Google Ads
            - El sistema generará múltiples variaciones de copy automáticamente
            - Las mejores variaciones se seleccionarán automáticamente
            
            ### 🎯 Objetivos Disponibles
            
            - **CONVERSIONS:** Optimizar para conversiones
            - **TRAFFIC:** Optimizar para tráfico al sitio
            - **ENGAGEMENT:** Optimizar para engagement en redes sociales
            - **AWARENESS:** Optimizar para alcance
            - **LEAD_GENERATION:** Optimizar para generación de leads
            - **SALES:** Optimizar para ventas
            """)
    
    return interface

