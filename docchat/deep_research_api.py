"""
API REST para el modo Deep Research de DocChat Enterprise.

Diseño inspirado explícitamente en la sección de *System Architecture* y
*Research Flow Mechanism* del paper de Enterprise Deep Research (EDR):

- Endpoint principal: POST /deep-research
  - Recibe: query de investigación, nivel de profundidad (quick/standard/deep),
    y opcionalmente mensajes de steering inicial.
  - Devuelve: informe final en Markdown + metadatos de la sesión.

- Endpoints de steering:
  - POST /steering/message         → añadir mensajes de steering durante la sesión.
  - GET  /steering/plan/{id}      → obtener vista actual de todo.md.
  - GET  /steering/status/{id}    → estado de la sesión (progreso básico).

NOTA: Esta versión es deliberadamente ligera:
- No usa SSE todavía (pero es compatible con streaming futuro).
- Mantiene las sesiones de investigación en memoria (dict) y carpeta en disco.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from .config import AppConfig
from .deep_research_mode import DeepResearchSession
from .observability.monitoring import MonitoringSystem


class DeepResearchRequest(BaseModel):
    query: str = Field(..., description="Consulta de investigación empresarial.")
    topic: Optional[str] = Field(
        None,
        description="Tema o título de alto nivel para el informe. Si se omite, se usa la propia query.",
    )
    mode: str = Field(
        "standard",
        description="Nivel de esfuerzo: quick (1-2 loops), standard (hasta 5), deep (hasta 8).",
    )
    steering_messages: Optional[List[str]] = Field(
        default=None,
        description="Mensajes de steering iniciales (prioridades, exclusiones, etc.).",
    )
    knowledge_paths: Optional[List[str]] = Field(
        default=None,
        description=(
            "Rutas locales opcionales a archivos (PDF, CSV, DOCX, etc.) que se usarán "
            "como conocimiento autoritativo en File Analysis dentro del flujo Deep Research."
        ),
    )


class DeepResearchResponse(BaseModel):
    session_id: str
    topic: str
    loops_run: int
    report_markdown: str
    created_at: float


class SteeringMessageRequest(BaseModel):
    session_id: str
    message: str


class SteeringStatusResponse(BaseModel):
    session_id: str
    topic: str
    version: int
    tasks: List[Dict[str, Any]]
    notes: List[str]


class SessionStatusResponse(BaseModel):
    session_id: str
    topic: str
    loops_run: int
    running_summary_chars: int
    created_at: float


class DeepResearchAPI:
    """
    Contenedor ligero para exponer DeepResearchSession vía FastAPI.
    Mantiene un registro en memoria de sesiones activas/finalizadas.
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.monitoring = MonitoringSystem(config)
        # Almacenamiento simple en memoria para ficheros y bases de datos (modo demo)
        self.files: Dict[str, Dict[str, Any]] = {}
        self.databases: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Gestión de sesiones
    # ------------------------------------------------------------------
    def _create_session(self, topic: str) -> DeepResearchSession:
        session = DeepResearchSession(
            self.config,
            topic=topic,
            monitoring=self.monitoring,
        )
        self.sessions[session.session_id] = {
            "session": session,
            "created_at": time.time(),
        }
        return session

    def _get_session(self, session_id: str) -> DeepResearchSession:
        data = self.sessions.get(session_id)
        if not data:
            raise KeyError(f"Sesión {session_id} no encontrada")
        return data["session"]


