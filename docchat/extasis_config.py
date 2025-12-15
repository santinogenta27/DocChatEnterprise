"""
ÉXTASIS Config - Gestión de Configuración de Servicios desde UI

Permite a las empresas configurar credenciales de servicios directamente desde la UI
sin necesidad de editar archivos .env manualmente.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime


class ExtasisConfigManager:
    """Gestiona la configuración de servicios de ÉXTASIS."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Inicializa el gestor de configuración.
        
        Args:
            config_dir: Directorio donde guardar configuración (default: data/extasis_config.json)
        """
        if config_dir:
            self.config_file = Path(config_dir) / "extasis_config.json"
        else:
            # Usar directorio data por defecto
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            self.config_file = data_dir / "extasis_config.json"
        
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self._config: Dict[str, Any] = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración desde archivo."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error cargando configuración de ÉXTASIS: {e}")
                return {}
        return {}
    
    def _save_config(self):
        """Guarda la configuración en archivo."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Error guardando configuración de ÉXTASIS: {e}")
            return False
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Obtiene configuración de un servicio específico."""
        return self._config.get("services", {}).get(service_name, {})
    
    def set_service_config(self, service_name: str, config: Dict[str, Any]) -> bool:
        """
        Guarda configuración de un servicio.
        
        Args:
            service_name: Nombre del servicio (jira, servicenow, email, slack, etc.)
            config: Diccionario con credenciales/configuración
        
        Returns:
            True si se guardó exitosamente
        """
        if "services" not in self._config:
            self._config["services"] = {}
        
        self._config["services"][service_name] = {
            **config,
            "updated_at": datetime.now().isoformat()
        }
        
        return self._save_config()
    
    def get_simulation_mode(self) -> bool:
        """Obtiene el estado del modo simulación."""
        return self._config.get("simulation_mode", False)
    
    def set_simulation_mode(self, enabled: bool) -> bool:
        """Activa/desactiva modo simulación."""
        self._config["simulation_mode"] = enabled
        # Actualizar variable de entorno también
        os.environ["EXTASIS_SIMULATION_MODE"] = "true" if enabled else "false"
        return self._save_config()
    
    def get_all_config(self) -> Dict[str, Any]:
        """Obtiene toda la configuración (sin contraseñas sensibles para mostrar)."""
        config_copy = json.loads(json.dumps(self._config))
        
        # Ocultar contraseñas/tokens sensibles
        if "services" in config_copy:
            for service_name, service_config in config_copy["services"].items():
                sensitive_fields = ["password", "token", "api_token", "secret", "access_token", "webhook_url"]
                for field in sensitive_fields:
                    if field in service_config:
                        if service_config[field]:
                            # Mostrar solo últimos 4 caracteres
                            value = str(service_config[field])
                            if len(value) > 4:
                                service_config[field] = "*" * (len(value) - 4) + value[-4:]
                            else:
                                service_config[field] = "****"
        
        return config_copy
    
    def apply_config_to_environment(self):
        """Aplica la configuración guardada a las variables de entorno."""
        if "services" not in self._config:
            return
        
        # Mapeo de servicios a variables de entorno
        env_mapping = {
            "jira": {
                "url": "JIRA_API_URL",
                "email": "JIRA_EMAIL",
                "api_token": "JIRA_API_TOKEN"
            },
            "servicenow": {
                "url": "SERVICENOW_API_URL",
                "user": "SERVICENOW_USER",
                "password": "SERVICENOW_PASSWORD"
            },
            "email": {
                "host": "SMTP_HOST",
                "port": "SMTP_PORT",
                "user": "SMTP_USER",
                "password": "SMTP_PASSWORD"
            },
            "slack": {
                "webhook_url": "SLACK_WEBHOOK_URL",
                "bot_token": "SLACK_BOT_TOKEN"
            },
            "s3": {
                "access_key_id": "AWS_ACCESS_KEY_ID",
                "secret_access_key": "AWS_SECRET_ACCESS_KEY",
                "region": "AWS_REGION"
            },
            "salesforce": {
                "instance_url": "SALESFORCE_INSTANCE_URL",
                "access_token": "SALESFORCE_ACCESS_TOKEN",
                "username": "SALESFORCE_USERNAME",
                "password": "SALESFORCE_PASSWORD",
                "security_token": "SALESFORCE_SECURITY_TOKEN"
            },
            "sap": {
                "odata_url": "SAP_ODATA_URL",
                "user": "SAP_USER",
                "password": "SAP_PASSWORD"
            },
            "oracle_erp": {
                "url": "ORACLE_ERP_URL",
                "token": "ORACLE_ERP_TOKEN"
            },
            "dynamics": {
                "api_url": "DYNAMICS_API_URL",
                "access_token": "DYNAMICS_ACCESS_TOKEN"
            }
        }
        
        # Aplicar configuración a variables de entorno
        for service_name, service_config in self._config["services"].items():
            if service_name in env_mapping:
                mapping = env_mapping[service_name]
                for config_key, env_var in mapping.items():
                    if config_key in service_config and service_config[config_key]:
                        os.environ[env_var] = str(service_config[config_key])
        
        # Aplicar modo simulación
        if "simulation_mode" in self._config:
            os.environ["EXTASIS_SIMULATION_MODE"] = "true" if self._config["simulation_mode"] else "false"


# Instancia global
_config_manager: Optional[ExtasisConfigManager] = None


def get_extasis_config_manager() -> ExtasisConfigManager:
    """Obtiene la instancia global del gestor de configuración."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ExtasisConfigManager()
        # Aplicar configuración guardada al entorno al inicializar
        _config_manager.apply_config_to_environment()
    return _config_manager

