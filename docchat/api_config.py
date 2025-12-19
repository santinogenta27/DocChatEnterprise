"""
Configuración de APIs y verificación de credenciales para modos integrados.
"""

from __future__ import annotations

import os
from typing import Dict, Any, Optional
from fastapi import APIRouter


def verify_api_credentials() -> Dict[str, Dict[str, Any]]:
    """
    Verifica el estado de las credenciales de APIs externas.
    
    Returns:
        Dict con el estado de cada API
    """
    status = {
        "openai": {
            "configured": bool(os.getenv("OPENAI_API_KEY")),
            "status": "✅ Configurada" if os.getenv("OPENAI_API_KEY") else "❌ No configurada",
            "env_var": "OPENAI_API_KEY"
        },
        "meta_ads": {
            "configured": bool(os.getenv("META_ACCESS_TOKEN") or os.getenv("FACEBOOK_ACCESS_TOKEN")),
            "status": "✅ Configurada" if (os.getenv("META_ACCESS_TOKEN") or os.getenv("FACEBOOK_ACCESS_TOKEN")) else "⚠️ No configurada",
            "env_var": "META_ACCESS_TOKEN o FACEBOOK_ACCESS_TOKEN",
            "note": "Necesaria para crear campañas en Meta Ads"
        },
        "tiktok_ads": {
            "configured": bool(os.getenv("TIKTOK_ACCESS_TOKEN") or os.getenv("TIKTOK_API_KEY")),
            "status": "✅ Configurada" if (os.getenv("TIKTOK_ACCESS_TOKEN") or os.getenv("TIKTOK_API_KEY")) else "⚠️ No configurada",
            "env_var": "TIKTOK_ACCESS_TOKEN o TIKTOK_API_KEY",
            "note": "Necesaria para crear campañas en TikTok Ads"
        },
        "stripe": {
            "configured": bool(os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_API_KEY")),
            "status": "✅ Configurada" if (os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_API_KEY")) else "⚠️ No configurada",
            "env_var": "STRIPE_SECRET_KEY o STRIPE_API_KEY",
            "note": "Necesaria para procesar pagos en Business AI Omnicanal"
        },
        "paypal": {
            "configured": bool(os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_CLIENT_SECRET")),
            "status": "✅ Configurada" if (os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_CLIENT_SECRET")) else "⚠️ No configurada",
            "env_var": "PAYPAL_CLIENT_ID y PAYPAL_CLIENT_SECRET",
            "note": "Necesaria para procesar pagos en Business AI Omnicanal"
        },
        "shopify": {
            "configured": bool(os.getenv("SHOPIFY_API_KEY") and os.getenv("SHOPIFY_API_SECRET")),
            "status": "✅ Configurada" if (os.getenv("SHOPIFY_API_KEY") and os.getenv("SHOPIFY_API_SECRET")) else "⚠️ No configurada",
            "env_var": "SHOPIFY_API_KEY y SHOPIFY_API_SECRET",
            "note": "Opcional: Para sincronizar catálogo desde Shopify"
        }
    }
    
    return status


def setup_fastapi_endpoints(app, business_ai_mode=None, top_ads_mode=None):
    """
    Configura los endpoints FastAPI para Business AI Omnicanal y Top Ads Mode.
    
    Args:
        app: Aplicación FastAPI (demo.app de Gradio)
        business_ai_mode: Instancia de BusinessAIMode (opcional)
        top_ads_mode: Instancia de TopAdsMode (opcional)
    """
    try:
        if business_ai_mode and hasattr(business_ai_mode, 'get_api_router'):
            router = business_ai_mode.get_api_router()
            app.include_router(router)
            print("✅ Endpoints FastAPI de Business AI Omnicanal configurados")
    except Exception as e:
        print(f"⚠️ Error configurando endpoints FastAPI de Business AI Omnicanal: {e}")
    
    try:
        if top_ads_mode and hasattr(top_ads_mode, 'get_api_router'):
            router = top_ads_mode.get_api_router()
            app.include_router(router)
            print("✅ Endpoints FastAPI de Top Ads Mode configurados")
    except Exception as e:
        print(f"⚠️ Error configurando endpoints FastAPI de Top Ads Mode: {e}")


def get_credentials_status_markdown() -> str:
    """
    Retorna un markdown con el estado de las credenciales.
    """
    status = verify_api_credentials()
    
    output = "## 🔐 Estado de Credenciales de APIs\n\n"
    
    for api_name, api_status in status.items():
        output += f"### {api_name.upper().replace('_', ' ')}\n"
        output += f"- **Estado**: {api_status['status']}\n"
        output += f"- **Variable de entorno**: `{api_status['env_var']}`\n"
        if 'note' in api_status:
            output += f"- **Nota**: {api_status['note']}\n"
        output += "\n"
    
    return output
