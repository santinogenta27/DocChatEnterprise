"""
API REST FastAPI para integraciones del modo BANKS.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException, UploadFile, File, Form
    from fastapi.responses import JSONResponse, FileResponse
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logging.warning("FastAPI no disponible. Instala con: pip install fastapi uvicorn")

from docchat.config import AppConfig
from ..banks_mode import BanksMode

logger = logging.getLogger(__name__)


if FASTAPI_AVAILABLE:
    # Schemas Pydantic para API
    class ComplianceCheckRequest(BaseModel):
        """Request para compliance check."""
        input_path: Optional[str] = None
        jurisdiction: str = Field(default="US", description="Jurisdicción (US, EU, MX, CO, etc.)")
        steering_commands: Optional[List[str]] = Field(default=[], description="Comandos de steering")
        action_config: Optional[Dict[str, Any]] = Field(default={}, description="Configuración de acciones")
        client_id: Optional[str] = Field(default=None, description="ID del cliente")
    
    class ComplianceCheckResponse(BaseModel):
        """Response de compliance check."""
        success: bool
        result: Optional[Dict[str, Any]] = None
        entities_count: int = 0
        risk_scores_count: int = 0
        reports_generated: int = 0
        actions_executed: int = 0
        errors: List[str] = []
        processing_time_seconds: float = 0.0
    
    class BatchComplianceRequest(BaseModel):
        """Request para batch processing."""
        clients: List[Dict[str, str]] = Field(description="Lista de clientes con input_path")
        jurisdiction: str = Field(default="US")
        action_config: Optional[Dict[str, Any]] = Field(default={})
    
    class HealthCheckResponse(BaseModel):
        """Health check response."""
        status: str
        version: str
        timestamp: str
        services: Dict[str, str]


class BanksAPI:
    """API REST para el modo BANKS."""
    
    def __init__(self, config: AppConfig):
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI no está instalado. Instala con: pip install fastapi uvicorn")
        
        self.config = config
        self.banks_mode = BanksMode(config)
        self.app = FastAPI(
            title="BANKS Compliance API",
            description="API REST para Compliance KYC/AML",
            version="1.0.0"
        )
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Configura las rutas de la API."""
        
        @self.app.get("/health", response_model=HealthCheckResponse)
        async def health_check():
            """Health check endpoint."""
            return HealthCheckResponse(
                status="healthy",
                version="1.0.0",
                timestamp=datetime.now().isoformat(),
                services={
                    "banks_mode": "operational",
                    "workflow": "operational"
                }
            )
        
        @self.app.post("/api/v1/compliance/check", response_model=ComplianceCheckResponse)
        async def compliance_check(request: ComplianceCheckRequest):
            """Ejecuta un compliance check."""
            start_time = datetime.now()
            
            try:
                if not request.input_path:
                    raise HTTPException(
                        status_code=400,
                        detail="input_path es requerido"
                    )
                
                result = self.banks_mode.process_compliance_check(
                    input_path=request.input_path,
                    jurisdiction=request.jurisdiction,
                    steering_commands=request.steering_commands or [],
                    action_config=request.action_config or {},
                    client_id=request.client_id
                )
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                return ComplianceCheckResponse(
                    success=result["success"],
                    result=result.get("result"),
                    entities_count=result.get("entities_count", 0),
                    risk_scores_count=result.get("risk_scores_count", 0),
                    reports_generated=result.get("reports_generated", 0),
                    actions_executed=result.get("actions_executed", 0),
                    errors=result.get("errors", []),
                    processing_time_seconds=processing_time
                )
            
            except Exception as e:
                logger.error(f"Error en compliance check API: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Error procesando compliance check: {str(e)}"
                )
        
        @self.app.post("/api/v1/compliance/check/batch")
        async def batch_compliance_check(request: BatchComplianceRequest):
            """Procesa múltiples clientes en batch."""
            try:
                result = self.banks_mode.process_batch_compliance(
                    clients=request.clients,
                    jurisdiction=request.jurisdiction,
                    action_config=request.action_config or {}
                )
                
                return JSONResponse(content=result)
            
            except Exception as e:
                logger.error(f"Error en batch compliance check: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Error procesando batch: {str(e)}"
                )
        
        @self.app.post("/api/v1/compliance/check/upload")
        async def compliance_check_upload(
            files: List[UploadFile] = File(...),
            jurisdiction: str = Form("US"),
            steering_commands: Optional[str] = Form(None),
            action_config: Optional[str] = Form(None)
        ):
            """Compliance check con archivos subidos."""
            import tempfile
            import shutil
            
            try:
                # Guardar archivos temporalmente
                temp_dir = Path(tempfile.mkdtemp())
                
                for file in files:
                    file_path = temp_dir / file.filename
                    with open(file_path, "wb") as f:
                        shutil.copyfileobj(file.file, f)
                
                # Parsear steering commands
                steering = []
                if steering_commands:
                    steering = [cmd.strip() for cmd in steering_commands.split('\n') if cmd.strip()]
                
                # Parsear action config
                action_cfg = {}
                if action_config:
                    import json
                    action_cfg = json.loads(action_config)
                
                # Procesar
                result = self.banks_mode.process_compliance_check(
                    input_path=str(temp_dir),
                    jurisdiction=jurisdiction,
                    steering_commands=steering,
                    action_config=action_cfg
                )
                
                return JSONResponse(content=result)
            
            except Exception as e:
                logger.error(f"Error en upload compliance check: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Error procesando archivos: {str(e)}"
                )
        
        @self.app.get("/api/v1/reports")
        async def list_reports():
            """Lista todos los reportes generados."""
            try:
                reports_dir = Path(self.config.cache_dir) / "banks" / "reports"
                
                if not reports_dir.exists():
                    return JSONResponse(content={"reports": []})
                
                reports = []
                for report_file in reports_dir.glob("*"):
                    reports.append({
                        "name": report_file.name,
                        "path": str(report_file),
                        "size_bytes": report_file.stat().st_size,
                        "modified": datetime.fromtimestamp(report_file.stat().st_mtime).isoformat(),
                        "type": report_file.suffix
                    })
                
                return JSONResponse(content={"reports": reports})
            
            except Exception as e:
                logger.error(f"Error listando reportes: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Error listando reportes: {str(e)}"
                )
        
        @self.app.get("/api/v1/reports/{report_name}")
        async def download_report(report_name: str):
            """Descarga un reporte específico."""
            try:
                report_path = Path(self.config.cache_dir) / "banks" / "reports" / report_name
                
                if not report_path.exists():
                    raise HTTPException(
                        status_code=404,
                        detail=f"Reporte no encontrado: {report_name}"
                    )
                
                return FileResponse(
                    path=str(report_path),
                    filename=report_name,
                    media_type="application/octet-stream"
                )
            
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error descargando reporte: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Error descargando reporte: {str(e)}"
                )
    
    def get_app(self) -> FastAPI:
        """Retorna la app FastAPI."""
        return self.app
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Ejecuta el servidor API."""
        try:
            import uvicorn
            uvicorn.run(self.app, host=host, port=port)
        except ImportError:
            raise ImportError("uvicorn no está instalado. Instala con: pip install uvicorn")


