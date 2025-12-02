"""
MCP Server - Model Context Protocol Implementation
Permite a JARVIS conectarse con cualquier sistema de forma estandarizada
"""

from __future__ import annotations

import json
import asyncio
import sys
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import time
import logging

logger = logging.getLogger(__name__)


class MCPMessageType(str, Enum):
    """Tipos de mensajes MCP."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class MCPTool:
    """Herramienta MCP disponible."""
    name: str
    description: str
    input_schema: Dict[str, Any]  # JSON Schema
    handler: Callable  # Función que ejecuta la herramienta
    category: str = "general"
    requires_auth: bool = False
    auth_type: Optional[str] = None  # "oauth", "api_key", "basic", etc.


@dataclass
class MCPResource:
    """Recurso MCP disponible."""
    uri: str
    name: str
    description: str
    mime_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPRequest:
    """Request MCP."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResponse:
    """Response MCP."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPServer:
    """
    Servidor MCP que expone herramientas y recursos para JARVIS.
    
    MCP permite conectar JARVIS con cualquier sistema externo de forma estandarizada:
    - Slack, Salesforce, APIs, Bases de datos, etc.
    - Todo se conecta igual usando el protocolo MCP
    """
    
    def __init__(self, server_name: str = "jarvis-mcp-server"):
        self.server_name = server_name
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.capabilities = {
            "tools": {},
            "resources": {},
            "prompts": {}
        }
        self.is_initialized = False
    
    def register_tool(self, tool: MCPTool):
        """Registra una herramienta MCP."""
        self.tools[tool.name] = tool
        self.capabilities["tools"][tool.name] = {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.input_schema
        }
        logger.info(f"✅ [MCP] Herramienta registrada: {tool.name}")
    
    def register_resource(self, resource: MCPResource):
        """Registra un recurso MCP."""
        self.resources[resource.uri] = resource
        self.capabilities["resources"][resource.uri] = {
            "uri": resource.uri,
            "name": resource.name,
            "description": resource.description,
            "mimeType": resource.mime_type
        }
        logger.info(f"✅ [MCP] Recurso registrado: {resource.uri}")
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Maneja un request MCP."""
        try:
            method = request.get("method", "")
            params = request.get("params", {})
            request_id = request.get("id")
            
            # Initialize
            if method == "initialize":
                return self._handle_initialize(request_id, params)
            
            # List tools
            elif method == "tools/list":
                return self._handle_list_tools(request_id)
            
            # Call tool
            elif method == "tools/call":
                return await self._handle_call_tool(request_id, params)
            
            # List resources
            elif method == "resources/list":
                return self._handle_list_resources(request_id)
            
            # Read resource
            elif method == "resources/read":
                return await self._handle_read_resource(request_id, params)
            
            else:
                return self._create_error_response(
                    request_id,
                    -32601,
                    f"Método no soportado: {method}"
                )
        
        except Exception as e:
            logger.error(f"❌ [MCP] Error manejando request: {e}")
            return self._create_error_response(
                request.get("id"),
                -32603,
                f"Error interno: {str(e)}"
            )
    
    def _handle_initialize(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Maneja initialize request."""
        self.is_initialized = True
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": self.capabilities,
                "serverInfo": {
                    "name": self.server_name,
                    "version": "1.0.0"
                }
            }
        }
    
    def _handle_list_tools(self, request_id: Any) -> Dict[str, Any]:
        """Lista todas las herramientas disponibles."""
        tools_list = []
        for tool_name, tool in self.tools.items():
            tools_list.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            })
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools_list
            }
        }
    
    async def _handle_call_tool(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta una herramienta."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            return self._create_error_response(
                request_id,
                -32602,
                f"Herramienta no encontrada: {tool_name}"
            )
        
        tool = self.tools[tool_name]
        
        try:
            # Ejecutar la herramienta
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**arguments)
            else:
                result = tool.handler(**arguments)
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            }
        
        except Exception as e:
            logger.error(f"❌ [MCP] Error ejecutando herramienta {tool_name}: {e}")
            return self._create_error_response(
                request_id,
                -32603,
                f"Error ejecutando herramienta: {str(e)}"
            )
    
    def _handle_list_resources(self, request_id: Any) -> Dict[str, Any]:
        """Lista todos los recursos disponibles."""
        resources_list = []
        for uri, resource in self.resources.items():
            resources_list.append({
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mimeType": resource.mime_type
            })
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "resources": resources_list
            }
        }
    
    async def _handle_read_resource(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Lee un recurso."""
        uri = params.get("uri")
        
        if uri not in self.resources:
            return self._create_error_response(
                request_id,
                -32602,
                f"Recurso no encontrado: {uri}"
            )
        
        resource = self.resources[uri]
        
        # Por ahora retornamos metadata, pero esto puede extenderse
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "contents": [
                    {
                        "uri": resource.uri,
                        "mimeType": resource.mime_type or "text/plain",
                        "text": json.dumps(resource.metadata, ensure_ascii=False, indent=2)
                    }
                ]
            }
        }
    
    def _create_error_response(
        self,
        request_id: Any,
        code: int,
        message: str
    ) -> Dict[str, Any]:
        """Crea una respuesta de error."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
    
    async def run_stdio(self):
        """Ejecuta el servidor MCP usando stdio (standard input/output)."""
        logger.info("🚀 [MCP] Iniciando servidor MCP en modo stdio...")
        
        while True:
            try:
                # Leer línea desde stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None,
                    sys.stdin.readline
                )
                
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Parsear JSON request
                request = json.loads(line)
                
                # Manejar request
                response = await self.handle_request(request)
                
                # Enviar respuesta
                print(json.dumps(response, ensure_ascii=False))
                sys.stdout.flush()
            
            except json.JSONDecodeError as e:
                logger.error(f"❌ [MCP] Error parseando JSON: {e}")
                error_response = self._create_error_response(
                    None,
                    -32700,
                    f"Parse error: {str(e)}"
                )
                print(json.dumps(error_response, ensure_ascii=False))
                sys.stdout.flush()
            
            except Exception as e:
                logger.error(f"❌ [MCP] Error en servidor: {e}")
                error_response = self._create_error_response(
                    None,
                    -32603,
                    f"Internal error: {str(e)}"
                )
                print(json.dumps(error_response, ensure_ascii=False))
                sys.stdout.flush()


class MCPClient:
    """
    Cliente MCP para que JARVIS se conecte a servidores MCP externos.
    """
    
    def __init__(self, server_name: str = "jarvis-mcp-client"):
        self.server_name = server_name
        self.connected_servers: Dict[str, Any] = {}
        self.request_counter = 0
    
    async def connect_to_server(
        self,
        server_id: str,
        connection_type: str = "stdio",
        connection_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Conecta a un servidor MCP.
        
        Args:
            server_id: ID único del servidor
            connection_type: "stdio", "http", "websocket"
            connection_config: Configuración de conexión
        """
        try:
            # Por ahora solo soportamos stdio
            # En el futuro se puede extender a HTTP/WebSocket
            
            self.connected_servers[server_id] = {
                "type": connection_type,
                "config": connection_config or {},
                "connected_at": time.time()
            }
            
            logger.info(f"✅ [MCP Client] Conectado a servidor: {server_id}")
            return True
        
        except Exception as e:
            logger.error(f"❌ [MCP Client] Error conectando: {e}")
            return False
    
    async def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Llama a una herramienta en un servidor MCP."""
        if server_id not in self.connected_servers:
            raise ValueError(f"Servidor no conectado: {server_id}")
        
        # Por ahora retornamos un placeholder
        # En implementación real, esto enviaría un request MCP al servidor
        return {
            "success": True,
            "result": f"Tool {tool_name} called with arguments: {arguments}",
            "server_id": server_id
        }
    
    def list_available_tools(self, server_id: str) -> List[Dict[str, Any]]:
        """Lista herramientas disponibles en un servidor."""
        if server_id not in self.connected_servers:
            return []
        
        # Por ahora retornamos lista vacía
        # En implementación real, esto consultaría al servidor MCP
        return []

