"""
Deep Research Mode para DocChat Enterprise.

Este módulo implementa un modo de investigación profunda multi‑agente
inspirado en **Enterprise Deep Research (EDR)** descrito en el paper:

    Enterprise Deep Research: Steerable MultiAgent Deep Research for Enterprise Analytics
    (Akshara Prabhakar et al., Salesforce AI Research, 2025)

Objetivo principal:
- Tomar un *prompt* de investigación empresarial.
- Ejecutar múltiples iteraciones de búsqueda y síntesis.
- Gestionar un plan de tareas (`todo.md`) transparente y editable.
- Producir un informe estructurado en Markdown con citas y trazabilidad.

Componentes implementados (versión inicial, simplificada pero fiel al diseño):
- MasterResearchAgent: orquesta el flujo de investigación y la descomposición adaptativa.
- ResearchTodoManager: gestiona el plan de tareas (todo.md) con prioridades, estados y provenance.
- SearchAgents: envoltorios de búsqueda (general, académica, GitHub, LinkedIn) usando las
  herramientas ya disponibles (por ahora, web search estándar + extensible).
- ReflectionEngine: detecta *knowledge gaps*, actualiza el plan y decide si continuar o terminar.

Limitaciones de esta primera versión:
- No integra todavía LangGraph para la orquestación de grafos; el bucle es secuencial en Python.
- Los agentes de búsqueda especializados reutilizan el `search_web` actual como backend,
  con filtros simples por dominio en lugar de APIs dedicadas (arXiv, GitHub, LinkedIn).
- La visualización y NL2SQL se exponen como “ganchos” (hooks) para integración futura
  con `enterprise_data_intelligence`, `sql_generation` o MCP tools.

La API REST que usa este modo se define en `deep_research_api.py`.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal, Tuple, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from .config import AppConfig
from .research_action_agent.tools.web_search import search_web
from .multi_format_processor import MultiFormatProcessor
from .data_registry import DataRegistry
from .sql_generation import SQLGenerator
from .mcp_manager import MCPManager
from .observability.monitoring import MonitoringSystem
from .deep_research_visualization import VisualizationAgent


TaskStatus = Literal["pending", "in_progress", "completed", "cancelled"]
TaskProvenance = Literal["initial_query", "knowledge_gap", "steering_message"]


@dataclass
class ResearchTask:
    """Tarea de investigación granular gestionada en todo.md."""

    id: str
    description: str
    priority: int  # 5–10 como en el paper
    status: TaskStatus = "pending"
    provenance: TaskProvenance = "initial_query"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TodoState:
    """Estado completo del plan de investigación (todo.md lógico)."""

    version: int = 0
    topic: str = ""
    tasks: List[ResearchTask] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "topic": self.topic,
            "tasks": [t.to_dict() for t in self.tasks],
            "notes": self.notes,
        }


class ResearchTodoManager:
    """
    Gestor de tareas de investigación alineado con EDR.

    - Mantiene un estado `TodoState` en memoria.
    - Persiste la representación en disco como `todo.md` para trazabilidad humana.
    - Expone métodos para inicializar el plan, actualizar estados y aplicar steering.
    """

    def __init__(self, workspace_dir: Path, topic: str):
        self.workspace_dir = workspace_dir
        self.todo_path = workspace_dir / "todo.md"
        self.state = TodoState(topic=topic)
        self._ensure_workspace()

    # ------------------------------------------------------------------
    # Inicialización y persistencia
    # ------------------------------------------------------------------
    def _ensure_workspace(self) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def _bump_version(self) -> None:
        self.state.version += 1

    def _write_md(self) -> None:
        """Escribe una representación legible del plan en `todo.md`."""
        lines: List[str] = []
        lines.append(f"# Deep Research Plan: {self.state.topic}")
        lines.append(f"Version: {self.state.version}")
        lines.append("")
        lines.append("## Tasks")
        for t in sorted(self.state.tasks, key=lambda x: (-x.priority, x.created_at)):
            lines.append(
                f"- [{self._status_to_checkbox(t.status)}] "
                f"({t.priority}) {t.description} "
                f"(id={t.id}, provenance={t.provenance})"
            )
        if self.state.notes:
            lines.append("")
            lines.append("## Notes")
            for n in self.state.notes:
                lines.append(f"- {n}")
        self.todo_path.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _status_to_checkbox(status: TaskStatus) -> str:
        return {
            "pending": " ",
            "in_progress": "-",
            "completed": "x",
            "cancelled": "!",
        }.get(status, " ")

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def init_initial_plan(self, query: str) -> None:
        """
        Genera un plan inicial ligero (3–5 tareas) para la consulta del usuario.
        Implementación simplificada basada en heurística + LLM.
        """
        if self.state.tasks:
            return  # ya inicializado

        base_tasks: List[str] = [
            "Entender el contexto general del tema y su relevancia empresarial.",
            "Identificar fuentes clave y trabajos de referencia recientes.",
            "Mapear impactos, riesgos y oportunidades principales.",
            "Detectar métricas y KPIs relevantes asociados al tema.",
        ]

        # Limitar a 3–5 tareas
        selected = base_tasks[:4]

        tasks: List[ResearchTask] = []
        n = len(selected)
        for i, desc in enumerate(selected):
            priority = 5 + (n - i)  # 5 + (N − i) como en el paper
            tasks.append(
                ResearchTask(
                    id=str(uuid.uuid4()),
                    description=desc,
                    priority=priority,
                    provenance="initial_query",
                )
            )

        self.state.tasks = tasks
        self._bump_version()
        self._write_md()

    def list_tasks(self) -> TodoState:
        return self.state

    def update_task_status(self, task_ids: List[str], status: TaskStatus) -> None:
        updated = False
        now = time.time()
        id_set = set(task_ids)
        for t in self.state.tasks:
            if t.id in id_set and t.status != status:
                t.status = status
                t.updated_at = now
                updated = True
        if updated:
            self._bump_version()
            self._write_md()

    def add_tasks(
        self, descriptions: List[str], provenance: TaskProvenance, base_priority: int
    ) -> List[ResearchTask]:
        new_tasks: List[ResearchTask] = []
        now = time.time()
        for i, desc in enumerate(descriptions):
            task = ResearchTask(
                id=str(uuid.uuid4()),
                description=desc,
                priority=max(5, min(10, base_priority - i)),
                provenance=provenance,
                created_at=now,
                updated_at=now,
            )
            self.state.tasks.append(task)
            new_tasks.append(task)
        if new_tasks:
            self._bump_version()
            self._write_md()
        return new_tasks

    def apply_steering_message(self, message: str) -> List[ResearchTask]:
        """
        Integra un mensaje de steering como nuevas tareas de máxima prioridad.
        Ejemplos:
        - "Enfócate en papers peer‑reviewed recientes"
        - "Añade una sección sobre impacto en Latinoamérica"
        """
        steering_task_desc = f"[STEERING] {message.strip()}"
        return self.add_tasks(
            descriptions=[steering_task_desc],
            provenance="steering_message",
            base_priority=10,
        )


@dataclass
class ResearchIterationResult:
    """Resultado de una iteración del bucle de investigación."""

    iteration: int
    used_tasks: List[str]
    summary_delta: str
    sources: List[Dict[str, Any]]
    knowledge_gap: Optional[str]
    research_complete: bool
    coverage: int = 0


class DeepResearchGraphState(TypedDict, total=False):
    """
    Estado para el grafo de LangGraph del modo Deep Research.

    Este estado es intencionalmente compacto: el grafo orquesta una
    sola iteración (plan → búsqueda+síntesis → reflexión) y el bucle
    externo controla cuántas iteraciones ejecutar.
    """

    user_query: str
    running_summary: str
    selected_task_ids: List[str]
    search_plan: Dict[str, Any]
    search_results: List[Dict[str, Any]]
    summary_delta: str
    reflection: Dict[str, Any]
    should_continue: Literal["continue", "end"]


class MasterResearchAgent:
    """
    Agente maestro responsable de:
    - Leer el plan de tareas de `ResearchTodoManager`.
    - Seleccionar tareas pendientes de mayor prioridad.
    - Generar consultas de búsqueda y ejecutar agentes de búsqueda.
    - Fusionar resultados en un *running summary* con citas.
    - Invocar el mecanismo de reflexión para detectar *knowledge gaps*.
    """

    def __init__(
        self,
        config: AppConfig,
        topic: str,
        todo_manager: ResearchTodoManager,
        knowledge_paths: Optional[List[str]] = None,
        monitoring: Optional[MonitoringSystem] = None,
    ):
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY requerida para Deep Research Mode")

        self.config = config
        self.topic = topic
        self.todo_manager = todo_manager
        self.monitoring = monitoring

        # LLM principal para planificación y síntesis
        self.llm = ChatOpenAI(
            model=config.research_model or "gpt-4o",
            temperature=0.2,
            api_key=config.openai_api_key,
            max_tokens=4000,
        )

        # Estado de investigación
        self.running_summary: str = ""
        self.collected_sources: Dict[str, Dict[str, Any]] = {}
        self.iteration: int = 0

        # ===== Herramientas de dominio (NL2SQL, File Analysis, MCP) =====
        # Conocimiento subido por el usuario (paths locales opcionales)
        self.knowledge_paths = [p for p in (knowledge_paths or []) if p]
        self._knowledge_docs: Optional[List[Any]] = None

        # Procesador multi‑formato para File Analysis
        self.file_processor: Optional[MultiFormatProcessor] = None
        try:
            self.file_processor = MultiFormatProcessor(config)
        except Exception as e:  # pragma: no cover - dependencias opcionales
            print(f"⚠️ DeepResearch: MultiFormatProcessor no disponible: {e}")

        # DataRegistry + SQLGenerator para NL2SQL
        self.data_registry: Optional[DataRegistry] = None
        self.sql_generator: Optional[SQLGenerator] = None
        try:
            self.data_registry = DataRegistry(config)
            if self.data_registry.table_index:
                self.sql_generator = SQLGenerator(config, self.data_registry)
        except Exception as e:  # pragma: no cover
            print(f"⚠️ DeepResearch: SQLGenerator/DataRegistry no disponible: {e}")

        # MCP Manager para conectores enterprise
        self.mcp_manager: Optional[MCPManager] = None
        try:
            self.mcp_manager = MCPManager(config, llm=self.llm)
        except Exception as e:  # pragma: no cover
            print(f"⚠️ DeepResearch: MCPManager no disponible: {e}")

        # Agente de visualización para gráficos básicos
        try:
            self.visualization_agent = VisualizationAgent(
                base_dir=Path(config.memory_dir) / "deep_research_viz"
            )
        except Exception:
            self.visualization_agent = None  # pragma: no cover

        # Grafo de orquestación explícita (LangGraph) para una iteración
        self.graph = self._build_graph()

    # ------------------------------------------------------------------
    # Construcción del grafo multi‑agente (LangGraph)
    # ------------------------------------------------------------------
    def _build_graph(self):
        """
        Construye un grafo explícito tipo LangGraph con nodos:
        - plan          → selecciona tareas y genera plan de búsqueda.
        - search_synth  → ejecuta agentes de búsqueda especializados y síntesis.
        - reflect       → aplica reflexión, actualiza todo.md y decide continuación.

        Cada invocación del grafo corresponde a **una iteración** del
        ciclo de investigación. El bucle externo controla `max_loops`.
        """
        graph = StateGraph(DeepResearchGraphState)

        graph.add_node("plan", self._graph_plan_step)
        graph.add_node("search_synth", self._graph_search_and_summarize_step)
        graph.add_node("reflect", self._graph_reflect_step)

        graph.set_entry_point("plan")
        graph.add_edge("plan", "search_synth")
        graph.add_edge("search_synth", "reflect")

        # El grafo siempre termina después de reflexión; el campo
        # `should_continue` nos dice si seguir iterando o no.
        graph.add_conditional_edges(
            "reflect",
            self._graph_decide_after_reflect,
            {
                "continue": END,
                "end": END,
            },
        )

        return graph.compile()

    # ------------------------------------------------------------------
    # Búsqueda (agentes especializados)
    # ------------------------------------------------------------------
    def _run_general_search(self, query: str, top_k: int = 6) -> List[Dict[str, Any]]:
        """Usa `search_web` como agente de búsqueda general."""
        raw = search_web.invoke({"query": query, "top_k": top_k})
        try:
            data = json.loads(raw)
        except Exception:
            return []
        results = data.get("data", {}).get("results", [])
        return results or []

    def _run_academic_search(self, query: str, top_k: int = 6) -> List[Dict[str, Any]]:
        """
        Agente de búsqueda académica.

        Implementación actual:
        - Prioriza papers y contenido académico usando filtros en la query
          (arxiv.org, menciones a "peer reviewed").
        - Se apoya en `search_web` (Tavily/Bing) para la búsqueda subyacente.

        NOTA: Es fácilmente extensible a APIs específicas (arXiv, Semantic Scholar).
        """
        return self._run_general_search(
            f"{query} site:arxiv.org OR \"peer reviewed\"", top_k
        )

    def _run_github_search(self, query: str, top_k: int = 6) -> List[Dict[str, Any]]:
        """
        Agente de búsqueda GitHub (repositorios y código).

        Actualmente restringe la búsqueda a `site:github.com` sobre el
        backend web; si en el futuro se configura un token de GitHub,
        se puede evolucionar a llamadas directas a la API REST.
        """
        return self._run_general_search(f"{query} site:github.com", top_k)

    def _run_linkedin_search(self, query: str, top_k: int = 6) -> List[Dict[str, Any]]:
        """
        Agente de búsqueda LinkedIn (perfiles/empresas).

        Por respeto a los términos de servicio, este agente:
        - Utiliza únicamente resultados devueltos por el proveedor de búsqueda
          configurado (`search_web`) restringiendo a `site:linkedin.com`.
        - No implementa scraping directo de LinkedIn.
        """
        return self._run_general_search(f"{query} site:linkedin.com", top_k)

    def _ensure_knowledge_docs_loaded(self) -> None:
        """Carga y cachea documentos de conocimiento subido (File Analysis)."""
        if self._knowledge_docs is not None or not self.knowledge_paths or not self.file_processor:
            return

        from io import BytesIO

        file_objs: List[Any] = []
        for p in self.knowledge_paths:
            path = Path(p)
            if not path.exists():
                continue
            try:
                data = path.read_bytes()
                bio = BytesIO(data)
                bio.name = path.name
                # compat opcional con original_name usado en otros módulos
                setattr(bio, "original_name", path.name)
                file_objs.append(bio)
            except Exception as e:
                print(f"⚠️ DeepResearch: no se pudo leer {p}: {e}")

        if not file_objs:
            self._knowledge_docs = []
            return

        try:
            self._knowledge_docs = self.file_processor.process(file_objs)
        except Exception as e:
            print(f"⚠️ DeepResearch: error procesando knowledge_paths: {e}")
            self._knowledge_docs = []

    def _run_file_analysis(self, query: str, top_k: int = 8) -> List[Dict[str, Any]]:
        """
        File Analysis Tool.

        Usa MultiFormatProcessor sobre `knowledge_paths` para integrar conocimiento
        subido por el usuario en el contexto de investigación.
        """
        self._ensure_knowledge_docs_loaded()
        if not self._knowledge_docs:
            return []

        q = query.lower()
        scored: List[Tuple[float, Any]] = []
        for doc in self._knowledge_docs:
            text = doc.page_content or ""
            if not text:
                continue
            score = 0.0
            for token in q.split():
                if token and token in text.lower():
                    score += 1.0
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_docs = [d for _, d in scored[:top_k]]

        results: List[Dict[str, Any]] = []
        for d in top_docs:
            src = d.metadata.get("source", "knowledge_file")
            snippet = d.page_content[:600]
            results.append(
                {
                    "title": f"File: {src}",
                    "url": f"file://{src}",
                    "snippet": snippet,
                    "content": d.page_content,
                    "source_type": "file_analysis",
                }
            )
        return results

    def _run_nl2sql(self, query: str) -> List[Dict[str, Any]]:
        """
        NL2SQL Agent.

        Convierte lenguaje natural a SQL usando `SQLGenerator` + `DataRegistry`.
        No ejecuta la query; devuelve SQL + explicación como evidencia.
        """
        if not self.sql_generator or not self.data_registry:
            return []
        try:
            result = self.sql_generator.generate_sql(query)
        except Exception as e:  # pragma: no cover
            print(f"⚠️ DeepResearch: error en NL2SQL: {e}")
            return []

        title = "Consulta NL2SQL generada"
        explanation = result.explanation or "SQL generado a partir de lenguaje natural."
        snippet = f"{explanation}\n\nSQL:\n{result.sql}"
        return [
            {
                "title": title,
                "url": "nl2sql://local",
                "snippet": snippet[:800],
                "content": result.sql,
                "tables_used": result.tables_used,
                "source_type": "nl2sql",
            }
        ]

    def _run_mcp_overview(self) -> List[Dict[str, Any]]:
        """
        MCP-based Enterprise Tools overview.

        Usa MCPManager para exponer qué conectores y herramientas enterprise
        están disponibles en la instalación actual (Salesforce, Slack, DB, APIs...).
        """
        if not self.mcp_manager:
            return []
        try:
            stats = self.mcp_manager.get_statistics()
            tools = self.mcp_manager.list_available_tools()
        except Exception as e:  # pragma: no cover
            print(f"⚠️ DeepResearch: error consultando MCPManager: {e}")
            return []

        snippet = (
            "Conectores MCP disponibles en esta instancia:\n"
            f"- Conexiones totales: {stats.get('total_connections', 0)}\n"
            f"- Herramientas MCP: {stats.get('total_tools', 0)}\n"
        )
        tool_names = ", ".join(t["name"] for t in tools[:15])
        if tool_names:
            snippet += f"- Herramientas: {tool_names}"

        return [
            {
                "title": "Panorama de herramientas MCP Enterprise",
                "url": "mcp://local",
                "snippet": snippet,
                "content": snippet,
                "source_type": "mcp_tools",
            }
        ]

    # ------------------------------------------------------------------
    # Bucle principal de investigación
    # ------------------------------------------------------------------
    def run_research_loop(
        self,
        user_query: str,
        max_loops: int = 5,
        steering_messages: Optional[List[str]] = None,
    ) -> List[ResearchIterationResult]:
        """
        Ejecuta el bucle completo de investigación profunda.

        Internamente utiliza un **grafo LangGraph** por iteración
        (plan → búsqueda/síntesis → reflexión) para hacer visible y
        trazable la trayectoria del agente, tal como propone el paper
        de Enterprise Deep Research.
        """
        results: List[ResearchIterationResult] = []
        steering_queue = list(steering_messages or [])

        for _ in range(max_loops):
            self.iteration += 1
            loop_start = time.time()

            # 1) Aplicar steering pendiente (entre iteraciones)
            if steering_queue:
                for msg in steering_queue:
                    self.todo_manager.apply_steering_message(msg)
                steering_queue = []

            # 2) Ejecutar UNA iteración del grafo LangGraph
            initial_state: DeepResearchGraphState = {
                "user_query": user_query,
                "running_summary": self.running_summary,
            }

            state = self.graph.invoke(initial_state, config={"recursion_limit": 5})

            # 3) Actualizar resumen acumulado y resultados de iteración
            self.running_summary = state.get("running_summary", self.running_summary)
            should_continue = state.get("should_continue", "end")

            if self.iteration_results:
                # Añadir la última iteración generada dentro de los nodos
                last_iter = self.iteration_results[-1]
                results.append(last_iter)

                # Métricas de observabilidad por iteración
                if self.monitoring:
                    duration_ms = (time.time() - loop_start) * 1000.0
                    self.monitoring.record_metric(
                        "deep_research.loop_duration_ms",
                        float(duration_ms),
                        tags={
                            "iteration": str(last_iter.iteration),
                            "topic": self.topic[:64],
                        },
                    )
                    self.monitoring.record_metric(
                        "deep_research.coverage",
                        float(last_iter.coverage),
                        tags={"iteration": str(last_iter.iteration)},
                    )
                    self.monitoring.record_metric(
                        "deep_research.sources_used",
                        float(len(last_iter.sources)),
                        tags={"iteration": str(last_iter.iteration)},
                    )

                if last_iter.research_complete:
                    break

            if should_continue == "end":
                break

        return results

    # ------------------------------------------------------------------
    # Planificación, síntesis y reflexión (LLM‑driven)
    # ------------------------------------------------------------------
    def _plan_search_queries(
        self,
        user_query: str,
        selected_tasks: List[ResearchTask],
        running_summary: str,
    ) -> Dict[str, Any]:
        """
        Genera un pequeño plan de consultas de búsqueda para esta iteración.
        Devuelve un diccionario con:
        - query_complexity
        - main_query
        - tasks: lista de {name, query, aspect, domain}

        Dominios soportados:
        - general       → web search genérico
        - academic      → papers y contenido académico
        - github        → código y repos técnicos
        - linkedin      → perfiles profesionales / empresas
        - file_analysis → análisis de archivos subidos (knowledge_paths)
        - nl2sql        → consultas sobre datos estructurados vía SQL generation
        - mcp           → conectores enterprise vía MCP (Salesforce, Slack, DB, APIs)
        """
        task_descriptions = "\n".join(
            f"- {t.description} (priority={t.priority})" for t in selected_tasks
        )
        prompt = f"""
