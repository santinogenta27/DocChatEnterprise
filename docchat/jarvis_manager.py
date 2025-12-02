"""
JARVIS Manager - Gestiona múltiples instancias de JARVIS
"""

from __future__ import annotations

import asyncio
from typing import Dict, Optional
from .config import AppConfig
from .jarvis_agent import JarvisAgent


class JarvisManager:
    """
    Gestiona múltiples instancias de JARVIS (una por usuario).
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.jarvis_instances: Dict[str, JarvisAgent] = {}
        self.is_running = False
    
    def get_or_create_jarvis(self, user_id: str) -> JarvisAgent:
        """Obtiene o crea una instancia de JARVIS para un usuario."""
        if user_id not in self.jarvis_instances:
            self.jarvis_instances[user_id] = JarvisAgent(
                user_id=user_id,
                config=self.config
            )
            print(f"✅ [JARVIS Manager] Instancia creada para usuario {user_id}")
        return self.jarvis_instances[user_id]
    
    def absorb_data_for_user(
        self,
        user_id: str,
        data: any,
        source: str,
        data_type: str = "document",
        metadata: Optional[Dict] = None
    ) -> str:
        """Absorbe data para un usuario específico."""
        jarvis = self.get_or_create_jarvis(user_id)
        return jarvis.absorb_data(data, source, data_type, metadata)
    
    async def start_all_continuous_loops(self, interval_minutes: int = 60):
        """Inicia loops continuos para todos los usuarios."""
        self.is_running = True
        
        tasks = []
        for user_id, jarvis in self.jarvis_instances.items():
            task = asyncio.create_task(jarvis.run_continuous_loop(interval_minutes))
            tasks.append(task)
            print(f"🚀 [JARVIS Manager] Loop iniciado para usuario {user_id}")
        
        # Esperar a que todos terminen (nunca deberían terminar)
        await asyncio.gather(*tasks)
    
    def stop_all(self):
        """Detiene todos los loops."""
        self.is_running = False
        for jarvis in self.jarvis_instances.values():
            jarvis.stop()
        print("🛑 [JARVIS Manager] Todos los loops detenidos")
    
    def get_all_dashboards(self) -> Dict[str, Dict]:
        """Obtiene datos de dashboard para todos los usuarios."""
        return {
            user_id: jarvis.get_dashboard_data()
            for user_id, jarvis in self.jarvis_instances.items()
        }

