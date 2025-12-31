"""
Script para lanzar la UI de Gradio de STAR AGENT.

Ejecuta: python run_star_agent_ui.py
"""

from docchat.star_agent import StarAgentMode
from docchat.config import load_config

def main():
    """Lanza la UI de Gradio de STAR AGENT."""
    print("🚀 Iniciando STAR AGENT...")
    
    # Cargar configuración
    config = load_config()
    
    # Inicializar STAR AGENT
    star_agent = StarAgentMode(config=config)
    
    print("✅ STAR AGENT inicializado")
    print("📱 Lanzando UI de Gradio...")
    
    # Lanzar UI de Gradio
    demo = star_agent.get_gradio_interface()
    
    # Intentar encontrar un puerto disponible
    import socket
    def find_free_port(start_port=7860, max_attempts=10):
        for i in range(max_attempts):
            port = start_port + i
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind(('127.0.0.1', port))
                sock.close()
                return port
            except OSError:
                sock.close()
                continue
        return start_port  # Si no encuentra, intenta el original
    
    port = find_free_port(7860)
    print(f"📡 Usando puerto: {port}")
    
    demo.launch(
        share=True,  # Cambiar a True para crear link público (necesario en algunos entornos)
        server_name="127.0.0.1",
        server_port=port,
        show_error=True
    )

if __name__ == "__main__":
    main()

