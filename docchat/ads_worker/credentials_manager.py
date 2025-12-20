"""
Credentials Manager for Ads Platforms
Maneja credenciales de Meta/Google de forma segura
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AdsCredentialsManager:
    """Gestor de credenciales para plataformas de ads"""
    
    def __init__(self, credentials_dir: Optional[Path] = None):
        if credentials_dir is None:
            credentials_dir = Path("./.docchat_memory") / "ads_credentials"
        self.credentials_dir = Path(credentials_dir)
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        
        self.meta_credentials_file = self.credentials_dir / "meta_credentials.json"
        self.google_credentials_file = self.credentials_dir / "google_credentials.json"
    
    def save_meta_credentials(
        self,
        access_token: str,
        app_id: str,
        app_secret: str,
        ad_account_id: str,
        page_id: Optional[str] = None
    ) -> bool:
        """Guarda credenciales de Meta"""
        try:
            credentials = {
                "access_token": access_token,
                "app_id": app_id,
                "app_secret": app_secret,
                "ad_account_id": ad_account_id,
                "page_id": page_id
            }
            
            with open(self.meta_credentials_file, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, indent=2)
            
            # También actualizar variables de entorno para compatibilidad
            os.environ["META_ACCESS_TOKEN"] = access_token
            os.environ["META_APP_ID"] = app_id
            os.environ["META_APP_SECRET"] = app_secret
            os.environ["META_AD_ACCOUNT_ID"] = ad_account_id
            if page_id:
                os.environ["META_PAGE_ID"] = page_id
            
            logger.info("✅ Credenciales de Meta guardadas")
            return True
        except Exception as e:
            logger.error(f"Error guardando credenciales de Meta: {e}")
            return False
    
    def load_meta_credentials(self) -> Optional[Dict[str, str]]:
        """Carga credenciales de Meta"""
        try:
            if not self.meta_credentials_file.exists():
                # Intentar cargar desde variables de entorno
                token = os.getenv("META_ACCESS_TOKEN")
                app_id = os.getenv("META_APP_ID")
                app_secret = os.getenv("META_APP_SECRET")
                ad_account_id = os.getenv("META_AD_ACCOUNT_ID")
                page_id = os.getenv("META_PAGE_ID")
                
                if token and app_id and app_secret and ad_account_id:
                    return {
                        "access_token": token,
                        "app_id": app_id,
                        "app_secret": app_secret,
                        "ad_account_id": ad_account_id,
                        "page_id": page_id
                    }
                return None
            
            with open(self.meta_credentials_file, 'r', encoding='utf-8') as f:
                credentials = json.load(f)
            
            # Actualizar variables de entorno
            os.environ["META_ACCESS_TOKEN"] = credentials.get("access_token", "")
            os.environ["META_APP_ID"] = credentials.get("app_id", "")
            os.environ["META_APP_SECRET"] = credentials.get("app_secret", "")
            os.environ["META_AD_ACCOUNT_ID"] = credentials.get("ad_account_id", "")
            if credentials.get("page_id"):
                os.environ["META_PAGE_ID"] = credentials.get("page_id", "")
            
            return credentials
        except Exception as e:
            logger.error(f"Error cargando credenciales de Meta: {e}")
            return None
    
    def save_google_credentials(
        self,
        customer_id: str,
        developer_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None
    ) -> bool:
        """Guarda credenciales de Google Ads"""
        try:
            credentials = {
                "customer_id": customer_id,
                "developer_token": developer_token,
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token
            }
            
            with open(self.google_credentials_file, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, indent=2)
            
            # Actualizar variables de entorno
            os.environ["GOOGLE_ADS_CUSTOMER_ID"] = customer_id
            if developer_token:
                os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"] = developer_token
            if client_id:
                os.environ["GOOGLE_ADS_CLIENT_ID"] = client_id
            if client_secret:
                os.environ["GOOGLE_ADS_CLIENT_SECRET"] = client_secret
            if refresh_token:
                os.environ["GOOGLE_ADS_REFRESH_TOKEN"] = refresh_token
            
            logger.info("✅ Credenciales de Google guardadas")
            return True
        except Exception as e:
            logger.error(f"Error guardando credenciales de Google: {e}")
            return False
    
    def load_google_credentials(self) -> Optional[Dict[str, str]]:
        """Carga credenciales de Google Ads"""
        try:
            if not self.google_credentials_file.exists():
                # Intentar cargar desde variables de entorno
                customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
                if customer_id:
                    return {
                        "customer_id": customer_id,
                        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
                        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
                        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
                        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN")
                    }
                return None
            
            with open(self.google_credentials_file, 'r', encoding='utf-8') as f:
                credentials = json.load(f)
            
            # Actualizar variables de entorno
            os.environ["GOOGLE_ADS_CUSTOMER_ID"] = credentials.get("customer_id", "")
            if credentials.get("developer_token"):
                os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"] = credentials["developer_token"]
            if credentials.get("client_id"):
                os.environ["GOOGLE_ADS_CLIENT_ID"] = credentials["client_id"]
            if credentials.get("client_secret"):
                os.environ["GOOGLE_ADS_CLIENT_SECRET"] = credentials["client_secret"]
            if credentials.get("refresh_token"):
                os.environ["GOOGLE_ADS_REFRESH_TOKEN"] = credentials["refresh_token"]
            
            return credentials
        except Exception as e:
            logger.error(f"Error cargando credenciales de Google: {e}")
            return None
    
    def test_meta_connection(self) -> tuple[bool, str]:
        """Prueba conexión con Meta Ads API"""
        try:
            credentials = self.load_meta_credentials()
            if not credentials:
                return False, "❌ No hay credenciales configuradas"
            
            # Intentar inicializar Meta Ads API
            try:
                from facebook_business.api import FacebookAdsApi
                from facebook_business.adobjects.adaccount import AdAccount
                
                FacebookAdsApi.init(
                    access_token=credentials["access_token"],
                    app_id=credentials["app_id"],
                    app_secret=credentials["app_secret"]
                )
                
                # Intentar obtener información de la cuenta
                account = AdAccount(f'act_{credentials["ad_account_id"]}')
                account_info = account.api_get(fields=['id', 'name', 'account_status'])
                
                return True, f"✅ Conexión exitosa - Cuenta: {account_info.get('name', 'N/A')}"
            except Exception as e:
                return False, f"❌ Error de conexión: {str(e)}"
        except ImportError:
            return False, "❌ facebook-business package no está instalado"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def has_meta_credentials(self) -> bool:
        """Verifica si hay credenciales de Meta configuradas"""
        credentials = self.load_meta_credentials()
        return credentials is not None and credentials.get("access_token")
    
    def has_google_credentials(self) -> bool:
        """Verifica si hay credenciales de Google configuradas"""
        credentials = self.load_google_credentials()
        return credentials is not None and credentials.get("customer_id")




