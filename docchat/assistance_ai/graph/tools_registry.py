"""Tools Registry - Registro centralizado de todas las herramientas disponibles."""

from typing import Dict, Any, Optional, Callable
from langchain_core.tools import BaseTool
from langchain.tools import tool
import json


class ToolsRegistry:
    """Registro centralizado de tools para el agente."""
    
    def __init__(self):
        self.tools: Dict[str, Any] = {}
        self.tools_by_name: Dict[str, Any] = {}
    
    def register_tool(self, name: str, tool_obj: Any):
        """Registra una herramienta."""
        self.tools[name] = tool_obj
        if hasattr(tool_obj, 'name'):
            self.tools_by_name[tool_obj.name] = tool_obj
        else:
            self.tools_by_name[name] = tool_obj
    
    def get_tool(self, name: str) -> Optional[Any]:
        """Obtiene una herramienta por nombre."""
        return self.tools.get(name) or self.tools_by_name.get(name)
    
    def get_all_tools(self) -> Dict[str, Any]:
        """Obtiene todas las herramientas."""
        return self.tools
    
    def create_order_status_tool(self, order_tool) -> BaseTool:
        """Crea tool para consultar estado de orden."""
        @tool
        def get_order_status(order_id: str) -> str:
            """Returns real-time order status.
            
            Args:
                order_id: ID de la orden a consultar
            
            Returns:
                Estado de la orden en formato JSON string
            """
            try:
                if order_tool:
                    status = order_tool.get_order_status(order_id)
                    return json.dumps(status) if isinstance(status, dict) else str(status)
                return json.dumps({"status": "unknown", "error": "Order tool not available"})
            except Exception as e:
                return json.dumps({"status": "error", "error": str(e)})
        
        return get_order_status
    
    def create_return_policy_tool(self, support_tool) -> BaseTool:
        """Crea tool para consultar política de devolución."""
        @tool
        def get_return_policy(product_category: str = "") -> str:
            """Returns official return policy text.
            
            Args:
                product_category: Categoría del producto (opcional)
            
            Returns:
                Texto de la política de devolución
            """
            try:
                if support_tool:
                    policy = support_tool.get_return_policy(product_category)
                    return policy if isinstance(policy, str) else json.dumps(policy)
                return "Política de devolución no disponible. Contacta con soporte."
            except Exception as e:
                return f"Error consultando política: {str(e)}"
        
        return get_return_policy
    
    def create_product_search_tool(self, catalog_tool) -> BaseTool:
        """Crea tool para búsqueda de productos."""
        @tool
        def search_products(query: str, limit: int = 5) -> str:
            """Search for products in the catalog.
            
            Args:
                query: Término de búsqueda
                limit: Número máximo de resultados
            
            Returns:
                Lista de productos en formato JSON string
            """
            try:
                if catalog_tool:
                    results = catalog_tool.search(query)
                    if isinstance(results, list):
                        # Limitar resultados
                        limited_results = results[:limit]
                        return json.dumps(limited_results, default=str)
                    return json.dumps(results, default=str) if results else "[]"
                return "[]"
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        return search_products
    
    def create_cart_tool(self, cart_tool) -> BaseTool:
        """Crea tool para gestión de carrito."""
        @tool
        def manage_cart(action: str, product_id: str = "", quantity: int = 1) -> str:
            """Manage shopping cart.
            
            Args:
                action: add, remove, get, clear
                product_id: ID del producto
                quantity: Cantidad
            
            Returns:
                Estado del carrito en formato JSON string
            """
            try:
                if not cart_tool:
                    return json.dumps({"error": "Cart tool not available"})
                
                if action == "get":
                    cart = cart_tool.get_cart()
                    return json.dumps(cart, default=str) if cart else "{}"
                elif action == "add" and product_id:
                    result = cart_tool.add_item(product_id, quantity)
                    return json.dumps(result, default=str) if result else "{}"
                elif action == "remove" and product_id:
                    result = cart_tool.remove_item(product_id)
                    return json.dumps(result, default=str) if result else "{}"
                elif action == "clear":
                    result = cart_tool.clear_cart()
                    return json.dumps(result, default=str) if result else "{}"
                else:
                    return json.dumps({"error": f"Invalid action: {action}"})
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        return manage_cart
    
    def create_ticket_tool(self, support_tool) -> BaseTool:
        """Crea tool para crear tickets de soporte."""
        @tool
        def create_support_ticket(subject: str, description: str, priority: str = "medium") -> str:
            """Create a support ticket.
            
            Args:
                subject: Asunto del ticket
                description: Descripción del problema
                priority: low, medium, high
            
            Returns:
                ID del ticket creado
            """
            try:
                if support_tool:
                    ticket = support_tool.create_ticket(
                        session_id="",
                        subject=subject,
                        description=description,
                        priority=priority
                    )
                    return json.dumps(ticket, default=str) if ticket else json.dumps({"error": "Failed to create ticket"})
                return json.dumps({"error": "Support tool not available"})
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        return create_support_ticket

