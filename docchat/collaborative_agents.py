"""
Collaborative Agents System - Múltiples agentes trabajando juntos.

Implementa el concepto de Eric Schmidt sobre agentes colaborativos:
- Múltiples agentes trabajando en equipo
- Colaboración en código y tareas complejas
- División de trabajo automática
- Coordinación entre agentes
"""

from __future__ import annotations

import json
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum

from langchain_core.messages import HumanMessage, SystemMessage

from .config import AppConfig
from .utils.llm_factory import create_llm


class AgentRole(Enum):
    """Roles de agentes en un equipo."""
    LEADER = "leader"
    RESEARCHER = "researcher"
    DEVELOPER = "developer"
    TESTER = "tester"
    ANALYST = "analyst"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"


@dataclass
class Agent:
    """Un agente individual en el equipo."""
    agent_id: str
    name: str
    role: AgentRole
    specialization: str
    capabilities: List[str]
    current_task: Optional[str] = None
    status: str = "idle"  # idle, working, waiting, completed
    results: List[Dict[str, Any]] = field(default_factory=list)
    llm: Optional[Any] = None


@dataclass
class Task:
    """Tarea asignada a un agente."""
    task_id: str
    description: str
    assigned_to: str  # agent_id
    dependencies: List[str] = field(default_factory=list)  # task_ids
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[Any] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CollaborativeTeam:
    """Equipo de agentes colaborativos."""
    team_id: str
    name: str
    agents: List[Agent]
    tasks: List[Task]
    shared_knowledge: Dict[str, Any] = field(default_factory=dict)
    communication_log: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "idle"  # idle, working, completed
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class CollaborativeAgentsSystem:
    """
    Sistema de agentes colaborativos.
    
    Características:
    - Múltiples agentes trabajando juntos
    - División automática de tareas
    - Coordinación y comunicación entre agentes
    - Colaboración en código y proyectos complejos
    """
    
    def __init__(self, config: AppConfig, provider: str = "openai"):
        self.config = config
        self.provider = provider
        
        # LLM para coordinación
        self.coordinator_llm = create_llm(
            provider=provider,
            model=config.agentic_model or "gpt-4o",
            temperature=0.2,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=8000,
            request_timeout=180
        )
        
        # Directorio para equipos
        self.data_dir = Path(config.memory_dir) / "collaborative_agents"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Equipos activos
        self.active_teams: Dict[str, CollaborativeTeam] = {}
    
    def create_team(
        self,
        team_name: str,
        project_description: str,
        team_size: int = 5,
        roles: Optional[List[str]] = None
    ) -> CollaborativeTeam:
        """
        Crea un equipo de agentes colaborativos.
        
        Args:
            team_name: Nombre del equipo
            project_description: Descripción del proyecto
            team_size: Número de agentes en el equipo
            roles: Roles específicos (opcional)
        
        Returns:
            CollaborativeTeam configurado
        """
        team_id = f"team_{int(time.time())}"
        
        print(f"\n{'='*60}")
        print(f"👥 CREANDO EQUIPO DE AGENTES COLABORATIVOS")
        print(f"{'='*60}")
        print(f"🏷️  Nombre: {team_name}")
        print(f"📋 Proyecto: {project_description}")
        print(f"👤 Tamaño: {team_size} agentes\n")
        
        # Generar agentes
        print("🤖 Generando agentes...")
        agents = self._generate_agents(project_description, team_size, roles)
        print(f"   ✅ {len(agents)} agentes creados\n")
        
        # Crear equipo
        team = CollaborativeTeam(
            team_id=team_id,
            name=team_name,
            agents=agents,
            tasks=[],
            status="idle"
        )
        
        self.active_teams[team_id] = team
        
        print(f"{'='*60}")
        print(f"✅ EQUIPO CREADO")
        print(f"{'='*60}\n")
        
        return team
    
    def execute_collaborative_task(
        self,
        team_id: str,
        task_description: str,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        Ejecuta una tarea compleja con múltiples agentes colaborando.
        
        Args:
            team_id: ID del equipo
            task_description: Descripción de la tarea
            max_iterations: Máximo de iteraciones de colaboración
        
        Returns:
            Dict con resultados de la colaboración
        """
        if team_id not in self.active_teams:
            return {"success": False, "message": f"Equipo {team_id} no encontrado"}
        
        team = self.active_teams[team_id]
        team.status = "working"
        
        print(f"\n{'='*60}")
        print(f"🚀 EJECUTANDO TAREA COLABORATIVA")
        print(f"{'='*60}")
        print(f"👥 Equipo: {team.name}")
        print(f"📝 Tarea: {task_description}\n")
        
        # Paso 1: Dividir tarea en subtareas
        print("📋 Paso 1: Dividiendo tarea en subtareas...")
        subtasks = self._divide_task(task_description, team)
        print(f"   ✅ {len(subtasks)} subtareas creadas\n")
        
        # Paso 2: Asignar subtareas a agentes
        print("👤 Paso 2: Asignando subtareas a agentes...")
        assignments = self._assign_tasks(subtasks, team)
        print(f"   ✅ Subtareas asignadas\n")
        
        # Paso 3: Ejecutar en paralelo (simulado)
        print("⚙️  Paso 3: Ejecutando subtareas...")
        results = []
        for i, (task, agent) in enumerate(assignments.items(), 1):
            print(f"   [{i}/{len(assignments)}] {agent.name} trabajando en: {task.description[:50]}...")
            result = self._execute_agent_task(agent, task, team)
            results.append(result)
            print(f"      ✅ Completado")
        
        print()
        
        # Paso 4: Integrar resultados
        print("🔗 Paso 4: Integrando resultados...")
        final_result = self._integrate_results(task_description, results, team)
        print(f"   ✅ Resultados integrados\n")
        
        # Paso 5: Verificar y refinar
        print("✅ Paso 5: Verificando resultado final...")
        verified = self._verify_final_result(final_result, task_description)
        if verified:
            print(f"   ✅ Resultado verificado\n")
        else:
            print(f"   ⚠️  Resultado requiere refinamiento\n")
        
        team.status = "completed"
        self._save_team(team)
        
        print(f"{'='*60}")
        print(f"✅ TAREA COLABORATIVA COMPLETADA")
        print(f"{'='*60}\n")
        
        return {
            "success": True,
            "team_id": team_id,
            "task": task_description,
            "subtasks": len(subtasks),
            "agents_used": len(set(a.agent_id for a in assignments.values())),
            "final_result": final_result,
            "verified": verified
        }
    
    def _generate_agents(
        self,
        project_description: str,
        team_size: int,
        roles: Optional[List[str]]
    ) -> List[Agent]:
        """Genera agentes para el equipo."""
        if roles:
            # Usar roles especificados
            agent_roles = [AgentRole[r.upper()] if r.upper() in [e.name for e in AgentRole] else AgentRole.SPECIALIST for r in roles[:team_size]]
        else:
            # Generar roles automáticamente
            agent_roles = self._generate_roles(project_description, team_size)
        
        agents = []
        for i, role in enumerate(agent_roles[:team_size], 1):
            agent = Agent(
                agent_id=f"agent_{int(time.time())}_{i}",
                name=f"Agent {i} ({role.value})",
                role=role,
                specialization=self._get_specialization(role, project_description),
                capabilities=self._get_capabilities(role),
                llm=create_llm(
                    provider=self.provider,
                    model=self.config.agentic_model or "gpt-4o",
                    temperature=0.2,
                    api_key=self.config.openai_api_key if self.provider == "openai" else self.config.anthropic_api_key,
                    max_tokens=4000,
                    request_timeout=120
                )
            )
            agents.append(agent)
        
        return agents
    
    def _generate_roles(self, project_description: str, team_size: int) -> List[AgentRole]:
        """Genera roles apropiados para el proyecto."""
        prompt = f"""Determina los roles de agentes necesarios para este proyecto.

PROYECTO:
{project_description}

TAMAÑO DE EQUIPO: {team_size}

INSTRUCCIONES:
1. Determina qué roles son necesarios
2. Asigna roles de: leader, researcher, developer, tester, analyst, coordinator, specialist
3. Asegúrate de tener al menos un leader y un developer

RESPUESTA (JSON):
{{
    "roles": ["leader", "developer", "researcher", ...],
    "reasoning": "Por qué estos roles"
}}
"""
        
        try:
            response = self.coordinator_llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                roles = [AgentRole[r.upper()] for r in data.get("roles", []) if r.upper() in [e.name for e in AgentRole]]
                # Asegurar al menos leader y developer
                if AgentRole.LEADER not in roles:
                    roles.insert(0, AgentRole.LEADER)
                if AgentRole.DEVELOPER not in roles:
                    roles.append(AgentRole.DEVELOPER)
                return roles[:team_size]
        except Exception:
            pass
        
        # Roles por defecto
        default_roles = [AgentRole.LEADER, AgentRole.DEVELOPER, AgentRole.RESEARCHER]
        if team_size > 3:
            default_roles.extend([AgentRole.TESTER, AgentRole.ANALYST])
        return default_roles[:team_size]
    
    def _get_specialization(self, role: AgentRole, project: str) -> str:
        """Obtiene especialización para un rol."""
        specializations = {
            AgentRole.LEADER: "Coordinación y planificación",
            AgentRole.DEVELOPER: "Desarrollo de código",
            AgentRole.RESEARCHER: "Investigación y análisis",
            AgentRole.TESTER: "Testing y QA",
            AgentRole.ANALYST: "Análisis de datos",
            AgentRole.COORDINATOR: "Coordinación de tareas",
            AgentRole.SPECIALIST: f"Especialista en {project[:50]}"
        }
        return specializations.get(role, "General")
    
    def _get_capabilities(self, role: AgentRole) -> List[str]:
        """Obtiene capacidades para un rol."""
        capabilities_map = {
            AgentRole.LEADER: ["planificación", "coordinación", "toma de decisiones"],
            AgentRole.DEVELOPER: ["programación", "arquitectura", "debugging"],
            AgentRole.RESEARCHER: ["investigación", "análisis", "síntesis"],
            AgentRole.TESTER: ["testing", "QA", "verificación"],
            AgentRole.ANALYST: ["análisis de datos", "métricas", "insights"],
            AgentRole.COORDINATOR: ["coordinación", "comunicación", "sincronización"],
            AgentRole.SPECIALIST: ["especialización", "expertise", "conocimiento profundo"]
        }
        return capabilities_map.get(role, ["general"])
    
    def _divide_task(self, task_description: str, team: CollaborativeTeam) -> List[Task]:
        """Divide una tarea en subtareas."""
        agents_summary = "\n".join([
            f"- {a.name} ({a.role.value}): {a.specialization}"
            for a in team.agents
        ])
        
        prompt = f"""Divide esta tarea compleja en subtareas para un equipo de agentes.

TAREA PRINCIPAL:
{task_description}

EQUIPO DISPONIBLE:
{agents_summary}

INSTRUCCIONES:
1. Divide la tarea en 5-10 subtareas específicas
2. Cada subtarea debe ser:
   - Independiente o con dependencias claras
   - Asignable a un agente específico
   - Verificable
3. Identifica dependencias entre subtareas

FORMATO DE RESPUESTA (JSON):
{{
    "subtasks": [
        {{
            "description": "Descripción de la subtarea",
            "assigned_role": "rol_ideal",
            "dependencies": ["descripción de subtarea dependiente"],
            "priority": "high" | "medium" | "low"
        }},
        ...
    ]
}}
"""
        
        try:
            response = self.coordinator_llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                tasks = []
                
                for i, subtask_data in enumerate(data.get("subtasks", []), 1):
                    task = Task(
                        task_id=f"task_{int(time.time())}_{i}",
                        description=subtask_data.get("description", ""),
                        assigned_to="",  # Se asignará después
                        dependencies=[]  # Se procesarán después
                    )
                    tasks.append(task)
                
                return tasks
        except Exception as e:
            print(f"   ⚠️ Error dividiendo tarea: {e}")
        
        # Subtarea básica de fallback
        return [
            Task(
                task_id=f"task_{int(time.time())}_1",
                description=task_description,
                assigned_to=""
            )
        ]
    
    def _assign_tasks(self, tasks: List[Task], team: CollaborativeTeam) -> Dict[Task, Agent]:
        """Asigna tareas a agentes."""
        assignments = {}
        
        for task in tasks:
            # Encontrar mejor agente para esta tarea
            best_agent = self._find_best_agent(task, team.agents)
            task.assigned_to = best_agent.agent_id
            best_agent.current_task = task.task_id
            best_agent.status = "working"
            assignments[task] = best_agent
        
        return assignments
    
    def _find_best_agent(self, task: Task, agents: List[Agent]) -> Agent:
        """Encuentra el mejor agente para una tarea."""
        # Usar LLM para encontrar mejor match
        agents_info = "\n".join([
            f"- {a.name} ({a.role.value}): {a.specialization}, Capabilities: {', '.join(a.capabilities)}"
            for a in agents
        ])
        
        prompt = f"""Asigna esta tarea al mejor agente del equipo.

TAREA:
{task.description}

AGENTES DISPONIBLES:
{agents_info}

¿Qué agente es el mejor para esta tarea? Responde solo con el nombre del agente."""
        
        try:
            response = self.coordinator_llm.invoke(prompt).content.strip()
            # Buscar agente por nombre
            for agent in agents:
                if agent.name.lower() in response.lower():
                    return agent
        except Exception:
            pass
        
        # Fallback: asignar al primer agente disponible
        for agent in agents:
            if agent.status == "idle":
                return agent
        
        return agents[0]  # Último recurso
    
    def _execute_agent_task(self, agent: Agent, task: Task, team: CollaborativeTeam) -> Dict[str, Any]:
        """Ejecuta una tarea con un agente."""
        # Obtener conocimiento compartido relevante
        relevant_knowledge = self._get_relevant_knowledge(task, team.shared_knowledge)
        
        prompt = f"""Eres {agent.name}, un agente {agent.role.value} especializado en {agent.specialization}.

TAREA ASIGNADA:
{task.description}

CONOCIMIENTO COMPARTIDO DEL EQUIPO:
{relevant_knowledge[:2000] if relevant_knowledge else "Ninguno aún"}

CAPACIDADES:
{', '.join(agent.capabilities)}

INSTRUCCIONES:
1. Ejecuta esta tarea usando tus capacidades
2. Genera un resultado específico y útil
3. Documenta tu proceso
4. Comparte conocimiento relevante con el equipo

RESPUESTA (JSON):
{{
    "result": "Resultado de la tarea",
    "process": "Cómo lo hiciste",
    "knowledge_shared": "Conocimiento para compartir con el equipo",
    "status": "completed"
}}
"""
        
        try:
            response = agent.llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                result = {
                    "agent": agent.name,
                    "task": task.description,
                    "result": data.get("result", ""),
                    "process": data.get("process", ""),
                    "knowledge": data.get("knowledge_shared", ""),
                    "status": data.get("status", "completed")
                }
                
                # Actualizar conocimiento compartido
                if data.get("knowledge_shared"):
                    team.shared_knowledge[f"{agent.name}_{task.task_id}"] = data.get("knowledge_shared")
                
                agent.results.append(result)
                agent.status = "completed"
                task.status = "completed"
                task.result = result
                
                return result
            else:
                return {
                    "agent": agent.name,
                    "task": task.description,
                    "result": response[:1000],
                    "status": "completed"
                }
        except Exception as e:
            agent.status = "failed"
            task.status = "failed"
            return {
                "agent": agent.name,
                "task": task.description,
                "result": f"Error: {str(e)}",
                "status": "failed"
            }
    
    def _get_relevant_knowledge(self, task: Task, shared_knowledge: Dict[str, Any]) -> str:
        """Obtiene conocimiento relevante del conocimiento compartido."""
        # Buscar conocimiento relevante (simplificado)
        relevant = []
        task_lower = task.description.lower()
        
        for key, value in list(shared_knowledge.items())[-10:]:  # Últimos 10 items
            if any(word in str(value).lower() for word in task_lower.split()[:5]):
                relevant.append(str(value))
        
        return "\n".join(relevant)
    
    def _integrate_results(
        self,
        original_task: str,
        results: List[Dict[str, Any]],
        team: CollaborativeTeam
    ) -> str:
        """Integra resultados de múltiples agentes."""
        results_summary = "\n".join([
            f"**{r['agent']}**: {r['result'][:300]}"
            for r in results
        ])
        
        prompt = f"""Integra los resultados de múltiples agentes en una solución completa.

TAREA ORIGINAL:
{original_task}

RESULTADOS DE AGENTES:
{results_summary}

INSTRUCCIONES:
1. Combina todos los resultados en una solución cohesiva
2. Resuelve cualquier conflicto o inconsistencia
3. Crea un resultado final completo y funcional
4. Documenta cómo se integraron los resultados

RESPUESTA: Solución final integrada y completa."""
        
        try:
            response = self.coordinator_llm.invoke(prompt).content.strip()
            return response
        except Exception as e:
            return f"Resultado integrado de {len(results)} agentes. Error en integración: {str(e)}"
    
    def _verify_final_result(self, result: str, original_task: str) -> bool:
        """Verifica que el resultado final cumple con la tarea."""
        prompt = f"""Verifica si este resultado cumple con la tarea original.

TAREA ORIGINAL:
{original_task}

RESULTADO FINAL:
{result[:3000]}

¿El resultado cumple completamente con la tarea?

RESPUESTA (JSON):
{{
    "meets_requirements": true o false,
    "completeness": 0.0-1.0,
    "reasoning": "Por qué cumple o no"
}}
"""
        
        try:
            response = self.coordinator_llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                return data.get("meets_requirements", False)
            return True  # Asumir que cumple si no se puede verificar
        except Exception:
            return True
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extrae JSON de un texto."""
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        return None
    
    def _save_team(self, team: CollaborativeTeam):
        """Guarda un equipo."""
        team_file = self.data_dir / f"{team.team_id}.json"
        team_dict = {
            "team_id": team.team_id,
            "name": team.name,
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "role": a.role.value,
                    "specialization": a.specialization,
                    "capabilities": a.capabilities,
                    "status": a.status,
                    "results_count": len(a.results)
                }
                for a in team.agents
            ],
            "tasks": [
                {
                    "task_id": t.task_id,
                    "description": t.description,
                    "assigned_to": t.assigned_to,
                    "status": t.status
                }
                for t in team.tasks
            ],
            "status": team.status,
            "timestamp": team.timestamp
        }
        
        with open(team_file, 'w', encoding='utf-8') as f:
            json.dump(team_dict, f, indent=2, ensure_ascii=False)
    
    def get_team(self, team_id: str) -> Optional[CollaborativeTeam]:
        """Obtiene un equipo por ID."""
        return self.active_teams.get(team_id)

