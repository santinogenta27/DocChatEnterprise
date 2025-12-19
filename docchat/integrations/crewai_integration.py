"""
CrewAI Integration - Multi-agent collaboration
Integración de CrewAI para equipos de agentes especializados.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import BaseTool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    # Crear clases dummy para que el código funcione sin CrewAI
    class Agent:
        pass
    class Task:
        pass
    class Crew:
        pass
    class Process:
        sequential = "sequential"
        hierarchical = "hierarchical"
    import sys
    try:
        if sys.version_info >= (3, 14):
            print("CrewAI no esta disponible: Requiere Python 3.10-3.13 (tienes Python 3.14)")
        else:
            print("CrewAI no esta instalado. Instala con: py -3.12 -m pip install crewai")
    except UnicodeEncodeError:
        pass  # Ignorar error de codificacion en Windows

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from ..config import AppConfig


class CrewAIIntegration:
    """
    Integración de CrewAI para multi-agent collaboration.
    
    Características:
    - Role-based agents
    - Multi-agent collaboration
    - Task delegation
    - Observability mejorada
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        if not CREWAI_AVAILABLE:
            raise ImportError("CrewAI no está instalado. Instala con: py -3.12 -m pip install crewai")
        
        # LLM para agentes
        if config.openai_api_key:
            self.llm = ChatOpenAI(
                model=config.agentic_model or "gpt-4o",
                temperature=0.7,
                api_key=config.openai_api_key
            )
        elif config.anthropic_api_key:
            self.llm = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                temperature=0.7,
                api_key=config.anthropic_api_key
            )
        else:
            raise ValueError("Se requiere OPENAI_API_KEY o ANTHROPIC_API_KEY")
        
        self.crews: Dict[str, Any] = {}
        self.agents: Dict[str, Any] = {}
    
    def create_agent(
        self,
        agent_id: str,
        role: str,
        goal: str,
        backstory: str,
        tools: Optional[List[Any]] = None,
        verbose: bool = True
    ) -> Any:
        """
        Crea un agente CrewAI.
        
        Args:
            agent_id: ID único del agente
            role: Rol del agente (ej: "Sales Development Representative")
            goal: Objetivo del agente
            backstory: Contexto del agente
            tools: Herramientas disponibles
            verbose: Si mostrar logs detallados
        """
        agent = Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            tools=tools or [],
            llm=self.llm,
            verbose=verbose,
            allow_delegation=False
        )
        
        self.agents[agent_id] = agent
        return agent
    
    def create_task(
        self,
        description: str,
        agent: Any,
        expected_output: str
    ) -> Any:
        """
        Crea una tarea para un agente.
        
        Args:
            description: Descripción de la tarea
            agent: Agente asignado
            expected_output: Output esperado
        """
        return Task(
            description=description,
            agent=agent,
            expected_output=expected_output
        )
    
    def create_crew(
        self,
        crew_id: str,
        agents: List[Any],
        tasks: List[Any],
        process: Any = "sequential",
        verbose: bool = True
    ) -> Any:
        """
        Crea un crew (equipo) de agentes.
        
        Args:
            crew_id: ID único del crew
            agents: Lista de agentes
            tasks: Lista de tareas
            process: Proceso de ejecución (sequential, hierarchical)
            verbose: Si mostrar logs detallados
        """
        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=process,
            verbose=verbose
        )
        
        self.crews[crew_id] = crew
        return crew
    
    def execute_crew(
        self,
        crew_id: str,
        inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta un crew.
        
        Args:
            crew_id: ID del crew
            inputs: Inputs para el crew
        """
        if crew_id not in self.crews:
            raise ValueError(f"Crew {crew_id} no encontrado")
        
        crew = self.crews[crew_id]
        
        try:
            result = crew.kickoff(inputs=inputs or {})
            
            return {
                "success": True,
                "result": str(result),
                "tasks_completed": len(crew.tasks),
                "agents_used": [agent.role for agent in crew.agents]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

