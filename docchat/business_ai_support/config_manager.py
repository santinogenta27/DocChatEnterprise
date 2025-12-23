"""Configuration Manager - Stores and loads omnicanal configuration without .env"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class OmnicanalConfig:
    """Omnicanal channel configuration."""
    # WhatsApp
    whatsapp_provider: str = ""  # "twilio" or "meta"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_number: str = ""
    meta_whatsapp_phone_number_id: str = ""
    meta_whatsapp_access_token: str = ""
    
    # Facebook Messenger
    facebook_page_access_token: str = ""
    facebook_verify_token: str = ""
    
    # Instagram
    instagram_access_token: str = ""
    instagram_user_id: str = ""
    
    # Email (SMTP)
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_to_emails: str = ""  # Comma-separated
    
    # Slack
    slack_webhook_url: str = ""


class ConfigurationManager:
    """Manages omnicanal and notification configuration (stored in JSON, not .env)."""
    
    def __init__(self, config_file: Optional[Path] = None):
        """Initialize ConfigurationManager.
        
        Args:
            config_file: Path to JSON config file (default: .docchat_memory/business_ai_support_config.json)
        """
        if config_file is None:
            config_file = Path(".docchat_memory") / "business_ai_support_config.json"
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> OmnicanalConfig:
        """Load configuration from JSON file."""
        if not self.config_file.exists():
            return OmnicanalConfig()
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return OmnicanalConfig(**data)
        except Exception as e:
            print(f"⚠️ Error cargando configuración: {e}")
            return OmnicanalConfig()
    
    def save_config(self, config: OmnicanalConfig) -> bool:
        """Save configuration to JSON file.
        
        Args:
            config: OmnicanalConfig to save
            
        Returns:
            True if saved successfully
        """
        try:
            # Convert to dict, excluding empty sensitive values for display
            config_dict = asdict(config)
            
            # Save to JSON
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Configuración guardada en {self.config_file}")
            return True
        except Exception as e:
            print(f"❌ Error guardando configuración: {e}")
            return False
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary (for Gradio UI)."""
        config = self.load_config()
        return asdict(config)
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update configuration with new values.
        
        Args:
            updates: Dictionary with keys to update
            
        Returns:
            True if updated successfully
        """
        config = self.load_config()
        
        # Update fields
        for key, value in updates.items():
            if hasattr(config, key):
                # Convert port to int if needed
                if key == "smtp_port":
                    try:
                        value = int(value)
                    except:
                        value = 587
                setattr(config, key, value)
        
        return self.save_config(config)

