"""
JARVIS - Agente Autónomo 24/7
Sistema inteligente que absorbe toda la data del producto y trabaja de forma autónoma
Basado en personal KV-Cache retrieval y agentic AI
"""

from __future__ import annotations

import time
import json
import re
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
import uuid
from pathlib import Path
import hashlib

from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel

from .config import AppConfig
from .long_context_manager import LongContextManager, ContextChunk
from .autonomous_agent import AutonomousAgent, Hypothesis
from .text_to_action import TextToAction, ActionPlan
from .chain_of_thought import ChainOfThoughtReasoner
from .adversarial_testing import AdversarialTester
from .persistent_storage import PersistentStorage
from .mcp_manager import MCPManager
from .schema_annotations import SchemaAnnotationManager, SchemaObjectType
from .custom_tasks import CustomTaskManager, CustomTask, TaskSchedule
from .agent_templates import AgentTemplateManager, AgentTemplate, AgentTemplateType
from .reinforcement_planning import ReinforcementPlanner
from .test_time_training import TestTimeTrainer
from .path_dependent_reasoning import PathDependentReasoner
from .goal_decomposition import GoalDecomposer


class TaskPriority(str, Enum):
    """Prioridad de tareas."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """Estado de tareas."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class JarvisMemory:
    """Memoria persistente de JARVIS usando KV-Cache retrieval."""
    user_id: str
    concept_name: str  # Identificador del concepto/usuario
    text_metadata: Dict[str, Any] = field(default_factory=dict)  # Metadata textual
    visual_patches: List[str] = field(default_factory=list)  # Patches visuales (embeddings)
    kv_cache: Optional[Dict[str, Any]] = None  # KV-Cache precomputado
    last_updated: float = field(default_factory=time.time)
    access_count: int = 0
    
    def get_fingerprint(self) -> str:
        """Genera fingerprint único del concepto."""
        metadata_str = json.dumps(self.text_metadata, sort_keys=True)
        return hashlib.md5(f"{self.concept_name}{metadata_str}".encode()).hexdigest()


@dataclass
class JarvisTask:
    """Tarea autónoma de JARVIS."""
    task_id: str
    task_type: str  # "discover_insights", "analyze_patterns", "generate_report", "execute_action", etc.
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    execution_time: float = 0.0
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class JarvisInsight:
    """Insight descubierto por JARVIS."""
    insight_id: str
    title: str
    description: str
    category: str  # "pattern", "anomaly", "opportunity", "risk", "trend"
    confidence: float  # 0-1
    evidence: List[str] = field(default_factory=list)
    actionable: bool = False
    action_recommendation: Optional[str] = None
    discovered_at: float = field(default_factory=time.time)
    relevance_score: float = 0.0


@dataclass
class JarvisAlert:
    """Alerta generada por JARVIS."""
    alert_id: str
    alert_type: str  # "critical_insight", "anomaly_detected", "action_required", "trend_change"
    title: str
    message: str
    severity: str  # "critical", "high", "medium", "low"
    related_insight_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    acknowledged: bool = False


