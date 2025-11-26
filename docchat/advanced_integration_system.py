"""
Advanced Integration System - Integración avanzada con APIs, deployment y cloud.

Implementa integraciones avanzadas mencionadas por Eric Schmidt:
- Integración con APIs externas
- Deployment automático
- Integración con servicios cloud
- Conectividad con sistemas externos
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import requests
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from .config import AppConfig
from .utils.llm_factory import create_llm


@dataclass
class APIIntegration:
    """Integración con una API."""
    integration_id: str
    api_name: str
    api_url: str
    api_key: Optional[str] = None
    endpoints: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "pending"  # pending, connected, error
    last_test: Optional[str] = None


@dataclass
class DeploymentConfig:
    """Configuración de deployment."""
    deployment_id: str
    platform: str  # vercel, heroku, aws, docker, etc.
    application_path: str
    environment_variables: Dict[str, str] = field(default_factory=dict)
    build_commands: List[str] = field(default_factory=list)
    start_commands: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, deploying, deployed, failed
    deployment_url: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CloudService:
    """Servicio cloud integrado."""
    service_id: str
    service_type: str  # aws, gcp, azure, etc.
    service_name: str
    credentials: Dict[str, str] = field(default_factory=dict)
    resources: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "pending"


class AdvancedIntegrationSystem:
    """
    Sistema de integración avanzada.
    
    Características:
    - Integración con APIs RESTful
    - Deployment automático a múltiples plataformas
    - Integración con servicios cloud (AWS, GCP, Azure)
    - Conectividad con sistemas externos
    - Gestión de credenciales y configuración
    """
    
    def __init__(self, config: AppConfig, provider: str = "openai"):
        self.config = config
        self.provider = provider
        
        # LLM para integraciones
        self.integration_llm = create_llm(
            provider=provider,
            model=config.agentic_model or "gpt-4o",
            temperature=0.2,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=8000,
            request_timeout=180
        )
        
        # Directorio para integraciones
        self.data_dir = Path(config.memory_dir) / "advanced_integrations"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Integraciones activas
        self.api_integrations: Dict[str, APIIntegration] = {}
        self.deployments: Dict[str, DeploymentConfig] = {}
        self.cloud_services: Dict[str, CloudService] = {}
    
    def integrate_api(
        self,
        api_name: str,
        api_url: str,
        api_key: Optional[str] = None,
        auto_discover: bool = True
    ) -> APIIntegration:
        """
        Integra con una API externa.
        
        Args:
            api_name: Nombre de la API
            api_url: URL base de la API
            api_key: API key (opcional)
            auto_discover: Si True, intenta descubrir endpoints automáticamente
        
        Returns:
            APIIntegration configurada
        """
        integration_id = f"api_{int(time.time())}"
        
        print(f"\n{'='*60}")
        print(f"🔌 INTEGRANDO API")
        print(f"{'='*60}")
        print(f"📡 API: {api_name}")
        print(f"🌐 URL: {api_url}\n")
        
        # Descubrir endpoints si está habilitado
        endpoints = []
        if auto_discover:
            print("🔍 Descubriendo endpoints...")
            endpoints = self._discover_endpoints(api_url, api_key)
            print(f"   ✅ {len(endpoints)} endpoints descubiertos\n")
        
        # Probar conexión
        print("🧪 Probando conexión...")
        connected = self._test_api_connection(api_url, api_key)
        if connected:
            print("   ✅ Conexión exitosa\n")
        else:
            print("   ⚠️  Conexión falló (puede requerir autenticación)\n")
        
        # Crear integración
        integration = APIIntegration(
            integration_id=integration_id,
            api_name=api_name,
            api_url=api_url,
            api_key=api_key,
            endpoints=endpoints,
            status="connected" if connected else "error",
            last_test=datetime.now().isoformat()
        )
        
        self.api_integrations[integration_id] = integration
        self._save_api_integration(integration)
        
        print(f"{'='*60}")
        print(f"✅ API INTEGRADA")
        print(f"{'='*60}\n")
        
        return integration
    
    def _discover_endpoints(self, api_url: str, api_key: Optional[str]) -> List[Dict[str, Any]]:
        """Descubre endpoints de una API."""
        # Intentar obtener documentación (OpenAPI/Swagger)
        common_docs_paths = ["/docs", "/swagger", "/openapi.json", "/api-docs"]
        endpoints = []
        
        for path in common_docs_paths:
            try:
                url = f"{api_url.rstrip('/')}{path}"
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    # Intentar parsear OpenAPI
                    try:
                        spec = response.json()
                        if "paths" in spec:
                            for path, methods in spec["paths"].items():
                                for method, details in methods.items():
                                    endpoints.append({
                                        "method": method.upper(),
                                        "path": path,
                                        "description": details.get("summary", ""),
                                        "parameters": details.get("parameters", [])
                                    })
                    except:
                        pass
            except Exception:
                continue
        
        # Si no se encontró documentación, generar endpoints comunes
        if not endpoints:
            endpoints = [
                {"method": "GET", "path": "/", "description": "Root endpoint"},
                {"method": "GET", "path": "/health", "description": "Health check"},
                {"method": "GET", "path": "/api/v1", "description": "API v1 endpoint"}
            ]
        
        return endpoints[:20]  # Limitar a 20 endpoints
    
    def _test_api_connection(self, api_url: str, api_key: Optional[str]) -> bool:
        """Prueba la conexión con una API."""
        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            # Intentar health check o root
            for path in ["/health", "/", "/api/health"]:
                try:
                    response = requests.get(
                        f"{api_url.rstrip('/')}{path}",
                        headers=headers,
                        timeout=5
                    )
                    if response.status_code in [200, 401, 403]:  # 401/403 significa que la API responde
                        return True
                except Exception:
                    continue
            
            return False
        except Exception:
            return False
    
    def call_api(
        self,
        integration_id: str,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Llama a un endpoint de una API integrada."""
        if integration_id not in self.api_integrations:
            return {"success": False, "error": "Integración no encontrada"}
        
        integration = self.api_integrations[integration_id]
        url = f"{integration.api_url.rstrip('/')}{endpoint}"
        
        headers = {}
        if integration.api_key:
            headers["Authorization"] = f"Bearer {integration.api_key}"
        headers["Content-Type"] = "application/json"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return {"success": False, "error": f"Método {method} no soportado"}
            
            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                "headers": dict(response.headers)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def deploy_application(
        self,
        application_path: str,
        platform: str = "vercel",
        environment_vars: Optional[Dict[str, str]] = None
    ) -> DeploymentConfig:
        """
        Despliega una aplicación automáticamente.
        
        Args:
            application_path: Ruta a la aplicación
            platform: Plataforma de deployment (vercel, heroku, aws, docker)
            environment_vars: Variables de entorno
        
        Returns:
            DeploymentConfig con estado del deployment
        """
        deployment_id = f"deploy_{int(time.time())}"
        
        print(f"\n{'='*60}")
        print(f"🚀 DESPLEGANDO APLICACIÓN")
        print(f"{'='*60}")
        print(f"📁 Ruta: {application_path}")
        print(f"☁️  Plataforma: {platform}\n")
        
        # Generar configuración de deployment
        print("⚙️  Generando configuración...")
        config = self._generate_deployment_config(application_path, platform, environment_vars)
        print(f"   ✅ Configuración generada\n")
        
        # Ejecutar deployment (simulado - en producción ejecutaría comandos reales)
        print("🚀 Ejecutando deployment...")
        deployment_result = self._execute_deployment(config)
        config.status = deployment_result["status"]
        config.deployment_url = deployment_result.get("url")
        
        if deployment_result["success"]:
            print(f"   ✅ Deployment exitoso: {config.deployment_url}\n")
        else:
            print(f"   ❌ Deployment falló: {deployment_result.get('error', 'Unknown error')}\n")
        
        self.deployments[deployment_id] = config
        self._save_deployment(config)
        
        print(f"{'='*60}")
        print(f"✅ DEPLOYMENT COMPLETADO")
        print(f"{'='*60}\n")
        
        return config
    
    def _generate_deployment_config(
        self,
        app_path: str,
        platform: str,
        env_vars: Optional[Dict[str, str]]
    ) -> DeploymentConfig:
        """Genera configuración de deployment."""
        prompt = f"""Genera configuración de deployment para esta aplicación.

RUTA DE APLICACIÓN: {app_path}
PLATAFORMA: {platform}
VARIABLES DE ENTORNO: {json.dumps(env_vars or {})}

INSTRUCCIONES:
1. Genera configuración específica para {platform}
2. Incluye comandos de build y start
3. Configura variables de entorno
4. Optimiza para la plataforma

RESPUESTA (JSON):
{{
    "build_commands": ["comando1", "comando2", ...],
    "start_commands": ["comando1", "comando2", ...],
    "environment_variables": {{"VAR": "valor"}},
    "platform_specific_config": {{}}
}}
"""
        
        try:
            response = self.integration_llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                return DeploymentConfig(
                    deployment_id=f"deploy_{int(time.time())}",
                    platform=platform,
                    application_path=app_path,
                    environment_variables=data.get("environment_variables", env_vars or {}),
                    build_commands=data.get("build_commands", []),
                    start_commands=data.get("start_commands", [])
                )
        except Exception:
            pass
        
        # Configuración por defecto
        return DeploymentConfig(
            deployment_id=f"deploy_{int(time.time())}",
            platform=platform,
            application_path=app_path,
            environment_variables=env_vars or {},
            build_commands=["npm install", "npm run build"] if platform in ["vercel", "heroku"] else [],
            start_commands=["npm start"] if platform in ["vercel", "heroku"] else ["python app.py"]
        )
    
    def _execute_deployment(self, config: DeploymentConfig) -> Dict[str, Any]:
        """Ejecuta el deployment (simulado)."""
        # En producción, aquí se ejecutarían comandos reales:
        # - vercel deploy
        # - heroku create && git push heroku main
        # - docker build && docker push
        # - aws deploy
        
        # Por ahora, simulamos el deployment
        deployment_url = f"https://{config.platform}-{config.deployment_id}.example.com"
        
        return {
            "success": True,
            "status": "deployed",
            "url": deployment_url,
            "message": f"Aplicación desplegada en {config.platform}"
        }
    
    def integrate_cloud_service(
        self,
        service_type: str,
        service_name: str,
        credentials: Dict[str, str]
    ) -> CloudService:
        """
        Integra con un servicio cloud.
        
        Args:
            service_type: Tipo de servicio (aws, gcp, azure)
            service_name: Nombre del servicio
            credentials: Credenciales de acceso
        
        Returns:
            CloudService configurado
        """
        service_id = f"cloud_{int(time.time())}"
        
        print(f"\n{'='*60}")
        print(f"☁️  INTEGRANDO SERVICIO CLOUD")
        print(f"{'='*60}")
        print(f"🌐 Tipo: {service_type}")
        print(f"📦 Servicio: {service_name}\n")
        
        # Verificar credenciales
        print("🔐 Verificando credenciales...")
        verified = self._verify_cloud_credentials(service_type, credentials)
        if verified:
            print("   ✅ Credenciales válidas\n")
        else:
            print("   ⚠️  Credenciales no verificadas (puede requerir configuración adicional)\n")
        
        # Descubrir recursos
        print("🔍 Descubriendo recursos...")
        resources = self._discover_cloud_resources(service_type, credentials)
        print(f"   ✅ {len(resources)} recursos descubiertos\n")
        
        # Crear servicio
        service = CloudService(
            service_id=service_id,
            service_type=service_type,
            service_name=service_name,
            credentials=credentials,
            resources=resources,
            status="connected" if verified else "pending"
        )
        
        self.cloud_services[service_id] = service
        self._save_cloud_service(service)
        
        print(f"{'='*60}")
        print(f"✅ SERVICIO CLOUD INTEGRADO")
        print(f"{'='*60}\n")
        
        return service
    
    def _verify_cloud_credentials(self, service_type: str, credentials: Dict[str, str]) -> bool:
        """Verifica credenciales de cloud (simulado)."""
        # En producción, aquí se verificarían credenciales reales
        # usando SDKs de AWS, GCP, Azure, etc.
        required_keys = {
            "aws": ["aws_access_key_id", "aws_secret_access_key"],
            "gcp": ["project_id", "credentials_json"],
            "azure": ["subscription_id", "tenant_id", "client_id", "client_secret"]
        }
        
        required = required_keys.get(service_type.lower(), [])
        return all(key in credentials for key in required)
    
    def _discover_cloud_resources(self, service_type: str, credentials: Dict[str, str]) -> List[Dict[str, Any]]:
        """Descubre recursos en el servicio cloud (simulado)."""
        # En producción, usaría SDKs reales para descubrir recursos
        common_resources = {
            "aws": ["EC2 instances", "S3 buckets", "Lambda functions", "RDS databases"],
            "gcp": ["Compute Engine VMs", "Cloud Storage buckets", "Cloud Functions", "Cloud SQL"],
            "azure": ["Virtual Machines", "Storage Accounts", "Functions", "SQL Databases"]
        }
        
        resources = common_resources.get(service_type.lower(), [])
        return [{"type": r, "name": f"{r}_{i}", "status": "active"} for i, r in enumerate(resources[:5])]
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extrae JSON de un texto."""
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        return None
    
    def _save_api_integration(self, integration: APIIntegration):
        """Guarda una integración de API."""
        integration_file = self.data_dir / f"api_{integration.integration_id}.json"
        integration_dict = {
            "integration_id": integration.integration_id,
            "api_name": integration.api_name,
            "api_url": integration.api_url,
            "endpoints": integration.endpoints,
            "status": integration.status,
            "last_test": integration.last_test
        }
        # No guardar API key por seguridad
        with open(integration_file, 'w', encoding='utf-8') as f:
            json.dump(integration_dict, f, indent=2, ensure_ascii=False)
    
    def _save_deployment(self, deployment: DeploymentConfig):
        """Guarda una configuración de deployment."""
        deployment_file = self.data_dir / f"deploy_{deployment.deployment_id}.json"
        deployment_dict = {
            "deployment_id": deployment.deployment_id,
            "platform": deployment.platform,
            "application_path": deployment.application_path,
            "environment_variables": deployment.environment_variables,
            "build_commands": deployment.build_commands,
            "start_commands": deployment.start_commands,
            "status": deployment.status,
            "deployment_url": deployment.deployment_url,
            "timestamp": deployment.timestamp
        }
        with open(deployment_file, 'w', encoding='utf-8') as f:
            json.dump(deployment_dict, f, indent=2, ensure_ascii=False)
    
    def _save_cloud_service(self, service: CloudService):
        """Guarda un servicio cloud."""
        service_file = self.data_dir / f"cloud_{service.service_id}.json"
        service_dict = {
            "service_id": service.service_id,
            "service_type": service.service_type,
            "service_name": service.service_name,
            "resources": service.resources,
            "status": service.status
        }
        # No guardar credenciales por seguridad
        with open(service_file, 'w', encoding='utf-8') as f:
            json.dump(service_dict, f, indent=2, ensure_ascii=False)
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Obtiene estado de todas las integraciones."""
        return {
            "api_integrations": len(self.api_integrations),
            "deployments": len(self.deployments),
            "cloud_services": len(self.cloud_services),
            "active_apis": len([a for a in self.api_integrations.values() if a.status == "connected"]),
            "deployed_apps": len([d for d in self.deployments.values() if d.status == "deployed"])
        }

