"""
Worker de Sincronización en Tiempo Real

Sincroniza datos de todas las integraciones conectadas periódicamente.
"""

from __future__ import annotations

import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import json

from langchain_core.documents import Document

from .integration_manager import IntegrationManager


class SyncWorker:
    """
    Worker que sincroniza datos de integraciones en tiempo real.
    
    Funciona en segundo plano, revisando cada X minutos las apps conectadas
    y trayendo información nueva.
    """
    
    def __init__(self, integration_manager: IntegrationManager, sync_interval_minutes: int = 15):
        """
        Inicializa el worker.
        
        Args:
            integration_manager: Gestor de integraciones
            sync_interval_minutes: Intervalo de sincronización en minutos (default: 15)
        """
        self.integration_manager = integration_manager
        self.sync_interval = sync_interval_minutes * 60  # Convertir a segundos
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
        
        # Directorio para caché
        self.cache_dir = Path(integration_manager.config.memory_dir) / "integrations" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Estadísticas
        self.stats = {
            "last_sync": None,
            "total_syncs": 0,
            "last_sync_results": {}
        }
    
    def start(self):
        """Inicia el worker en segundo plano."""
        if self.running:
            print("⚠️ Worker ya está corriendo")
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        print(f"✅ Worker de sincronización iniciado (cada {self.sync_interval // 60} minutos)")
    
    def stop(self):
        """Detiene el worker."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        print("🛑 Worker de sincronización detenido")
    
    def _worker_loop(self):
        """Loop principal del worker."""
        while self.running:
            try:
                print(f"🔄 [Worker] Iniciando sincronización... ({datetime.now().strftime('%H:%M:%S')})")
                self.sync_all_integrations()
                self.stats["last_sync"] = datetime.now().isoformat()
                self.stats["total_syncs"] += 1
                self._save_stats()
                
                # Esperar hasta la próxima sincronización
                time.sleep(self.sync_interval)
            except Exception as e:
                print(f"❌ [Worker] Error en sincronización: {e}")
                import traceback
                traceback.print_exc()
                # Esperar un poco antes de reintentar
                time.sleep(60)
    
    def sync_all_integrations(self):
        """Sincroniza todas las integraciones conectadas."""
        connections = self.integration_manager.list_connections(user_id="user")
        active_connections = [c for c in connections if c["status"] == "active"]
        
        if not active_connections:
            print("ℹ️ [Worker] No hay conexiones activas para sincronizar")
            return
        
        print(f"🔄 [Worker] Sincronizando {len(active_connections)} integraciones...")
        
        sync_results = {}
        
        for connection in active_connections:
            integration_id = connection["integration_id"]
            integration_type = connection["integration_type"]
            
            try:
                # Buscar datos nuevos (últimos 24 horas)
                print(f"  📥 Sincronizando {integration_type}...")
                
                # Query genérica para obtener datos recientes
                query = self._get_recent_query(integration_type)
                
                docs = self.integration_manager.search_integration(
                    integration_id=integration_id,
                    query=query,
                    max_results=50  # Obtener más datos en sincronización
                )
                
                # Guardar en caché
                if docs:
                    self._save_to_cache(integration_type, integration_id, docs)
                    sync_results[integration_type] = len(docs)
                    print(f"  ✅ {integration_type}: {len(docs)} elementos sincronizados")
                else:
                    sync_results[integration_type] = 0
                    print(f"  ℹ️ {integration_type}: Sin datos nuevos")
                
            except Exception as e:
                print(f"  ❌ Error sincronizando {integration_type}: {e}")
                sync_results[integration_type] = f"Error: {str(e)}"
        
        self.stats["last_sync_results"] = sync_results
        print(f"✅ [Worker] Sincronización completada")
    
    def _get_recent_query(self, integration_type: str) -> str:
        """Obtiene query apropiada para buscar datos recientes según el tipo."""
        from datetime import datetime, timedelta
        
        today = datetime.now().date()
        
        queries = {
            "gmail": f"after:{today.strftime('%Y/%m/%d')}",
            "outlook": f"receivedDateTime ge {today.isoformat()}",
            "slack": "in:all",  # Slack no tiene búsqueda por fecha fácil
            "github": "is:open updated:>=" + today.isoformat(),
            "jira": f'updated >= "{today.isoformat()}"',
            "salesforce": "",  # Salesforce usa SOSL diferente
            "zendesk": f"updated>{today.isoformat()}",
            "servicenow": f"sys_updated_on>={today.isoformat()}",
            "notion": "",  # Notion busca por relevancia
            "confluence": f"lastModified >= {today.isoformat()}",
        }
        
        return queries.get(integration_type, "in:all")
    
    def _save_to_cache(self, integration_type: str, integration_id: str, documents: List[Document]):
        """Guarda documentos en caché."""
        cache_file = self.cache_dir / f"{integration_type}_{integration_id}.json"
        
        try:
            # Cargar caché existente
            existing_docs = []
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    existing_docs = [
                        Document(
                            page_content=item["content"],
                            metadata=item["metadata"]
                        )
                        for item in data.get("documents", [])
                    ]
            
            # Combinar y deduplicar (por message_id, issue_id, etc.)
            existing_ids = set()
            for doc in existing_docs:
                doc_id = doc.metadata.get("message_id") or doc.metadata.get("issue_id") or doc.metadata.get("ticket_id") or doc.metadata.get("page_id")
                if doc_id:
                    existing_ids.add(str(doc_id))
            
            # Agregar solo documentos nuevos
            new_docs = []
            for doc in documents:
                doc_id = doc.metadata.get("message_id") or doc.metadata.get("issue_id") or doc.metadata.get("ticket_id") or doc.metadata.get("page_id")
                if doc_id and str(doc_id) not in existing_ids:
                    new_docs.append(doc)
                    existing_ids.add(str(doc_id))
            
            # Combinar
            all_docs = existing_docs + new_docs
            
            # Limitar tamaño del caché (últimos 1000 documentos)
            if len(all_docs) > 1000:
                all_docs = all_docs[-1000:]
            
            # Guardar
            cache_data = {
                "integration_type": integration_type,
                "integration_id": integration_id,
                "last_updated": datetime.now().isoformat(),
                "document_count": len(all_docs),
                "documents": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    }
                    for doc in all_docs
                ]
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            print(f"⚠️ Error guardando caché para {integration_type}: {e}")
    
    def get_cached_documents(self, integration_type: str, integration_id: str, query: str = "") -> List[Document]:
        """Obtiene documentos del caché, opcionalmente filtrados por query."""
        cache_file = self.cache_dir / f"{integration_type}_{integration_id}.json"
        
        if not cache_file.exists():
            return []
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                documents = [
                    Document(
                        page_content=item["content"],
                        metadata=item["metadata"]
                    )
                    for item in data.get("documents", [])
                ]
            
            # Filtrar por query si se proporciona
            if query:
                query_lower = query.lower()
                documents = [
                    doc for doc in documents
                    if query_lower in doc.page_content.lower() or
                       query_lower in str(doc.metadata.get("subject", "")).lower() or
                       query_lower in str(doc.metadata.get("title", "")).lower()
                ]
            
            return documents
        except Exception as e:
            print(f"⚠️ Error leyendo caché para {integration_type}: {e}")
            return []
    
    def _save_stats(self):
        """Guarda estadísticas del worker."""
        stats_file = self.cache_dir / "worker_stats.json"
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error guardando estadísticas: {e}")
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas del worker."""
        return self.stats.copy()


