#!/usr/bin/env python3
"""
Script de Respaldo Completo - DocChat Enterprise
Guarda todos los archivos modificados en el directorio de trabajo.
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Directorio base
BASE_DIR = Path(r"C:\Users\Random\Downloads\uploaded_files")
BACKUP_DIR = BASE_DIR / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Archivos críticos a respaldar
CRITICAL_FILES = [
    "app.py",
    "docchat/banking_mode.py",
    "docchat/event_horizon_mode.py",
    "docchat/event_bus_mode.py",
    "docchat/event_storage_mode.py",
    "docchat/extasis_mode.py",
    "docchat/extraction_x_mode.py",
    "docchat/data_point_mode.py",
    "docchat/judge_agent_mode.py",
    "docchat/alien_mode.py",
    "docchat/__init__.py",
    "docchat/kafka_bridge.py",
    "docchat/enterprise_connectors/connector_manager.py",
    "docchat/enterprise_connectors/sharepoint_connector.py",
    "docchat/enterprise_connectors/aws_s3_connector.py",
    "docchat/enterprise_connectors/google_drive_connector.py",
    "docchat/enterprise_connectors/salesforce_connector.py",
    "docchat/enterprise_connectors/servicenow_connector.py",
]

def backup_file(file_path: Path) -> Dict[str, any]:
    """Respalda un archivo individual."""
    try:
        if not file_path.exists():
            return {"status": "not_found", "file": str(file_path)}
        
        # Crear estructura de directorios en backup
        relative_path = file_path.relative_to(BASE_DIR)
        backup_path = BACKUP_DIR / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copiar archivo
        shutil.copy2(file_path, backup_path)
        
        return {
            "status": "backed_up",
            "file": str(relative_path),
            "size": file_path.stat().st_size,
            "backup_path": str(backup_path)
        }
    except Exception as e:
        return {"status": "error", "file": str(file_path), "error": str(e)}

def backup_all_critical_files():
    """Respalda todos los archivos críticos."""
    results = []
    
    print(f"📦 Iniciando respaldo en: {BACKUP_DIR}")
    print(f"📁 Directorio base: {BASE_DIR}\n")
    
    for file_path_str in CRITICAL_FILES:
        file_path = BASE_DIR / file_path_str
        result = backup_file(file_path)
        results.append(result)
        
        if result["status"] == "backed_up":
            print(f"✅ {file_path_str} ({result['size']} bytes)")
        elif result["status"] == "not_found":
            print(f"⚠️ {file_path_str} (no encontrado)")
        else:
            print(f"❌ {file_path_str} (error: {result.get('error', 'unknown')})")
    
    # Guardar metadata del respaldo
    metadata = {
        "backup_date": datetime.now().isoformat(),
        "backup_dir": str(BACKUP_DIR),
        "base_dir": str(BASE_DIR),
        "files": results,
        "total_files": len(results),
        "successful": len([r for r in results if r["status"] == "backed_up"]),
        "failed": len([r for r in results if r["status"] == "error"]),
        "not_found": len([r for r in results if r["status"] == "not_found"])
    }
    
    metadata_path = BACKUP_DIR / "backup_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Resumen:")
    print(f"   ✅ Exitosos: {metadata['successful']}")
    print(f"   ⚠️ No encontrados: {metadata['not_found']}")
    print(f"   ❌ Errores: {metadata['failed']}")
    print(f"\n💾 Metadata guardada en: {metadata_path}")
    print(f"📦 Respaldo completo en: {BACKUP_DIR}")
    
    return metadata

if __name__ == "__main__":
    print("=" * 60)
    print("🔄 RESPALDO COMPLETO - DocChat Enterprise")
    print("=" * 60)
    print()
    
    metadata = backup_all_critical_files()
    
    print()
    print("=" * 60)
    print("✅ RESPALDO COMPLETADO")
    print("=" * 60)










