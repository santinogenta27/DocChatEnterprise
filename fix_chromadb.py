"""
Script para limpiar ChromaDB corrupto
Ejecuta este script si ChromaDB da errores de corrupción
"""

import shutil
from pathlib import Path

# Ruta de ChromaDB
chroma_path = Path("data/chroma_db")

if chroma_path.exists():
    print(f"🗑️ Eliminando base de datos ChromaDB corrupta en: {chroma_path}")
    try:
        shutil.rmtree(chroma_path)
        print("✅ Base de datos ChromaDB eliminada. Se recreará automáticamente al iniciar la app.")
    except Exception as e:
        print(f"❌ Error eliminando ChromaDB: {e}")
else:
    print("ℹ️ No hay base de datos ChromaDB para limpiar.")

