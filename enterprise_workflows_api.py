"""FastAPI para Enterprise Autonomous Workflows (headless Agentic AI).

Permite a clientes:
- Subir documentos vía HTTP (multipart)
- Lanzar workflows específicos (contratos, facturas, compliance, riesgo, multisistema)
- Recibir el resultado estructurado en JSON

Esta API envuelve EnterpriseAPIMode + ResearchActionAgent + EnterpriseAutonomousWorkflows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import shutil
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from docchat.config import AppConfig
from docchat.semantic_data_engine import SemanticDataEngine
from docchat.data_ingestion_engine import DataIngestionEngine
from docchat.enterprise_api import EnterpriseAPIMode
from docchat.research_action_agent import ResearchActionAgent
from docchat.enterprise_autonomous_workflows import EnterpriseAutonomousWorkflows
from docchat.audit import AuditLogger

try:
    import json
    import requests  # type: ignore
    REQUESTS_AVAILABLE = True
except Exception:  # pragma: no cover - opcional
    REQUESTS_AVAILABLE = False


config = AppConfig()

semantic_engine = SemanticDataEngine(config)
data_ingestion_engine = DataIngestionEngine(semantic_engine)
enterprise_api = EnterpriseAPIMode(config, provider="openai")
research_agent = ResearchActionAgent(config, semantic_engine=semantic_engine)
audit_logger = AuditLogger(config.audit_log_dir, config.enable_audit_logs)

workflows = EnterpriseAutonomousWorkflows(
    config=config,
    enterprise_api=enterprise_api,
    research_agent=research_agent,
    ingestion_engine=data_ingestion_engine,
    audit_logger=audit_logger,
)

app = FastAPI(title="DocChat Enterprise Autonomous Workflows API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/enterprise-workflows/health")
def health_check() -> Dict[str, Any]:
    """Endpoint simple de healthcheck."""
    return {"status": "ok", "message": "Enterprise Autonomous Workflows API running"}


@app.post("/api/enterprise-workflows/run")
async def run_enterprise_workflow(
    workflow_type: str = Form(..., description="Tipo de workflow (ej: auditoria_contratos, ap_automation, compliance_normativo, etc.)"),
    tenant_id: str = Form("default", description="Identificador del tenant / cliente"),
    auto_detect: bool = Form(True, description="Usar detección automática de problemas/oportunidades en Enterprise API"),
    auto_execute_actions: bool = Form(False, description="Permitir que el agente ejecute acciones automáticamente donde sea seguro"),
    simulation_mode: bool = Form(False, description="Si True, NO ejecuta acciones reales, solo simula lo que haría"),
    integration_prefs_json: Optional[str] = Form(
        None,
        description="JSON opcional con preferencias de integraciones (por ejemplo, qué sistemas usar para tickets, ERP, CRM, etc.)",
    ),
    webhook_url: Optional[str] = Form(
        None,
        description="URL opcional de webhook para enviar el resultado al completar el workflow",
    ),
    files: List[UploadFile] = File(..., description="Documentos empresariales (PDF, DOCX, etc.)"),
) -> Dict[str, Any]:
    """Ejecuta un workflow autónomo de extremo a extremo vía API."""
    if not files:
        raise HTTPException(status_code=400, detail="No se recibieron archivos")

    # Parsear preferencias de integraciones si se envían
    integration_prefs: Dict[str, Any] = {}
    if integration_prefs_json:
        try:
            integration_prefs = json.loads(integration_prefs_json)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"integration_prefs_json inválido: {e}")

    # Guardar archivos temporalmente en disco para reutilizar la misma ruta que la UI
    temp_dir = Path(tempfile.mkdtemp(prefix="eaw_api_"))
    paths: List[Path] = []

    try:
        for f in files:
            dest = temp_dir / (f.filename or "documento")
            with dest.open("wb") as out:
                shutil.copyfileobj(f.file, out)
            paths.append(dest)

        # Ejecutar workflow interno
        result = workflows.run_workflow(
            files=paths,
            workflow_type=workflow_type,
            auto_detect=auto_detect,
            auto_execute_actions=auto_execute_actions,
            tenant_id=tenant_id,
            integration_prefs=integration_prefs,
            webhook_url=webhook_url,
            simulation_mode=simulation_mode,
        )

        response_payload: Dict[str, Any] = {
            "workflow_type": result.workflow_type,
            "tenant_id": tenant_id,
            "enterprise_summary": result.enterprise_summary,
            "research_result": result.research_result,
            "logs": result.logs,
        }

        # Enviar webhook si se proporciona URL y hay librería disponible
        if webhook_url and REQUESTS_AVAILABLE:
            try:
                requests.post(webhook_url, json=response_payload, timeout=5)  # type: ignore[arg-type]
            except Exception as e:  # pragma: no cover - fallo de red no rompe la API
                audit_logger.log(
                    event_type="webhook_error",
                    action="send_webhook",
                    resource="enterprise_workflow",
                    user_id=tenant_id,
                    metadata={"webhook_url": webhook_url, "error": str(e)},
                )

        return response_payload
    finally:
        # Limpiar archivos temporales
        shutil.rmtree(temp_dir, ignore_errors=True)


__all__ = ["app"]


