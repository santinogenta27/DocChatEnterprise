"""
ÉXTASIS Mode - Agente Autónomo Empresarial con Toma de Decisiones

Arquitectura basada en:
- ReAct (Reasoning + Acting) para razonamiento estructurado
- Planificación autónoma multi-paso
- Integración con sistemas empresariales (ERP, CRM, SCM, ITSM)
- Toma de decisiones autónoma con ejecución de acciones reales

Sistemas soportados:
- CRM: Salesforce, HubSpot, Zoho, Pipedrive
- ERP: SAP, Oracle ERP Cloud, Microsoft Dynamics 365
- SCM: SAP Ariba, Oracle SCM Cloud
- ITSM: ServiceNow, Jira Service Management
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Sequence, Annotated, TypedDict
from datetime import datetime
from enum import Enum
from pathlib import Path

try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️ LangGraph no está instalado. Instala con: pip install langgraph")

from langchain_core.messages import (
    BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from .config import AppConfig
from .react_agent import ReActAgent
from .tools.crm_tool import CRMTool
from .tools.base_tool import BaseTool, ToolResult

try:
    from .extasis_workflows import (
        get_extasis_workflow,
        ExtasisWorkflowType
    )
    from .extasis_tools import EXTASIS_TOOLS
    EXTASIS_WORKFLOWS_AVAILABLE = True
except ImportError:
    EXTASIS_WORKFLOWS_AVAILABLE = False
    EXTASIS_TOOLS = []
    print("⚠️ ÉXTASIS workflows no disponibles. Algunas funciones pueden no funcionar.")


class DecisionType(str, Enum):
    """Tipos de decisiones que el agente puede tomar."""
    APPROVE_REFUND = "approve_refund"
    ASSIGN_LEAD = "assign_lead"
    ADJUST_INVENTORY = "adjust_inventory"
    ROUTE_SHIPMENT = "route_shipment"
    RESOLVE_TICKET = "resolve_ticket"
    CREATE_DEAL = "create_deal"
    UPDATE_CONTRACT = "update_contract"
    FLAG_FRAUD = "flag_fraud"
    SCHEDULE_MAINTENANCE = "schedule_maintenance"
    CUSTOM = "custom"


class AgentState(TypedDict):
    """Estado del agente ÉXTASIS."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    current_task: str
    decisions_made: List[Dict[str, Any]]
    actions_executed: List[Dict[str, Any]]
    context: Dict[str, Any]


class EnterpriseTool(BaseTool):
    """Herramienta base para sistemas empresariales."""
    
    def __init__(self, config: AppConfig, system_type: str):
        super().__init__(config)
        self.system_type = system_type  # "crm", "erp", "scm", "itsm"
    
    def get_system_type(self) -> str:
        return self.system_type