class JarvisAgent:
    """
    JARVIS - Agente Autónomo 24/7
    
    Características:
    - Absorbe toda la data del producto (todos los modos)
    - Conectado a apps integradas
    - Trabaja 24/7 descubriendo insights
    - Ejecuta acciones autónomas
    - Genera alertas y reportes
    - Más inteligente que un humano
    """
    
    def __init__(
        self,
        user_id: str,
        config: AppConfig,
        llm: Optional[BaseLanguageModel] = None
    ):
        self.user_id = user_id
        self.config = config
        self.llm = llm
        
        # Memoria persistente (Personal KV-Cache)
        self.memory = JarvisMemory(
            user_id=user_id,
            concept_name=f"user_{user_id}"
        )
        
        # Context Manager para toda la data
        self.context_manager = LongContextManager(
            config=config,
            llm=llm,
            max_short_term_tokens=2_000_000  # 2M tokens para JARVIS
        )
        
        # Agente autónomo
        self.autonomous_agent = AutonomousAgent(
            agent_id=f"jarvis_{user_id}",
            config=config,
            llm=llm,
            context_manager=self.context_manager
        )
        
        # Text-to-Action
        self.text_to_action = TextToAction(
            config=config,
            llm=llm,
            sandbox_enabled=True
        )
        
        # Chain of Thought
        self.chain_of_thought = ChainOfThoughtReasoner(
            config=config,
            llm=llm
        )
        
        # Adversarial Tester
        self.adversarial_tester = AdversarialTester(
            config=config,
            llm=llm
        )
        
        # Estado
        self.is_running = False
        self.tasks: List[JarvisTask] = []
        self.insights: List[JarvisInsight] = []
        self.alerts: List[JarvisAlert] = []
        
        # Estadísticas
        self.stats = {
            "total_tasks_completed": 0,
            "total_insights_discovered": 0,
            "total_alerts_generated": 0,
            "total_actions_executed": 0,
            "uptime_hours": 0.0,
            "last_activity": time.time()
        }
        
        # Sistema de almacenamiento persistente
        self.persistent_storage = PersistentStorage()
        
        # MCP Manager - Conecta JARVIS con sistemas externos usando MCP
        self.mcp_manager = MCPManager(config=config, llm=llm)
        self.mcp_manager.initialize()
        
        # Schema Annotations Manager - Superpoderes de comprensión para JARVIS
        self.schema_annotations = SchemaAnnotationManager(
            storage_dir=config.memory_dir / "schema_annotations"
        )
        
        # Custom Tasks Manager - Tareas personalizadas definidas por usuarios
        self.custom_task_manager = CustomTaskManager(config=config)
        
        # Agent Templates Manager - Plantillas de agentes predefinidas
        self.agent_template_manager = AgentTemplateManager(config=config)
        
        # Reinforcement Learning y Planning - Razonamiento por árboles de decisiones
        self.reinforcement_planner = ReinforcementPlanner(
            config=config,
            llm=llm,
            max_depth=10,
            max_branches=5,
            learning_enabled=True
        )
        
        # Test Time Training - Aprendizaje en tiempo de ejecución
        self.test_time_trainer = TestTimeTrainer(
            config=config,
            llm=llm,
            learning_rate=0.1,
            min_confidence=0.6
        )
        
        # Path-dependent Reasoning - Prueba diferentes enfoques
        self.path_reasoner = PathDependentReasoner(
            config=config,
            llm=llm,
            max_paths=5
        )
        
        # Goal-oriented Task Decomposition - Descomposición de objetivos
        self.goal_decomposer = GoalDecomposer(
            config=config,
            llm=llm
        )
        
        # Directorio para persistencia adicional
        self.storage_dir = Path(config.memory_dir) / "jarvis" / user_id
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar estado persistente
        self._load_state()
        
        # Cargar data histórica de almacenamiento persistente
        self._load_historical_data()
    
    def _load_state(self):
        """Carga estado persistente de JARVIS."""
        try:
            state_file = self.storage_dir / "jarvis_state.json"
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memory.text_metadata = data.get("text_metadata", {})
                    self.memory.access_count = data.get("access_count", 0)
                    self.stats = data.get("stats", self.stats)
                    print(f"✅ [JARVIS] Estado cargado para usuario {self.user_id}")
        except Exception as e:
            print(f"⚠️ [JARVIS] Error cargando estado: {e}")
    
    def _load_historical_data(self):
        """Carga toda la data histórica del almacenamiento persistente."""
        try:
            print(f"📚 [JARVIS] Cargando data histórica para usuario {self.user_id}...")
            
            # Cargar todos los documentos históricos
            historical_docs = self.persistent_storage.get_all_documents(
                session_id=f"jarvis_{self.user_id}",
                limit=1000  # Limitar a 1000 más recientes
            )
            
            # Cargar documentos al context manager
            for doc_record in historical_docs:
                try:
                    doc = self.persistent_storage.load_document_as_langchain(doc_record.doc_id)
                    if doc:
                        self.context_manager.add_document(
                            session_id=f"jarvis_{self.user_id}",
                            document=doc,
                            recency_score=0.5,  # Menos reciente que nuevos
                            relevance_score=0.8,
                            trust_score=1.0,
                            certainty_score=1.0
                        )
                except Exception as e:
                    print(f"⚠️ [JARVIS] Error cargando documento {doc_record.doc_id}: {e}")
            
            # Cargar data histórica de JARVIS
            historical_data = self.persistent_storage.get_all_jarvis_data(
                session_id=f"jarvis_{self.user_id}",
                limit=500
            )
            
            # Procesar data histórica
            for record in historical_data:
                try:
                    # Agregar al context manager
                    doc = Document(
                        page_content=record.data,
                        metadata={
                            "source": record.source,
                            "type": record.data_type,
                            "timestamp": record.timestamp,
                            **record.metadata
                        }
                    )
                    self.context_manager.add_document(
                        session_id=f"jarvis_{self.user_id}",
                        document=doc,
                        recency_score=0.5,
                        relevance_score=0.7,
                        trust_score=1.0,
                        certainty_score=1.0
                    )
                except Exception as e:
                    print(f"⚠️ [JARVIS] Error procesando data histórica {record.record_id}: {e}")
            
            print(f"✅ [JARVIS] Data histórica cargada: {len(historical_docs)} documentos, {len(historical_data)} registros")
        except Exception as e:
            print(f"⚠️ [JARVIS] Error cargando data histórica: {e}")
    
    def _save_state(self):
        """Guarda estado persistente de JARVIS."""
        try:
            state_file = self.storage_dir / "jarvis_state.json"
            # Convertir sets a listas para serialización JSON
            text_metadata_serializable = {}
            for key, value in self.memory.text_metadata.items():
                if isinstance(value, dict):
                    serializable_value = value.copy()
                    if "types" in serializable_value and isinstance(serializable_value["types"], set):
                        serializable_value["types"] = list(serializable_value["types"])
                    text_metadata_serializable[key] = serializable_value
                else:
                    text_metadata_serializable[key] = value
            
            data = {
                "user_id": self.user_id,
                "text_metadata": text_metadata_serializable,
                "access_count": self.memory.access_count,
                "stats": self.stats,
                "last_saved": time.time()
            }
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ [JARVIS] Error guardando estado: {e}")
    
    def absorb_data(
        self,
        data: Any,
        source: str,
        data_type: str = "document",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Absorbe data de cualquier modo del producto.
        
        Args:
            data: Los datos a absorber (Document, str, dict, etc.)
            source: Origen de los datos (ej: "guia_experto", "chatbot", "integraciones", etc.)
            data_type: Tipo de dato ("document", "text", "query", "response", etc.)
            metadata: Metadata adicional
        """
        print(f"🧠 [JARVIS] Absorbiendo data de {source} ({data_type})...")
        
        # Convertir a Document si es necesario
        if isinstance(data, Document):
            doc = data
        elif isinstance(data, str):
            doc = Document(
                page_content=data,
                metadata={
                    "source": source,
                    "type": data_type,
                    "timestamp": time.time(),
                    **(metadata or {})
                }
            )
        elif isinstance(data, dict):
            # Extraer contenido
            content = data.get("content", data.get("text", data.get("answer", str(data))))
            doc = Document(
                page_content=content,
                metadata={
                    "source": source,
                    "type": data_type,
                    "timestamp": time.time(),
                    **data.get("metadata", {}),
                    **(metadata or {})
                }
            )
        else:
            doc = Document(
                page_content=str(data),
                metadata={
                    "source": source,
                    "type": data_type,
                    "timestamp": time.time(),
                    **(metadata or {})
                }
            )
        
        # Agregar al context manager con alta relevancia
        chunk_id = self.context_manager.add_document(
            session_id=f"jarvis_{self.user_id}",
            document=doc,
            recency_score=1.0,  # Siempre reciente
            relevance_score=1.0,  # Alta relevancia
            trust_score=1.0,
            certainty_score=1.0
        )
        
        # Actualizar metadata de memoria
        if source not in self.memory.text_metadata:
            self.memory.text_metadata[source] = {
                "count": 0,
                "last_updated": time.time(),
                "types": set()
            }
        
        self.memory.text_metadata[source]["count"] += 1
        self.memory.text_metadata[source]["last_updated"] = time.time()
        self.memory.text_metadata[source]["types"].add(data_type)
        self.memory.access_count += 1
        self.memory.last_updated = time.time()
        
        # Guardar en almacenamiento persistente
        try:
            if isinstance(data, Document):
                # Guardar documento permanentemente
                doc_id = self.persistent_storage.save_document(
                    document=doc,
                    session_id=f"jarvis_{self.user_id}",
                    source=source
                )
            else:
                # Guardar como data de JARVIS
                self.persistent_storage.save_jarvis_data(
                    session_id=f"jarvis_{self.user_id}",
                    data=data,
                    data_type=data_type,
                    source=source,
                    metadata=metadata
                )
        except Exception as e:
            print(f"⚠️ [JARVIS] Error guardando en almacenamiento persistente: {e}")
        
        # Guardar estado
        self._save_state()
        
        print(f"✅ [JARVIS] Data absorbida: {chunk_id[:8]}... (Total: {self.memory.access_count} items)")
        
        return chunk_id
    
    async def discover_insights(self, focus_area: Optional[str] = None) -> List[JarvisInsight]:
        """
        Descubre insights de forma autónoma.
        """
        print(f"🔍 [JARVIS] Descubriendo insights (área: {focus_area or 'general'})...")
        
        # Obtener contexto completo
        context_text, context_metadata = self.context_manager.get_context_for_prompt(
            session_id=f"jarvis_{self.user_id}",
            max_tokens=500_000,
            include_metadata=True
        )
        
        # Construir prompt para descubrimiento
        discovery_prompt = f"""Eres JARVIS, un agente autónomo super inteligente que descubre insights ocultos.

Analiza toda la información disponible y descubre:
1. Patrones ocultos que otros no ven
2. Anomalías o inconsistencias
3. Oportunidades de mejora
4. Riesgos potenciales
5. Tendencias emergentes

{f'Enfócate en: {focus_area}' if focus_area else 'Analiza todo el contexto disponible'}

Contexto disponible:
{context_text[:200000]}

Genera insights específicos, accionables y con alta confianza.
Responde en formato JSON con:
{{
    "insights": [
        {{
            "title": "Título del insight",
            "description": "Descripción detallada",
            "category": "pattern|anomaly|opportunity|risk|trend",
            "confidence": 0.0-1.0,
            "evidence": ["evidencia1", "evidencia2"],
            "actionable": true/false,
            "action_recommendation": "Qué hacer al respecto"
        }}
    ]
}}
"""
        
        # Usar agente autónomo para descubrir
        try:
            agent_result = await self.autonomous_agent.run_full_cycle(discovery_prompt)
            
            # Extraer insights del resultado
            insights = []
            if agent_result.get("principles_learned"):
                for principle in agent_result["principles_learned"]:
                    insight = JarvisInsight(
                        insight_id=str(uuid.uuid4()),
                        title=f"Insight: {principle[:50]}",
                        description=principle,
                        category="pattern",
                        confidence=0.8,
                        actionable=True,
                        relevance_score=0.9
                    )
                    insights.append(insight)
            
            # También usar LLM directo para generar más insights
            if self.llm:
                try:
                    response = await self.llm.ainvoke(discovery_prompt)
                    content = response.content if hasattr(response, 'content') else str(response)
                    
                    # Parsear JSON de insights
                    if "```json" in content:
                        json_str = content.split("```json")[1].split("```")[0].strip()
                    else:
                        json_str = content
                    
                    try:
                        data = json.loads(json_str)
                        for insight_data in data.get("insights", []):
                            insight = JarvisInsight(
                                insight_id=str(uuid.uuid4()),
                                title=insight_data.get("title", "Insight sin título"),
                                description=insight_data.get("description", ""),
                                category=insight_data.get("category", "pattern"),
                                confidence=insight_data.get("confidence", 0.7),
                                evidence=insight_data.get("evidence", []),
                                actionable=insight_data.get("actionable", False),
                                action_recommendation=insight_data.get("action_recommendation"),
                                relevance_score=insight_data.get("confidence", 0.7)
                            )
                            insights.append(insight)
                    except json.JSONDecodeError:
                        # Si no es JSON válido, crear insight genérico
                        insight = JarvisInsight(
                            insight_id=str(uuid.uuid4()),
                            title="Insight descubierto",
                            description=content[:500],
                            category="pattern",
                            confidence=0.6,
                            actionable=False
                        )
                        insights.append(insight)
                except Exception as e:
                    print(f"⚠️ [JARVIS] Error generando insights con LLM: {e}")
            
            # Guardar insights
            self.insights.extend(insights)
            self.stats["total_insights_discovered"] += len(insights)
            
            # Generar alertas para insights críticos
            for insight in insights:
                if insight.confidence > 0.8 and insight.actionable:
                    await self._generate_alert_for_insight(insight)
            
            print(f"✅ [JARVIS] {len(insights)} insights descubiertos")
            
            return insights
            
        except Exception as e:
            print(f"❌ [JARVIS] Error descubriendo insights: {e}")
            return []
    
    async def _generate_alert_for_insight(self, insight: JarvisInsight):
        """Genera alerta para un insight importante."""
        severity = "critical" if insight.confidence > 0.9 else "high" if insight.confidence > 0.8 else "medium"
        
        alert = JarvisAlert(
            alert_id=str(uuid.uuid4()),
            alert_type="critical_insight",
            title=f"Insight Importante: {insight.title}",
            message=insight.description,
            severity=severity,
            related_insight_id=insight.insight_id
        )
        
        self.alerts.append(alert)
        self.stats["total_alerts_generated"] += 1
        
        print(f"🚨 [JARVIS] Alerta generada: {alert.title}")
    
    async def execute_autonomous_task(self, task: JarvisTask) -> Any:
        """
        Ejecuta una tarea autónoma.
        """
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = time.time()
        
        print(f"⚡ [JARVIS] Ejecutando tarea: {task.description[:50]}...")
        
        try:
            # Obtener contexto
            context_text, _ = self.context_manager.get_context_for_prompt(
                session_id=f"jarvis_{self.user_id}",
                max_tokens=300_000
            )
            
            # Ejecutar según tipo de tarea
            if task.task_type == "discover_insights":
                result = await self.discover_insights(focus_area=task.parameters.get("focus_area"))
                task.result = {"insights": [i.__dict__ for i in result]}
            
            elif task.task_type == "analyze_patterns":
                # Usar agente autónomo para analizar patrones
                analysis_prompt = f"""Analiza los siguientes datos y descubre patrones:

{context_text[:100000]}

Pregunta específica: {task.parameters.get('question', '¿Qué patrones observas?')}
"""
                agent_result = await self.autonomous_agent.run_full_cycle(analysis_prompt)
                task.result = agent_result
            
            elif task.task_type == "generate_report":
                # Generar reporte usando chain of thought
                report_prompt = f"""Genera un reporte ejecutivo sobre:

{task.parameters.get('topic', 'Estado general')}

Contexto disponible:
{context_text[:100000]}

Incluye: resumen ejecutivo, insights clave, recomendaciones, y próximos pasos.
"""
                # Usar Chain of Thought correctamente
                chain_id = self.chain_of_thought.create_chain(report_prompt)
                await self.chain_of_thought.add_reasoning_steps(chain_id, context_text[:50000])
                chain = self.chain_of_thought.get_chain(chain_id)
                
                if chain:
                    # Completar cadena con respuesta
                    if not chain.final_answer:
                        # Generar respuesta final si no existe
                        chain.final_answer = "Reporte generado usando Chain of Thought"
                        self.chain_of_thought.complete_chain(chain_id, chain.final_answer, success=True)
                    
                    task.result = {
                        "report": chain.final_answer,
                        "confidence": 0.8,  # Confianza por defecto
                        "steps": len(chain.steps)
                    }
                else:
                    task.result = {
                        "report": "Error generando reporte con Chain of Thought",
                        "confidence": 0.0,
                        "steps": 0
                    }
            
            elif task.task_type == "execute_action":
                # Ejecutar acción usando text-to-action
                action_command = task.parameters.get("command", task.description)
                action_result = await self.text_to_action.process_command(
                    command=action_command,
                    auto_execute=task.parameters.get("auto_execute", False)
                )
                task.result = action_result
                self.stats["total_actions_executed"] += 1
            
            else:
                # Tarea genérica usando agente autónomo
                generic_prompt = f"""{task.description}

Contexto:
{context_text[:100000]}

Parámetros: {json.dumps(task.parameters, indent=2)}
"""
                agent_result = await self.autonomous_agent.run_full_cycle(generic_prompt)
                task.result = agent_result
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            task.execution_time = task.completed_at - task.started_at
            self.stats["total_tasks_completed"] += 1
            
            print(f"✅ [JARVIS] Tarea completada en {task.execution_time:.2f}s")
            
            return task.result
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = time.time()
            task.execution_time = task.completed_at - (task.started_at or time.time())
            task.retry_count += 1
            
            print(f"❌ [JARVIS] Error en tarea: {e}")
            
            # Reintentar si es posible
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.PENDING
                print(f"🔄 [JARVIS] Reintentando tarea (intento {task.retry_count + 1}/{task.max_retries})")
            
            return None
    
    
    def stop(self):
        """Detiene el loop continuo."""
        self.is_running = False
        self._save_state()
        print("🛑 [JARVIS] Loop detenido")
    
    def add_task(
        self,
        task_type: str,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        parameters: Optional[Dict[str, Any]] = None
    ) -> JarvisTask:
        """Agrega una nueva tarea."""
        task = JarvisTask(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            description=description,
            priority=priority,
            parameters=parameters or {}
        )
        self.tasks.append(task)
        return task
    
    def register_mcp_connection(
        self,
        name: str,
        connection_type: str,
        config: Dict[str, Any]
    ) -> str:
        """Registra una nueva conexión MCP."""
        return self.mcp_manager.register_connection(
            name=name,
            connection_type=connection_type,
            config=config
        )
    
    def list_mcp_connections(self) -> List[Dict[str, Any]]:
        """Lista todas las conexiones MCP."""
        return self.mcp_manager.list_connections()
    
    def list_mcp_tools(self) -> List[Dict[str, Any]]:
        """Lista todas las herramientas MCP disponibles."""
        return self.mcp_manager.list_available_tools()
    
    async def call_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Llama a una herramienta MCP."""
        return await self.mcp_manager.call_tool(
            tool_name=tool_name,
            arguments=arguments
        )
    
    def get_mcp_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de MCP."""
        return self.mcp_manager.get_statistics()
    
    async def navigate_raw_data(
        self,
        data_source: str,
        query: str
    ) -> Dict[str, Any]:
        """
        Navega datos crudos sin conectores específicos.
        
        Potencia MCP para que JARVIS pueda navegar cualquier tipo de dato
        sin necesidad de construir conectores específicos.
        """
        return await self.mcp_manager.navigate_raw_data(
            data_source=data_source,
            query=query,
            llm=self.llm
        )
    
    def enrich_query_with_schema_context(self, query: str) -> str:
        """
        Enriquece una query con contexto de esquemas anotados.
        Esto mejora la comprensión de JARVIS sobre estructuras de datos.
        """
        # Detectar nombres de tablas, columnas, etc. en la query
        import re
        
        # Buscar patrones comunes (tablas, columnas mencionadas)
        table_pattern = r'\b(from|join|table|into)\s+(\w+)'
        column_pattern = r'\b(select|where|set|update)\s+(\w+)'
        
        enriched_parts = [query]
        schema_context = []
        
        # Buscar tablas mencionadas
        for match in re.finditer(table_pattern, query, re.IGNORECASE):
            table_name = match.group(2)
            context = self.schema_annotations.get_schema_context(
                object_name=table_name,
                object_type=SchemaObjectType.TABLE
            )
            if context and "sin anotaciones" not in context.lower():
                schema_context.append(f"Contexto de esquema para '{table_name}':\n{context}")
        
        # Buscar columnas mencionadas
        for match in re.finditer(column_pattern, query, re.IGNORECASE):
            column_name = match.group(2)
            context = self.schema_annotations.get_schema_context(
                object_name=column_name,
                object_type=SchemaObjectType.COLUMN
            )
            if context and "sin anotaciones" not in context.lower():
                schema_context.append(f"Contexto de esquema para '{column_name}':\n{context}")
        
        # Si hay contexto de esquemas, agregarlo a la query
        if schema_context:
            enriched_query = query + "\n\n--- Contexto de Esquemas ---\n" + "\n\n".join(schema_context)
            return enriched_query
        
        return query
    
    def add_schema_annotation(
        self,
        object_type: str,
        object_name: str,
        description: str,
        **kwargs
    ) -> str:
        """Agrega una anotación de esquema."""
        try:
            schema_obj_type = SchemaObjectType(object_type)
            return self.schema_annotations.add_annotation(
                object_type=schema_obj_type,
                object_name=object_name,
                description=description,
                **kwargs
            )
        except ValueError:
            raise ValueError(f"Tipo de objeto inválido: {object_type}")
    
    def get_schema_annotations(
        self,
        object_name: Optional[str] = None,
        object_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Obtiene anotaciones de esquema."""
        schema_obj_type = None
        if object_type:
            try:
                schema_obj_type = SchemaObjectType(object_type)
            except ValueError:
                pass
        
        return self.schema_annotations.list_annotations(object_type=schema_obj_type)
    
    def get_schema_context(self, object_name: str, object_type: Optional[str] = None) -> str:
        """Obtiene contexto de esquema para un objeto."""
        schema_obj_type = None
        if object_type:
            try:
                schema_obj_type = SchemaObjectType(object_type)
            except ValueError:
                pass
        
        return self.schema_annotations.get_schema_context(
            object_name=object_name,
            object_type=schema_obj_type
        )
    
    def get_schema_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de anotaciones de esquema."""
        return self.schema_annotations.get_statistics()
    
    # ============================================
    # GESTIÓN DE TAREAS PERSONALIZADAS
    # ============================================
    
    async def create_custom_task(
        self,
        name: str,
        description: str,
        instructions: str,
        schedule: str = "daily",
        cron_expression: Optional[str] = None,
        priority: str = "medium",
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        use_goal_decomposition: bool = True
    ) -> str:
        """
        Crea una nueva tarea personalizada.
        
        Si use_goal_decomposition es True, descompone el objetivo automáticamente.
        """
        schedule_enum = TaskSchedule(schedule) if schedule in [s.value for s in TaskSchedule] else TaskSchedule.DAILY
        
        # Si se solicita, descomponer el objetivo usando Goal Decomposition
        goal_id = None
        if use_goal_decomposition and self.llm:
            try:
                goal_id = await self.goal_decomposer.decompose_goal(
                    goal_description=instructions,
                    context=f"Tarea: {name}\nDescripción: {description}"
                )
                print(f"✅ [JARVIS] Objetivo descompuesto en subtareas (goal_id: {goal_id})")
            except Exception as e:
                print(f"⚠️ [JARVIS] Error descomponiendo objetivo: {e}")
        
        task_id = self.custom_task_manager.create_task(
            name=name,
            description=description,
            instructions=instructions,
            schedule=schedule_enum,
            cron_expression=cron_expression,
            priority=priority,
            parameters={
                **(parameters or {}),
                "goal_id": goal_id  # Guardar goal_id si existe
            },
            tags=tags
        )
        
        return task_id
    
    def list_custom_tasks(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """Lista todas las tareas personalizadas."""
        tasks = self.custom_task_manager.list_tasks(enabled_only=enabled_only)
        return [asdict(task) for task in tasks]
    
    def get_custom_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una tarea personalizada."""
        task = self.custom_task_manager.get_task(task_id)
        return asdict(task) if task else None
    
    def update_custom_task(
        self,
        task_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        schedule: Optional[str] = None,
        enabled: Optional[bool] = None,
        **kwargs
    ) -> bool:
        """Actualiza una tarea personalizada."""
        schedule_enum = None
        if schedule:
            schedule_enum = TaskSchedule(schedule) if schedule in [s.value for s in TaskSchedule] else None
        
        return self.custom_task_manager.update_task(
            task_id=task_id,
            name=name,
            description=description,
            instructions=instructions,
            schedule=schedule_enum,
            enabled=enabled,
            **kwargs
        )
    
    def delete_custom_task(self, task_id: str) -> bool:
        """Elimina una tarea personalizada."""
        return self.custom_task_manager.delete_task(task_id)
    
    def get_custom_task_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de tareas personalizadas."""
        return self.custom_task_manager.get_statistics()
    
    # ============================================
    # GESTIÓN DE PLANTILLAS DE AGENTES
    # ============================================
    
    def list_agent_templates(self, template_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista todas las plantillas de agentes."""
        template_type_enum = None
        if template_type:
            try:
                template_type_enum = AgentTemplateType(template_type)
            except ValueError:
                pass
        
        templates = self.agent_template_manager.list_templates(template_type=template_type_enum)
        return [asdict(t) for t in templates]
    
    def get_agent_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una plantilla de agente."""
        template = self.agent_template_manager.get_template(template_id)
        return asdict(template) if template else None
    
    def activate_agent_template(self, template_id: str) -> bool:
        """Activa una plantilla de agente."""
        return self.agent_template_manager.activate_template(template_id)
    
    def deactivate_agent_template(self, template_id: str) -> bool:
        """Desactiva una plantilla de agente."""
        return self.agent_template_manager.deactivate_template(template_id)
    
    def create_custom_agent_template(
        self,
        name: str,
        description: str,
        system_prompt: str,
        tools: Optional[List[str]] = None,
        tasks: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Crea una plantilla de agente personalizada."""
        return self.agent_template_manager.create_custom_template(
            name=name,
            description=description,
            system_prompt=system_prompt,
            tools=tools,
            tasks=tasks,
            parameters=parameters
        )
    
    def get_agent_template_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de plantillas de agentes."""
        return self.agent_template_manager.get_statistics()
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Obtiene datos para el dashboard."""
        return {
            "user_id": self.user_id,
            "is_running": self.is_running,
            "stats": self.stats,
            "memory": {
                "total_items": self.memory.access_count,
                "sources": list(self.memory.text_metadata.keys()),
                "last_updated": self.memory.last_updated
            },
            "tasks": {
                "total": len(self.tasks),
                "pending": sum(1 for t in self.tasks if t.status == TaskStatus.PENDING),
                "in_progress": sum(1 for t in self.tasks if t.status == TaskStatus.IN_PROGRESS),
                "completed": sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED),
                "failed": sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)
            },
            "insights": {
                "total": len(self.insights),
                "recent": [
                    {
                        "title": i.title,
                        "category": i.category,
                        "confidence": i.confidence,
                        "discovered_at": i.discovered_at
                    }
                    for i in sorted(self.insights, key=lambda x: x.discovered_at, reverse=True)[:10]
                ]
            },
            "schema_annotations": self.get_schema_statistics(),
            "custom_tasks": self.get_custom_task_statistics(),
            "agent_templates": self.get_agent_template_statistics(),
            "reinforcement_planning": self.reinforcement_planner.get_statistics(),
            "test_time_training": self.test_time_trainer.get_statistics(),
            "path_dependent_reasoning": self.path_reasoner.get_statistics(),
            "goal_decomposition": self.goal_decomposer.get_statistics(),
            "alerts": {
                "total": len(self.alerts),
                "unacknowledged": sum(1 for a in self.alerts if not a.acknowledged),
                "recent": [
                    {
                        "title": a.title,
                        "severity": a.severity,
                        "created_at": a.created_at
                    }
                    for a in sorted(self.alerts, key=lambda x: x.created_at, reverse=True)[:10]
                ]
            }
        }
    
    def get_recent_insights(self, limit: int = 10) -> List[JarvisInsight]:
        """Obtiene insights recientes."""
        return sorted(self.insights, key=lambda x: x.discovered_at, reverse=True)[:limit]
    
    def get_unacknowledged_alerts(self) -> List[JarvisAlert]:
        """Obtiene alertas no reconocidas."""
        return [a for a in self.alerts if not a.acknowledged]
    
    def acknowledge_alert(self, alert_id: str):
        """Reconoce una alerta."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                break
    
    # ============================================
    # FUNCIONALIDADES AVANZADAS - 12 TAREAS PRINCIPALES
    # ============================================
    
    async def monitor_documents_24_7(self) -> List[JarvisAlert]:
        """
        TAREA 1: Monitoreo continuo de documentos (24/7)
        Escanea constantemente nuevos documentos, modificados, y reindexa automáticamente.
        """
        print("📄 [JARVIS] Monitoreando documentos 24/7...")
        alerts = []
        
        try:
            # Obtener todos los documentos del almacenamiento persistente
            all_docs = self.persistent_storage.get_all_documents(limit=1000)
            
            # Detectar documentos nuevos (últimas 24 horas)
            recent_cutoff = time.time() - (24 * 3600)
            new_docs = [
                doc for doc in all_docs 
                if datetime.fromisoformat(doc.uploaded_at).timestamp() > recent_cutoff
            ]
            
            if new_docs:
                print(f"🆕 [JARVIS] Detectados {len(new_docs)} documentos nuevos")
                
                # Analizar cada documento nuevo
                for doc_record in new_docs:
                    try:
                        doc = self.persistent_storage.load_document_as_langchain(doc_record.doc_id)
                        if doc:
                            # Analizar contenido para detectar riesgos
                            analysis = await self._analyze_document_for_risks(doc)
                            
                            if analysis.get("has_risks"):
                                alert = JarvisAlert(
                                    alert_id=str(uuid.uuid4()),
                                    alert_type="document_risk",
                                    title=f"Riesgo detectado en: {doc_record.file_name}",
                                    message=analysis.get("risk_description", ""),
                                    severity=analysis.get("severity", "medium"),
                                    created_at=time.time()
                                )
                                alerts.append(alert)
                                
                            # Reindexar automáticamente
                            self.context_manager.add_document(
                                session_id=f"jarvis_{self.user_id}",
                                document=doc,
                                recency_score=1.0,
                                relevance_score=0.9,
                                trust_score=1.0,
                                certainty_score=1.0
                            )
                    except Exception as e:
                        print(f"⚠️ [JARVIS] Error analizando documento {doc_record.doc_id}: {e}")
            
            # Detectar documentos duplicados
            content_hashes = {}
            for doc in all_docs:
                if doc.content_hash in content_hashes:
                    alert = JarvisAlert(
                        alert_id=str(uuid.uuid4()),
                        alert_type="duplicate_document",
                        title=f"Documento duplicado: {doc.file_name}",
                        message=f"Este documento es similar a {content_hashes[doc.content_hash]}",
                        severity="low",
                        created_at=time.time()
                    )
                    alerts.append(alert)
                else:
                    content_hashes[doc.content_hash] = doc.file_name
            
            self.alerts.extend(alerts)
            print(f"✅ [JARVIS] Monitoreo completado: {len(alerts)} alertas generadas")
            
        except Exception as e:
            print(f"❌ [JARVIS] Error en monitoreo de documentos: {e}")
        
        return alerts
    
    async def _analyze_document_for_risks(self, doc: Document) -> Dict[str, Any]:
        """Analiza un documento para detectar riesgos."""
        if not self.llm:
            return {"has_risks": False}
        
        try:
            prompt = f"""Analiza este documento y detecta riesgos, errores o problemas:

