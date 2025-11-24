"""
Script para verificar que las APIs de ads están correctamente configuradas.
Ejecuta: python verificar_apis.py
"""

import os
import sys
from pathlib import Path

# Cargar .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv no está instalado. Instala con: pip install python-dotenv")
    sys.exit(1)

import requests

def verificar_meta():
    """Verifica conexión con Meta API."""
    token = os.getenv("META_ACCESS_TOKEN")
    account_id = os.getenv("META_AD_ACCOUNT_ID")
    
    if not token:
        return "⚠️ No configurado (META_ACCESS_TOKEN faltante)"
    
    try:
        # Verificar token básico
        url = f"https://graph.facebook.com/v18.0/me?access_token={token}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            if account_id:
                # Verificar acceso a Ad Account
                url = f"https://graph.facebook.com/v18.0/{account_id}?access_token={token}&fields=id,name"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    return "✅ Conectado correctamente"
                else:
                    return f"⚠️ Token válido pero Ad Account no accesible: {response.text[:100]}"
            return "✅ Token válido (falta META_AD_ACCOUNT_ID)"
        else:
            return f"❌ Error: {response.json().get('error', {}).get('message', 'Unknown error')}"
    except Exception as e:
        return f"❌ Error de conexión: {str(e)}"

def verificar_tiktok():
    """Verifica conexión con TikTok API."""
    token = os.getenv("TIKTOK_ACCESS_TOKEN")
    advertiser_id = os.getenv("TIKTOK_ADVERTISER_ID")
    
    if not token:
        return "⚠️ No configurado (TIKTOK_ACCESS_TOKEN faltante)"
    
    try:
        url = "https://business-api.tiktok.com/open_api/v1.3/advertiser/info/"
        headers = {
            "Access-Token": token,
            "Content-Type": "application/json"
        }
        params = {}
        if advertiser_id:
            params["advertiser_ids"] = f"[{advertiser_id}]"
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            return "✅ Conectado correctamente"
        else:
            error_data = response.json() if response.content else {}
            return f"❌ Error: {error_data.get('message', response.text[:100])}"
    except Exception as e:
        return f"❌ Error de conexión: {str(e)}"

def verificar_linkedin():
    """Verifica conexión con LinkedIn API."""
    token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    account_id = os.getenv("LINKEDIN_ACCOUNT_ID")
    
    if not token:
        return "⚠️ No configurado (LINKEDIN_ACCESS_TOKEN faltante)"
    
    try:
        # Verificar token básico
        url = "https://api.linkedin.com/v2/me"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            if account_id:
                return "✅ Conectado correctamente"
            return "✅ Token válido (falta LINKEDIN_ACCOUNT_ID)"
        else:
            error_data = response.json() if response.content else {}
            return f"❌ Error: {error_data.get('message', response.text[:100])}"
    except Exception as e:
        return f"❌ Error de conexión: {str(e)}"

def verificar_google_ads():
    """Verifica configuración de Google Ads."""
    customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
    developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
    client_id = os.getenv("GOOGLE_ADS_CLIENT_ID")
    refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")
    
    if not developer_token:
        return "⚠️ No configurado (GOOGLE_ADS_DEVELOPER_TOKEN faltante)"
    
    # Verificar que todas las credenciales estén presentes
    missing = []
    if not customer_id:
        missing.append("GOOGLE_ADS_CUSTOMER_ID")
    if not client_id:
        missing.append("GOOGLE_ADS_CLIENT_ID")
    if not refresh_token:
        missing.append("GOOGLE_ADS_REFRESH_TOKEN")
    
    if missing:
        return f"⚠️ Configurado parcialmente (faltan: {', '.join(missing)})"
    
    # Verificar si la librería está instalada
    try:
        import google.ads.googleads.client
        return "✅ Configurado correctamente (requiere verificación manual con google-ads library)"
    except ImportError:
        return "⚠️ Configurado pero falta librería (pip install google-ads)"

def main():
    """Ejecuta verificación de todas las APIs."""
    print("🔍 Verificando conexiones de APIs de Ads...\n")
    print("=" * 60)
    
    print("\n📘 Meta (Facebook/Instagram) Ads:")
    print(f"   {verificar_meta()}")
    
    print("\n🎵 TikTok Ads:")
    print(f"   {verificar_tiktok()}")
    
    print("\n💼 LinkedIn Ads:")
    print(f"   {verificar_linkedin()}")
    
    print("\n🔍 Google Ads:")
    print(f"   {verificar_google_ads()}")
    
    print("\n" + "=" * 60)
    print("\n💡 Tip: Si alguna API muestra error, revisa:")
    print("   1. Que las credenciales en .env sean correctas")
    print("   2. Que los tokens no hayan expirado")
    print("   3. Que tengas los permisos necesarios")
    print("\n📚 Consulta CONECTAR_APIS_ADS.md para guías detalladas")

if __name__ == "__main__":
    main()