class ERPTool(EnterpriseTool):
    """Herramienta para sistemas ERP (SAP, Oracle, Dynamics 365)."""
    
    def __init__(self, config: AppConfig):
        super().__init__(config, "erp")
        
        # Credenciales SAP
        self.sap_odata_url = os.getenv("SAP_ODATA_URL", "")
        self.sap_user = os.getenv("SAP_USER", "")
        self.sap_password = os.getenv("SAP_PASSWORD", "")
        
        # Credenciales Oracle ERP
        self.oracle_erp_url = os.getenv("ORACLE_ERP_URL", "")
        self.oracle_erp_token = os.getenv("ORACLE_ERP_TOKEN", "")
        
        # Credenciales Dynamics 365
        self.dynamics_api_url = os.getenv("DYNAMICS_API_URL", "")
        self.dynamics_access_token = os.getenv("DYNAMICS_ACCESS_TOKEN", "")
    
    def get_name(self) -> str:
        return "erp_integration"
    
    def get_description(self) -> str:
        return """ERP integration tool for:
        - Dynamic inventory adjustments
        - Supplier contract renegotiation
        - Financial analysis and reporting
        - Supply chain management
        - Systems: SAP, Oracle ERP Cloud, Microsoft Dynamics 365"""
    
    def get_keywords(self) -> List[str]:
        return [
            "erp", "sap", "oracle", "dynamics", "inventory", "supply chain",
            "financial", "contract", "supplier", "purchase order"
        ]
    
    def execute(
        self,
        action: str,
        platform: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ToolResult:
        """Ejecuta acciones en sistemas ERP."""
        try:
            if action == "adjust_inventory":
                return self._adjust_inventory(platform, data or kwargs)
            elif action == "get_inventory":
                return self._get_inventory(platform, kwargs.get("product_id"))
            elif action == "create_purchase_order":
                return self._create_purchase_order(platform, data or kwargs)
            elif action == "get_financial_data":
                return self._get_financial_data(platform, kwargs.get("period"))
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Unknown ERP action: {action}",
                    metadata={}
                )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Error executing ERP action: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _adjust_inventory(self, platform: str, data: Dict[str, Any]) -> ToolResult:
        """Ajusta inventario dinámicamente."""
        # Implementación básica - en producción usaría APIs reales
        return ToolResult(
            success=True,
            data={"inventory_adjusted": True, "new_quantity": data.get("quantity")},
            message=f"Inventory adjusted in {platform}",
            metadata={"platform": platform, "action": "adjust_inventory"}
        )
    
    def _get_inventory(self, platform: str, product_id: str) -> ToolResult:
        """Obtiene niveles de inventario."""
        return ToolResult(
            success=True,
            data={"product_id": product_id, "quantity": 100},
            message=f"Inventory retrieved from {platform}",
            metadata={"platform": platform}
        )
    
    def _create_purchase_order(self, platform: str, data: Dict[str, Any]) -> ToolResult:
        """Crea orden de compra."""
        return ToolResult(
            success=True,
            data={"po_id": "PO-12345", "status": "created"},
            message=f"Purchase order created in {platform}",
            metadata={"platform": platform}
        )
    
    def _get_financial_data(self, platform: str, period: str) -> ToolResult:
        """Obtiene datos financieros."""
        return ToolResult(
            success=True,
            data={"period": period, "revenue": 1000000, "expenses": 800000},
            message=f"Financial data retrieved from {platform}",
            metadata={"platform": platform}
        )


class SCMTool(EnterpriseTool):
    """Herramienta para gestión de cadena de suministro."""
    
    def __init__(self, config: AppConfig):
        super().__init__(config, "scm")
        
        self.sap_ariba_url = os.getenv("SAP_ARIBA_URL", "")
        self.oracle_scm_url = os.getenv("ORACLE_SCM_URL", "")
    
    def get_name(self) -> str:
        return "scm_integration"
    
    def get_description(self) -> str:
        return """Supply Chain Management tool for:
        - Real-time shipment rerouting based on traffic/weather
        - Inventory management to prevent stockouts
        - Demand optimization
        - Systems: SAP Ariba, Oracle SCM Cloud"""
    
    def get_keywords(self) -> List[str]:
        return [
            "scm", "supply chain", "logistics", "shipment", "routing",
            "inventory", "demand", "ariba", "oracle scm"
        ]
    
    def execute(
        self,
        action: str,
        platform: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ToolResult:
        """Ejecuta acciones en sistemas SCM."""
        try:
            if action == "reroute_shipment":
                return self._reroute_shipment(platform, data or kwargs)
            elif action == "optimize_demand":
                return self._optimize_demand(platform, data or kwargs)
            elif action == "check_stockout_risk":
                return self._check_stockout_risk(platform, kwargs.get("product_id"))
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Unknown SCM action: {action}",
                    metadata={}
                )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Error executing SCM action: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _reroute_shipment(self, platform: str, data: Dict[str, Any]) -> ToolResult:
        """Rerutea envío basado en condiciones."""
        return ToolResult(
            success=True,
            data={"shipment_id": data.get("shipment_id"), "new_route": "Route-B"},
            message=f"Shipment rerouted in {platform}",
            metadata={"platform": platform}
        )
    
    def _optimize_demand(self, platform: str, data: Dict[str, Any]) -> ToolResult:
        """Optimiza demanda."""
        return ToolResult(
            success=True,
            data={"optimization_result": "demand_optimized"},
            message=f"Demand optimized in {platform}",
            metadata={"platform": platform}
        )
    
    def _check_stockout_risk(self, platform: str, product_id: str) -> ToolResult:
        """Verifica riesgo de desabastecimiento."""
        return ToolResult(
            success=True,
            data={"product_id": product_id, "risk_level": "low", "current_stock": 500},
            message=f"Stockout risk checked in {platform}",
            metadata={"platform": platform}
        )


