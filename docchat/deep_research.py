"""Deep Research Mode - Enterprise Deep Research (EDR)-style multi-agent research.

Este modo NO modifica los otros modos existentes. Funciona como una
“capa de orquestación” encima del Research & Action Agent, inspirada
en Enterprise Deep Research (EDR):

- Master Research Agent (usamos ResearchActionAgent en modo deep_search)
- Todo/plan de investigación ligero
- Soporte opcional para subir archivos empresariales
- Reporte final en Markdown con secciones y citas
- Registro en AuditLogger para trazabilidad enterprise
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json
from datetime import datetime

from .data_ingestion_engine import DataIngestionEngine
from .audit import AuditLogger


@dataclass
class DeepResearchTask:
    """Representa un sub-task de investigación dentro de Deep Research."""

    task_id: str
    description: str
    priority: int = 5
    status: str = "pending"  # pending | in_progress | completed | cancelled
    source: str = "initial_query"  # initial_query | knowledge_gap | steering
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


@dataclass
class DeepResearchResult:
    """Resultado agregado del modo Deep Research."""

    success: bool
    query: str
    mode: str
    report_markdown: str
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    iterations: int = 1
    sources: List[Dict[str, Any]] = field(default_factory=list)
    steering_messages: List[str] = field(default_factory=list)
    error: Optional[str] = None
    raw_research_result: Optional[Dict[str, Any]] = None


class DeepResearch:
    """Modo Deep Research: orquestación tipo Enterprise Deep Research.

    Importante:
    - Usa únicamente ResearchActionAgent y componentes enterprise
      ya existentes (no toca otros modos).
    - Se centra en investigación profunda y generación de reportes
      estructurados en Markdown.
    """

    def __init__(
        self,
        config: Any,
        research_agent: Any,
        ingestion_engine: Optional[DataIngestionEngine] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        self.config = config
        self.research_agent = research_agent
        self.ingestion_engine = ingestion_engine
        self.audit_logger = audit_logger or AuditLogger()

    # ------------------------------------------------------------------
    # API pública principal
    # ------------------------------------------------------------------

    def run_research(
        self,
        query: str,
        files: Optional[List[Any]] = None,
        run_mode: str = "standard",  # quick | standard | deep
        steering_messages: Optional[List[str]] = None,
        tenant_id: str = "deep_research_ui",
    ) -> DeepResearchResult:
        """Ejecuta una investigación profunda tipo EDR.

        Args:
            query: Pregunta o tema de research.
            files: Archivos empresariales opcionales (PDF, DOCX, etc.).
            run_mode: quick / standard / deep (afecta la instrucción, no el resto del sistema).
            steering_messages: Mensajes de steering opcionales (human-in-the-loop).
            tenant_id: Identificador de tenant para logging.
        """
        steering_messages = steering_messages or []

        # 1) Ingesta opcional de archivos en el motor semántico enterprise
        ingested_doc_ids: List[str] = []
        if files and self.ingestion_engine is not None:
            try:
                ingested_doc_ids = self.ingestion_engine.ingest_files_from_gradio(files)
            except Exception as e:
                # No fallar todo el modo por error de ingesta: registrar y seguir
                print(f"⚠️ DeepResearch: error ingiriendo archivos: {e}")

        # 2) Construir plan de tareas (todo-like) para transparencia
        tasks: List[DeepResearchTask] = []
        base_task = DeepResearchTask(
            task_id="task-1",
            description=(
                "Realizar investigación profunda sobre el tema solicitado "
                "usando fuentes internas (documentos ingeridos) y externas (web, código, datos públicos)."
            ),
            priority=9,
            source="initial_query",
        )
        tasks.append(base_task)

        # Incorporar steering como tareas adicionales
        for idx, msg in enumerate(steering_messages):
            if not msg.strip():
                continue
            tasks.append(
                DeepResearchTask(
                    task_id=f"steering-{idx+1}",
                    description=f"Steering humano: {msg}",
                    priority=10,
                    source="steering",
                )
            )

        # 3) Configurar número de iteraciones según modo
        max_loops = {"quick": 2, "standard": 4, "deep": 6}.get(run_mode, 3)
        ra_mode = "deep_search"

        run_depth_text = {
            "quick": "Realiza un research rápido (high-level) con foco en las 3 ideas más importantes.",
            "standard": "Realiza un research profundo equilibrado: cobertura sólida y ejemplos clave.",
            "deep": "Realiza un research exhaustivo tipo analista senior: integra muchas fuentes y construye un informe largo y bien justificado.",
        }.get(run_mode, "Realiza un research profundo equilibrado.")

        # Estado acumulado de investigación
        running_summary = ""
        all_sources: List[Dict[str, Any]] = []
        iterations_used = 0

        # Bucle principal tipo EDR: planificación → búsqueda → síntesis → reflexión
        for loop_idx in range(max_loops):
            iterations_used += 1

            steering_block = ""
            if steering_messages:
                steering_block = "\n\nINSTRUCCIONES DE STEERING HUMANO:\n"
                for msg in steering_messages:
                    steering_block += f"- {msg}\n"

            internal_docs_block = ""
            if ingested_doc_ids:
                internal_docs_block = (
                    "\n\nContexto adicional: se han ingerido documentos internos en el motor semántico. "
                    "Antes de usar la web, intenta recuperar evidencia desde los documentos internos relevantes.\n"
                    "Trata documentos internos como fuentes de alta confianza y complementa con web/academic/GitHub/LinkedIn cuando sea necesario.\n"
                )

            todo_md = self._build_todo_markdown(tasks)

            deep_research_instruction = (
                "Eres el **Enterprise Deep Research Agent** de una gran empresa.\n"
                "Tu misión es realizar un **deep research multi-agente** al estilo Enterprise Deep Research (EDR):\n"
                "- Descomponer el problema en sub-tareas mentales y seleccionar inteligentemente herramientas de búsqueda.\n"
                "- Usar buscadores especializados: general_search, academic_search, github_search, linkedin_search, nl2sql y análisis de archivos cuando aporten valor.\n"
                "- Sintetizar hallazgos en un **reporte estructurado en Markdown** con secciones, bullets y citas.\n"
                "- Incluir referencias de fuentes (URLs, títulos de documentos, repositorios, papers, perfiles profesionales) cerca de las afirmaciones clave.\n"
                "- Mantener trazabilidad y explicar por qué cada hallazgo es relevante para la pregunta de negocio.\n\n"
                f"{run_depth_text}\n\n"
                f"{internal_docs_block}\n"
                "ESTADO ACTUAL DEL RESEARCH (resumen acumulado):\n"
                f"{running_summary or '(sin resumen acumulado aún)'}\n\n"
                "PLAN DE TAREAS (todo.md):\n"
                f"{todo_md}\n\n"
                f"{steering_block}\n"
                "PREGUNTA O TEMA DE INVESTIGACIÓN DEL USUARIO:\n"
                f"{query}\n"
                "\nIMPORTANTE:\n"
                "- Para esta iteración, enfócate en cubrir lagunas de conocimiento y profundizar donde aún falte detalle.\n"
                "- Usa herramientas especializadas según el tipo de subproblema (general, académico, código, perfiles profesionales, NL2SQL, análisis de archivos, visualización).\n"
                "- Devuelve un `summary` en texto plano largo que pueda ser usado como parte del reporte final.\n"
            )

            # Llamada al Research & Action Agent
            try:
                if not self.research_agent:
                    raise RuntimeError("ResearchActionAgent no está inicializado.")

                ra_result: Dict[str, Any] = self.research_agent.run_query(
                    query=deep_research_instruction,
                    mode=ra_mode,
                    stream=False,
                )
            except Exception as e:
                error_msg = f"Error ejecutando Deep Research (iteración {loop_idx + 1}): {e}"
                print(f"⚠️ {error_msg}")

                self.audit_logger.log(
                    event_type="deep_research",
                    action="run_research_error",
                    resource="deep_research_mode",
                    user_id=tenant_id,
                    metadata={
                        "query": query,
                        "run_mode": run_mode,
                        "error": str(e),
                        "doc_ids": ingested_doc_ids,
                        "iteration": loop_idx + 1,
                    },
                )

                return DeepResearchResult(
                    success=False,
                    query=query,
                    mode=run_mode,
                    report_markdown="❌ Error ejecutando Deep Research. Revisa los logs del servidor.",
                    tasks=[t.__dict__ for t in tasks],
                    iterations=iterations_used,
                    sources=all_sources,
                    steering_messages=steering_messages,
                    error=error_msg,
                    raw_research_result=None,
                )

            # Actualizar resumen acumulado
            iter_summary = ra_result.get("summary") or ra_result.get("answer") or ""
            if iter_summary:
                if running_summary:
                    running_summary += "\n\n---\n\n" + iter_summary
                else:
                    running_summary = iter_summary

            # Acumular fuentes
            iter_sources = ra_result.get("sources") or ra_result.get("documents") or []
            if isinstance(iter_sources, list):
                all_sources.extend(iter_sources)

            # Reflexión y actualización de tareas (tipo ResearchTodoManager)
            reflection_done, tasks = self._reflect_and_update_tasks(
                query=query,
                run_mode=run_mode,
                tasks=tasks,
                running_summary=running_summary,
                steering_messages=steering_messages,
            )

            if reflection_done:
                break

        # Construir reporte final
        report_md = running_summary
        if not report_md:
            report_md = (
                "⚠️ El Research & Action Agent no devolvió un resumen explícito en las iteraciones.\n"
                "A continuación se muestra una vista simplificada del estado final de investigación.\n\n"
                "```json\n"
                f"{json.dumps({'query': query, 'tasks': [t.__dict__ for t in tasks]}, ensure_ascii=False, indent=2)}\n"
                "```"
            )

        # Marcar tareas pendientes como completadas al final (si no fueron canceladas)
        now_iso = datetime.now().isoformat()
        for t in tasks:
            if t.status == "pending":
                t.status = "completed"
                t.completed_at = now_iso

        # Registrar en auditoría enterprise
        self.audit_logger.log(
            event_type="deep_research",
            action="run_research",
            resource="deep_research_mode",
            user_id=tenant_id,
            metadata={
                "query": query,
                "run_mode": run_mode,
                "iterations": iterations_used,
                "doc_ids": ingested_doc_ids,
                "steering_messages": steering_messages,
                "tasks": [t.__dict__ for t in tasks],
                "ra_mode": ra_mode,
            },
        )

        return DeepResearchResult(
            success=True,
            query=query,
            mode=run_mode,
            report_markdown=report_md,
            tasks=[t.__dict__ for t in tasks],
            iterations=iterations_used,
            sources=all_sources,
            steering_messages=steering_messages,
            error=None,
            raw_research_result=None,
        )

    # ------------------------------------------------------------------
    # Helpers (todo.md y reflexión tipo EDR)
    # ------------------------------------------------------------------

    def _build_todo_markdown(self, tasks: List[DeepResearchTask]) -> str:
        """Construye una vista tipo todo.md para el LLM y para auditoría."""
        lines: List[str] = []
        for t in tasks:
            checkbox = {
                "pending": "[ ]",
                "in_progress": "[-]",
                "completed": "[x]",
                "cancelled": "[!]",
            }.get(t.status, "[ ]")
            lines.append(f"{checkbox} ({t.task_id}) [p={t.priority}] [{t.source}] {t.description}")
        return "\n".join(lines) if lines else "(sin tareas)"

    def _reflect_and_update_tasks(
        self,
        query: str,
        run_mode: str,
        tasks: List[DeepResearchTask],
        running_summary: str,
        steering_messages: List[str],
    ) -> (bool, List[DeepResearchTask]):
        """Reflexión tipo EDR: decide si el research está completo y actualiza tareas."""
        # Si no tenemos acceso al LLM interno, no hacemos reflexión avanzada
        llm = getattr(self.research_agent, "llm", None)
        if llm is None:
            return False, tasks

        pending = [t for t in tasks if t.status == "pending"]
        completed = [t for t in tasks if t.status == "completed"]

        reflection_prompt = (
            "Eres un evaluador experto de investigaciones enterprise.\n"
            "Recibiste el siguiente resumen acumulado de investigación y un conjunto de tareas (todo.md).\n"
            "Debes decidir si la investigación es suficientemente completa y qué hacer con las tareas.\n\n"
            f"TEMA DE INVESTIGACIÓN: {query}\n"
            f"MODO: {run_mode}\n\n"
            "RESUMEN ACUMULADO:\n"
            f"{running_summary or '(vacío)'}\n\n"
            "TAREAS PENDIENTES:\n"
            f"{[t.__dict__ for t in pending]}\n\n"
            "TAREAS COMPLETADAS:\n"
            f"{[t.__dict__ for t in completed]}\n\n"
            "MENSAJES DE STEERING HUMANO:\n"
            f"{steering_messages}\n\n"
            "Devuelve un JSON con la siguiente estructura:\n"
            '{\n'
            '  "research_complete": true|false,\n'
            '  "todo_updates": {\n'
            '    "mark_completed": ["task-1", "..."],\n'
            '    "cancel_tasks": ["task-2", "..."],\n'
            '    "add_tasks": [\n'
            '      {"description": "Nueva tarea", "rationale": "Por qué hace falta"}\n'
            '    ]\n'
            '  }\n'
            '}\n\n'
            "Si el resumen ya cubre muy bien el tema principal y no hay gaps críticos, marca research_complete=true.\n"
            "Si no estás seguro, marca research_complete=false y crea nuevas tareas específicas solo para los gaps importantes.\n"
            "Responde SOLO con JSON válido."
        )

        try:
            response = llm.invoke(reflection_prompt)
            content = getattr(response, "content", "") if not isinstance(response, str) else response
            parsed = json.loads(content)
        except Exception as e:
            print(f"⚠️ DeepResearch reflexión fallida: {e}")
            return False, tasks

        research_complete = bool(parsed.get("research_complete", False))
        updates = parsed.get("todo_updates", {}) or {}

        # Actualizar tareas completadas
        to_complete = set(updates.get("mark_completed", []) or [])
        to_cancel = set(updates.get("cancel_tasks", []) or [])
        new_tasks = updates.get("add_tasks", []) or []

        for t in tasks:
            if t.task_id in to_complete and t.status == "pending":
                t.status = "completed"
                t.completed_at = datetime.now().isoformat()
            if t.task_id in to_cancel and t.status != "cancelled":
                t.status = "cancelled"

        # Agregar nuevas tareas
        next_idx = 1
        existing_ids = {t.task_id for t in tasks}
        while f"gap-{next_idx}" in existing_ids:
            next_idx += 1
        for nt in new_tasks:
            desc = nt.get("description")
            if not desc:
                continue
            tid = f"gap-{next_idx}"
            next_idx += 1
            tasks.append(
                DeepResearchTask(
                    task_id=tid,
                    description=desc,
                    priority=8,
                    source="knowledge_gap",
                )
            )

        return research_complete, tasks


__all__ = ["DeepResearch", "DeepResearchResult", "DeepResearchTask"]


