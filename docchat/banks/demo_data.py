"""
Generador de datos de ejemplo para demos del modo BANKS.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


def create_demo_documents(output_dir: Path) -> Dict[str, Any]:
    """Crea documentos de ejemplo para demo."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Documento 1: DNI español
    dni_content = """
    DOCUMENTO NACIONAL DE IDENTIDAD
    
    Nombre: JUAN PÉREZ GARCÍA
    DNI: 12345678A
    Fecha de Nacimiento: 15/03/1985
    Nacionalidad: ESPAÑOLA
    Domicilio: Calle Mayor 123, 28001 Madrid, España
    
    Fecha de Expedición: 10/01/2020
    Válido hasta: 10/01/2030
    """
    
    dni_file = output_dir / "DNI_Juan_Perez.txt"
    with open(dni_file, 'w', encoding='utf-8') as f:
        f.write(dni_content)
    
    # Documento 2: Extracto bancario
    extracto_content = """
    EXTRACTO BANCARIO
    Banco: Banco Ejemplo S.A.
    Cuenta: ES12 3456 7890 1234 5678 9012
    Cliente: JUAN PÉREZ GARCÍA
    Período: Enero 2025
    
    TRANSACCIONES:
    
    05/01/2025 - Transferencia recibida
    Origen: EMPRESA ABC S.L., España
    Importe: €15,000.00
    
    12/01/2025 - Transferencia enviada
    Destino: CUENTA XYZ, Panamá
    Importe: €25,000.00
    
    20/01/2025 - Transferencia recibida
    Origen: INVERSIONES GLOBAL LTD, Islas Caimán
    Importe: €50,000.00
    
    Saldo Final: €125,000.00
    """
    
    extracto_file = output_dir / "Extracto_Bancario_Juan_Perez.txt"
    with open(extracto_file, 'w', encoding='utf-8') as f:
        f.write(extracto_content)
    
    # Documento 3: Contrato (con UBO)
    contrato_content = """
    CONTRATO DE SOCIEDAD
    
    Empresa: INVERSIONES GLOBAL LTD
    Registro: Islas Caimán, Registro #12345
    Fecha Constitución: 15/06/2020
    
    BENEFICIARIOS FINALES (UBO):
    
    1. JUAN PÉREZ GARCÍA (España)
       Participación: 60%
       DNI: 12345678A
    
    2. AHMED KHAN (Pakistán)
       Participación: 40%
       Pasaporte: PK123456
    
    ACTIVIDAD PRINCIPAL:
    Inversiones internacionales y gestión de activos
    
    CAPITAL SOCIAL: €500,000.00
    """
    
    contrato_file = output_dir / "Contrato_UBO.txt"
    with open(contrato_file, 'w', encoding='utf-8') as f:
        f.write(contrato_content)
    
    # Documento 4: Cliente de bajo riesgo (para contraste)
    cliente_bajo_riesgo = """
    INFORMACIÓN DE CLIENTE
    
    Nombre: MARÍA GONZÁLEZ LÓPEZ
    DNI: 87654321B
    Fecha de Nacimiento: 20/05/1990
    Nacionalidad: ESPAÑOLA
    Domicilio: Avenida Principal 456, 08001 Barcelona, España
    
    Profesión: Ingeniera de Software
    Empleador: TechCorp España S.L.
    Ingresos Anuales: €65,000
    
    HISTORIAL:
    - Cliente desde 2018
    - Sin incidencias
    - Transacciones normales <€5,000
    """
    
    cliente_file = output_dir / "Cliente_Bajo_Riesgo.txt"
    with open(cliente_file, 'w', encoding='utf-8') as f:
        f.write(cliente_bajo_riesgo)
    
    return {
        "demo_dir": str(output_dir),
        "files": [
            str(dni_file),
            str(extracto_file),
            str(contrato_file),
            str(cliente_file)
        ],
        "description": "Demo con 4 documentos: DNI, extracto bancario, contrato con UBO, y cliente de bajo riesgo"
    }


def get_demo_expected_results() -> Dict[str, Any]:
    """Retorna resultados esperados para la demo."""
    return {
        "entities": [
            {
                "name": "JUAN PÉREZ GARCÍA",
                "id_number": "12345678A",
                "risk_level": "high",
                "reasons": [
                    "Transacciones a países de alto riesgo (Panamá, Islas Caimán)",
                    "Importes sospechosos (>€10k)",
                    "UBO en empresa offshore"
                ]
            },
            {
                "name": "AHMED KHAN",
                "risk_level": "critical",
                "reasons": [
                    "Posible match con listas de sanciones (fuzzy match)",
                    "UBO en empresa offshore",
                    "Nacionalidad de alto riesgo"
                ]
            },
            {
                "name": "MARÍA GONZÁLEZ LÓPEZ",
                "risk_level": "low",
                "reasons": [
                    "Cliente establecido",
                    "Sin transacciones sospechosas",
                    "Perfil de bajo riesgo"
                ]
            }
        ],
        "expected_sars": 2,
        "expected_high_risk": 2
    }


