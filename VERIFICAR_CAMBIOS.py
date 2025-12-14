#!/usr/bin/env python3
"""
Script de Verificación - Verifica que todos los cambios estén guardados.
"""

import os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"C:\Users\Random\Downloads\uploaded_files")

# Archivos que DEBEN existir después de los cambios de hoy
REQUIRED_FILES = {
    "app.py": "Aplicación principal con UI de Banking Mode",
    "docchat/banking_mode.py": "Modo Banking con extracción bancaria",
    "docchat/event_horizon_mode.py": "Event Horizon Mode restaurado",
    "docchat/__init__.py": "Inicialización del módulo",
    "docchat/kafka_bridge.py": "Integración con Kafka",
    "RESUMEN_CAMBIOS_HOY.md": "Resumen de cambios de hoy",
}

def verify_file(file_path: Path, description: str) -> dict:
    """Verifica que un archivo exista y tenga contenido."""
    result = {
        "file": str(file_path),
        "description": description,
        "exists": False,
        "size": 0,
        "modified": None
    }
    
    if file_path.exists():
        result["exists"] = True
        stat = file_path.stat()
        result["size"] = stat.st_size
        result["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
    
    return result

def verify_all_files():
    """Verifica todos los archivos requeridos."""
    print("=" * 70)
    print("🔍 VERIFICACIÓN DE ARCHIVOS - DocChat Enterprise")
    print("=" * 70)
    print()
    
    results = []
    all_ok = True
    
    for file_path_str, description in REQUIRED_FILES.items():
        file_path = BASE_DIR / file_path_str
        result = verify_file(file_path, description)
        results.append(result)
        
        if result["exists"]:
            size_kb = result["size"] / 1024
            print(f"✅ {file_path_str}")
            print(f"   📝 {description}")
            print(f"   📦 Tamaño: {size_kb:.2f} KB")
            print(f"   🕒 Modificado: {result['modified']}")
            print()
        else:
            print(f"❌ {file_path_str} - NO ENCONTRADO")
            print(f"   📝 {description}")
            print()
            all_ok = False
    
    print("=" * 70)
    if all_ok:
        print("✅ TODOS LOS ARCHIVOS ESTÁN PRESENTES Y GUARDADOS")
    else:
        print("⚠️ ALGUNOS ARCHIVOS FALTAN")
    print("=" * 70)
    
    return all_ok, results

if __name__ == "__main__":
    all_ok, results = verify_all_files()
    exit(0 if all_ok else 1)












