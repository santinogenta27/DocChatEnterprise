"""
JARVIS API - Sistema completo de APIs para integración enterprise
Permite que JARVIS se integre con cualquier sistema externo
Basado en principios de "make more than you take" - dar más valor del que se recibe
"""

from __future__ import annotations

import json
import time
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid
import hashlib
from pathlib import Path

from langchain_core.documents import Document

from .config import AppConfig
from .jarvis_agent import JarvisAgent, JarvisInsight, JarvisAlert, JarvisTask, TaskPriority
from .jarvis_manager import JarvisManager
from .persistent_storage import PersistentStorage


class APIEndpoint(str, Enum):
    """Endpoints de la API de JARVIS."""
    WEBHOOK_INGEST = "/api/jarvis/webhook/ingest"
    ALERTS_SEND = "/api/jarvis/alerts/send"
    STATUS_QUERY = "/api/jarvis/status"
    INSIGHTS_QUERY = "/api/jarvis/insights"
    TASKS_ADD = "/api/jarvis/tasks/add"
    TASKS_QUERY = "/api/jarvis/tasks"
    AUTOMATION_EXECUTE = "/api/jarvis/automation/execute"
    REPORTS_GET = "/api/jarvis/reports"
    DOCUMENTS_UPLOAD = "/api/jarvis/documents/upload"
    CLOUD_SYNC = "/api/jarvis/cloud/sync"


@dataclass
class WebhookPayload:
    """Payload de webhook para ingerir datos."""
    source: str  # Sistema externo (CRM, ERP, etc.)
    data: Any  # Datos a absorber
    data_type: str  # Tipo de dato
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[str] = None
    api_key: Optional[str] = None


