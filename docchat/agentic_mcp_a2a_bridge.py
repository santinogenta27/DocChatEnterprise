"""MCP × A2A Bridge: Integración de MCP tools con A2A agents.

Permite que agents descubran y usen herramientas MCP automáticamente
usando el protocolo A2A para comunicación.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .agentic_a2a_protocol import A2AProtocol, AgentCard, A2ATask, TaskStatus
from .mcp_manager import MCPManager


@dataclass
class MCPToolCapability:
    """Capacidad de un tool MCP expuesta como capability A2A."""
    tool_name: str
    mcp_connection_id: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    category: str = "tool"


class MCPA2ABridge:
    """Bridge que conecta MCP tools con A2A agents."""
    
    def __init__(
        self,
        a2a_protocol: A2AProtocol,
        mcp_manager: MCPManager,
    ):
        self.a2a = a2a_protocol
        self.mcp = mcp_manager
        
        # Cache de tools MCP convertidos a capabilities A2A
        self.mcp_capabilities: Dict[str, MCPToolCapability] = {}
        
        # Sincronizar tools MCP con A2A
        self._sync_mcp_tools_to_a2a()
    
    def _sync_mcp_tools_to_a2a(self):
        """Sincroniza tools MCP y los expone como capabilities A2A."""
        try:
            # Obtener todos los tools MCP disponibles
            mcp_tools = self.mcp.list_available_tools()
            
            for tool in mcp_tools:
                tool_name = tool.get("name", "")
                connection_id = tool.get("connection_id", "")
                
                # Crear capability A2A desde tool MCP
                capability = MCPToolCapability(
                    tool_name=tool_name,
                    mcp_connection_id=connection_id,
                    description=tool.get("description", ""),
                    input_schema=tool.get("input_schema", {}),
                    output_schema=tool.get("output_schema", {}),
                    category=tool.get("category", "tool"),
                )
                
                self.mcp_capabilities[tool_name] = capability
                
                # Registrar como capability A2A
                # (Los tools MCP se exponen como capabilities que cualquier agent puede usar)
                if f"mcp_tool_{tool_name}" not in [c.get("name") for c in self._get_all_capabilities()]:
                    self._register_mcp_tool_as_capability(capability)
        
        except Exception as e:
            print(f"⚠️ Error sincronizando MCP tools a A2A: {e}")
    
    def _get_all_capabilities(self) -> List[Dict[str, Any]]:
        """Obtiene todas las capabilities registradas en A2A."""
        all_caps = []
        for card in self.a2a.agent_registry.values():
            all_caps.extend(card.capabilities)
        return all_caps
    
    def _register_mcp_tool_as_capability(self, capability: MCPToolCapability):
        """Registra un tool MCP como capability A2A."""
        # Crear capability description
        cap_description = {
            "name": f"mcp_tool_{capability.tool_name}",
            "description": f"Tool MCP: {capability.description}",
            "input_schema": capability.input_schema,
            "output_schema": capability.output_schema,
            "mcp_connection_id": capability.mcp_connection_id,
            "tool_name": capability.tool_name,
            "category": capability.category,
        }
        
        # Agregar a un "agent virtual" que representa tools MCP
        virtual_agent_id = "mcp_tools_provider"
        
        # Verificar si el agent virtual existe
        virtual_agent = self.a2a.get_agent_card(virtual_agent_id)
        
        if not virtual_agent:
            # Crear agent virtual para tools MCP
            virtual_agent = self.a2a.register_agent(
                agent_id=virtual_agent_id,
                name="MCP Tools Provider",
                description="Proveedor de herramientas MCP disponibles para todos los agents",
                category="tool_provider",
                tags=["mcp", "tools", "automation"],
            )
        
        # Agregar capability al agent virtual
        if cap_description not in virtual_agent.capabilities:
            virtual_agent.capabilities.append(cap_description)
            self.a2a._save_registry()
    
    def discover_tools_for_agent(
        self,
        agent_id: str,
        task_description: str,
    ) -> List[MCPToolCapability]:
        """Descubre tools MCP relevantes para una tarea específica."""
        # Buscar tools MCP que coincidan con la descripción de la tarea
        relevant_tools = []
        
        task_lower = task_description.lower()
        
        for tool_name, capability in self.mcp_capabilities.items():
            # Match simple por keywords
            if any(keyword in task_lower for keyword in [
                tool_name.lower(),
                capability.description.lower(),
                capability.category.lower(),
            ]):
                relevant_tools.append(capability)
        
        return relevant_tools
    
    def execute_mcp_tool_via_a2a(
        self,
        from_agent_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        response_format: Optional[str] = "concise",
    ) -> Dict[str, Any]:
        """Ejecuta un tool MCP usando el protocolo A2A con formato de respuesta optimizado."""
        # Verificar que el tool existe
        if tool_name not in self.mcp_capabilities:
            return {
                "success": False,
                "error": f"Tool MCP no encontrado: {tool_name}",
            }
        
        capability = self.mcp_capabilities[tool_name]
        
        # Crear tarea A2A
        task = self.a2a.create_task(
            task_type="mcp_tool_execution",
            from_agent_id=from_agent_id,
            to_agent_id="mcp_tools_provider",
            parameters={
                "tool_name": tool_name,
                "mcp_connection_id": capability.mcp_connection_id,
                "parameters": parameters,
            },
        )
        
        # Actualizar estado a in_progress
        self.a2a.update_task_status(task.task_id, TaskStatus.IN_PROGRESS)
        
        try:
            # Ejecutar tool MCP
            import asyncio
            
            # Si estamos en contexto async, usar await
            # Si no, crear nuevo event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                # Si el loop ya está corriendo, usar run_coroutine_threadsafe
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.mcp.call_tool(
                            tool_name=tool_name,
                            parameters=parameters,
                            connection_id=capability.mcp_connection_id,
                        )
                    )
                    result = future.result()
            else:
                result = loop.run_until_complete(
                    self.mcp.call_tool(
                        tool_name=tool_name,
                        parameters=parameters,
                        connection_id=capability.mcp_connection_id,
                    )
                )
            
            # Optimizar respuesta según formato solicitado
            if response_format == "concise":
                try:
                    from .mcp_progressive_disclosure import MCPProgressiveDisclosure, ResponseFormat
                    # Crear instancia temporal para formatear
                    temp_disclosure = MCPProgressiveDisclosure(self.mcp)
                    result = temp_disclosure.format_tool_response(result, ResponseFormat.CONCISE)
                except:
                    pass  # Si falla, usar resultado original
            
            # Crear artifact con resultado
            artifact = self.a2a.create_artifact(
                task_id=task.task_id,
                artifact_type="tool_result",
                content=result,
                metadata={
                    "tool_name": tool_name,
                    "mcp_connection_id": capability.mcp_connection_id,
                    "response_format": response_format,
                },
            )
            
            # Actualizar tarea a completada
            self.a2a.update_task_status(
                task.task_id,
                TaskStatus.COMPLETED,
                result=result,
                artifacts=[asdict(artifact)],
            )
            
            return {
                "success": True,
                "task_id": task.task_id,
                "result": result,
                "artifact_id": artifact.artifact_id,
            }
            
        except Exception as e:
            # Actualizar tarea a fallida
            self.a2a.update_task_status(
                task.task_id,
                TaskStatus.FAILED,
                error=str(e),
            )
            
            return {
                "success": False,
                "task_id": task.task_id,
                "error": str(e),
            }
    
    def auto_discover_and_use_tools(
        self,
        agent_id: str,
        task_description: str,
        auto_execute: bool = False,
    ) -> Dict[str, Any]:
        """Descubre automáticamente tools MCP relevantes y los sugiere/ejecuta."""
        # Descubrir tools relevantes
        relevant_tools = self.discover_tools_for_agent(agent_id, task_description)
        
        if not relevant_tools:
            return {
                "success": False,
                "message": "No se encontraron tools MCP relevantes para esta tarea",
                "tools": [],
            }
        
        # Si auto_execute y hay un solo tool, ejecutarlo
        if auto_execute and len(relevant_tools) == 1:
            tool = relevant_tools[0]
            # Extraer parámetros básicos de la descripción (simplificado)
            # En producción, usaría un LLM para extraer parámetros
            parameters = self._extract_parameters_from_description(
                task_description,
                tool.input_schema,
            )
            
            result = self.execute_mcp_tool_via_a2a(
                from_agent_id=agent_id,
                tool_name=tool.tool_name,
                parameters=parameters,
            )
            
            return {
                "success": True,
                "auto_executed": True,
                "tool": tool.tool_name,
                "result": result,
            }
        
        # Retornar lista de tools sugeridos
        return {
            "success": True,
            "auto_executed": False,
            "tools": [
                {
                    "tool_name": tool.tool_name,
                    "description": tool.description,
                    "category": tool.category,
                }
                for tool in relevant_tools
            ],
        }
    
    def _extract_parameters_from_description(
        self,
        description: str,
        input_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extrae parámetros de la descripción usando el schema (simplificado)."""
        # Esto es una implementación básica
        # En producción, usaría un LLM para extraer parámetros inteligentemente
        parameters = {}
        
        # Extracción básica por keywords
        schema_properties = input_schema.get("properties", {})
        
        for param_name, param_schema in schema_properties.items():
            param_type = param_schema.get("type", "string")
            param_desc = param_schema.get("description", "")
            
            # Buscar el parámetro en la descripción
            if param_name.lower() in description.lower():
                # Intentar extraer valor (muy básico)
                # En producción, usar LLM para esto
                if param_type == "string":
                    # Buscar valor después del nombre del parámetro
                    parts = description.lower().split(param_name.lower())
                    if len(parts) > 1:
                        # Extraer siguiente palabra/frase
                        value = parts[1].strip().split()[0] if parts[1].strip() else ""
                        if value:
                            parameters[param_name] = value
        
        return parameters
    
    def refresh_mcp_tools(self):
        """Refresca la lista de tools MCP y los sincroniza con A2A."""
        self._sync_mcp_tools_to_a2a()
        print(f"✅ Tools MCP sincronizados con A2A: {len(self.mcp_capabilities)} tools disponibles")

