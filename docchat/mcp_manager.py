"""
MCP Manager - Gestiona conexiones MCP para JARVIS
Permite a JARVIS conectarse con cualquier sistema usando MCP
"""

from __future__ import annotations

import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
import time

from langchain_core.language_models import BaseLanguageModel

from .config import AppConfig
from .mcp_server import MCPServer, MCPClient, MCPTool
from .mcp_tools import register_common_mcp_tools

logger = logging.getLogger(__name__)


@dataclass
class MCPConnection:
    """Conexión MCP configurada."""
    connection_id: str
    name: str
    connection_type: str  # "slack", "salesforce", "api", "database", "custom"
    config: Dict[str, Any]
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    last_used: Optional[float] = None
    usage_count: int = 0


class MCPManager:
    """
    Gestiona todas las conexiones MCP para JARVIS.
    
    Permite:
    - Registrar nuevas conexiones MCP (Slack, Salesforce, APIs, etc.)
    - Conectar JARVIS con sistemas externos de forma estandarizada
    - Ejecutar herramientas MCP desde JARVIS
    """
    
    def __init__(self, config: AppConfig, llm: Optional[BaseLanguageModel] = None):
        self.config = config
        self.llm = llm
        self.mcp_server = MCPServer(server_name="jarvis-mcp-server")
        self.mcp_client = MCPClient(server_name="jarvis-mcp-client")
        self.connections: Dict[str, MCPConnection] = {}
        self.integrations_config: Dict[str, Any] = {}
        self.is_initialized = False
        
        # Cargar conexiones guardadas
        self._load_connections()
    
    def set_llm(self, llm: BaseLanguageModel):
        """Establece el LLM para navegación de datos crudos."""
        self.llm = llm
    
    def _load_connections(self):
        """Carga conexiones MCP guardadas."""
        connections_file = Path(self.config.memory_dir) / "mcp_connections.json"
        
        if connections_file.exists():
            try:
                with open(connections_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for conn_data in data.get("connections", []):
                        conn = MCPConnection(**conn_data)
                        self.connections[conn.connection_id] = conn
                        self._add_to_integrations_config(conn)
                
                logger.info(f"✅ [MCP Manager] {len(self.connections)} conexiones MCP cargadas")
            except Exception as e:
                logger.error(f"❌ [MCP Manager] Error cargando conexiones: {e}")
    
    def _save_connections(self):
        """Guarda conexiones MCP."""
        connections_file = Path(self.config.memory_dir) / "mcp_connections.json"
        connections_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            data = {
                "connections": [asdict(conn) for conn in self.connections.values()]
            }
            with open(connections_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ [MCP Manager] Error guardando conexiones: {e}")
    
    def _add_to_integrations_config(self, connection: MCPConnection):
        """Agrega una conexión a la configuración de integraciones."""
        conn_type = connection.connection_type
        
        if conn_type == "slack":
            self.integrations_config["slack"] = {
                "token": connection.config.get("token")
            }
        elif conn_type == "salesforce":
            self.integrations_config["salesforce"] = {
                "instance_url": connection.config.get("instance_url"),
                "access_token": connection.config.get("access_token")
            }
        elif conn_type == "database":
            self.integrations_config["database"] = {
                "connection_string": connection.config.get("connection_string")
            }
        elif conn_type == "email":
            self.integrations_config["email"] = {
                "smtp_config": connection.config.get("smtp_config", {})
            }
    
    def initialize(self):
        """Inicializa el servidor MCP con todas las herramientas."""
        if self.is_initialized:
            return
        
        # Registrar todas las herramientas comunes
        register_common_mcp_tools(
            self.mcp_server,
            self.integrations_config
        )
        
        self.is_initialized = True
        logger.info("✅ [MCP Manager] Servidor MCP inicializado")
    
    def register_connection(
        self,
        name: str,
        connection_type: str,
        config: Dict[str, Any],
        connection_id: Optional[str] = None
    ) -> str:
        """
        Registra una nueva conexión MCP.
        
        Args:
            name: Nombre descriptivo de la conexión
            connection_type: Tipo ("slack", "salesforce", "api", "database", "email", "custom")
            config: Configuración específica de la conexión
            connection_id: ID único (se genera si no se proporciona)
        
        Returns:
            connection_id: ID de la conexión creada
        """
        if connection_id is None:
            connection_id = f"{connection_type}_{int(time.time())}"
        
        connection = MCPConnection(
            connection_id=connection_id,
            name=name,
            connection_type=connection_type,
            config=config,
            enabled=True
        )
        
        self.connections[connection_id] = connection
        self._add_to_integrations_config(connection)
        
        # Reinicializar servidor para incluir nuevas herramientas
        self.is_initialized = False
        self.initialize()
        
        # Guardar
        self._save_connections()
        
        logger.info(f"✅ [MCP Manager] Conexión registrada: {name} ({connection_id})")
        return connection_id
    
    def remove_connection(self, connection_id: str) -> bool:
        """Elimina una conexión MCP."""
        if connection_id in self.connections:
            del self.connections[connection_id]
            self._save_connections()
            
            # Reconstruir integrations_config
            self.integrations_config = {}
            for conn in self.connections.values():
                self._add_to_integrations_config(conn)
            
            # Reinicializar
            self.is_initialized = False
            self.initialize()
            
            logger.info(f"✅ [MCP Manager] Conexión eliminada: {connection_id}")
            return True
        
        return False
    
    def list_connections(self) -> List[Dict[str, Any]]:
        """Lista todas las conexiones MCP."""
        return [
            {
                "connection_id": conn.connection_id,
                "name": conn.name,
                "type": conn.connection_type,
                "enabled": conn.enabled,
                "created_at": conn.created_at,
                "last_used": conn.last_used,
                "usage_count": conn.usage_count
            }
            for conn in self.connections.values()
        ]
    
    def list_available_tools(self) -> List[Dict[str, Any]]:
        """Lista todas las herramientas MCP disponibles."""
        if not self.is_initialized:
            self.initialize()
        
        tools_list = []
        for tool_name, tool in self.mcp_server.tools.items():
            tools_list.append({
                "name": tool.name,
                "description": tool.description,
                "category": tool.category,
                "requires_auth": tool.requires_auth,
                "auth_type": tool.auth_type
            })
        
        return tools_list
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        connection_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Llama a una herramienta MCP.
        
        Args:
            tool_name: Nombre de la herramienta
            arguments: Argumentos para la herramienta
            connection_id: ID de conexión específica (opcional)
        
        Returns:
            Resultado de la herramienta
        """
        if not self.is_initialized:
            self.initialize()
        
        # Actualizar estadísticas de uso
        if connection_id and connection_id in self.connections:
            conn = self.connections[connection_id]
            conn.last_used = time.time()
            conn.usage_count += 1
            self._save_connections()
        
        # Llamar a la herramienta
        try:
            request = {
                "jsonrpc": "2.0",
                "id": int(time.time()),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            response = await self.mcp_server.handle_request(request)
            
            if "error" in response:
                return {
                    "success": False,
                    "error": response["error"].get("message", "Error desconocido")
                }
            
            result = response.get("result", {})
            content = result.get("content", [])
            
            if content and len(content) > 0:
                text_content = content[0].get("text", "")
                try:
                    parsed_result = json.loads(text_content)
                    return parsed_result
                except:
                    return {"success": True, "result": text_content}
            
            return {"success": True, "result": result}
        
        except Exception as e:
            logger.error(f"❌ [MCP Manager] Error llamando herramienta {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_connection_by_type(self, connection_type: str) -> Optional[MCPConnection]:
        """Obtiene la primera conexión de un tipo específico."""
        for conn in self.connections.values():
            if conn.connection_type == connection_type and conn.enabled:
                return conn
        return None
    
    async def navigate_raw_data(
        self,
        data_source: str,
        query: str,
        llm: Optional[BaseLanguageModel] = None
    ) -> Dict[str, Any]:
        """
        Navega datos crudos sin conectores específicos.
        
        Potencia MCP para que JARVIS pueda navegar cualquier tipo de dato
        sin necesidad de construir conectores específicos.
        
        Args:
            data_source: Fuente de datos (path, URL, connection_id, etc.)
            query: Pregunta o consulta sobre los datos
            llm: LLM para interpretar y navegar los datos
        
        Returns:
            Resultado de la navegación
        """
        print(f"🔍 [MCP Manager] Navegando datos crudos: {data_source[:50]}...")
        
        try:
            # Intentar cargar datos desde diferentes fuentes
            raw_data = await self._load_raw_data(data_source)
            
            if raw_data is None:
                return {
                    "success": False,
                    "error": f"No se pudo cargar datos desde: {data_source}"
                }
            
            # Si hay LLM, usarlo para navegar los datos
            if llm:
                navigation_result = await self._navigate_with_llm(
                    raw_data=raw_data,
                    query=query,
                    llm=llm
                )
                return {
                    "success": True,
                    "result": navigation_result,
                    "method": "llm_navigation"
                }
            else:
                # Fallback: búsqueda básica
                return {
                    "success": True,
                    "result": self._basic_search(raw_data, query),
                    "method": "basic_search"
                }
                
        except Exception as e:
            print(f"❌ [MCP Manager] Error navegando datos: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _load_raw_data(self, data_source: str) -> Optional[Any]:
        """Carga datos crudos desde diferentes fuentes."""
        import json
        from pathlib import Path
        
        # Intentar como path de archivo
        if Path(data_source).exists():
            try:
                with open(data_source, "r", encoding="utf-8") as f:
                    # Intentar JSON
                    try:
                        return json.load(f)
                    except:
                        # Si no es JSON, leer como texto
                        f.seek(0)
                        return f.read()
            except Exception as e:
                print(f"⚠️ [MCP Manager] Error cargando archivo: {e}")
        
        # Intentar como connection_id
        if data_source in self.connections:
            conn = self.connections[data_source]
            # Aquí se podría conectar y obtener datos
            # Por ahora, retornar metadata
            return {
                "connection": conn.name,
                "type": conn.connection_type,
                "config": conn.config
            }
        
        # Intentar como URL
        if data_source.startswith(("http://", "https://")):
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(data_source) as response:
                        if response.content_type == "application/json":
                            return await response.json()
                        else:
                            return await response.text()
            except Exception as e:
                print(f"⚠️ [MCP Manager] Error cargando URL: {e}")
        
        return None
    
    async def _navigate_with_llm(
        self,
        raw_data: Any,
        query: str,
        llm: BaseLanguageModel
    ) -> Any:
        """Navega datos usando LLM para interpretarlos."""
        from langchain_core.prompts import ChatPromptTemplate
        
        # Convertir datos a string si es necesario
        if isinstance(raw_data, (dict, list)):
            import json
            data_str = json.dumps(raw_data, ensure_ascii=False, indent=2)
        else:
            data_str = str(raw_data)
        
        # Limitar tamaño para no exceder contexto
        if len(data_str) > 50000:
            data_str = data_str[:50000] + "\n... (datos truncados)"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un experto en navegar y analizar datos crudos.

Dado datos en cualquier formato (JSON, texto, CSV, etc.), puedes:
1. Entender la estructura
2. Responder preguntas sobre los datos
3. Extraer información relevante
4. Identificar patrones

Responde de forma clara y precisa."""),
            ("human", """Datos disponibles:
{data}

Pregunta: {query}

Responde la pregunta basándote en los datos proporcionados.""")
        ])
        
        try:
            response = await llm.ainvoke(prompt.format_messages(
                data=data_str,
                query=query
            ))
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            print(f"⚠️ [MCP Manager] Error navegando con LLM: {e}")
            return f"Error: {e}"
    
    def _basic_search(self, raw_data: Any, query: str) -> str:
        """Búsqueda básica sin LLM."""
        data_str = str(raw_data).lower()
        query_lower = query.lower()
        
        # Búsqueda simple de palabras clave
        keywords = query_lower.split()
        matches = []
        
        for keyword in keywords:
            if keyword in data_str:
                # Encontrar contexto alrededor de la palabra clave
                idx = data_str.find(keyword)
                start = max(0, idx - 100)
                end = min(len(data_str), idx + len(keyword) + 100)
                context = data_str[start:end]
                matches.append(context)
        
        if matches:
            return "\n\n".join(matches[:5])  # Primeros 5 matches
        else:
            return "No se encontraron coincidencias"
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del MCP Manager."""
        return {
            "total_connections": len(self.connections),
            "enabled_connections": sum(1 for c in self.connections.values() if c.enabled),
            "total_tools": len(self.mcp_server.tools),
            "connections_by_type": {
                conn_type: sum(1 for c in self.connections.values() if c.connection_type == conn_type)
                for conn_type in set(c.connection_type for c in self.connections.values())
            },
            "most_used_connections": sorted(
                [
                    {
                        "name": conn.name,
                        "type": conn.connection_type,
                        "usage_count": conn.usage_count
                    }
                    for conn in self.connections.values()
                ],
                key=lambda x: x["usage_count"],
                reverse=True
            )[:5],
            "raw_data_navigation_enabled": True
        }

