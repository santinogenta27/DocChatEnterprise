"""
Script para ejecutar el servidor FastAPI del widget STAR AGENT.

Uso:
    python run_widget_server.py

El servidor se ejecutará en http://localhost:8000
El widget estará disponible en http://localhost:8000/widget
API REST: http://localhost:8000/api/widget/chat
WebSocket: ws://localhost:8000/ws/widget
"""

import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from docchat.config import load_config
from docchat.star_agent import StarAgentMode

try:
    import uvicorn
except ImportError:
    print("❌ uvicorn no está instalado. Instala con: pip install uvicorn")
    sys.exit(1)

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    print("❌ fastapi no está instalado. Instala con: pip install fastapi")
    sys.exit(1)


def main():
    """Ejecuta el servidor del widget STAR AGENT."""
    print("🚀 Iniciando servidor STAR AGENT Widget...")
    
    # Cargar configuración
    config = load_config()
    
    # Inicializar STAR AGENT
    print("📦 Inicializando STAR AGENT...")
    star_agent = StarAgentMode(config=config)
    print("✅ STAR AGENT inicializado")
    
    # Crear aplicación FastAPI del widget
    widget_app = star_agent.get_widget_app()
    
    if not widget_app:
        print("❌ No se pudo crear la aplicación del widget")
        sys.exit(1)
    
    # Montar el router de API si existe
    try:
        api_router = star_agent.get_api_router()
        widget_app.include_router(api_router)
        print("✅ Router de API incluido")
    except Exception as e:
        print(f"⚠️ No se pudo incluir router de API: {e}")
    
    # Configurar CORS globalmente
    widget_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # En producción, especificar dominios
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    print("\n" + "="*60)
    print("⭐ STAR AGENT WIDGET SERVER")
    print("="*60)
    print("\n📍 Endpoints disponibles:")
    print("   - Widget HTML:     http://localhost:8000/widget")
    print("   - API REST Chat:    http://localhost:8000/api/widget/chat")
    print("   - WebSocket:        ws://localhost:8000/ws/widget")
    print("   - Métricas:         http://localhost:8000/api/widget/metrics")
    print("   - Health Check:     http://localhost:8000/api/widget/health")
    print("\n🚀 Servidor iniciando en http://localhost:8000")
    print("="*60 + "\n")
    
    # Ejecutar servidor
    uvicorn.run(
        widget_app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False,  # Desactivar reload en producción
    )


if __name__ == "__main__":
    main()

