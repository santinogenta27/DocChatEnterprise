"""
Agent 5: Steering Manager - Maneja human-in-the-loop steering.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from langchain_anthropic import ChatAnthropic
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

from .base_agent import BaseBanksAgent
from ..schemas import SteeringCommand
from ....config import AppConfig

logger = logging.getLogger(__name__)


class SteeringManagerAgent(BaseBanksAgent):
    """Agente que maneja steering humano y re-planifica workflows."""
    
    def __init__(self, config: AppConfig):
        super().__init__(config, "steering_manager")
        
        if LLM_AVAILABLE:
            if config.anthropic_api_key:
                self.llm = ChatAnthropic(
                    model="claude-3-5-sonnet-20241022",
                    temperature=0.2,
                    api_key=config.anthropic_api_key
                )
            elif config.openai_api_key:
                self.llm = ChatOpenAI(
                    model="gpt-4o",
                    temperature=0.2,
                    api_key=config.openai_api_key
                )
            else:
                self.llm = None
        else:
            self.llm = None
        
        # Archivo todo.md estilo EDR para tracking
        self.todo_file = Path(config.audit_log_dir) / "banks" / "todo.md"
        self.todo_file.parent.mkdir(parents=True, exist_ok=True)
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa comandos de steering y actualiza el estado.
        
        Input state:
            - steering_commands: List[str] (comandos en lenguaje natural)
            - current_workflow_state: Dict
        
        Output state:
            - steering_applied: List[SteeringCommand]
            - workflow_updated: bool
        """
        commands = state.get("steering_commands", [])
        steering_applied = []
        
        for cmd_text in commands:
            try:
                command = self._parse_command(cmd_text)
                if command:
                    # Aplicar el comando al estado
                    state = self._apply_command(command, state)
                    steering_applied.append(command)
                    
                    # Actualizar todo.md
                    self._update_todo_file(command)
            except Exception as e:
                logger.error(f"Error procesando steering command '{cmd_text}': {e}")
        
        # Log de auditoría
        self.log_audit(
            action="steering",
            input_data={"commands_count": len(commands)},
            output_data={"commands_applied": len(steering_applied)}
        )
        
        state["steering_applied"] = steering_applied
        state["workflow_updated"] = len(steering_applied) > 0
        
        return state
    
    def _parse_command(self, cmd_text: str) -> Optional[SteeringCommand]:
        """Parsea un comando en lenguaje natural a acción estructurada."""
        
        if not self.llm:
            # Fallback: parsing básico con regex
            return self._parse_command_basic(cmd_text)
        
        prompt = f"""Eres un parser de comandos de steering para un sistema de compliance KYC/AML.

Comando del usuario: "{cmd_text}"

Parsea este comando a una acción estructurada. Los comandos comunes son:
- "Ignora PEP level 1 para clientes España" → {{"action": "filter", "pep_level": 1, "country": "ES", "operation": "exclude"}}
- "Solo flaggea si beneficiario final en Panamá + Islas Caimán" → {{"action": "filter", "countries": ["Panama", "Cayman Islands"], "operation": "include_only"}}
- "Revisa solo documentos subidos hoy" → {{"action": "filter", "date": "today", "operation": "include_only"}}
- "Prioriza EU AI Act risks" → {{"action": "prioritize", "regulation": "EU_AI_ACT"}}
- "Excluye clientes retail" → {{"action": "filter", "segment": "retail", "operation": "exclude"}}
- "Aplica regla nueva a todos pendientes" → {{"action": "apply_rule", "scope": "all_pending"}}

Responde SOLO con un JSON válido:
{{
    "action": "string",
    "parameters": {{}},
    "affected_agents": ["list", "of", "agent", "names"]
}}

Si no puedes parsear, retorna null."""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Limpiar markdown
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            content = content.strip()
            
            import json
            data = json.loads(content)
            
            return SteeringCommand(
                command_id=f"steering_{datetime.now().timestamp()}",
                command_text=cmd_text,
                parsed_action=data,
                affected_agents=data.get("affected_agents", [])
            )
        except Exception as e:
            logger.error(f"Error parseando comando con LLM: {e}")
            return self._parse_command_basic(cmd_text)
    
    def _parse_command_basic(self, cmd_text: str) -> Optional[SteeringCommand]:
        """Parsing básico con regex como fallback."""
        cmd_lower = cmd_text.lower()
        
        # Detectar patrones comunes
        if "ignora" in cmd_lower or "excluye" in cmd_lower:
            action = "filter"
            operation = "exclude"
        elif "solo" in cmd_lower or "prioriza" in cmd_lower:
            action = "filter"
            operation = "include_only"
        else:
            action = "unknown"
            operation = "unknown"
        
        # Detectar PEP
        pep_level = None
        if "pep level 1" in cmd_lower:
            pep_level = 1
        elif "pep level 2" in cmd_lower:
            pep_level = 2
        elif "pep level 3" in cmd_lower:
            pep_level = 3
        
        # Detectar países
        countries = []
        country_patterns = ["españa", "spain", "panamá", "panama", "caimán", "cayman"]
        for pattern in country_patterns:
            if pattern in cmd_lower:
                if "españa" in cmd_lower or "spain" in cmd_lower:
                    countries.append("ES")
                elif "panamá" in cmd_lower or "panama" in cmd_lower:
                    countries.append("Panama")
                elif "caimán" in cmd_lower or "cayman" in cmd_lower:
                    countries.append("Cayman Islands")
        
        return SteeringCommand(
            command_id=f"steering_{datetime.now().timestamp()}",
            command_text=cmd_text,
            parsed_action={
                "action": action,
                "operation": operation,
                "pep_level": pep_level,
                "countries": countries
            },
            affected_agents=["screener", "risk_engine"]
        )
    
    def _apply_command(self, command: SteeringCommand, state: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica un comando de steering al estado."""
        action = command.parsed_action.get("action")
        params = command.parsed_action.get("parameters", {})
        
        if action == "filter":
            # Aplicar filtros
            state = self._apply_filter(state, command.parsed_action)
        elif action == "prioritize":
            # Cambiar prioridades
            state = self._apply_prioritization(state, params)
        elif action == "apply_rule":
            # Aplicar regla nueva
            state = self._apply_rule(state, params)
        
        # Marcar que se necesita re-procesamiento
        state["needs_reprocessing"] = True
        
        return state
    
    def _apply_filter(self, state: Dict[str, Any], action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica filtros según steering."""
        operation = action_data.get("operation", "exclude")
        pep_level = action_data.get("pep_level")
        countries = action_data.get("countries", [])
        
        # Filtrar entities, hits, etc.
        if "extracted_entities" in state:
            entities = state["extracted_entities"]
            filtered = []
            
            for entity in entities:
                if isinstance(entity, dict):
                    entity_pep = entity.get("pep_status")
                    entity_country = entity.get("nationality") or entity.get("address", "")
                else:
                    entity_pep = getattr(entity, "pep_status", None)
                    entity_country = getattr(entity, "nationality", "") or getattr(entity, "address", "")
                
                should_include = True
                
                # Filtro PEP
                if pep_level and entity_pep:
                    if operation == "exclude" and str(pep_level) == str(entity_pep):
                        should_include = False
                
                # Filtro países
                if countries and entity_country:
                    country_match = any(c.lower() in entity_country.lower() for c in countries)
                    if operation == "exclude" and country_match:
                        should_include = False
                    elif operation == "include_only" and not country_match:
                        should_include = False
                
                if should_include:
                    filtered.append(entity)
            
            state["extracted_entities"] = filtered
        
        return state
    
    def _apply_prioritization(self, state: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica cambios de priorización."""
        # Implementar lógica de priorización
        state["prioritization"] = params
        return state
    
    def _apply_rule(self, state: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica una regla nueva."""
        # Implementar lógica de reglas
        if "rules" not in state:
            state["rules"] = []
        state["rules"].append(params)
        return state
    
    def _update_todo_file(self, command: SteeringCommand):
        """Actualiza el archivo todo.md estilo EDR."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"""
## {timestamp} - Steering Command

**Comando:** {command.command_text}
**Acción:** {command.parsed_action.get('action', 'unknown')}
**Agentes afectados:** {', '.join(command.affected_agents)}

**Estado:** Aplicado

---
"""
        
        # Append al archivo
        with open(self.todo_file, 'a', encoding='utf-8') as f:
            f.write(entry)

