"""
Búsqueda Unificada

Busca en todas las integraciones conectadas simultáneamente.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from langchain_core.documents import Document

from .integration_manager import IntegrationManager, IntegrationType


class UnifiedSearch:
    """
    Búsqueda unificada que busca en todas las apps conectadas.
    
    Cuando el usuario pregunta algo, busca automáticamente en:
    - Gmail (emails)
    - Slack (mensajes)
    - Salesforce (clientes, ventas)
    - Jira (tareas)
    - GitHub (código, issues)
    - Y todas las demás apps conectadas
    """
    
    def __init__(self, integration_manager: IntegrationManager, sync_worker=None):
        self.integration_manager = integration_manager
        self.sync_worker = sync_worker  # Worker opcional para usar caché
    
    def search_all(
        self,
        query: str,
        user_id: str,
        integration_types: Optional[List[IntegrationType]] = None,
        max_results_per_integration: int = 5
    ) -> Dict[str, Any]:
        """
        Busca en todas las integraciones conectadas.
        
        Args:
            query: Consulta del usuario
            user_id: ID del usuario
            integration_types: Tipos de integraciones a buscar (None = todas)
            max_results_per_integration: Máx resultados por integración
        
        Returns:
            Dict con resultados organizados por integración
        """
        # Obtener conexiones activas del usuario
        connections = self.integration_manager.list_connections(user_id=user_id)
        active_connections = [c for c in connections if c["status"] == "active"]
        
        if not active_connections:
            print("⚠️ No hay conexiones activas para buscar")
            return {
                "query": query,
                "results": {},
                "total_results": 0,
                "integrations_searched": 0
            }
        
        # Filtrar por tipos si se especifican
        if integration_types:
            active_connections = [
                c for c in active_connections
                if IntegrationType(c["integration_type"]) in integration_types
            ]
        
        # Ordenar por fecha de conexión (más recientes primero) para priorizar tokens frescos
        active_connections.sort(key=lambda x: x.get("connected_at", ""), reverse=True)
        
        print(f"🔍 Buscando en {len(active_connections)} conexiones activas...")
        
        # Buscar en cada integración
        results = {}
        total_results = 0
        
        for connection in active_connections:
            integration_id = connection["integration_id"]
            integration_type = connection["integration_type"]
            
            print(f"🔍 Buscando en {integration_type} (ID: {integration_id[:8]}...)")
            
            try:
                # Intentar usar caché primero si está disponible
                docs = []
                if self.sync_worker:
                    cached_docs = self.sync_worker.get_cached_documents(integration_type, integration_id, query)
                    if cached_docs:
                        docs = cached_docs[:max_results_per_integration]
                        print(f"📦 {integration_type}: {len(docs)} resultados desde caché")
                
                # Si no hay caché o no es suficiente, buscar en tiempo real
                if not docs or len(docs) < max_results_per_integration:
                    realtime_docs = self.integration_manager.search_integration(
                        integration_id=integration_id,
                        query=query,
                        max_results=max_results_per_integration
                    )
                    
                    # Combinar resultados (caché + tiempo real), evitando duplicados
                    if realtime_docs:
                        existing_ids = set()
                        for doc in docs:
                            doc_id = doc.metadata.get("message_id") or doc.metadata.get("issue_id") or doc.metadata.get("ticket_id") or doc.metadata.get("page_id")
                            if doc_id:
                                existing_ids.add(str(doc_id))
                        
                        for doc in realtime_docs:
                            doc_id = doc.metadata.get("message_id") or doc.metadata.get("issue_id") or doc.metadata.get("ticket_id") or doc.metadata.get("page_id")
                            if not doc_id or str(doc_id) not in existing_ids:
                                docs.append(doc)
                                if doc_id:
                                    existing_ids.add(str(doc_id))
                        
                        if realtime_docs:
                            print(f"🔄 {integration_type}: {len(realtime_docs)} resultados en tiempo real agregados")
                
                if docs:
                    results[integration_type] = {
                        "documents": docs[:max_results_per_integration],
                        "count": len(docs),
                        "integration_id": integration_id,
                        "from_cache": bool(self.sync_worker and cached_docs) if 'cached_docs' in locals() else False
                    }
                    total_results += len(docs)
                    print(f"✅ {integration_type}: {len(docs)} resultados totales encontrados")
                else:
                    print(f"ℹ️ {integration_type}: 0 resultados (puede ser token expirado o sin coincidencias)")
            except Exception as e:
                print(f"❌ Error buscando en {integration_type}: {e}")
                import traceback
                traceback.print_exc()
                results[integration_type] = {
                    "error": str(e),
                    "count": 0
                }
        
        return {
            "query": query,
            "results": results,
            "total_results": total_results,
            "integrations_searched": len(active_connections)
        }
    
    def search_and_combine(
        self,
        query: str,
        user_id: str,
        max_total_results: int = 20
    ) -> List[Document]:
        """
        Busca en todas las integraciones y combina resultados.
        
        Útil para RAG: obtiene documentos de todas las apps y los usa como contexto.
        
        Args:
            query: Consulta del usuario
            user_id: ID del usuario
            max_total_results: Máximo total de resultados
        
        Returns:
            Lista de documentos combinados de todas las integraciones
        """
        search_results = self.search_all(query, user_id)
        
        # Combinar todos los documentos
        all_documents = []
        for integration_type, data in search_results["results"].items():
            if "documents" in data:
                # Agregar metadata de la integración
                for doc in data["documents"]:
                    doc.metadata["integration_type"] = integration_type
                    doc.metadata["integration_id"] = data.get("integration_id", "")
                all_documents.extend(data["documents"])
        
        # Limitar resultados totales
        return all_documents[:max_total_results]

