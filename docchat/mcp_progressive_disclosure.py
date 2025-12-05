"""Progressive Disclosure para MCP Tools: Carga on-demand de tools.

Implementa carga progresiva de tools MCP en lugar de cargar todos upfront.
Basado en las mejores prácticas de Anthropic para eficiencia de tokens.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass


class ToolDetailLevel(str, Enum):
    """Nivel de detalle para tool descriptions."""
    NAME_ONLY = "name_only"  # Solo nombre
    NAME_DESCRIPTION = "name_description"  # Nombre + descripción
    FULL = "full"  # Definición completa con schemas


class ResponseFormat(str, Enum):
    """Formato de respuesta para tools."""
    CONCISE = "concise"  # Solo información esencial
    DETAILED = "detailed"  # Información completa con IDs técnicos


@dataclass
class ToolSearchResult:
    """Resultado de búsqueda de tool."""
    tool_name: str
    description: str
    category: str
    detail_level: ToolDetailLevel
    full_definition: Optional[Dict[str, Any]] = None


class MCPProgressiveDisclosure:
    """Sistema de carga progresiva de tools MCP."""
    
    def __init__(self, mcp_manager: Any):
        self.mcp_manager = mcp_manager
        
        # Cache de tools cargados
        self.loaded_tools: Dict[str, Dict[str, Any]] = {}  # tool_name -> full definition
        
        # Estadísticas
        self.stats = {
            "tools_searched": 0,
            "tools_loaded": 0,
            "tokens_saved": 0,
        }
    
    def search_tools(
        self,
        query: str,
        category: Optional[str] = None,
        detail_level: ToolDetailLevel = ToolDetailLevel.NAME_DESCRIPTION,
        limit: int = 10,
    ) -> List[ToolSearchResult]:
        """Busca tools relevantes sin cargar todas las definiciones."""
        self.stats["tools_searched"] += 1
        
        # Obtener lista de tools disponibles (solo metadata básica)
        all_tools = self.mcp_manager.list_available_tools()
        
        results = []
        query_lower = query.lower()
        
        for tool in all_tools:
            tool_name = tool.get("name", "")
            tool_desc = tool.get("description", "")
            tool_category = tool.get("category", "general")
            
            # Filtrar por categoría
            if category and tool_category != category:
                continue
            
            # Buscar match en nombre o descripción
            matches = (
                query_lower in tool_name.lower() or
                query_lower in tool_desc.lower() or
                query_lower in tool_category.lower()
            )
            
            if not matches:
                continue
            
            # Construir resultado según detail_level
            result = ToolSearchResult(
                tool_name=tool_name,
                description=tool_desc,
                category=tool_category,
                detail_level=detail_level,
            )
            
            # Si se necesita full definition, cargarla
            if detail_level == ToolDetailLevel.FULL:
                full_def = self._load_tool_definition(tool_name)
                result.full_definition = full_def
            
            results.append(result)
            
            if len(results) >= limit:
                break
        
        return results
    
    def _load_tool_definition(self, tool_name: str) -> Dict[str, Any]:
        """Carga la definición completa de un tool (con cache)."""
        if tool_name in self.loaded_tools:
            return self.loaded_tools[tool_name]
        
        # Obtener definición completa del MCP manager
        all_tools = self.mcp_manager.list_available_tools()
        for tool in all_tools:
            if tool.get("name") == tool_name:
                self.loaded_tools[tool_name] = tool
                self.stats["tools_loaded"] += 1
                # Estimar tokens ahorrados (aproximado)
                self.stats["tokens_saved"] += len(str(tool)) // 4  # ~4 chars per token
                return tool
        
        return {}
    
    def get_tool_definition(
        self,
        tool_name: str,
        detail_level: ToolDetailLevel = ToolDetailLevel.FULL,
    ) -> Dict[str, Any]:
        """Obtiene definición de tool con nivel de detalle especificado."""
        full_def = self._load_tool_definition(tool_name)
        
        if detail_level == ToolDetailLevel.NAME_ONLY:
            return {"name": full_def.get("name", tool_name)}
        
        elif detail_level == ToolDetailLevel.NAME_DESCRIPTION:
            return {
                "name": full_def.get("name", tool_name),
                "description": full_def.get("description", ""),
                "category": full_def.get("category", "general"),
            }
        
        else:  # FULL
            return full_def
    
    def format_tool_response(
        self,
        response: Any,
        response_format: ResponseFormat = ResponseFormat.CONCISE,
    ) -> Any:
        """Formatea respuesta de tool según formato solicitado."""
        if response_format == ResponseFormat.CONCISE:
            return self._make_concise(response)
        else:
            return response
    
    def _make_concise(self, response: Any) -> Any:
        """Convierte respuesta a formato conciso (solo información esencial)."""
        if isinstance(response, dict):
            concise = {}
            
            # Campos esenciales que siempre incluir
            essential_fields = [
                "status", "success", "message", "result", "content",
                "name", "title", "summary", "count", "id",
            ]
            
            for key, value in response.items():
                # Incluir campos esenciales
                if any(essential in key.lower() for essential in essential_fields):
                    concise[key] = value
                # Excluir campos técnicos innecesarios
                elif key.lower() in ["uuid", "mime_type", "256px_image_url", "technical_id"]:
                    continue
                # Incluir otros campos si son strings cortos o números
                elif isinstance(value, (str, int, float, bool)) and len(str(value)) < 100:
                    concise[key] = value
                elif isinstance(value, list) and len(value) <= 5:
                    concise[key] = value
            
            return concise
        
        elif isinstance(response, list):
            # Limitar lista a primeros elementos
            return response[:10] if len(response) > 10 else response
        
        else:
            return response
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de uso."""
        return {
            "tools_searched": self.stats["tools_searched"],
            "tools_loaded": self.stats["tools_loaded"],
            "tokens_saved_estimate": self.stats["tokens_saved"],
            "cache_size": len(self.loaded_tools),
        }

