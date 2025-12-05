"""Optimizador de Tool Descriptions para MCP.

Mejora descriptions de tools siguiendo mejores prácticas de Anthropic:
- Claridad y especificidad
- Ejemplos de uso
- Nombres de parámetros no ambiguos
- Contexto explícito
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class OptimizedToolDescription:
    """Descripción optimizada de un tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    examples: List[Dict[str, Any]] = field(default_factory=list)
    category: str = "general"
    requires_context: bool = False


class MCPToolOptimizer:
    """Optimiza descriptions de tools MCP para mejor uso por agents."""
    
    def __init__(self):
        self.optimization_rules = {
            "avoid_ambiguity": True,
            "add_examples": True,
            "explicit_context": True,
            "clear_parameter_names": True,
        }
    
    def optimize_tool_description(
        self,
        tool_name: str,
        current_description: str,
        input_schema: Dict[str, Any],
        examples: Optional[List[Dict[str, Any]]] = None,
    ) -> OptimizedToolDescription:
        """Optimiza la descripción de un tool."""
        
        # Mejorar descripción
        optimized_desc = self._improve_description(
            tool_name,
            current_description,
            input_schema,
        )
        
        # Mejorar schema de input
        optimized_schema = self._improve_input_schema(input_schema)
        
        # Agregar ejemplos si no existen
        if not examples:
            examples = self._generate_examples(tool_name, optimized_schema)
        
        return OptimizedToolDescription(
            name=tool_name,
            description=optimized_desc,
            input_schema=optimized_schema,
            examples=examples,
        )
    
    def _improve_description(
        self,
        tool_name: str,
        description: str,
        input_schema: Dict[str, Any],
    ) -> str:
        """Mejora la descripción del tool."""
        improved = description
        
        # Si es muy corta o vaga, expandirla
        if len(description) < 50:
            improved = f"{description}. "
            improved += f"Este tool permite {self._extract_action(tool_name)}."
        
        # Agregar información sobre parámetros requeridos
        required_params = input_schema.get("required", [])
        if required_params:
            improved += f" Requiere: {', '.join(required_params)}."
        
        # Agregar información sobre qué retorna
        improved += f" Retorna información sobre {self._extract_return_type(tool_name)}."
        
        # Hacer más específica
        improved = improved.replace("tool", tool_name)
        improved = improved.replace("herramienta", tool_name)
        
        return improved.strip()
    
    def _improve_input_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Mejora el schema de input para evitar ambigüedad."""
        properties = schema.get("properties", {})
        improved_properties = {}
        
        for param_name, param_def in properties.items():
            # Mejorar nombres ambiguos
            improved_name = self._improve_parameter_name(param_name)
            
            # Mejorar descripción del parámetro
            param_desc = param_def.get("description", "")
            if not param_desc or len(param_desc) < 20:
                param_desc = self._generate_parameter_description(improved_name, param_def)
            
            improved_properties[improved_name] = {
                **param_def,
                "description": param_desc,
            }
        
        return {
            **schema,
            "properties": improved_properties,
        }
    
    def _improve_parameter_name(self, name: str) -> str:
        """Mejora nombres de parámetros ambiguos."""
        # Mapeo de nombres ambiguos a específicos
        improvements = {
            "user": "user_id",
            "id": "record_id",
            "data": "update_data",
            "info": "record_info",
            "params": "parameters",
            "config": "configuration",
        }
        
        name_lower = name.lower()
        if name_lower in improvements:
            return improvements[name_lower]
        
        return name
    
    def _generate_parameter_description(
        self,
        param_name: str,
        param_def: Dict[str, Any],
    ) -> str:
        """Genera descripción clara para un parámetro."""
        param_type = param_def.get("type", "string")
        
        descriptions = {
            "user_id": f"ID único del usuario (string o número). Ejemplo: 'user_123' o 12345.",
            "record_id": f"ID único del registro (string). Ejemplo: 'rec_abc123'.",
            "update_data": f"Objeto con campos a actualizar. Ejemplo: {{'name': 'Nuevo nombre', 'status': 'active'}}.",
            "query": f"Texto de búsqueda (string). Ejemplo: 'buscar cliente'.",
            "email": f"Dirección de email (string). Ejemplo: 'user@example.com'.",
        }
        
        if param_name.lower() in descriptions:
            return descriptions[param_name.lower()]
        
        # Descripción genérica basada en tipo
        type_descriptions = {
            "string": f"Texto: {param_name}",
            "number": f"Número: {param_name}",
            "boolean": f"Booleano: {param_name} (true/false)",
            "object": f"Objeto: {param_name}",
            "array": f"Lista: {param_name}",
        }
        
        return type_descriptions.get(param_type, f"{param_name} ({param_type})")
    
    def _generate_examples(
        self,
        tool_name: str,
        input_schema: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Genera ejemplos de uso del tool."""
        examples = []
        
        # Ejemplo básico
        basic_example = {}
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        
        for param_name in required[:3]:  # Solo primeros 3 requeridos
            param_def = properties.get(param_name, {})
            param_type = param_def.get("type", "string")
            
            if param_type == "string":
                if "id" in param_name.lower():
                    basic_example[param_name] = f"{param_name}_example_123"
                elif "email" in param_name.lower():
                    basic_example[param_name] = "user@example.com"
                elif "query" in param_name.lower() or "search" in param_name.lower():
                    basic_example[param_name] = "example search query"
                else:
                    basic_example[param_name] = f"example_{param_name}"
            elif param_type == "number":
                basic_example[param_name] = 123
            elif param_type == "boolean":
                basic_example[param_name] = True
        
        if basic_example:
            examples.append({
                "input": basic_example,
                "description": f"Ejemplo básico de uso de {tool_name}",
            })
        
        return examples
    
    def _extract_action(self, tool_name: str) -> str:
        """Extrae la acción principal del nombre del tool."""
        name_lower = tool_name.lower()
        
        if "create" in name_lower or "add" in name_lower:
            return "crear nuevos registros"
        elif "update" in name_lower or "edit" in name_lower:
            return "actualizar registros existentes"
        elif "get" in name_lower or "fetch" in name_lower or "read" in name_lower:
            return "obtener información"
        elif "search" in name_lower or "find" in name_lower:
            return "buscar información"
        elif "delete" in name_lower or "remove" in name_lower:
            return "eliminar registros"
        elif "send" in name_lower:
            return "enviar mensajes o notificaciones"
        else:
            return "realizar operaciones"
    
    def _extract_return_type(self, tool_name: str) -> str:
        """Extrae el tipo de retorno del tool."""
        name_lower = tool_name.lower()
        
        if "user" in name_lower:
            return "usuarios"
        elif "ticket" in name_lower or "issue" in name_lower:
            return "tickets o incidencias"
        elif "message" in name_lower:
            return "mensajes"
        elif "record" in name_lower:
            return "registros"
        elif "document" in name_lower:
            return "documentos"
        else:
            return "resultados de la operación"

