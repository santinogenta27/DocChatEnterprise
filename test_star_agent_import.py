"""Test script para verificar que STAR AGENT se importa correctamente."""

import os
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

# Cargar .env
from dotenv import load_dotenv
load_dotenv()

print("Verificando API Keys...")
print(f"OPENAI_API_KEY: {'EXISTE' if os.getenv('OPENAI_API_KEY') else 'NO EXISTE'}")
print(f"GROQ_API_KEY: {'EXISTE' if os.getenv('GROQ_API_KEY') else 'NO EXISTE'}")

print("\nIntentando importar StarAgentMode...")
try:
    from docchat.star_agent import StarAgentMode
    print("✅ Import exitoso: StarAgentMode")
    
    # Intentar inicializar
    print("\nIntentando inicializar StarAgentMode...")
    from docchat.config import load_config
    config = load_config()
    star_agent = StarAgentMode(config=config)
    print("✅ STAR AGENT inicializado correctamente!")
    
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

