#!/usr/bin/env python3
"""
Script de Sincronización - Copia todos los cambios a DocChatEnterprise local
"""

import shutil
from pathlib import Path

# Directorios
SOURCE_DIR = Path(r"C:\Users\Random\Downloads\uploaded_files")
TARGET_DIR = Path(r"C:\Users\Random\DocChatEnterprise")

# Archivos a sincronizar
FILES_TO_SYNC = [
    "app.py",
    "docchat/banking_mode.py",
    "docchat/event_horizon_mode.py",
    "docchat/__init__.py",
    "docchat/kafka_bridge.py",
    "docchat/event_bus_mode.py",
    "docchat/event_storage_mode.py",
    "docchat/extasis_mode.py",
    "docchat/extraction_x_mode.py",
    "docchat/data_point_mode.py",
    "docchat/judge_agent_mode.py",
]

def sync_file(source_path: Path, target_path: Path) -> dict:
    """Sincroniza un archivo."""
    try:
        if not source_path.exists():
            return {"status": "source_not_found", "file": str(source_path)}
        
        # Crear directorio destino si no existe
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copiar archivo
        shutil.copy2(source_path, target_path)
        
        return {
            "status": "synced",
            "file": str(target_path.relative_to(TARGET_DIR)),
            "size": source_path.stat().st_size
        }
    except Exception as e:
        return {"status": "error", "file": str(source_path), "error": str(e)}

def sync_all_files():
    """Sincroniza todos los archivos."""
    print("=" * 70)
    print("🔄 SINCRONIZACIÓN A LOCAL - DocChatEnterprise")
    print("=" * 70)
    print()
    print(f"📂 Origen: {SOURCE_DIR}")
    print(f"📂 Destino: {TARGET_DIR}")
    print()
    
    results = []
    
    for file_path_str in FILES_TO_SYNC:
        source_path = SOURCE_DIR / file_path_str
        target_path = TARGET_DIR / file_path_str
        
        result = sync_file(source_path, target_path)
        results.append(result)
        
        if result["status"] == "synced":
            size_kb = result["size"] / 1024
            print(f"✅ {file_path_str} ({size_kb:.2f} KB)")
        elif result["status"] == "source_not_found":
            print(f"⚠️ {file_path_str} (no encontrado en origen)")
        else:
            print(f"❌ {file_path_str} (error: {result.get('error', 'unknown')})")
    
    successful = len([r for r in results if r["status"] == "synced"])
    total = len(results)
    
    print()
    print("=" * 70)
    print(f"✅ Sincronización completada: {successful}/{total} archivos")
    print("=" * 70)
    
    return results

if __name__ == "__main__":
    sync_all_files()










