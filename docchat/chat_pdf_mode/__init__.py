# ChatPDF Mode Package
# Importar desde el mÃ³dulo chat_pdf_mode.py en el directorio padre

import sys
from pathlib import Path

# Obtener la ruta del archivo chat_pdf_mode.py en el directorio padre
parent_dir = Path(__file__).parent.parent
chat_pdf_module_path = parent_dir / "chat_pdf_mode.py"

if chat_pdf_module_path.exists():
    # Agregar el directorio padre al path si no estÃ¡
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    # Importar usando importlib para evitar conflictos
    import importlib.util
    spec = importlib.util.spec_from_file_location("docchat.chat_pdf_mode_module", str(chat_pdf_module_path))
    chat_pdf_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(chat_pdf_module)
    
    # Exportar las clases y funciones
    ChatPDFMode = chat_pdf_module.ChatPDFMode
    run_chat_pdf_mode = chat_pdf_module.run_chat_pdf_mode
    get_chat_pdf_mode = chat_pdf_module.get_chat_pdf_mode
    
    __all__ = ["ChatPDFMode", "run_chat_pdf_mode", "get_chat_pdf_mode"]
else:
    # Si el archivo no existe, dejar vacÃ­o
    __all__ = []