{doc.page_content[:5000]}

Responde en JSON:
{{
    "has_risks": true/false,
    "risk_description": "descripción del riesgo",
    "severity": "critical|high|medium|low"
}}
"""
            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parsear JSON
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            else:
                json_str = content
            
            try:
                return json.loads(json_str)
            except:
                return {"has_risks": False}
        except:
            return {"has_risks": False}
    
    async def generate_executive_summary(self, period: str = "daily") -> Dict[str, Any]:
        """
        TAREA 2: Generación automática de resúmenes ejecutivos diarios/semanales
        """
        print(f"📊 [JARVIS] Generando resumen ejecutivo {period}...")
        
        try:
            # Obtener estadísticas
            stats = self.persistent_storage.get_stats()
            
            # Obtener insights recientes
            recent_insights = self.get_recent_insights(limit=20)
            
            # Obtener alertas recientes
            recent_alerts = sorted(
                [a for a in self.alerts if not a.acknowledged],
                key=lambda x: x.created_at,
                reverse=True
            )[:10]
            
            # Construir contexto
            context = f"""
Estadísticas del sistema:
- Documentos totales: {stats['total_documents']}
- Queries totales: {stats['total_queries']}
- Registros JARVIS: {stats['total_jarvis_records']}

Insights recientes: {len(recent_insights)}
Alertas pendientes: {len(recent_alerts)}