@dataclass
class AlertNotification:
    """Notificación de alerta para enviar a sistemas externos."""
    alert_id: str
    title: str
    message: str
    severity: str
    destination: str  # Slack, Email, Teams, SMS, etc.
    destination_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class APIResponse:
    """Respuesta estándar de la API."""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class JarvisAPI:
    """
    Sistema completo de APIs para JARVIS.
    
    Permite integración enterprise completa:
    - Recibir datos de sistemas externos
    - Enviar alertas a sistemas externos
    - Consultar estado e insights
    - Agregar tareas programáticamente
    - Ejecutar automatizaciones
    - Obtener reportes
    - Subir documentos
    - Sincronizar con cloud
    """
    
    def __init__(
        self,
        jarvis_manager: JarvisManager,
        persistent_storage: PersistentStorage,
        config: AppConfig
    ):
        self.jarvis_manager = jarvis_manager
        self.persistent_storage = persistent_storage
        self.config = config
        
        # API keys para autenticación (en producción, usar sistema de auth robusto)
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        
        # Configuración de integraciones externas
        self.integrations_config: Dict[str, Dict[str, Any]] = {}
        
        # Estadísticas de API
        self.api_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "webhooks_received": 0,
            "alerts_sent": 0,
            "tasks_added": 0,
            "automations_executed": 0
        }
        
        print("✅ JARVIS API inicializado - Listo para integraciones enterprise")
    
    # ============================================
    # API 1: Webhook/Ingestión de Datos
    # ============================================
    
    async def webhook_ingest(
        self,
        payload: WebhookPayload,
        api_key: Optional[str] = None
    ) -> APIResponse:
        """
        API 1: Webhook para recibir datos de sistemas externos.
        
        Permite que cualquier sistema envíe datos a JARVIS automáticamente.
        """
        try:
            self.api_stats["total_requests"] += 1
            self.api_stats["webhooks_received"] += 1
            
            # Validar API key si está configurado
            if api_key and not self._validate_api_key(api_key):
                return APIResponse(
                    success=False,
                    error="Invalid API key"
                )
            
            # Obtener o crear instancia de JARVIS
            user_id = payload.metadata.get("user_id", "api_user")
            jarvis = self.jarvis_manager.get_or_create_jarvis(user_id)
            
            # Absorber datos
            chunk_id = jarvis.absorb_data(
                data=payload.data,
                source=payload.source,
                data_type=payload.data_type,
                metadata={
                    **payload.metadata,
                    "api_received": True,
                    "timestamp": payload.timestamp or datetime.now().isoformat()
                }
            )
            
            self.api_stats["successful_requests"] += 1
            
            return APIResponse(
                success=True,
                data={
                    "chunk_id": chunk_id,
                    "message": f"Data absorbed from {payload.source}",
                    "data_type": payload.data_type
                },
                message="Data successfully ingested by JARVIS"
            )
            
        except Exception as e:
            self.api_stats["failed_requests"] += 1
            return APIResponse(
                success=False,
                error=str(e)
            )
    
    # ============================================
    # API 2: Envío de Alertas a Sistemas Externos
    # ============================================
    
    async def send_alert_notification(
        self,
        alert: JarvisAlert,
        notification: AlertNotification
    ) -> APIResponse:
        """
        API 2: Enviar alertas a sistemas externos (Slack, Email, Teams, SMS, etc.).
        """
        try:
            self.api_stats["total_requests"] += 1
            self.api_stats["alerts_sent"] += 1
            
            destination = notification.destination.lower()
            config = notification.destination_config
            
            # Enviar según destino
            if destination == "slack":
                result = await self._send_to_slack(alert, config)
            elif destination == "email":
                result = await self._send_to_email(alert, config)
            elif destination == "teams":
                result = await self._send_to_teams(alert, config)
            elif destination == "sms":
                result = await self._send_to_sms(alert, config)
            elif destination == "webhook":
                result = await self._send_to_webhook(alert, config)
            else:
                return APIResponse(
                    success=False,
                    error=f"Unsupported destination: {destination}"
                )
            
            self.api_stats["successful_requests"] += 1
            
            return APIResponse(
                success=True,
                data=result,
                message=f"Alert sent to {destination}"
            )
            
        except Exception as e:
            self.api_stats["failed_requests"] += 1
            return APIResponse(
                success=False,
                error=str(e)
            )
    
    async def _send_to_slack(self, alert: JarvisAlert, config: Dict[str, Any]) -> Dict[str, Any]:
        """Envía alerta a Slack."""
        # En producción, usar Slack SDK
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            raise ValueError("Slack webhook_url required")
        
        import requests
        
        severity_colors = {
            "critical": "#FF0000",
            "high": "#FF8800",
            "medium": "#FFBB00",
            "low": "#00AA00"
        }
        
        payload = {
            "text": f"🚨 JARVIS Alert: {alert.title}",
            "attachments": [{
                "color": severity_colors.get(alert.severity, "#808080"),
                "fields": [
                    {"title": "Severity", "value": alert.severity.upper(), "short": True},
                    {"title": "Type", "value": alert.alert_type, "short": True},
                    {"title": "Message", "value": alert.message, "short": False}
                ],
                "ts": int(alert.created_at)
            }]
        }
        
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        
        return {"sent": True, "destination": "slack"}
    
    async def _send_to_email(self, alert: JarvisAlert, config: Dict[str, Any]) -> Dict[str, Any]:
        """Envía alerta por email."""
        # En producción, usar servicio de email (SendGrid, AWS SES, etc.)
        recipients = config.get("recipients", [])
        if not recipients:
            raise ValueError("Email recipients required")
        
        # Simulación - en producción usar servicio real
        return {
            "sent": True,
            "destination": "email",
            "recipients": recipients
        }
    
    async def _send_to_teams(self, alert: JarvisAlert, config: Dict[str, Any]) -> Dict[str, Any]:
        """Envía alerta a Microsoft Teams."""
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            raise ValueError("Teams webhook_url required")
        
        import requests
        
        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": alert.title,
            "themeColor": "0078D4",
            "title": f"🚨 JARVIS Alert: {alert.title}",
            "sections": [{
                "activityTitle": alert.alert_type,
                "facts": [
                    {"name": "Severity", "value": alert.severity.upper()},
                    {"name": "Message", "value": alert.message}
                ]
            }]
        }
        
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        
        return {"sent": True, "destination": "teams"}
    
    async def _send_to_sms(self, alert: JarvisAlert, config: Dict[str, Any]) -> Dict[str, Any]:
        """Envía alerta por SMS."""
        # En producción, usar servicio de SMS (Twilio, AWS SNS, etc.)
        phone_numbers = config.get("phone_numbers", [])
        if not phone_numbers:
            raise ValueError("Phone numbers required")
        
        return {
            "sent": True,
            "destination": "sms",
            "phone_numbers": phone_numbers
        }
    
    async def _send_to_webhook(self, alert: JarvisAlert, config: Dict[str, Any]) -> Dict[str, Any]:
        """Envía alerta a webhook personalizado."""
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            raise ValueError("Webhook URL required")
        
        import requests
        
        payload = {
            "alert_id": alert.alert_id,
            "title": alert.title,
            "message": alert.message,
            "severity": alert.severity,
            "alert_type": alert.alert_type,
            "created_at": alert.created_at
        }
        
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        
        return {"sent": True, "destination": "webhook"}
    
    # ============================================
    # API 3: Consulta de Estado e Insights
    # ============================================
    
    async def get_status(
        self,
        user_id: str = "user",
        include_insights: bool = True,
        include_alerts: bool = True
    ) -> APIResponse:
        """
        API 3: Obtener estado completo de JARVIS.
        """
        try:
            self.api_stats["total_requests"] += 1
            
            jarvis = self.jarvis_manager.get_or_create_jarvis(user_id)
            dashboard_data = jarvis.get_dashboard_data()
            
            result = {
                "status": "active" if dashboard_data["is_running"] else "inactive",
                "stats": dashboard_data["stats"],
                "memory": dashboard_data["memory"],
                "tasks_summary": dashboard_data["tasks"]
            }
            
            if include_insights:
                insights = jarvis.get_recent_insights(limit=10)
                result["insights"] = [
                    {
                        "title": i.title,
                        "category": i.category,
                        "confidence": i.confidence,
                        "actionable": i.actionable
                    }
                    for i in insights
                ]
            
            if include_alerts:
                alerts = jarvis.get_unacknowledged_alerts()
                result["alerts"] = [
                    {
                        "title": a.title,
                        "severity": a.severity,
                        "message": a.message[:200]
                    }
                    for a in alerts[:10]
                ]
            
            self.api_stats["successful_requests"] += 1
            
            return APIResponse(
                success=True,
                data=result
            )
            
        except Exception as e:
            self.api_stats["failed_requests"] += 1
            return APIResponse(
                success=False,
                error=str(e)
            )
    
    async def get_insights(
        self,
        user_id: str = "user",
        limit: int = 20,
        category: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> APIResponse:
        """
        API 3b: Obtener insights específicos.
        """
        try:
            self.api_stats["total_requests"] += 1
            
            jarvis = self.jarvis_manager.get_or_create_jarvis(user_id)
            all_insights = jarvis.get_recent_insights(limit=limit * 2)
            
            # Filtrar por categoría y confianza
            filtered = [
                i for i in all_insights
                if (not category or i.category == category)
                and i.confidence >= min_confidence
            ][:limit]
            
            insights_data = [
                {
                    "insight_id": i.insight_id,
                    "title": i.title,
                    "description": i.description,
                    "category": i.category,
                    "confidence": i.confidence,
                    "actionable": i.actionable,
                    "action_recommendation": i.action_recommendation,
                    "evidence": i.evidence,
                    "discovered_at": i.discovered_at
                }
                for i in filtered
            ]
            
            self.api_stats["successful_requests"] += 1
            
            return APIResponse(
                success=True,
                data={
                    "insights": insights_data,
                    "total": len(insights_data)
                }
            )
            
        except Exception as e:
            self.api_stats["failed_requests"] += 1
            return APIResponse(
                success=False,
                error=str(e)
            )
    
    # ============================================
    # API 4: Gestión de Tareas
    # ============================================
    
    async def add_task(
        self,
        task_type: str,
        description: str,
        priority: str = "medium",
        parameters: Optional[Dict[str, Any]] = None,
        user_id: str = "user"
    ) -> APIResponse:
        """
        API 4: Agregar tarea a JARVIS programáticamente.
        """
        try:
            self.api_stats["total_requests"] += 1
            self.api_stats["tasks_added"] += 1
            
            jarvis = self.jarvis_manager.get_or_create_jarvis(user_id)
            task = jarvis.add_task(
                task_type=task_type,
                description=description,
                priority=TaskPriority(priority),
                parameters=parameters or {}
            )
            
            self.api_stats["successful_requests"] += 1
            
            return APIResponse(
                success=True,
                data={
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "description": task.description
                },
                message="Task added successfully"
            )
            
        except Exception as e:
            self.api_stats["failed_requests"] += 1
            return APIResponse(
                success=False,
                error=str(e)
            )
    
    async def get_tasks(
        self,
        user_id: str = "user",
        status: Optional[str] = None,
        limit: int = 20
    ) -> APIResponse:
        """
        API 4b: Obtener tareas de JARVIS.
        """
        try:
            self.api_stats["total_requests"] += 1
            
            jarvis = self.jarvis_manager.get_or_create_jarvis(user_id)
            all_tasks = jarvis.tasks[-limit * 2:] if hasattr(jarvis, 'tasks') else []
            
            # Filtrar por estado
            if status:
                all_tasks = [t for t in all_tasks if t.status.value == status]
            
            tasks_data = [
                {
                    "task_id": t.task_id,
                    "task_type": t.task_type,
                    "description": t.description,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "created_at": t.created_at,
                    "completed_at": t.completed_at,
                    "execution_time": t.execution_time,
                    "error": t.error
                }
                for t in all_tasks[-limit:]
            ]
            
            self.api_stats["successful_requests"] += 1
            
            return APIResponse(
                success=True,
                data={
                    "tasks": tasks_data,
                    "total": len(tasks_data)
                }
            )
            
        except Exception as e:
            self.api_stats["failed_requests"] += 1
            return APIResponse(
                success=False,
                error=str(e)
            )
    
    # ============================================
    # API 5: Automatización
    # ============================================
    
    async def execute_automation(
        self,
        command: str,
        auto_execute: bool = True,
        user_id: str = "user"
    ) -> APIResponse:
        """
        API 5: Ejecutar automatización desde sistemas externos.
        """
        try:
            self.api_stats["total_requests"] += 1
            self.api_stats["automations_executed"] += 1
            
            jarvis = self.jarvis_manager.get_or_create_jarvis(user_id)
            result = await jarvis.execute_automation(
                command=command,
                auto_execute=auto_execute
            )
            
            self.api_stats["successful_requests"] += 1
            
            return APIResponse(
                success=result.get("success", False),
                data=result,
                message="Automation executed" if result.get("success") else "Automation failed"
            )
            
        except Exception as e:
            self.api_stats["failed_requests"] += 1
            return APIResponse(
                success=False,
                error=str(e)
            )
    
    # ============================================
    # API 6: Reportes
    # ============================================
    
    async def get_reports(
        self,
        user_id: str = "user",
        period: str = "daily",
        limit: int = 10
    ) -> APIResponse:
        """
        API 6: Obtener reportes generados por JARVIS.
        """
        try:
            self.api_stats["total_requests"] += 1
            
            jarvis = self.jarvis_manager.get_or_create_jarvis(user_id)
            
            # Buscar tareas de tipo "generate_report"
            report_tasks = [
                t for t in jarvis.tasks
                if t.task_type == "generate_report" and t.status.value == "completed"
            ][-limit:]
            
            reports = []
            for task in report_tasks:
                if task.result:
                    reports.append({
                        "task_id": task.task_id,
                        "period": task.result.get("period", "unknown"),
                        "generated_at": task.result.get("generated_at"),
                        "content": task.result.get("content", "")[:1000],  # Primeros 1000 chars
                        "stats": task.result.get("stats", {})
                    })
            
            self.api_stats["successful_requests"] += 1
            
            return APIResponse(
                success=True,
                data={
                    "reports": reports,
                    "total": len(reports)
                }
            )
            
        except Exception as e:
            self.api_stats["failed_requests"] += 1
            return APIResponse(
                success=False,
                error=str(e)
            )
    
    # ============================================
    # API 7: Subida de Documentos
    # ============================================
    
    async def upload_document(
        self,
        document_content: str,
        file_name: str,
        source: str = "api",
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "user"
    ) -> APIResponse:
        """
        API 7: Subir documentos a JARVIS desde sistemas externos.
        """
        try:
            self.api_stats["total_requests"] += 1
            
            # Crear documento
            doc = Document(
                page_content=document_content,
                metadata={
                    "source": source,
                    "file_name": file_name,
                    "uploaded_via_api": True,
                    "timestamp": datetime.now().isoformat(),
                    **(metadata or {})
                }
            )
            
            # Guardar en almacenamiento persistente
            doc_id = self.persistent_storage.save_document(
                document=doc,
                session_id=f"jarvis_{user_id}",
                source=source
            )
            
            # Absorber en JARVIS
            jarvis = self.jarvis_manager.get_or_create_jarvis(user_id)
            chunk_id = jarvis.absorb_data(
                data=doc,
                source=source,
                data_type="document",
                metadata=metadata
            )
            
            # Auto-indexar
            indexing_data = await jarvis.intelligent_auto_indexing(doc)
            
            self.api_stats["successful_requests"] += 1
            
            return APIResponse(
                success=True,
                data={
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                    "indexing": indexing_data,
                    "message": "Document uploaded and indexed"
                }
            )
            
        except Exception as e:
            self.api_stats["failed_requests"] += 1
            return APIResponse(
                success=False,
                error=str(e)
            )
    
    # ============================================
    # API 8: Sincronización con Cloud
    # ============================================
    
    async def sync_with_cloud(
        self,
        cloud_provider: str,  # aws, gcp, azure
        bucket_name: str,
        sync_direction: str = "bidirectional",  # upload, download, bidirectional
        user_id: str = "user"
    ) -> APIResponse:
        """
        API 8: Sincronizar datos de JARVIS con cloud storage.
        """
        try:
            self.api_stats["total_requests"] += 1
            
            jarvis = self.jarvis_manager.get_or_create_jarvis(user_id)
            
            # Obtener todos los documentos
            all_docs = self.persistent_storage.get_all_documents(
                session_id=f"jarvis_{user_id}",
                limit=1000
            )
            
            sync_results = {
                "provider": cloud_provider,
                "bucket": bucket_name,
                "direction": sync_direction,
                "documents_synced": 0,
                "errors": []
            }
            
            # En producción, implementar sincronización real con cloud
            # Por ahora, simular sincronización
            if sync_direction in ["upload", "bidirectional"]:
                # Subir documentos a cloud
                for doc_record in all_docs[:100]:  # Limitar a 100 por sync
                    try:
                        # En producción, usar SDK del cloud provider
                        sync_results["documents_synced"] += 1
                    except Exception as e:
                        sync_results["errors"].append(f"Error syncing {doc_record.doc_id}: {e}")
            
            if sync_direction in ["download", "bidirectional"]:
                # Descargar documentos de cloud
                # En producción, listar objetos en bucket y descargar
                pass
            
            self.api_stats["successful_requests"] += 1
            
            return APIResponse(
                success=True,
                data=sync_results,
                message=f"Sync completed with {cloud_provider}"
            )
            
        except Exception as e:
            self.api_stats["failed_requests"] += 1
            return APIResponse(
                success=False,
                error=str(e)
            )
    
    # ============================================
    # Utilidades
    # ============================================
    
    def _validate_api_key(self, api_key: str) -> bool:
        """Valida API key."""
        # En producción, usar sistema de autenticación robusto
        if api_key in self.api_keys:
            return True
        # Permitir API keys del config
        if hasattr(self.config, 'jarvis_api_keys'):
            return api_key in self.config.jarvis_api_keys
        return True  # Por defecto, permitir (en producción, cambiar)
    
    def get_api_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de uso de la API."""
        return {
            **self.api_stats,
            "endpoints_available": len(APIEndpoint),
            "integrations_configured": len(self.integrations_config)
        }
    
    def register_integration(
        self,
        integration_name: str,
        config: Dict[str, Any]
    ):
        """Registra una integración externa."""
        self.integrations_config[integration_name] = config
        print(f"✅ Integración registrada: {integration_name}")
    
    def generate_api_key(self, user_id: str, permissions: List[str]) -> str:
        """Genera una API key para un usuario."""
        api_key = hashlib.sha256(
            f"{user_id}{time.time()}{uuid.uuid4()}".encode()
        ).hexdigest()
        
        self.api_keys[api_key] = {
            "user_id": user_id,
            "permissions": permissions,
            "created_at": time.time()
        }
        
        return api_key

