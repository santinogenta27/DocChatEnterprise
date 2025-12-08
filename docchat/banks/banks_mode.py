"""
Modo BANKS - Compliance Agent para KYC/AML en bancos.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from ...config import AppConfig
from .workflow import BanksWorkflow

logger = logging.getLogger(__name__)


class BanksMode:
    """
    Modo BANKS: Sistema de compliance KYC/AML para bancos.
    
    Características:
    - Procesamiento masivo de documentos
    - Screening contra listas de sanciones (OFAC, EU, UN, World-Check)
    - Risk scoring automático con explicación
    - Generación de SARs en formato FinCEN XML
    - Human-in-the-loop steering
    - Audit trail completo
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.workflow = BanksWorkflow(config)
        self.output_dir = Path(config.cache_dir) / "banks"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_compliance_check(
        self,
        input_path: str,
        jurisdiction: str = "US",
        steering_commands: Optional[List[str]] = None,
        action_config: Optional[Dict[str, Any]] = None,
        batch_mode: bool = False,
        client_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta un check completo de compliance.
        
        Args:
            input_path: Ruta a carpeta/ZIP/archivo con documentos
            jurisdiction: Jurisdicción (US, EU, MX, CO, etc.)
            steering_commands: Comandos de steering en lenguaje natural
            action_config: Configuración de acciones (Salesforce, Jira, Slack, etc.)
            batch_mode: Si es True, procesa múltiples clientes
            client_id: ID del cliente para tracking
        
        Returns:
            Resultado completo con entities, scores, reports, actions, etc.
        """
        # Validaciones de entrada
        if not input_path or not input_path.strip():
            return {
                "success": False,
                "error": "❌ Error: Debes proporcionar una ruta o subir archivos",
                "result": None
            }
        
        input_path = input_path.strip()
        path = Path(input_path)
        
        # Verificar que la ruta existe
        if not path.exists():
            return {
                "success": False,
                "error": f"❌ Error: La ruta '{input_path}' no existe",
                "result": None
            }
        
        try:
            result = self.workflow.run(
                input_path=input_path,
                jurisdiction=jurisdiction,
                steering_commands=steering_commands or [],
                action_config=action_config or {},
                batch_mode=batch_mode,
                client_id=client_id or f"CLIENT_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            # Validar resultado
            if not result:
                return {
                    "success": False,
                    "error": "❌ Error: El workflow no retornó resultados",
                    "result": None
                }
            
            return {
                "success": True,
                "result": result,
                "entities_count": len(result.get("extracted_entities", [])),
                "risk_scores_count": len(result.get("risk_scores", [])),
                "reports_generated": len(result.get("generated_reports", [])),
                "actions_executed": len(result.get("actions_executed", [])),
                "errors": result.get("errors", [])
            }
        
        except FileNotFoundError as e:
            logger.error(f"Archivo no encontrado: {e}")
            return {
                "success": False,
                "error": f"❌ Error: Archivo o carpeta no encontrado: {str(e)}",
                "result": None
            }
        except PermissionError as e:
            logger.error(f"Error de permisos: {e}")
            return {
                "success": False,
                "error": f"❌ Error: Sin permisos para acceder a '{input_path}'. Verifica los permisos del archivo/carpeta.",
                "result": None
            }
        except Exception as e:
            logger.error(f"Error en process_compliance_check: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"❌ Error inesperado: {str(e)}\n\n💡 Tip: Verifica que los documentos estén en formato válido (PDF, DOCX, TXT, etc.)",
                "result": None
            }
    
    def process_batch_compliance(
        self,
        clients: List[Dict[str, str]],
        jurisdiction: str = "US",
        action_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Procesa compliance check para múltiples clientes en batch.
        
        Args:
            clients: Lista de dicts con {"client_id": str, "input_path": str}
            jurisdiction: Jurisdicción
            action_config: Configuración de acciones
        
        Returns:
            Resultados consolidados de todos los clientes
        """
        results = []
        total_high_risk = 0
        total_sars = 0
        
        for client in clients:
            try:
                result = self.process_compliance_check(
                    input_path=client["input_path"],
                    jurisdiction=jurisdiction,
                    action_config=action_config,
                    batch_mode=True,
                    client_id=client.get("client_id", "")
                )
                results.append(result)
                
                if result["success"]:
                    summary = self.get_reports_summary(result["result"])
                    total_high_risk += len(summary["high_risk_entities"])
                    total_sars += len(summary["sars"])
            except Exception as e:
                logger.error(f"Error procesando cliente {client.get('client_id')}: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "client_id": client.get("client_id", "")
                })
        
        return {
            "success": True,
            "total_clients": len(clients),
            "processed": len([r for r in results if r.get("success")]),
            "total_high_risk": total_high_risk,
            "total_sars": total_sars,
            "results": results
        }
    
    def get_reports_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Genera un resumen de los reportes generados."""
        reports = result.get("generated_reports", [])
        
        summary = {
            "total_reports": len(reports),
            "sars": [r for r in reports if r.get("type") == "SAR"],
            "pdfs": [r for r in reports if r.get("type") == "PDF"],
            "high_risk_entities": []
        }
        
        # Entidades de alto riesgo
        risk_scores = result.get("risk_scores", [])
        entities = result.get("extracted_entities", [])
        
        for i, score in enumerate(risk_scores):
            score_value = score.get("total_score") if isinstance(score, dict) else getattr(score, "total_score", 0)
            if score_value >= 70:
                entity = entities[i] if i < len(entities) else {}
                entity_name = entity.get("name") if isinstance(entity, dict) else getattr(entity, "name", "Unknown")
                summary["high_risk_entities"].append({
                    "name": entity_name,
                    "risk_score": score_value
                })
        
        return summary