def create_deep_research_api(app: FastAPI, config: AppConfig) -> DeepResearchAPI:
    """
    Registra los endpoints de Deep Research sobre un `FastAPI` existente
    y devuelve el objeto `DeepResearchAPI` para usos avanzados.
    """
    api = DeepResearchAPI(config)

    @app.get("/research-status")
    async def research_status() -> Dict[str, Any]:
        """Endpoint ligero de estado del modo Deep Research."""
        return {"status": "ok", "active_sessions": len(api.sessions)}

    @app.post("/deep-research", response_model=DeepResearchResponse)
    async def deep_research(request: DeepResearchRequest):
        """Ejecuta una investigación profunda y devuelve un informe Markdown."""
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="La query no puede estar vacía.")

        topic = request.topic or request.query[:120]
        mode = request.mode.lower().strip()
        if mode not in {"quick", "standard", "deep"}:
            mode = "standard"

        max_loops = {"quick": 2, "standard": 5, "deep": 8}[mode]

        session = api._create_session(topic=topic)
        # Inyectar conocimiento de archivos si se proporcionan rutas
        if request.knowledge_paths:
            # Re-crear la sesión con knowledge_paths (manteniendo mismo session_id/directorio)
            session = DeepResearchSession(
                config,
                topic=topic,
                base_dir=session.base_dir,
                knowledge_paths=request.knowledge_paths,
            )
            api.sessions[session.session_id] = {
                "session": session,
                "created_at": time.time(),
            }
        session.run(
            user_query=request.query,
            max_loops=max_loops,
            steering_messages=request.steering_messages,
        )

        report = session.get_report_markdown(user_query=request.query)
        loops_run = len(session.iteration_results)
        created_at = api.sessions[session.session_id]["created_at"]

        return DeepResearchResponse(
            session_id=session.session_id,
            topic=topic,
            loops_run=loops_run,
            report_markdown=report,
            created_at=created_at,
        )

    @app.post("/steering/message")
    async def steering_message(req: SteeringMessageRequest):
        """
        Añade un mensaje de steering a una sesión de Deep Research.
        Se aplica en la siguiente iteración (en esta versión la sesión
        típica es sin streaming, por lo que este endpoint se usa sobre todo
        en versiones futuras con modo interactivo).
        """
        try:
            session = api._get_session(req.session_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")

        # En esta versión, el mensaje se traduce a tareas de máxima prioridad.
        session.todo_manager.apply_steering_message(req.message)
        return {"status": "ok", "message": "Steering aplicado a todo.md"}

    @app.get("/steering/plan/{session_id}", response_model=SteeringStatusResponse)
    async def steering_plan(session_id: str):
        """Devuelve el estado actual del plan (equivalente lógico a `todo.md`)."""
        try:
            session = api._get_session(session_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")

        state = session.todo_manager.list_tasks()
        return SteeringStatusResponse(
            session_id=session_id,
            topic=state.topic,
            version=state.version,
            tasks=[t.to_dict() for t in state.tasks],
            notes=state.notes,
        )

    @app.get("/steering/status/{session_id}", response_model=SessionStatusResponse)
    async def steering_status(session_id: str):
        """Devuelve un resumen ligero del estado de la sesión de investigación."""
        try:
            session = api._get_session(session_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")

        created_at = api.sessions[session_id]["created_at"]
        loops_run = len(session.iteration_results)
        summary_len = len(session.master_agent.running_summary or "")

        return SessionStatusResponse(
            session_id=session_id,
            topic=session.topic,
            loops_run=loops_run,
            running_summary_chars=summary_len,
            created_at=created_at,
        )

    @app.get("/stream/{session_id}")
    async def stream_session(session_id: str):
        """
        Streaming tipo SSE (simplificado) de los resultados de una sesión.
        Envía cada iteración como un evento `data: ...` en formato JSON.
        """
        import json as _json
        from fastapi.responses import StreamingResponse

        try:
            session = api._get_session(session_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")

        async def event_generator():
            for it in session.iteration_results:
                payload = {
                    "iteration": it.iteration,
                    "coverage": getattr(it, "coverage", 0),
                    "knowledge_gap": it.knowledge_gap,
                    "research_complete": it.research_complete,
                }
                yield f"data: {_json.dumps(payload, ensure_ascii=False)}\n\n"
            yield "event: end\ndata: {}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # ------------------------------------------------------------------
    # Endpoints extra: File Analysis y Database (modo simplificado)
    # ------------------------------------------------------------------

    files_base_dir = Path(config.memory_dir) / "deep_research_files"
    files_base_dir.mkdir(parents=True, exist_ok=True)

    @app.post("/api/files/upload")
    async def upload_file(file: UploadFile = File(...)) -> Dict[str, Any]:
        """Sube un fichero y lo registra para posibles análisis posteriores."""
        import uuid

        file_id = str(uuid.uuid4())
        dest = files_base_dir / f"{file_id}_{file.filename}"
        content = await file.read()
        dest.write_bytes(content)
        api.files[file_id] = {
            "file_id": file_id,
            "path": str(dest),
            "filename": file.filename,
            "size": len(content),
        }
        return api.files[file_id]

    @app.get("/api/files/{file_id}/status")
    async def file_status(file_id: str) -> Dict[str, Any]:
        """Devuelve metadatos básicos del fichero subido."""
        data = api.files.get(file_id)
        if not data:
            raise HTTPException(status_code=404, detail="Fichero no encontrado")
        return data

    @app.get("/api/files")
    async def list_files() -> List[Dict[str, Any]]:
        """Lista todos los ficheros conocidos (en memoria)."""
        return list(api.files.values())

    return api