Eres el Master Research Agent de un sistema de Deep Research empresarial.

Tema global: {self.topic}
Consulta del usuario: {user_query}

Tareas seleccionadas para esta iteración:
{task_descriptions}

Resumen acumulado hasta ahora (puede estar vacío):
\"\"\"{running_summary[:6000]}\"\"\"

Debes generar un pequeño plan de búsqueda web / uso de herramientas para avanzar estas tareas.

Instrucciones:
- Clasifica la consulta como "simple" o "complex" en "query_complexity".
- Define una "main_query" que capture el objetivo principal.
- Crea de 3 a 7 sub‑tareas de búsqueda en el campo "tasks".
- Cada entrada en "tasks" debe incluir:
  - "name": nombre corto del aspecto a investigar.
  - "query": texto de búsqueda concreto (máx 300 caracteres).
  - "aspect": descripción breve de qué cubre.
  - "domain": uno de ["general", "academic", "github", "linkedin", "file_analysis", "nl2sql", "mcp"].

Responde SOLO con JSON válido.
Ejemplo:
{{
  "query_complexity": "complex",
  "main_query": "impacto de la IA generativa en productividad B2B",
  "tasks": [
    {{"name": "Panorama general", "query": "...", "aspect": "...", "domain": "general"}},
    {{"name": "Papers recientes", "query": "...", "aspect": "...", "domain": "academic"}},
    {{"name": "KPIs internos", "query": "tasa de conversión por segmento", "aspect": "consultar warehouse interno", "domain": "nl2sql"}}
  ]
}}
"""
        try:
            resp = self.llm.invoke(prompt).content.strip()
            if resp.startswith("```"):
                resp = resp.split("```", 2)[-1].strip()
            data = json.loads(resp)
        except Exception:
            # Fallback simple si algo falla
            data = {
                "query_complexity": "complex",
                "main_query": user_query,
                "tasks": [
                    {
                        "name": "Panorama general",
                        "query": f"{user_query} impacto, riesgos, oportunidades",
                        "aspect": "Visión general del tema en contexto empresarial",
                        "domain": "general",
                    }
                ],
            }
        return data

    def _synthesize_incremental(
        self,
        user_query: str,
        tasks: List[ResearchTask],
        search_results: List[Dict[str, Any]],
        previous_summary: str,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Fusiona los nuevos resultados de búsqueda con el resumen previo.
        Devuelve:
        - summary_delta: texto Markdown que describe lo aprendido en esta iteración.
        - used_sources: subconjunto de resultados con los que se apoyó la síntesis.
        """
        # Seleccionar hasta 15 resultados para síntesis
        top_results = search_results[:15]
        snippets = []
        for r in top_results:
            title = r.get("title") or "Untitled"
            url = r.get("url") or ""
            snippet = r.get("snippet") or r.get("content") or ""
            snippets.append(f"- {title} ({url}): {snippet[:400]}")

        tasks_text = "\n".join(f"- {t.description}" for t in tasks)
        sources_text = "\n".join(snippets)

        prompt = f"""
Eres el agente de síntesis de un sistema de Deep Research empresarial.
Debes integrar nueva evidencia con el resumen acumulado.

Tema: {self.topic}
Consulta del usuario: {user_query}

Tareas objetivo de esta iteración:
{tasks_text}

Resumen acumulado hasta ahora:
\"\"\"{previous_summary[:8000]}\"\"\"

Nuevas fuentes recopiladas (títulos, URLs y fragmentos):
{sources_text}

Instrucciones:
- Escribe SOLO el *delta* de conocimiento de esta iteración:
  - Nuevos hallazgos.
  - Matices o correcciones a lo anterior.
  - Sin repetir textualmente párrafos ya cubiertos.
- Usa formato Markdown estructurado:
  - Encabezado breve para la iteración.
  - Bullets y secciones por sub‑tema si es útil.
- Incluye referencias en línea tipo [Fuente 1], [Fuente 2], etc., pero NO necesitas listar la bibliografía completa aquí.
"""
        try:
            summary_delta = self.llm.invoke(prompt).content.strip()
        except Exception as e:
            summary_delta = f"Error durante síntesis: {e}"

        return summary_delta, top_results

    def _reflect_and_update_todos(
        self,
        user_query: str,
        tasks: List[ResearchTask],
        summary: str,
        search_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Implementa el mecanismo de reflexión:
        - Evalúa cobertura.
        - Decide qué tareas se consideran completadas.
        - Sugiere nuevas tareas derivadas de *knowledge gaps*.
        """
        tasks_text = "\n".join(f"- {t.description}" for t in tasks)
        prompt = f"""
Eres el componente de reflexión de un sistema de Deep Research empresarial.

Tema: {self.topic}
Consulta del usuario: {user_query}

Tareas cubiertas en esta iteración:
{tasks_text}

Resumen completo actual:
\"\"\"{summary[:10000]}\"\"\"

Necesitas:
1. Evaluar qué tan completo es el análisis actual (0–100%).
2. Identificar *knowledge gaps* críticos (si los hay).
3. Decidir si las tareas de esta iteración se pueden marcar como completadas.
4. Proponer nuevas tareas SOLO si son necesarias para cerrar gaps importantes.

Responde en JSON con esta estructura:
{{
  "coverage": 0-100,
  "research_complete": true/false,
  "mark_completed": ["task_id_1", ...],
  "cancel_tasks": ["task_id_2", ...],
  "knowledge_gap": "descripción breve o null",
  "new_tasks": ["descripcion tarea 1", "descripcion tarea 2"]
}}
"""
        # Mapear ids para el prompt (el LLM no necesita verlos, pero sí el código)
        id_map = {t.description: t.id for t in tasks}

        try:
            resp = self.llm.invoke(prompt).content.strip()
            if resp.startswith("```"):
                resp = resp.split("```", 2)[-1].strip()
            data = json.loads(resp)
        except Exception:
            # Fallback conservador
            data = {
                "coverage": 60,
                "research_complete": False,
                "mark_completed": [t.id for t in tasks],
                "cancel_tasks": [],
                "knowledge_gap": "Refinar detalles y buscar evidencias cuantitativas adicionales.",
                "new_tasks": [],
            }

        mark_completed = data.get("mark_completed") or [t.id for t in tasks]
        cancel_tasks = data.get("cancel_tasks") or []
        new_tasks = data.get("new_tasks") or []

        return {
            "coverage": data.get("coverage", 0),
            "research_complete": bool(data.get("research_complete", False)),
            "mark_completed": mark_completed,
            "cancel_tasks": cancel_tasks,
            "knowledge_gap": data.get("knowledge_gap"),
            "new_tasks": new_tasks,
        }

    # ------------------------------------------------------------------
    # Nodos del grafo LangGraph
    # ------------------------------------------------------------------
    def _graph_plan_step(self, state: DeepResearchGraphState) -> DeepResearchGraphState:
        """Nodo PLAN: selecciona tareas pendientes y genera el plan de búsqueda."""
        trace = self.monitoring.start_trace(
            "deep_research.plan",
            metadata={"iteration": self.iteration, "topic": self.topic[:64]},
        ) if self.monitoring else None

        try:
            todo_state = self.todo_manager.list_tasks()
            pending = [t for t in todo_state.tasks if t.status == "pending"]

            if not pending:
                # No hay más tareas → marcar como completo
                return {
                    **state,
                    "selected_task_ids": [],
                    "search_plan": {"tasks": []},
                    "search_results": [],
                    "summary_delta": "",
                    "reflection": {
                        "coverage": 100,
                        "research_complete": True,
                        "mark_completed": [],
                        "cancel_tasks": [],
                        "knowledge_gap": None,
                        "new_tasks": [],
                    },
                    "should_continue": "end",
                }

            pending_sorted = sorted(
                pending, key=lambda t: (-t.priority, t.created_at)
            )
            selected_tasks = pending_sorted[:3]
            selected_ids = [t.id for t in selected_tasks]

            # Marcar como in_progress
            self.todo_manager.update_task_status(selected_ids, "in_progress")

            search_plan = self._plan_search_queries(
                user_query=state["user_query"],
                selected_tasks=selected_tasks,
                running_summary=state.get("running_summary", ""),
            )

            if self.monitoring:
                self.monitoring.record_metric(
                    "deep_research.tool_calls_planned",
                    float(len(search_plan.get("tasks", []) or [])),
                    tags={
                        "iteration": str(self.iteration),
                        "topic": self.topic[:64],
                    },
                )

            return {
                **state,
                "selected_task_ids": selected_ids,
                "search_plan": search_plan,
            }
        finally:
            if trace:
                self.monitoring.end_trace(trace)

    def _graph_search_and_summarize_step(
        self, state: DeepResearchGraphState
    ) -> DeepResearchGraphState:
        """Nodo SEARCH_SYNTH: ejecuta agentes de búsqueda y síntesis incremental."""
        trace = self.monitoring.start_trace(
            "deep_research.search_synth",
            metadata={"iteration": self.iteration, "topic": self.topic[:64]},
        ) if self.monitoring else None

        try:
            selected_ids = state.get("selected_task_ids", [])
            if not selected_ids:
                return {**state, "search_results": [], "summary_delta": ""}

            # Recuperar objetos de tarea a partir de los ids
            todo_state = self.todo_manager.list_tasks()
            task_by_id = {t.id: t for t in todo_state.tasks}
            selected_tasks = [task_by_id[tid] for tid in selected_ids if tid in task_by_id]

            search_plan = state.get("search_plan", {}) or {}
            all_results: List[Dict[str, Any]] = []

            for item in search_plan.get("tasks", []):
                domain = item.get("domain", "general")
                q = item.get("query", "")
                if not q:
                    continue
                if domain == "academic":
                    hits = self._run_academic_search(q)
                elif domain == "github":
                    hits = self._run_github_search(q)
                elif domain == "linkedin":
                    hits = self._run_linkedin_search(q)
                elif domain == "file_analysis":
                    hits = self._run_file_analysis(q)
                elif domain == "nl2sql":
                    hits = self._run_nl2sql(q)
                elif domain == "mcp":
                    hits = self._run_mcp_overview()
                else:
                    hits = self._run_general_search(q)
                all_results.extend(hits)

            summary_delta, used_sources = self._synthesize_incremental(
                user_query=state["user_query"],
                tasks=selected_tasks,
                search_results=all_results,
                previous_summary=state.get("running_summary", ""),
            )

            new_running_summary = (
                (state.get("running_summary", "") + "\n\n" + summary_delta)
                if state.get("running_summary")
                else summary_delta
            )

            for src in used_sources:
                url = src.get("url") or src.get("link") or ""
                if not url or url in self.collected_sources:
                    continue
                self.collected_sources[url] = src

            if self.monitoring:
                self.monitoring.record_metric(
                    "deep_research.search_results",
                    float(len(all_results)),
                    tags={"iteration": str(self.iteration)},
                )

            return {
                **state,
                "running_summary": new_running_summary,
                "search_results": all_results,
                "summary_delta": summary_delta,
            }
        finally:
            if trace:
                self.monitoring.end_trace(trace)

    def _graph_reflect_step(self, state: DeepResearchGraphState) -> DeepResearchGraphState:
        """Nodo REFLECT: aplica reflexión, actualiza tareas y decide si continuar."""
        trace = self.monitoring.start_trace(
            "deep_research.reflect",
            metadata={"iteration": self.iteration, "topic": self.topic[:64]},
        ) if self.monitoring else None

        try:
            selected_ids = state.get("selected_task_ids", [])
            todo_state = self.todo_manager.list_tasks()
            task_by_id = {t.id: t for t in todo_state.tasks}
            selected_tasks = [task_by_id[tid] for tid in selected_ids if tid in task_by_id]

            reflection = self._reflect_and_update_todos(
                user_query=state["user_query"],
                tasks=selected_tasks,
                summary=state.get("running_summary", ""),
                search_results=state.get("search_results", []) or [],
            )

            # Actualizar estado de tareas en función de la reflexión
            if reflection.get("mark_completed"):
                self.todo_manager.update_task_status(
                    reflection["mark_completed"], "completed"
                )
            if reflection.get("cancel_tasks"):
                self.todo_manager.update_task_status(
                    reflection["cancel_tasks"], "cancelled"
                )
            if reflection.get("new_tasks"):
                self.todo_manager.add_tasks(
                    descriptions=reflection["new_tasks"],
                    provenance="knowledge_gap",
                    base_priority=7,
                )

            coverage = int(reflection.get("coverage", 0) or 0)

            # Generar visualizaciones placeholder si el agente está disponible
            viz_paths: List[str] = []
            if self.visualization_agent:
                try:
                    charts = self.visualization_agent.generate_placeholder_charts(count=1)
                    viz_paths = [str(p) for p in charts]
                except Exception:
                    viz_paths = []
            iter_result = ResearchIterationResult(
                iteration=self.iteration,
                used_tasks=selected_ids,
                summary_delta=state.get("summary_delta", ""),
                sources=state.get("search_results", [])[:15],
                knowledge_gap=reflection.get("knowledge_gap"),
                research_complete=reflection.get("research_complete", False),
                coverage=coverage,
            )
            # Registrar resultado para consumo externo
            # (run_research_loop los agregará a la lista visible)
            self.iteration_results.append(iter_result)

            if self.monitoring:
                self.monitoring.record_metric(
                    "deep_research.coverage_raw",
                    float(coverage),
                    tags={"iteration": str(self.iteration)},
                )

            should_continue: Literal["continue", "end"] = (
                "end" if iter_result.research_complete else "continue"
            )

            return {
                **state,
                "reflection": reflection,
                "should_continue": should_continue,
            }
        finally:
            if trace:
                self.monitoring.end_trace(trace)

    @staticmethod
    def _graph_decide_after_reflect(state: DeepResearchGraphState) -> Literal["continue", "end"]:
        return state.get("should_continue", "end")


class DeepResearchSession:
    """
    Representa una sesión de Deep Research.

    - Mantiene el MasterResearchAgent y el ResearchTodoManager.
    - Expone un método de alto nivel para ejecutar la investigación completa
      y otro para obtener un informe final estructurado en Markdown.
    """

    def __init__(
        self,
        config: AppConfig,
        topic: str,
        base_dir: Optional[Path] = None,
        knowledge_paths: Optional[List[str]] = None,
        monitoring: Optional[MonitoringSystem] = None,
    ):
        self.config = config
        self.topic = topic
        self.session_id = str(uuid.uuid4())
        self.base_dir = base_dir or Path(config.memory_dir) / "deep_research"
        self.session_dir = self.base_dir / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.todo_manager = ResearchTodoManager(self.session_dir, topic=topic)
        self.todo_manager.init_initial_plan(topic)
        self.master_agent = MasterResearchAgent(
            config,
            topic,
            self.todo_manager,
            knowledge_paths=knowledge_paths,
            monitoring=monitoring,
        )

        self.iteration_results: List[ResearchIterationResult] = []

    def run(
        self,
        user_query: str,
        max_loops: int = 5,
        steering_messages: Optional[List[str]] = None,
    ) -> None:
        self.iteration_results = self.master_agent.run_research_loop(
            user_query=user_query,
            max_loops=max_loops,
            steering_messages=steering_messages,
        )

        # Guardar resumen y fuentes en disco para auditoría
        (self.session_dir / "summary.md").write_text(
            self.master_agent.running_summary, encoding="utf-8"
        )
        (self.session_dir / "sources.json").write_text(
            json.dumps(self.master_agent.collected_sources, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_report_markdown(self, user_query: str) -> str:
        """
        Genera un informe final estructurado, reutilizando el *running summary*
        y las fuentes recogidas.
        """
        sources_list = [
            {"url": url, **meta} for url, meta in self.master_agent.collected_sources.items()
        ]
        sources_text = "\n".join(
            f"- [{s.get('title') or 'Fuente'}]({s.get('url')})"
            for s in sources_list
            if s.get("url")
        )

        iterations = len(self.iteration_results)
        coverage = max(
            (getattr(r, "coverage", None) or 0) for r in self.iteration_results
        ) if self.iteration_results else 0

        header = f"""# Informe de Deep Research: {self.topic}

**Consulta original:** {user_query}
**Iteraciones ejecutadas:** {iterations}

---

"""

        report = header + self.master_agent.running_summary

        if sources_text:
            report += "\n\n---\n\n## Fuentes principales\n\n" + sources_text

        # Añadir sección de visualizaciones si existen gráficos generados para la sesión
        charts_dir = self.session_dir / "charts"
        if charts_dir.exists():
            chart_files = sorted(
                [p for p in charts_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
            )
            if chart_files:
                report += "\n\n## 📊 Visualizaciones\n\n"
                for chart in chart_files:
                    rel_path = chart.relative_to(self.session_dir)
                    report += f"![Visualización]({rel_path.as_posix()})\n\n"

        return report