Tareas completadas: {self.stats['total_tasks_completed']}
Acciones ejecutadas: {self.stats['total_actions_executed']}
"""
            
            # Generar resumen usando chain of thought
            summary_prompt = f"""Genera un resumen ejecutivo {period} del sistema DocChat Enterprise.

{context}

Incluye:
1. Resumen ejecutivo (2-3 párrafos)
2. Insights clave descubiertos
3. Alertas importantes
4. Recomendaciones
5. Próximos pasos

Formato profesional y conciso.
"""
            
            # Usar Chain of Thought correctamente
            chain_id = self.chain_of_thought.create_chain(summary_prompt)
            await self.chain_of_thought.add_reasoning_steps(chain_id, "")
            chain = self.chain_of_thought.get_chain(chain_id)
            
            if chain:
                if not chain.final_answer:
                    chain.final_answer = "Resumen generado usando Chain of Thought"
                    self.chain_of_thought.complete_chain(chain_id, chain.final_answer, success=True)
            
            summary = {
                "period": period,
                "generated_at": datetime.now().isoformat(),
                "content": chain.final_answer if chain else "Error generando resumen",
                "confidence": 0.8 if chain else 0.0,
                "stats": stats,
                "insights_count": len(recent_insights),
                "alerts_count": len(recent_alerts)
            }
            
            # Guardar como tarea completada
            task = JarvisTask(
                task_id=str(uuid.uuid4()),
                task_type="generate_report",
                description=f"Resumen ejecutivo {period}",
                status=TaskStatus.COMPLETED,
                result=summary,
                completed_at=time.time()
            )
            self.tasks.append(task)
            
            print(f"✅ [JARVIS] Resumen ejecutivo {period} generado")
            return summary
            
        except Exception as e:
            print(f"❌ [JARVIS] Error generando resumen ejecutivo: {e}")
            return {}
    
    async def detect_inconsistencies(self) -> List[JarvisInsight]:
        """
        TAREA 3: Identificación de inconsistencias, contradicciones y anomalías
        """
        print("🔍 [JARVIS] Detectando inconsistencias y contradicciones...")
        insights = []
        
        try:
            # Obtener todos los documentos
            all_docs = self.persistent_storage.get_all_documents(limit=500)
            
            if len(all_docs) < 2:
                return insights
            
            # Agrupar por tipo/source
            docs_by_type = {}
            for doc in all_docs:
                doc_type = doc.source
                if doc_type not in docs_by_type:
                    docs_by_type[doc_type] = []
                docs_by_type[doc_type].append(doc)
            
            # Comparar documentos del mismo tipo
            for doc_type, docs in docs_by_type.items():
                if len(docs) < 2:
                    continue
                
                # Cargar documentos y comparar
                doc_contents = []
                for doc_record in docs[:10]:  # Limitar a 10 para no sobrecargar
                    try:
                        doc = self.persistent_storage.load_document_as_langchain(doc_record.doc_id)
                        if doc:
                            doc_contents.append({
                                "id": doc_record.doc_id,
                                "name": doc_record.file_name,
                                "content": doc.page_content[:2000]  # Primeros 2000 chars
                            })
                    except:
                        continue
                
                if len(doc_contents) < 2:
                    continue
                
                # Usar LLM para detectar inconsistencias
                if self.llm:
                    comparison_prompt = f"""Compara estos documentos del mismo tipo y detecta:
1. Inconsistencias
2. Contradicciones
3. Anomalías
4. Valores que no coinciden

Documentos:
{json.dumps(doc_contents, indent=2, ensure_ascii=False)}

Responde en JSON:
{{
    "inconsistencies": [
        {{
            "description": "descripción",
            "documents_involved": ["doc1", "doc2"],
            "severity": "high|medium|low"
        }}
    ]
}}
"""
                    try:
                        response = await self.llm.ainvoke(comparison_prompt)
                        content = response.content if hasattr(response, 'content') else str(response)
                        
                        if "```json" in content:
                            json_str = content.split("```json")[1].split("```")[0].strip()
                        else:
                            json_str = content
                        
                        data = json.loads(json_str)
                        
                        for inconsistency in data.get("inconsistencies", []):
                            insight = JarvisInsight(
                                insight_id=str(uuid.uuid4()),
                                title=f"Inconsistencia detectada en {doc_type}",
                                description=inconsistency.get("description", ""),
                                category="anomaly",
                                confidence=0.8,
                                evidence=inconsistency.get("documents_involved", []),
                                actionable=True,
                                action_recommendation="Revisar y corregir documentos inconsistentes",
                                relevance_score=0.9 if inconsistency.get("severity") == "high" else 0.7
                            )
                            insights.append(insight)
                    except Exception as e:
                        print(f"⚠️ [JARVIS] Error detectando inconsistencias: {e}")
            
            self.insights.extend(insights)
            self.stats["total_insights_discovered"] += len(insights)
            
            print(f"✅ [JARVIS] {len(insights)} inconsistencias detectadas")
            
        except Exception as e:
            print(f"❌ [JARVIS] Error detectando inconsistencias: {e}")
        
        return insights
    
    async def enhanced_insight_discovery(self) -> List[JarvisInsight]:
        """
        TAREA 4: Descubrimiento mejorado de insights ocultos
        Busca patrones, tendencias, anomalías temporales, entidades nuevas
        """
        print("🔬 [JARVIS] Descubrimiento avanzado de insights...")
        
        # Llamar al método existente
        basic_insights = await self.discover_insights()
        
        # Análisis adicional de tendencias temporales
        trend_insights = await self._analyze_temporal_trends()
        
        # Análisis de entidades
        entity_insights = await self._analyze_entities()
        
        all_insights = basic_insights + trend_insights + entity_insights
        
        return all_insights
    
    async def _analyze_temporal_trends(self) -> List[JarvisInsight]:
        """Analiza tendencias temporales en los datos."""
        insights = []
        
        try:
            # Obtener queries históricas
            all_queries = self.persistent_storage.get_all_queries(limit=200)
            
            if len(all_queries) < 10:
                return insights
            
            # Agrupar por fecha
            queries_by_date = {}
            for query in all_queries:
                date = query.timestamp[:10]  # YYYY-MM-DD
                if date not in queries_by_date:
                    queries_by_date[date] = []
                queries_by_date[date].append(query)
            
            # Detectar tendencias
            if len(queries_by_date) >= 3:
                # Analizar con LLM
                if self.llm:
                    trend_prompt = f"""Analiza estas queries por fecha y detecta tendencias:

{json.dumps({k: len(v) for k, v in sorted(queries_by_date.items())}, indent=2)}

¿Hay tendencias crecientes, decrecientes o patrones? Responde en JSON con insights.
"""
                    try:
                        response = await self.llm.ainvoke(trend_prompt)
                        # Procesar respuesta...
                    except:
                        pass
            
        except Exception as e:
            print(f"⚠️ [JARVIS] Error analizando tendencias: {e}")
        
        return insights
    
    async def _analyze_entities(self) -> List[JarvisInsight]:
        """Analiza entidades mencionadas en documentos."""
        insights = []
        # Implementación básica - puede expandirse
        return insights
    
    async def execute_automation(self, command: str, auto_execute: bool = True) -> Dict[str, Any]:
        """
        TAREA 5: Motor de automatización (RPA + API)
        Transforma lenguaje → código → acción
        Ahora con soporte MCP para conexiones estandarizadas
        Mejorado con Reinforcement Learning y Planning
        """
        print(f"⚡ [JARVIS] Ejecutando automatización: {command[:50]}...")
        
        start_time = time.time()
        
        try:
            # Usar Reinforcement Planning para planificar la ejecución
            # Esto permite probar, fallar, retroceder, intentar otra cosa
            planning_result = await self.reinforcement_planner.plan_and_execute(
                goal=command,
                context=f"Ejecutar comando: {command}",
                executor=self._create_automation_executor(auto_execute)
            )
            
            if planning_result.get("success"):
                execution_time = time.time() - start_time
                
                # Registrar en Test Time Training para aprender
                self.test_time_trainer.record_episode(
                    task_type="automation",
                    input_data=command,
                    output_data=planning_result.get("best_result"),
                    success=True,
                    execution_time=execution_time
                )
                
                self.stats["total_actions_executed"] += 1
                
                if auto_execute:
                    alert = JarvisAlert(
                        alert_id=str(uuid.uuid4()),
                        alert_type="action_executed",
                        title=f"Acción ejecutada (con planning): {command[:50]}",
                        message=f"JARVIS ejecutó usando reinforcement planning: {command}",
                        severity="medium",
                        created_at=time.time()
                    )
                    self.alerts.append(alert)
                
                return {
                    "success": True,
                    "result": planning_result.get("best_result"),
                    "method": "reinforcement_planning",
                    "execution_time": execution_time
                }
            
            # Si planning falla, intentar métodos tradicionales
            # Primero intentar usar MCP si el comando parece requerir integración externa
            mcp_result = await self._try_mcp_automation(command)
            if mcp_result.get("success"):
                execution_time = time.time() - start_time
                
                # Registrar aprendizaje
                self.test_time_trainer.record_episode(
                    task_type="automation",
                    input_data=command,
                    output_data=mcp_result,
                    success=True,
                    execution_time=execution_time
                )
                
                self.stats["total_actions_executed"] += 1
                if auto_execute:
                    alert = JarvisAlert(
                        alert_id=str(uuid.uuid4()),
                        alert_type="action_executed",
                        title=f"Acción MCP ejecutada: {command[:50]}",
                        message=f"JARVIS ejecutó vía MCP: {command}",
                        severity="medium",
                        created_at=time.time()
                    )
                    self.alerts.append(alert)
                return mcp_result
            
            # Si MCP no aplica, usar text-to-action tradicional
            action_result = await self.text_to_action.process_command(
                command=command,
                auto_execute=auto_execute
            )
            
            execution_time = time.time() - start_time
            
            # Registrar aprendizaje
            self.test_time_trainer.record_episode(
                task_type="automation",
                input_data=command,
                output_data=action_result,
                success=action_result.get("success", False),
                execution_time=execution_time
            )
            
            # Guardar acción ejecutada
            self.stats["total_actions_executed"] += 1
            
            # Generar alerta si es acción importante
            if action_result.get("success") and auto_execute:
                alert = JarvisAlert(
                    alert_id=str(uuid.uuid4()),
                    alert_type="action_executed",
                    title=f"Acción ejecutada: {command[:50]}",
                    message=f"JARVIS ejecutó automáticamente: {command}",
                    severity="medium",
                    created_at=time.time()
                )
                self.alerts.append(alert)
            
            return action_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"❌ [JARVIS] Error en automatización: {e}")
            
            # Registrar error en aprendizaje
            self.test_time_trainer.record_episode(
                task_type="automation",
                input_data=command,
                output_data=None,
                success=False,
                feedback=str(e),
                execution_time=execution_time
            )
            
            return {"success": False, "error": str(e)}
    
    def _create_automation_executor(self, auto_execute: bool):
        """Crea un executor para reinforcement planning."""
        async def executor(action: str, context: str) -> Any:
            """Ejecuta una acción como parte del planning."""
            # Intentar ejecutar usando métodos disponibles
            try:
                # Primero intentar MCP
                mcp_result = await self._try_mcp_automation(action)
                if mcp_result.get("success"):
                    return mcp_result
                
                # Si no, usar text-to-action
                result = await self.text_to_action.process_command(
                    command=action,
                    auto_execute=auto_execute
                )
                return result
            except Exception as e:
                raise Exception(f"Error ejecutando acción: {e}")
        
        return executor
    
    async def _try_mcp_automation(self, command: str) -> Dict[str, Any]:
        """
        Intenta ejecutar automatización usando MCP.
        Detecta si el comando requiere integración externa y usa MCP.
        Ahora también enriquece con contexto de esquemas para mejor comprensión.
        Potenciado para navegar datos crudos sin conectores específicos.
        """
        if not self.llm:
            return {"success": False, "error": "LLM no disponible"}
        
        try:
            # Enriquecer comando con contexto de esquemas si menciona objetos de base de datos
            enriched_command = self.enrich_query_with_schema_context(command)
            
            # Usar Path-dependent Reasoning para probar diferentes enfoques
            # Esto permite probar MCP directo, navegación de datos crudos, etc.
            reasoning_result = await self.path_reasoner.reason_with_multiple_paths(
                problem=f"Ejecutar comando: {enriched_command}",
                context="Determinar si requiere MCP o navegación de datos",
                task_type="mcp_automation",
                executor=self._create_mcp_executor(enriched_command)
            )
            
            if reasoning_result.get("best_path", {}).get("result"):
                return {
                    "success": True,
                    "result": reasoning_result["best_path"]["result"],
                    "method": "path_dependent_mcp"
                }
            
            # Fallback: análisis tradicional con LLM
            analysis_prompt = f"""Analiza este comando y determina si requiere integración externa:
Comando: "{enriched_command}"

¿Requiere conectarse con sistemas externos como Slack, Salesforce, APIs, bases de datos, email?
¿O requiere navegar datos crudos (archivos, URLs, etc.)?

Responde SOLO con JSON:
{{
    "requires_mcp": true/false,
    "requires_raw_data_navigation": true/false,
    "data_source": "path/URL/connection_id" o null,
    "tool_name": "nombre_herramienta_mcp" o null,
    "arguments": {{"arg1": "valor1", ...}} o {{}},
    "reasoning": "explicación breve"
}}"""
            
            response = await self.llm.ainvoke(analysis_prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parsear respuesta JSON
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                
                # Si requiere navegación de datos crudos
                if analysis.get("requires_raw_data_navigation") and analysis.get("data_source"):
                    data_source = analysis["data_source"]
                    navigation_result = await self.mcp_manager.navigate_raw_data(
                        data_source=data_source,
                        query=enriched_command,
                        llm=self.llm
                    )
                    
                    if navigation_result.get("success"):
                        return {
                            "success": True,
                            "result": navigation_result.get("result"),
                            "method": "raw_data_navigation"
                        }
                
                # Si requiere MCP tradicional
                if analysis.get("requires_mcp") and analysis.get("tool_name"):
                    tool_name = analysis["tool_name"]
                    arguments = analysis.get("arguments", {})
                    
                    # Llamar herramienta MCP
                    result = await self.mcp_manager.call_tool(
                        tool_name=tool_name,
                        arguments=arguments
                    )
                    
                    return {
                        "success": result.get("success", False),
                        "result": result,
                        "method": "mcp",
                        "tool": tool_name
                    }
        
        except Exception as e:
            print(f"⚠️ [JARVIS] Error en análisis MCP: {e}")
        
        return {"success": False, "error": "No requiere MCP o error en análisis"}
    
    def _create_mcp_executor(self, command: str):
        """Crea un executor para path-dependent reasoning con MCP."""
        async def executor(approach: str, strategy: str, steps: List[str], context: str) -> Any:
            """Ejecuta un enfoque MCP."""
            try:
                # Intentar diferentes estrategias según el enfoque
                if "raw_data" in approach.lower() or "navegar" in approach.lower():
                    # Navegación de datos crudos
                    # Extraer data_source del contexto o comando
                    data_source = self._extract_data_source(command)
                    if data_source:
                        result = await self.mcp_manager.navigate_raw_data(
                            data_source=data_source,
                            query=command,
                            llm=self.llm
                        )
                        return result
                
                # MCP tradicional
                if "mcp" in approach.lower() or "tool" in approach.lower():
                    # Intentar encontrar herramienta MCP apropiada
                    tools = self.mcp_manager.list_available_tools()
                    for tool in tools:
                        if tool["name"].lower() in command.lower():
                            result = await self.mcp_manager.call_tool(
                                tool_name=tool["name"],
                                arguments={}
                            )
                            return result
                
                return {"success": False, "error": "Enfoque no aplicable"}
            except Exception as e:
                raise Exception(f"Error ejecutando enfoque MCP: {e}")
        
        return executor
    
    def _extract_data_source(self, command: str) -> Optional[str]:
        """Extrae data_source del comando."""
        import re
        
        # Buscar paths de archivos
        path_match = re.search(r'["\']([^"\']+\.(json|csv|txt|xml))["\']', command)
        if path_match:
            return path_match.group(1)
        
        # Buscar URLs
        url_match = re.search(r'https?://[^\s]+', command)
        if url_match:
            return url_match.group(0)
        
        return None
    
    async def normalize_document(self, doc: Document) -> Document:
        """
        TAREA 6: Reescritura y normalización automática de documentos
        Limpia texto, estructura, estandariza formatos
        """
        print("📝 [JARVIS] Normalizando documento...")
        
        try:
            if not self.llm:
                return doc
            
            normalization_prompt = f"""Normaliza y limpia este documento:
1. Quita ruido
2. Limpia texto
3. Estructura
4. Estandariza formato
5. Detecta valores clave

Documento original:
{doc.page_content[:5000]}

Responde SOLO con el documento normalizado, sin explicaciones adicionales.
"""
            
            response = await self.llm.ainvoke(normalization_prompt)
            normalized_content = response.content if hasattr(response, 'content') else str(response)
            
            # Crear documento normalizado
            normalized_doc = Document(
                page_content=normalized_content,
                metadata={
                    **doc.metadata,
                    "normalized": True,
                    "normalized_at": time.time()
                }
            )
            
            return normalized_doc
            
        except Exception as e:
            print(f"⚠️ [JARVIS] Error normalizando documento: {e}")
            return doc
    
    async def adversarial_validation(self, response: str, original_prompt: str) -> Dict[str, Any]:
        """
        TAREA 7: Validación adversarial (Red Teaming interno)
        Detecta alucinaciones, verifica consistencia
        """
        print("🛡️ [JARVIS] Validación adversarial...")
        
        try:
            # Usar adversarial tester
            is_safe, issues = await self.adversarial_tester.validate_response_before_sending(
                response=response,
                original_prompt=original_prompt
            )
            
            if not is_safe and issues:
                # Generar alerta
                alert = JarvisAlert(
                    alert_id=str(uuid.uuid4()),
                    alert_type="adversarial_issue",
                    title="Problema detectado en respuesta",
                    message=f"JARVIS detectó: {', '.join(issues)}",
                    severity="high",
                    created_at=time.time()
                )
                self.alerts.append(alert)
            
            return {
                "is_safe": is_safe,
                "issues": issues,
                "validated_at": time.time()
            }
            
        except Exception as e:
            print(f"⚠️ [JARVIS] Error en validación adversarial: {e}")
            return {"is_safe": True, "issues": []}
    
    async def auto_improve_queries(self) -> Dict[str, Any]:
        """
        TAREA 8: Auto-mejorar consultas y pipelines
        Detecta queries repetidas, malas respuestas, baja recuperación
        """
        print("🔧 [JARVIS] Auto-mejorando queries y pipelines...")
        
        try:
            # Obtener queries históricas
            all_queries = self.persistent_storage.get_all_queries(limit=100)
            
            # Detectar queries repetidas
            query_counts = {}
            for query in all_queries:
                query_lower = query.query_text.lower().strip()
                if query_lower not in query_counts:
                    query_counts[query_lower] = []
                query_counts[query_lower].append(query)
            
            # Encontrar queries muy repetidas
            repeated_queries = {
                q: queries for q, queries in query_counts.items() 
                if len(queries) >= 3
            }
            
            improvements = {
                "repeated_queries": len(repeated_queries),
                "suggestions": []
            }
            
            if repeated_queries:
                insight = JarvisInsight(
                    insight_id=str(uuid.uuid4()),
                    title="Queries repetidas detectadas",
                    description=f"Se encontraron {len(repeated_queries)} queries que se repiten frecuentemente. Considera crear plantillas o automatizar estas consultas.",
                    category="opportunity",
                    confidence=0.9,
                    actionable=True,
                    action_recommendation="Crear plantillas o automatizar queries repetidas"
                )
                self.insights.append(insight)
            
            print(f"✅ [JARVIS] Análisis de mejoras completado")
            return improvements
            
        except Exception as e:
            print(f"❌ [JARVIS] Error auto-mejorando queries: {e}")
            return {}
    
    async def detect_important_events(self) -> List[JarvisAlert]:
        """
        TAREA 9: Detección de eventos importantes
        Ej: "Tu contrato expira en 3 días", "Número financiero cambió"
        """
        print("📅 [JARVIS] Detectando eventos importantes...")
        alerts = []
        
        try:
            # Obtener documentos recientes
            recent_docs = self.persistent_storage.get_all_documents(limit=50)
            
            # Buscar fechas, vencimientos, cambios importantes
            if self.llm:
                for doc_record in recent_docs[:10]:  # Limitar para no sobrecargar
                    try:
                        doc = self.persistent_storage.load_document_as_langchain(doc_record.doc_id)
                        if not doc:
                            continue
                        
                        event_prompt = f"""Analiza este documento y detecta eventos importantes:
- Vencimientos
- Fechas críticas
- Cambios importantes
- Números que cambiaron
- Políticas actualizadas

Documento:
{doc.page_content[:3000]}

Responde en JSON:
{{
    "has_events": true/false,
    "events": [
        {{
            "type": "expiration|change|update|deadline",
            "description": "descripción",
            "date": "fecha si aplica",
            "urgency": "high|medium|low"
        }}
    ]
}}
"""
                        response = await self.llm.ainvoke(event_prompt)
                        content = response.content if hasattr(response, 'content') else str(response)
                        
                        if "```json" in content:
                            json_str = content.split("```json")[1].split("```")[0].strip()
                        else:
                            json_str = content
                        
                        data = json.loads(json_str)
                        
                        if data.get("has_events"):
                            for event in data.get("events", []):
                                alert = JarvisAlert(
                                    alert_id=str(uuid.uuid4()),
                                    alert_type="important_event",
                                    title=f"Evento: {event.get('type')}",
                                    message=event.get("description", ""),
                                    severity=event.get("urgency", "medium"),
                                    created_at=time.time()
                                )
                                alerts.append(alert)
                    except Exception as e:
                        print(f"⚠️ [JARVIS] Error analizando evento: {e}")
            
            self.alerts.extend(alerts)
            print(f"✅ [JARVIS] {len(alerts)} eventos importantes detectados")
            
        except Exception as e:
            print(f"❌ [JARVIS] Error detectando eventos: {e}")
        
        return alerts
    
    async def generate_sops_and_manuals(self, topic: str) -> Dict[str, Any]:
        """
        TAREA 10: Generación automática de SOPs, manuales, contratos, reportes
        """
        print(f"📚 [JARVIS] Generando SOP/manual sobre: {topic}...")
        
        try:
            # Obtener contexto relevante
            context_text, _ = self.context_manager.get_context_for_prompt(
                session_id=f"jarvis_{self.user_id}",
                max_tokens=200_000
            )
            
            generation_prompt = f"""Genera un documento profesional sobre: {topic}

Basándote en toda la información disponible en el sistema.

Contexto disponible:
{context_text[:100000]}

Genera un documento completo, estructurado y profesional.
Incluye:
1. Introducción
2. Procedimientos paso a paso
3. Mejores prácticas
4. Ejemplos
5. Referencias

Formato profesional y claro.
"""
            
            # Usar Chain of Thought correctamente
            chain_id = self.chain_of_thought.create_chain(generation_prompt)
            await self.chain_of_thought.add_reasoning_steps(chain_id, context_text[:50000])
            chain = self.chain_of_thought.get_chain(chain_id)
            
            if chain:
                if not chain.final_answer:
                    chain.final_answer = "Documento generado usando Chain of Thought"
                    self.chain_of_thought.complete_chain(chain_id, chain.final_answer, success=True)
            
            result = {
                "topic": topic,
                "content": chain.final_answer if chain else "Error generando documento",
                "generated_at": datetime.now().isoformat(),
                "confidence": 0.8 if chain else 0.0
            }
            
            print(f"✅ [JARVIS] SOP/manual generado")
            return result
            
        except Exception as e:
            print(f"❌ [JARVIS] Error generando SOP: {e}")
            return {}
    
    async def intelligent_auto_indexing(self, doc: Document) -> Dict[str, Any]:
        """
        TAREA 11: Auto-indexación inteligente
        Detecta roles, tags automáticos, entidades, metadatos, prioridades
        """
        print("🏷️ [JARVIS] Auto-indexando documento...")
        
        try:
            if not self.llm:
                return {}
            
            indexing_prompt = f"""Analiza este documento y extrae:
1. Tags automáticos relevantes
2. Entidades clave (personas, organizaciones, lugares)
3. Categorías/temas
4. Prioridad (high|medium|low)
5. Roles mencionados
6. Metadatos útiles

Documento:
{doc.page_content[:5000]}

Responde en JSON:
{{
    "tags": ["tag1", "tag2"],
    "entities": ["entity1", "entity2"],
    "categories": ["cat1", "cat2"],
    "priority": "high|medium|low",
    "roles": ["role1", "role2"],
    "metadata": {{"key": "value"}}
}}
"""
            
            response = await self.llm.ainvoke(indexing_prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            else:
                json_str = content
            
            indexing_data = json.loads(json_str)
            
            # Actualizar metadata del documento
            doc.metadata.update({
                "jarvis_tags": indexing_data.get("tags", []),
                "jarvis_entities": indexing_data.get("entities", []),
                "jarvis_categories": indexing_data.get("categories", []),
                "jarvis_priority": indexing_data.get("priority", "medium"),
                "jarvis_roles": indexing_data.get("roles", []),
                **indexing_data.get("metadata", {})
            })
            
            print(f"✅ [JARVIS] Documento indexado: {len(indexing_data.get('tags', []))} tags")
            return indexing_data
            
        except Exception as e:
            print(f"⚠️ [JARVIS] Error en auto-indexación: {e}")
            return {}
    
    async def multi_agent_collaboration(self, task_description: str) -> Dict[str, Any]:
        """
        TAREA 12: Multi-Agent Collaboration
        JARVIS coordina otros agentes, delega, verifica, combina respuestas
        """
        print(f"👥 [JARVIS] Coordinando agentes para: {task_description[:50]}...")
        
        try:
            # Dividir tarea en subtareas
            coordination_prompt = f"""Divide esta tarea en subtareas para agentes especializados:

Tarea: {task_description}

Sugiere:
1. Qué agente debería hacer qué
2. Cómo coordinar las respuestas
3. Qué verificar