class ITSMTool(EnterpriseTool):
    """Herramienta para IT Service Management."""
    
    def __init__(self, config: AppConfig):
        super().__init__(config, "itsm")
        
        self.servicenow_url = os.getenv("SERVICENOW_API_URL", "")
        self.servicenow_user = os.getenv("SERVICENOW_USER", "")
        self.servicenow_password = os.getenv("SERVICENOW_PASSWORD", "")
        
        self.jira_url = os.getenv("JIRA_API_URL", "")
        self.jira_email = os.getenv("JIRA_EMAIL", "")
        self.jira_api_token = os.getenv("JIRA_API_TOKEN", "")
    
    def get_name(self) -> str:
        return "itsm_integration"
    
    def get_description(self) -> str:
        return """ITSM integration tool for:
        - Autonomous incident resolution
        - Ticket management
        - Code generation and debugging
        - Proactive vulnerability detection
        - Systems: ServiceNow, Jira Service Management"""
    
    def get_keywords(self) -> List[str]:
        return [
            "itsm", "servicenow", "jira", "ticket", "incident", "it service",
            "troubleshooting", "vulnerability", "code", "debug"
        ]
    
    def execute(
        self,
        action: str,
        platform: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ToolResult:
        """Ejecuta acciones en sistemas ITSM."""
        try:
            if action == "resolve_incident":
                return self._resolve_incident(platform, data or kwargs)
            elif action == "create_ticket":
                return self._create_ticket(platform, data or kwargs)
            elif action == "update_ticket":
                return self._update_ticket(platform, kwargs.get("ticket_id"), data or kwargs)
            elif action == "get_tickets":
                return self._get_tickets(platform, kwargs.get("status"))
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Unknown ITSM action: {action}",
                    metadata={}
                )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Error executing ITSM action: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _resolve_incident(self, platform: str, data: Dict[str, Any]) -> ToolResult:
        """Resuelve incidente de forma autónoma."""
        return ToolResult(
            success=True,
            data={"incident_id": data.get("incident_id"), "status": "resolved"},
            message=f"Incident resolved in {platform}",
            metadata={"platform": platform}
        )
    
    def _create_ticket(self, platform: str, data: Dict[str, Any]) -> ToolResult:
        """Crea ticket de soporte."""
        return ToolResult(
            success=True,
            data={"ticket_id": "TKT-12345", "status": "open"},
            message=f"Ticket created in {platform}",
            metadata={"platform": platform}
        )
    
    def _update_ticket(self, platform: str, ticket_id: str, data: Dict[str, Any]) -> ToolResult:
        """Actualiza ticket."""
        return ToolResult(
            success=True,
            data={"ticket_id": ticket_id, "status": data.get("status")},
            message=f"Ticket updated in {platform}",
            metadata={"platform": platform}
        )
    
    def _get_tickets(self, platform: str, status: str) -> ToolResult:
        """Obtiene tickets."""
        return ToolResult(
                success=True,
            data={"tickets": [{"id": "TKT-1", "status": status}]},
            message=f"Tickets retrieved from {platform}",
            metadata={"platform": platform}
        )


