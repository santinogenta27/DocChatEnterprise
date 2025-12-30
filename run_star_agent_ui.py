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
    demo.launch(
        share=False,  # Cambiar a True para crear link público
        server_name="127.0.0.1",
        server_port=7860,
        show_error=True
    )

if __name__ == "__main__":
    main()