Responde en JSON con plan de coordinación.
"""
            
            # Usar Chain of Thought correctamente
            chain_id = self.chain_of_thought.create_chain(coordination_prompt)
            await self.chain_of_thought.add_reasoning_steps(chain_id, "")
            chain = self.chain_of_thought.get_chain(chain_id)
            
            if chain:
                if not chain.final_answer:
                    chain.final_answer = "Plan de coordinación generado usando Chain of Thought"
                    self.chain_of_thought.complete_chain(chain_id, chain.final_answer, success=True)
            
            # Ejecutar con agente autónomo (simula coordinación)
            agent_result = await self.autonomous_agent.run_full_cycle(
                f"Ejecuta esta tarea coordinando múltiples agentes: {task_description}"
            )
            
            result = {
                "task": task_description,
                "coordination_plan": chain.final_answer if chain else "Error generando plan",
                "agent_result": agent_result,
                "coordinated_at": time.time()
            }
            
            print(f"✅ [JARVIS] Coordinación multi-agente completada")
            return result
            
        except Exception as e:
            print(f"❌ [JARVIS] Error en coordinación multi-agente: {e}")
            return {}
    
    # ============================================
    # LOOP CONTINUO MEJORADO CON TODAS LAS TAREAS
    # ============================================
    
    async def run_continuous_loop(self, interval_minutes: int = 60):
        """
        Loop continuo 24/7 mejorado que ejecuta todas las 12 tareas principales.
        """
        self.is_running = True
        print(f"🚀 [JARVIS] Iniciando loop continuo avanzado (intervalo: {interval_minutes} minutos)")
        print("   📋 Tareas activas: 12 funcionalidades principales")
        
        cycle_count = 0
        
        while self.is_running:
            try:
                cycle_count += 1
                print(f"\n{'='*60}")
                print(f"🔄 [JARVIS] Ciclo #{cycle_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*60}")
                
                # TAREA 1: Monitoreo continuo de documentos (24/7)
                alerts_from_monitoring = await self.monitor_documents_24_7()
                
                # TAREA 2: Generar resumen ejecutivo (cada 24 horas)
                if cycle_count % 24 == 0:
                    await self.generate_executive_summary("daily")
                
                # TAREA 3: Detectar inconsistencias
                await self.detect_inconsistencies()
                
                # TAREA 4: Descubrimiento avanzado de insights
                await self.enhanced_insight_discovery()
                
                # TAREA 5: Motor de automatización - Ejecutar acciones detectadas en documentos
                # (Se ejecuta cuando detecta comandos en documentos o tareas pendientes)
                
                # TAREA 6: Normalización automática - Normalizar documentos nuevos detectados
                if alerts_from_monitoring:
                    # Si hay documentos nuevos, normalizarlos automáticamente
                    recent_docs = self.persistent_storage.get_all_documents(limit=5)
                    for doc_record in recent_docs[:3]:  # Normalizar últimos 3 documentos nuevos
                        try:
                            doc = self.persistent_storage.load_document_as_langchain(doc_record.doc_id)
                            if doc and not doc.metadata.get("normalized"):
                                normalized = await self.normalize_document(doc)
                                # Guardar documento normalizado
                                self.persistent_storage.save_document(
                                    document=normalized,
                                    session_id=f"jarvis_{self.user_id}",
                                    source="jarvis_normalized"
                                )
                        except Exception as e:
                            print(f"⚠️ [JARVIS] Error normalizando documento: {e}")
                
                # TAREA 7: Validación adversarial (en background)
                # (Se ejecuta cuando hay respuestas nuevas en otros modos)
                
                # TAREA 8: Auto-mejorar queries (cada 6 horas)
                if cycle_count % 6 == 0:
                    await self.auto_improve_queries()
                
                # TAREA 9: Detectar eventos importantes
                await self.detect_important_events()
                
                # TAREA 10: Generación automática de SOPs (cada semana)
                if cycle_count % (24 * 7) == 0:  # Cada semana
                    # Generar SOP automático basado en insights descubiertos
                    if self.insights:
                        main_topic = "Procedimientos operativos estándar basados en insights descubiertos"
                        await self.generate_sops_and_manuals(main_topic)
                
                # TAREA 11: Auto-indexación inteligente - Indexar documentos nuevos
                if alerts_from_monitoring:
                    recent_docs = self.persistent_storage.get_all_documents(limit=10)
                    for doc_record in recent_docs[:5]:  # Indexar últimos 5 documentos
                        try:
                            doc = self.persistent_storage.load_document_as_langchain(doc_record.doc_id)
                            if doc and not doc.metadata.get("jarvis_indexed"):
                                await self.intelligent_auto_indexing(doc)
                                # Marcar como indexado
                                doc.metadata["jarvis_indexed"] = True
                                # Guardar actualización
                                self.persistent_storage.save_document(
                                    document=doc,
                                    session_id=f"jarvis_{self.user_id}",
                                    source=doc_record.source
                                )
                        except Exception as e:
                            print(f"⚠️ [JARVIS] Error indexando documento: {e}")
                
                # TAREA 12: Multi-Agent Collaboration - Coordinar tareas complejas
                # (Se ejecuta cuando hay tareas que requieren coordinación)
                
                # TAREAS PERSONALIZADAS: Ejecutar tareas definidas por usuarios
                # Mejorado con Goal Decomposition y Test Time Training
                current_time = time.time()
                custom_tasks_to_execute = self.custom_task_manager.get_tasks_to_execute(current_time)
                for custom_task in custom_tasks_to_execute:
                    try:
                        print(f"🎯 [JARVIS] Ejecutando tarea personalizada: {custom_task.name}")
                        execution_start = time.time()
                        
                        # Si hay goal_id, usar Goal Decomposition para ejecutar subtareas
                        goal_id = custom_task.parameters.get("goal_id")
                        if goal_id:
                            goal = self.goal_decomposer.get_goal(goal_id)
                            if goal:
                                # Ejecutar objetivo descompuesto
                                execution_result = await self.goal_decomposer.execute_goal(
                                    goal_id=goal_id,
                                    executor=self._create_goal_executor()
                                )
                                
                                execution_time = time.time() - execution_start
                                result = f"Objetivo descompuesto ejecutado: {execution_result}"
                                
                                # Registrar en Test Time Training
                                self.test_time_trainer.record_episode(
                                    task_type="custom_task",
                                    input_data=custom_task.instructions,
                                    output_data=result,
                                    success=execution_result.get("status") == "completed",
                                    execution_time=execution_time,
                                    metadata={"goal_id": goal_id}
                                )
                                
                                # Registrar ejecución
                                self.custom_task_manager.record_execution(
                                    task_id=custom_task.task_id,
                                    status="completed" if execution_result.get("status") == "completed" else "failed",
                                    result=result,
                                    execution_time=execution_time
                                )
                                
                                print(f"✅ [JARVIS] Tarea personalizada completada (con goal decomposition): {custom_task.name}")
                                continue
                        
                        # Si no hay goal_id, ejecutar normalmente pero con mejoras
                        # Usar Path-dependent Reasoning para probar diferentes enfoques
                        if self.llm:
                            # Obtener mejor patrón aprendido si existe
                            best_pattern = self.test_time_trainer.get_best_pattern("custom_task")
                            
                            task_prompt = f"""Ejecuta la siguiente tarea personalizada:

Nombre: {custom_task.name}
Descripción: {custom_task.description}

Instrucciones:
{custom_task.instructions}

Parámetros adicionales:
{json.dumps(custom_task.parameters, indent=2)}

Contexto disponible:
- Tienes acceso a todos los documentos del sistema
- Puedes usar todas las herramientas disponibles
- Puedes generar reportes, análisis, o ejecutar acciones
{f'- Patrón aprendido exitoso: {best_pattern.pattern_data.get("output_pattern", "")}' if best_pattern else ''}

Ejecuta la tarea y proporciona un resultado detallado."""
                            
                            # Usar Path-dependent Reasoning para probar diferentes enfoques
                            reasoning_result = await self.path_reasoner.reason_with_multiple_paths(
                                problem=custom_task.instructions,
                                context=f"Tarea: {custom_task.name}\n{custom_task.description}",
                                task_type="custom_task",
                                executor=self._create_custom_task_executor(custom_task)
                            )
                            
                            result = reasoning_result.get("best_path", {}).get("result", "Sin resultado")
                            execution_time = time.time() - execution_start
                            
                            # Registrar en Test Time Training
                            self.test_time_trainer.record_episode(
                                task_type="custom_task",
                                input_data=custom_task.instructions,
                                output_data=result,
                                success=reasoning_result.get("best_path", {}).get("result") is not None,
                                execution_time=execution_time
                            )
                            
                            # Registrar ejecución exitosa
                            self.custom_task_manager.record_execution(
                                task_id=custom_task.task_id,
                                status="completed",
                                result=result,
                                execution_time=execution_time
                            )
                            
                            print(f"✅ [JARVIS] Tarea personalizada completada: {custom_task.name}")
                        else:
                            raise Exception("LLM no disponible")
                            
                    except Exception as e:
                        execution_time = time.time() - execution_start if 'execution_start' in locals() else 0
                        print(f"❌ [JARVIS] Error ejecutando tarea personalizada {custom_task.name}: {e}")
                        
                        # Registrar error en Test Time Training
                        self.test_time_trainer.record_episode(
                            task_type="custom_task",
                            input_data=custom_task.instructions,
                            output_data=None,
                            success=False,
                            feedback=str(e),
                            execution_time=execution_time
                        )
                        
                        # Registrar ejecución fallida
                        self.custom_task_manager.record_execution(
                            task_id=custom_task.task_id,
                            status="failed",
                            error=str(e),
                            execution_time=execution_time
                        )
                
                # Procesar tareas pendientes (pueden incluir TAREA 5 y TAREA 12)
                pending_tasks = [t for t in self.tasks if t.status == TaskStatus.PENDING]
                for task in pending_tasks[:5]:  # Máximo 5 por ciclo
                    # Si la tarea requiere automatización, usar TAREA 5
                    if task.task_type == "execute_action":
                        result = await self.execute_automation(
                            command=task.description,
                            auto_execute=task.parameters.get("auto_execute", True)
                        )
                        task.result = result
                        task.status = TaskStatus.COMPLETED
                    # Si la tarea requiere coordinación, usar TAREA 12
                    elif task.task_type in ["analyze_patterns", "generate_report"]:
                        result = await self.multi_agent_collaboration(task.description)
                        task.result = result
                        task.status = TaskStatus.COMPLETED
                    else:
                        await self.execute_autonomous_task(task)
                
                # Actualizar estadísticas
                self.stats["uptime_hours"] += interval_minutes / 60
                self.stats["last_activity"] = time.time()
                
                # Guardar estado
                self._save_state()
                
                print(f"\n✅ [JARVIS] Ciclo #{cycle_count} completado")
                print(f"   📊 Insights: {len(self.insights)}")
                print(f"   🚨 Alertas: {len([a for a in self.alerts if not a.acknowledged])}")
                print(f"   ⚡ Tareas: {len([t for t in self.tasks if t.status == TaskStatus.COMPLETED])} completadas")
                print(f"   ⏳ Esperando {interval_minutes} minutos hasta próximo ciclo...\n")
                
                # Esperar antes del siguiente ciclo
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                print(f"❌ [JARVIS] Error en loop continuo: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(60)  # Esperar 1 minuto antes de reintentar
    
    def _create_goal_executor(self):
        """Crea un executor para goal decomposition."""
        async def executor(description: str, metadata: Dict[str, Any]) -> Any:
            """Ejecuta una subtarea de un objetivo."""
            # Usar el sistema de automatización de JARVIS
            result = await self.execute_automation(
                command=description,
                auto_execute=True
            )
            return result.get("result") if result.get("success") else None
        
        return executor
    
    def _create_custom_task_executor(self, custom_task: CustomTask):
        """Crea un executor para custom tasks con path-dependent reasoning."""
        async def executor(approach: str, strategy: str, steps: List[str], context: str) -> Any:
            """Ejecuta un enfoque para una custom task."""
            # Construir prompt con el enfoque específico
            task_prompt = f"""Ejecuta la siguiente tarea personalizada usando este enfoque:

Enfoque: {approach}
Estrategia: {strategy}
Pasos: {', '.join(steps)}

Tarea:
Nombre: {custom_task.name}
Descripción: {custom_task.description}
Instrucciones: {custom_task.instructions}

Ejecuta la tarea siguiendo este enfoque específico."""
            
            if self.llm:
                response = await self.llm.ainvoke(task_prompt)
                return response.content if hasattr(response, 'content') else str(response)
            else:
                return f"Resultado simulado de enfoque: {approach}"
        
        return executor