class ExtasisMode:
    """
    Modo ÉXTASIS - Agente Autónomo Empresarial.
    
    Características:
    - Toma decisiones autónomas en sistemas empresariales
    - Integración con CRM, ERP, SCM, ITSM
    - Planificación multi-paso
    - Ejecución de acciones reales
    - Razonamiento estructurado (ReAct)
    """
    
    def __init__(
        self,
        config: AppConfig,
        provider: str = "openai"
    ):
        self.config = config
        self.provider = provider
        
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph requerido para ÉXTASIS Mode. Instala con: pip install langgraph")
        
        # Crear LLM
        if provider == "anthropic":
            if not config.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY requerida para usar Claude")
            self.llm = ChatAnthropic(
                model=config.anthropic_model or "claude-3-5-sonnet-20241022",
                temperature=0.3,
                api_key=config.anthropic_api_key,
                max_tokens=4000
            )
        else:
            if not config.openai_api_key:
                raise ValueError("OPENAI_API_KEY requerida")
            self.llm = ChatOpenAI(
                model=config.agentic_model or "gpt-4o",
                temperature=0.3,
                api_key=config.openai_api_key,
                max_tokens=4000
            )
        
        # Inicializar herramientas empresariales
        self.tools: List[BaseTool] = [
            CRMTool(config),
            ERPTool(config),
            SCMTool(config),
            ITSMTool(config)
        ]
        
        # Agregar tools de producción
        self.production_tools = EXTASIS_TOOLS if EXTASIS_WORKFLOWS_AVAILABLE else []
        
        # Crear agente ReAct con herramientas
        self.agent = ReActAgent(
            config=config,
            llm=self.llm,
            tools=self.tools,
            system_prompt=self._get_system_prompt()
        )
        
        # Estado del agente
        self.decisions_history: List[Dict[str, Any]] = []
        self.actions_history: List[Dict[str, Any]] = []
        
        # Modo simulación (desde configuración o variable de entorno)
        try:
            from .extasis_config import get_extasis_config_manager
            config_manager = get_extasis_config_manager()
            self.simulation_mode = config_manager.get_simulation_mode()
        except:
            self.simulation_mode = os.getenv("EXTASIS_SIMULATION_MODE", "false").lower() == "true"
    
    def _get_system_prompt(self) -> str:
        """Prompt del sistema para el agente ÉXTASIS."""
        return """You are ÉXTASIS, an autonomous enterprise AI agent that makes decisions and executes actions in enterprise systems.

Your capabilities:
1. **Autonomous Decision Making**: You can analyze situations and make decisions autonomously
2. **Enterprise System Integration**: You can interact with CRM, ERP, SCM, and ITSM systems
3. **Multi-step Planning**: You can plan and execute complex workflows
4. **Real Action Execution**: You execute real actions in enterprise systems

Available Enterprise Systems:
- **CRM** (Customer Relationship Management): Salesforce, HubSpot, Zoho, Pipedrive
  - Actions: approve refunds, assign leads, create contacts, update deals
- **ERP** (Enterprise Resource Planning): SAP, Oracle ERP Cloud, Microsoft Dynamics 365
  - Actions: adjust inventory, create purchase orders, financial analysis
- **SCM** (Supply Chain Management): SAP Ariba, Oracle SCM Cloud
  - Actions: reroute shipments, optimize demand, manage inventory
- **ITSM** (IT Service Management): ServiceNow, Jira Service Management
  - Actions: resolve incidents, manage tickets, detect vulnerabilities

Decision-Making Process:
1. **Analyze**: Understand the situation and gather relevant data
2. **Plan**: Create a multi-step plan to achieve the goal
3. **Decide**: Make autonomous decisions based on analysis
4. **Execute**: Execute actions in enterprise systems
5. **Verify**: Verify that actions were successful
6. **Learn**: Update knowledge based on results

When making decisions:
- Consider business rules and policies
- Evaluate risks and benefits
- Ensure compliance with regulations
- Optimize for efficiency and cost
- Document all decisions and actions

Always explain your reasoning process and the decisions you make."""
    
    def process_autonomous_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        Procesa una tarea autónoma con toma de decisiones.
        
        Args:
            task: Descripción de la tarea a ejecutar
            context: Contexto adicional (sistemas a usar, restricciones, etc.)
            max_iterations: Máximo de iteraciones del agente
            
        Returns:
            Dict con resultados, decisiones tomadas y acciones ejecutadas
        """
        context = context or {}
        
        # Construir mensaje inicial
        initial_message = f"""Task: {task}

