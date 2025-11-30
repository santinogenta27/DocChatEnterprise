"""
Handler Base para Integraciones

Clase base para todos los handlers de integraciones.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional
from langchain_core.documents import Document


class BaseIntegrationHandler(ABC):
    """Clase base para handlers de integraciones."""
    
    def __init__(self, config):
        self.config = config
    
    @abstractmethod
    def search(
        self,
        query: str,
        access_token: str,
        max_results: int = 10
    ) -> List[Document]:
        """
        Busca en la integración.
        
        Args:
            query: Consulta de búsqueda
            access_token: Token de acceso OAuth
            max_results: Máximo de resultados
        
        Returns:
            Lista de documentos encontrados
        """
        pass
    
    def refresh_token(self, refresh_token: str) -> Optional[str]:
        """
        Refresca el token de acceso.
        
        Args:
            refresh_token: Token de refresco
        
        Returns:
            Nuevo access_token o None si falla
        """
        return None


