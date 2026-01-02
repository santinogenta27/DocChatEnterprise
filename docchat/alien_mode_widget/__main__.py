"""Script para ejecutar el servidor API de Alien Mode Widget directamente."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from docchat.config import load_config
from docchat.alien_mode_widget import AlienModeWidgetWrapper


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Alien Mode Widget API Server")
    parser.add_argument("--port", type=int, default=7865, help="Puerto del servidor (default: 7865)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host del servidor (default: 0.0.0.0)")
    
    args = parser.parse_args()
    
    print("👽 Iniciando Alien Mode Widget API Server...")
    
    # Cargar configuración
    config = load_config()
    
    # Crear wrapper
    wrapper = AlienModeWidgetWrapper(config=config)
    
    # Iniciar servidor
    wrapper.start_api_server(port=args.port, host=args.host)


if __name__ == "__main__":
    main()