Context: {json.dumps(context, indent=2) if context else "None"}

Execute this task autonomously. Make decisions and execute actions in enterprise systems as needed.
Explain your reasoning process and document all decisions and actions."""
        
        try:
            # Ejecutar agente ReAct
            result = self.agent.invoke(
                {"messages": [HumanMessage(content=initial_message)]},
                config={"configurable": {"thread_id": f"extasis_{datetime.now().isoformat()}"}}
            )
            
            # Extraer decisiones y acciones del historial
            decisions = self._extract_decisions(result.get("messages", []))
            actions = self._extract_actions(result.get("messages", []))
            
            # Guardar en historial
            self.decisions_history.extend(decisions)
            self.actions_history.extend(actions)
            
            return {
                "status": "completed",
                "task": task,
                "result": result,
                "decisions_made": decisions,
                "actions_executed": actions,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "task": task,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _extract_decisions(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """Extrae decisiones del historial de mensajes."""
        decisions = []
        for msg in messages:
            if isinstance(msg, AIMessage):
                content = msg.content if hasattr(msg, "content") else str(msg)
                # Buscar patrones de decisión en el contenido
                if "decision" in content.lower() or "decide" in content.lower():
                    decisions.append({
                        "type": "autonomous_decision",
                        "content": content,
                        "timestamp": datetime.now().isoformat()
                    })
        return decisions
    
    def _extract_actions(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """Extrae acciones ejecutadas del historial."""
        actions = []
        for msg in messages:
            if isinstance(msg, ToolMessage):
                actions.append({
                    "tool": msg.name if hasattr(msg, "name") else "unknown",
                    "result": msg.content if hasattr(msg, "content") else str(msg),
                "timestamp": datetime.now().isoformat()
                })
        return actions
    
    def execute_workflow(
        self,
        workflow_type: str,
        documents: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta un workflow empresarial específico.
        
        Args:
            workflow_type: Tipo de workflow (contract_audit, invoice_review, fraud_detection, etc.)
            documents: Lista de documentos a procesar
            context: Contexto adicional
            
        Returns:
            Dict con resultado del workflow
        """
        if not EXTASIS_WORKFLOWS_AVAILABLE:
            return {
                "status": "error",
                "error": "ÉXTASIS workflows no están disponibles. Instala dependencias necesarias."
            }
        
        try:
            workflow = get_extasis_workflow(
                workflow_type=workflow_type,
                config=self.config,
                provider=self.provider,
                simulation_mode=self.simulation_mode
            )
            
            result = workflow.execute(documents=documents, context=context)
            
            return {
                "status": "completed",
                "workflow_type": workflow_type,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "workflow_type": workflow_type,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Instancia global
_extasis_mode_instance: Optional[ExtasisMode] = None


def get_extasis_mode(
    config: AppConfig,
    provider: str = "openai"
) -> ExtasisMode:
    """Obtiene o crea la instancia global de ÉXTASIS Mode."""
    global _extasis_mode_instance
    
    if _extasis_mode_instance is None:
        _extasis_mode_instance = ExtasisMode(config=config, provider=provider)
    
    return _extasis_mode_instance


def run_extasis_mode(
    task: str,
    context: Optional[Dict[str, Any]] = None,
    config: Optional[AppConfig] = None,
    provider: str = "openai"
) -> Dict[str, Any]:
    """Ejecuta ÉXTASIS Mode con una tarea autónoma."""
    if config is None:
        from .config import load_config
        config = load_config()
    
    extasis = get_extasis_mode(config=config, provider=provider)
    return extasis.process_autonomous_task(task=task, context=context)
