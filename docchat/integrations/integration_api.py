"""
API Endpoints para Integraciones

Endpoints REST para consultar integraciones desde otras aplicaciones.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from .integration_manager import IntegrationManager
from .unified_search import UnifiedSearch
from .sync_worker import SyncWorker


router = APIRouter(prefix="/integrations", tags=["integrations"])


class IntegrationSearchRequest(BaseModel):
    """Request para búsqueda en integraciones."""
    query: str
    integration_types: Optional[List[str]] = None
    max_results: int = 10
    user_id: str = "default"


class IntegrationSearchResponse(BaseModel):
    """Response de búsqueda en integraciones."""
    query: str
    results: Dict[str, Any]
    total_results: int
    integrations_searched: int


class IntegrationListResponse(BaseModel):
    """Response de lista de integraciones."""
    connections: List[Dict[str, Any]]
    total: int


@router.get("/", response_model=IntegrationListResponse)
async def list_integrations(
    user_id: str = Query(default="default", description="ID del usuario")
):
    """
    Lista todas las integraciones conectadas.
    
    Ejemplo:
    ```bash
    curl http://localhost:8000/api/v1/integrations/?user_id=user123
    ```
    """
    # Esto se inicializará desde el servidor
    integration_manager: IntegrationManager = router.dependencies[0] if router.dependencies else None
    
    if not integration_manager:
        raise HTTPException(status_code=500, detail="Integration manager no inicializado")
    
    connections = integration_manager.list_connections(user_id=user_id)
    
    return IntegrationListResponse(
        connections=connections,
        total=len(connections)
    )


@router.post("/search", response_model=IntegrationSearchResponse)
async def search_integrations(request: IntegrationSearchRequest):
    """
    Busca en todas las integraciones conectadas.
    
    Ejemplo:
    ```bash
    curl -X POST http://localhost:8000/api/v1/integrations/search \
      -H "Content-Type: application/json" \
      -d '{"query": "emails de hoy", "max_results": 5}'
    ```
    """
    integration_manager: IntegrationManager = router.dependencies[0] if router.dependencies else None
    unified_search: UnifiedSearch = router.dependencies[1] if len(router.dependencies) > 1 else None
    
    if not integration_manager or not unified_search:
        raise HTTPException(status_code=500, detail="Services no inicializados")
    
    # Convertir tipos de integración
    integration_types = None
    if request.integration_types:
        from .integration_manager import IntegrationType
        try:
            integration_types = [IntegrationType(it) for it in request.integration_types]
        except ValueError:
            raise HTTPException(status_code=400, detail="Tipos de integración inválidos")
    
    # Buscar
    results = unified_search.search_all(
        query=request.query,
        user_id=request.user_id,
        integration_types=integration_types,
        max_results_per_integration=request.max_results
    )
    
    return IntegrationSearchResponse(**results)


@router.get("/{integration_type}/search")
async def search_single_integration(
    integration_type: str,
    query: str = Query(..., description="Query de búsqueda"),
    max_results: int = Query(default=10, ge=1, le=100),
    user_id: str = Query(default="default")
):
    """
    Busca en una integración específica.
    
    Ejemplo:
    ```bash
    curl "http://localhost:8000/api/v1/integrations/gmail/search?query=emails%20de%20hoy&max_results=5"
    ```
    """
    integration_manager: IntegrationManager = router.dependencies[0] if router.dependencies else None
    
    if not integration_manager:
        raise HTTPException(status_code=500, detail="Integration manager no inicializado")
    
    # Obtener conexiones del tipo especificado
    connections = integration_manager.list_connections(user_id=user_id)
    matching_connections = [c for c in connections if c["integration_type"] == integration_type and c["status"] == "active"]
    
    if not matching_connections:
        raise HTTPException(status_code=404, detail=f"No hay conexiones activas de tipo {integration_type}")
    
    # Buscar en la primera conexión activa
    connection_id = matching_connections[0]["integration_id"]
    documents = integration_manager.search_integration(
        integration_id=connection_id,
        query=query,
        max_results=max_results
    )
    
    return {
        "integration_type": integration_type,
        "query": query,
        "results": [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in documents
        ],
        "count": len(documents)
    }


@router.get("/sync/status")
async def get_sync_status():
    """
    Obtiene el estado del worker de sincronización.
    
    Ejemplo:
    ```bash
    curl http://localhost:8000/api/v1/integrations/sync/status
    ```
    """
    sync_worker: SyncWorker = router.dependencies[2] if len(router.dependencies) > 2 else None
    
    if not sync_worker:
        return {
            "status": "not_initialized",
            "message": "Worker de sincronización no inicializado"
        }
    
    stats = sync_worker.get_stats()
    
    return {
        "status": "running" if sync_worker.running else "stopped",
        "sync_interval_minutes": sync_worker.sync_interval // 60,
        "stats": stats
    }


@router.post("/sync/trigger")
async def trigger_sync():
    """
    Dispara una sincronización manual inmediata.
    
    Ejemplo:
    ```bash
    curl -X POST http://localhost:8000/api/v1/integrations/sync/trigger
    ```
    """
    sync_worker: SyncWorker = router.dependencies[2] if len(router.dependencies) > 2 else None
    
    if not sync_worker:
        raise HTTPException(status_code=500, detail="Worker de sincronización no inicializado")
    
    # Ejecutar sincronización en thread separado para no bloquear
    import threading
    thread = threading.Thread(target=sync_worker.sync_all_integrations, daemon=True)
    thread.start()
    
    return {
        "status": "triggered",
        "message": "Sincronización iniciada en segundo plano"
    }


@router.get("/cache/{integration_type}")
async def get_cached_data(
    integration_type: str,
    query: Optional[str] = Query(default=None),
    user_id: str = Query(default="default")
):
    """
    Obtiene datos del caché de una integración.
    
    Ejemplo:
    ```bash
    curl "http://localhost:8000/api/v1/integrations/cache/gmail?query=emails"
    ```
    """
    integration_manager: IntegrationManager = router.dependencies[0] if router.dependencies else None
    sync_worker: SyncWorker = router.dependencies[2] if len(router.dependencies) > 2 else None
    
    if not integration_manager or not sync_worker:
        raise HTTPException(status_code=500, detail="Services no inicializados")
    
    # Obtener conexión
    connections = integration_manager.list_connections(user_id=user_id)
    matching_connections = [c for c in connections if c["integration_type"] == integration_type and c["status"] == "active"]
    
    if not matching_connections:
        raise HTTPException(status_code=404, detail=f"No hay conexiones activas de tipo {integration_type}")
    
    connection_id = matching_connections[0]["integration_id"]
    documents = sync_worker.get_cached_documents(integration_type, connection_id, query or "")
    
    return {
        "integration_type": integration_type,
        "query": query,
        "cached_documents": [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in documents
        ],
        "count": len(documents)
    }

