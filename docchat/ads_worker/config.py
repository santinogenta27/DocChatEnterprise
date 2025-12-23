"""
Configuration for ADS WORKER
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class AdsWorkerConfig(BaseSettings):
    """Configuration settings for ADS WORKER"""
    
    # OpenAI
    openai_api_key: Optional[str] = None
    
    # Meta Ads
    meta_access_token: Optional[str] = None
    meta_app_id: Optional[str] = None
    meta_app_secret: Optional[str] = None
    meta_ad_account_id: Optional[str] = None
    meta_page_id: Optional[str] = None  # Required for creatives
    
    # Google Ads
    google_customer_id: Optional[str] = None
    google_config_path: Optional[str] = None
    
    # Database
    ads_worker_db_url: Optional[str] = None
    
    # Processing
    max_workers: int = 4
    storage_path: str = "./assets"
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_prefix = "ADS_WORKER_"
        case_sensitive = False






































