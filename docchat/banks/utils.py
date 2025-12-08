"""
Utilidades para el modo BANKS.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_input_path(input_path: str) -> tuple[bool, Optional[str]]:
    """
    Valida que la ruta de entrada sea válida.
    
    Returns:
        (is_valid, error_message)
    """
    if not input_path or not input_path.strip():
        return False, "La ruta no puede estar vacía"
    
    path = Path(input_path.strip())
    
    if not path.exists():
        return False, f"La ruta no existe: {input_path}"
    
    if not (path.is_file() or path.is_dir()):
        return False, f"La ruta no es un archivo ni una carpeta: {input_path}"
    
    return True, None


def format_risk_score(score: int) -> str:
    """Formatea un risk score con emoji y color."""
    if score >= 90:
        return f"🔴 **{score}/100** (Crítico)"
    elif score >= 70:
        return f"🟠 **{score}/100** (Alto)"
    elif score >= 50:
        return f"🟡 **{score}/100** (Medio)"
    elif score >= 30:
        return f"🟢 **{score}/100** (Bajo)"
    else:
        return f"✅ **{score}/100** (Muy Bajo)"


def format_file_size(size_bytes: int) -> str:
    """Formatea el tamaño de archivo en formato legible."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def get_supported_formats() -> List[str]:
    """Retorna lista de formatos soportados."""
    return [
        ".pdf", ".docx", ".doc", ".txt", ".md",
        ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".zip"
    ]


def validate_jurisdiction(jurisdiction: str) -> bool:
    """Valida que la jurisdicción sea válida."""
    valid_jurisdictions = ["US", "EU", "MX", "CO", "CL", "PE", "ES", "PT", "PL"]
    return jurisdiction.upper() in valid_jurisdictions


def parse_steering_commands(steering_text: str) -> List[str]:
    """Parsea comandos de steering desde texto."""
    if not steering_text or not steering_text.strip():
        return []
    
    commands = []
    for line in steering_text.strip().split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):  # Ignorar líneas vacías y comentarios
            commands.append(line)
    
    return commands


def format_action_result(action: Dict[str, Any]) -> str:
    """Formatea el resultado de una acción para mostrar en UI."""
    action_type = action.get("action", "unknown").replace("_", " ").title()
    status = action.get("status", "unknown")
    
    if status == "success":
        result = f"✅ **{action_type}**: Exitoso\n"
        
        if action.get("ticket_id"):
            result += f"   - 🎫 Ticket: `{action.get('ticket_id')}`\n"
        if action.get("ticket_url"):
            result += f"   - 🔗 URL: {action.get('ticket_url')}\n"
        if action.get("opportunity_id"):
            result += f"   - 💼 Salesforce: `{action.get('opportunity_id')}`\n"
    else:
        result = f"❌ **{action_type}**: Error\n"
        if action.get("error"):
            result += f"   - ⚠️ {action.get('error')}\n"
    
    return result


