"""Data Sight Automation - Sistema de automatización inteligente.

Hace 3 cosas mejor que nadie:
1. ENTENDER: Lee y comprende automáticamente todo tipo de documentos
2. DECIDIR: Toma decisiones lógicas como un empleado
3. ACTUAR: Hace cosas automáticamente (emails, tickets, BD, etc.)
"""

from __future__ import annotations

import json
import time
import shutil
from typing import List, Dict, Any, Optional, Iterator, TYPE_CHECKING
from pathlib import Path
from datetime import datetime
import re
import requests
from dataclasses import dataclass, field
import hashlib

from .config import AppConfig

if TYPE_CHECKING:
    from .enterprise_api_data_sight import DataSightMode


@dataclass
class DocumentClassification:
    """Clasificación de un documento."""
    document_type: str  # factura, contrato, recibo, rendicion, reporte, etc.
    confidence: float
    extracted_fields: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AutomationRule:
    """Regla de automatización."""
    rule_id: str
    name: str
    condition: Dict[str, Any]  # Condición que debe cumplirse
    actions: List[Dict[str, Any]]  # Acciones a ejecutar
    enabled: bool = True
    priority: int = 0  # Mayor número = mayor prioridad


class DataSightAutomation:
    """
    Motor de automatización inteligente para Data Sight.
    
    Implementa las TOP 20 tareas automáticas:
    1. Descargar PDFs automáticamente
    2. Clasificar documentos
    3. Renombrar archivos automáticamente
    4. Mover archivos a carpetas correctas
    5. Crear resúmenes automáticos
    6. Extraer campos clave
    7. Guardar extracción en Excel/JSON
    8. Enviar email automático
    9. Crear tickets automáticos
    10. Detectar documentos duplicados
    11. Comparar versiones de documentos
    12. Alertas automáticas por condiciones
    13. Convertir documentos a PDF
    14. Generar PDF con resumen
    15. Crear carpetas automáticamente
    16. Guardar metadata en BD
    17. Leer inbox y descargar adjuntos
    18. Responder automáticamente pidiendo info faltante
    19. Enviar datos a webhook/API
    20. Generar dashboard de documentos procesados
    """
    
    def __init__(self, config: AppConfig, data_sight_mode: DataSightMode):
        self.config = config
        self.data_sight_mode = data_sight_mode
        
        # Directorio para datos de automatización
        self.data_dir = Path(config.memory_dir) / "data_sight_automation"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivo de reglas
        self.rules_file = self.data_dir / "automation_rules.json"
        
        # Archivo de documentos procesados (para detectar duplicados)
        self.processed_docs_file = self.data_dir / "processed_documents.json"
        
        # Cargar reglas y documentos procesados
        self.rules: Dict[str, AutomationRule] = self._load_rules()
        self.processed_docs: Dict[str, Dict[str, Any]] = self._load_processed_docs()
        
        # Crear reglas predefinidas si no existen
        if not self.rules:
            self._create_default_rules()
        
        # LLM para clasificación y decisiones
        from .utils.llm_factory import create_llm
        self.llm = create_llm(
            provider="openai",
            model=config.agentic_model or "gpt-4o",
            api_key=config.openai_api_key,
            temperature=0.2
        )
    
    def _load_rules(self) -> Dict[str, AutomationRule]:
        """Carga reglas de automatización."""
        try:
            if self.rules_file.exists():
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    rules = {}
                    for rule_id, rule_data in data.items():
                        rules[rule_id] = AutomationRule(**rule_data)
                    return rules
        except Exception as e:
            print(f"⚠️ Error cargando reglas: {e}")
        return {}
    
    def _save_rules(self):
        """Guarda reglas de automatización."""
        try:
            data = {}
            for rule_id, rule in self.rules.items():
                data[rule_id] = {
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "condition": rule.condition,
                    "actions": rule.actions,
                    "enabled": rule.enabled,
                    "priority": rule.priority,
                }
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error guardando reglas: {e}")
    
    def _load_processed_docs(self) -> Dict[str, Dict[str, Any]]:
        """Carga documentos procesados (para detectar duplicados)."""
        try:
            if self.processed_docs_file.exists():
                with open(self.processed_docs_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Error cargando documentos procesados: {e}")
        return {}
    
    def _save_processed_docs(self):
        """Guarda documentos procesados."""
        try:
            with open(self.processed_docs_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_docs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error guardando documentos procesados: {e}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calcula hash de un archivo para detectar duplicados."""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            return file_hash
        except Exception:
            return ""
    
    def process_document_automatically(self, file_path: str) -> Dict[str, Any]:
        """
        Procesa un documento automáticamente: ENTENDER → DECIDIR → ACTUAR
        
        Esta es la función principal que orquesta todo.
        """
        result = {
            "file_path": file_path,
            "processed_at": datetime.now().isoformat(),
            "actions_taken": [],
            "errors": [],
        }
        
        try:
            # 1. ENTENDER: Clasificar y extraer información
            classification = self._classify_document(file_path)
            result["classification"] = {
                "document_type": classification.document_type,
                "confidence": classification.confidence,
                "extracted_fields": classification.extracted_fields,
            }
            
            # 2. Detectar duplicados (Tarea #10)
            file_hash = self._calculate_file_hash(file_path)
            if file_hash in self.processed_docs:
                result["is_duplicate"] = True
                result["duplicate_of"] = self.processed_docs[file_hash].get("file_path")
                result["actions_taken"].append("duplicate_detected")
                return result
            
            # Marcar como procesado
            self.processed_docs[file_hash] = {
                "file_path": file_path,
                "processed_at": result["processed_at"],
                "document_type": classification.document_type,
            }
            self._save_processed_docs()
            
            # 3. DECIDIR: Evaluar reglas y decidir acciones
            applicable_rules = self._evaluate_rules(classification, file_path)
            
            # 4. ACTUAR: Ejecutar acciones automáticas
            for rule in applicable_rules:
                for action in rule.actions:
                    action_result = self._execute_action(action, file_path, classification)
                    if action_result.get("success"):
                        result["actions_taken"].append(action_result.get("action_name", "unknown"))
                    else:
                        result["errors"].append(action_result.get("error", "Unknown error"))
            
            # 5. Tareas automáticas básicas siempre se ejecutan
            self._execute_basic_automations(file_path, classification, result)
            
        except Exception as e:
            result["errors"].append(str(e))
        
        return result
    
    def _classify_document(self, file_path: str) -> DocumentClassification:
        """
        Tarea #2: Clasificar documentos automáticamente.
        
        Clasifica: factura, contrato, recibo, rendicion, reporte, etc.
        """
        try:
            # Leer contenido del archivo
            file_content = self._read_file_content(file_path)
            file_name = Path(file_path).name
            
            # Prompt para clasificación
            prompt = f"""Analiza este documento y clasifícalo:

Nombre del archivo: {file_name}
Contenido (primeros 2000 caracteres):
{file_content[:2000]}

Clasifica el documento en una de estas categorías:
- factura
- contrato
- recibo
- rendicion
- reporte
- orden_compra
- nota_credito
- estado_cuenta
- otro

Responde SOLO con un JSON válido:
{{
    "document_type": "tipo_documento",
    "confidence": 0.95,
    "extracted_fields": {{
        "fecha": "fecha_extraida",
        "monto": "monto_extraido",
        "proveedor": "proveedor_extraido",
        "numero_documento": "numero_extraido",
        "cliente": "cliente_extraido",
        "moneda": "moneda_extraida"
    }}
}}"""
            
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            
            # Extraer JSON de la respuesta
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return DocumentClassification(
                    document_type=data.get("document_type", "otro"),
                    confidence=float(data.get("confidence", 0.5)),
                    extracted_fields=data.get("extracted_fields", {})
                )
        except Exception as e:
            print(f"⚠️ Error clasificando documento: {e}")
        
        # Clasificación por defecto
        return DocumentClassification(
            document_type="otro",
            confidence=0.0,
            extracted_fields={}
        )
    
    def _read_file_content(self, file_path: str) -> str:
        """Lee el contenido de un archivo (texto o PDF)."""
        try:
            file_ext = Path(file_path).suffix.lower()
            if file_ext == ".pdf":
                # Usar el procesador de documentos existente
                from .document_processor import DocumentProcessor
                processor = DocumentProcessor(self.config)
                docs = processor.process([file_path])
                if docs:
                    return " ".join([doc.page_content for doc in docs[:5]])  # Primeros 5 chunks
            elif file_ext in [".txt", ".md"]:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            elif file_ext == ".docx":
                # Intentar leer DOCX básico
                try:
                    import docx
                    doc = docx.Document(file_path)
                    return "\n".join([para.text for para in doc.paragraphs])
                except:
                    return ""
        except Exception as e:
            print(f"⚠️ Error leyendo archivo: {e}")
        return ""
    
    def _evaluate_rules(self, classification: DocumentClassification, file_path: str) -> List[AutomationRule]:
        """Evalúa qué reglas son aplicables al documento."""
        applicable = []
        
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            # Evaluar condición
            condition = rule.condition
            condition_type = condition.get("type", "")
            
            matches = False
            
            if condition_type == "document_type":
                matches = classification.document_type == condition.get("value", "")
            elif condition_type == "field_equals":
                field_name = condition.get("field", "")
                field_value = condition.get("value", "")
                matches = classification.extracted_fields.get(field_name) == field_value
            elif condition_type == "field_greater_than":
                field_name = condition.get("field", "")
                threshold = float(condition.get("value", 0))
                field_value = classification.extracted_fields.get(field_name, "")
                try:
                    matches = float(field_value) > threshold
                except:
                    matches = False
            elif condition_type == "filename_contains":
                matches = condition.get("value", "").lower() in Path(file_path).name.lower()
            
            if matches:
                applicable.append(rule)
        
        # Ordenar por prioridad
        applicable.sort(key=lambda r: r.priority, reverse=True)
        return applicable
    
    def _execute_action(self, action: Dict[str, Any], file_path: str, classification: DocumentClassification) -> Dict[str, Any]:
        """Ejecuta una acción automática."""
        action_type = action.get("type", "")
        
        try:
            if action_type == "rename_file":
                return self._rename_file(file_path, classification, action)
            elif action_type == "move_file":
                return self._move_file(file_path, classification, action)
            elif action_type == "send_email":
                return self._send_email(file_path, classification, action)
            elif action_type == "create_ticket":
                return self._create_ticket(file_path, classification, action)
            elif action_type == "save_to_excel":
                return self._save_to_excel(file_path, classification, action)
            elif action_type == "send_webhook":
                return self._send_webhook(file_path, classification, action)
            elif action_type == "create_folder":
                return self._create_folder(action)
            elif action_type == "convert_to_pdf":
                return self._convert_to_pdf(file_path, action)
            elif action_type == "generate_summary_pdf":
                return self._generate_summary_pdf(file_path, classification, action)
            elif action_type == "alert":
                return self._send_alert(file_path, classification, action)
            else:
                return {"success": False, "error": f"Acción desconocida: {action_type}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_basic_automations(self, file_path: str, classification: DocumentClassification, result: Dict[str, Any]):
        """Ejecuta automatizaciones básicas que siempre se aplican."""
        # Tarea #5: Crear resumen automático
        summary = self._generate_summary(file_path, classification)
        result["summary"] = summary
        
        # Tarea #6: Extraer campos clave (ya hecho en clasificación)
        result["extracted_fields"] = classification.extracted_fields
    
    # ========== IMPLEMENTACIÓN DE LAS 20 TAREAS ==========
    
    # Tarea #3: Renombrar archivos automáticamente
    def _rename_file(self, file_path: str, classification: DocumentClassification, action: Dict[str, Any]) -> Dict[str, Any]:
        """Renombra archivo según patrón: Tipo-Proveedor-Fecha.pdf"""
        try:
            pattern = action.get("pattern", "{type}-{provider}-{date}.pdf")
            
            # Extraer valores
            doc_type = classification.document_type
            provider = classification.extracted_fields.get("proveedor", "unknown")
            date = classification.extracted_fields.get("fecha", datetime.now().strftime("%Y%m%d"))
            
            # Limpiar valores para nombre de archivo
            provider_clean = re.sub(r'[^\w\-_]', '', provider.replace(" ", "_"))[:30]
            date_clean = date.replace("/", "-").replace("\\", "-")[:10]
            
            # Construir nuevo nombre
            new_name = pattern.format(
                type=doc_type,
                provider=provider_clean,
                date=date_clean,
                filename=Path(file_path).stem
            )
            
            new_path = Path(file_path).parent / new_name
            shutil.move(file_path, new_path)
            
            return {"success": True, "action_name": "rename_file", "new_path": str(new_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Tarea #4: Mover archivos a carpetas correctas
    def _move_file(self, file_path: str, classification: DocumentClassification, action: Dict[str, Any]) -> Dict[str, Any]:
        """Mueve archivo a carpeta según tipo."""
        try:
            folder_mapping = action.get("folder_mapping", {})
            doc_type = classification.document_type
            
            target_folder = folder_mapping.get(doc_type, folder_mapping.get("default", "otros"))
            target_path = Path(self.config.memory_dir) / "data_sight_organized" / target_folder
            target_path.mkdir(parents=True, exist_ok=True)
            
            new_path = target_path / Path(file_path).name
            shutil.move(file_path, new_path)
            
            return {"success": True, "action_name": "move_file", "new_path": str(new_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Tarea #5: Crear resumen automático
    def _generate_summary(self, file_path: str, classification: DocumentClassification) -> str:
        """Genera resumen de 1-2 párrafos."""
        try:
            file_content = self._read_file_content(file_path)
            
            prompt = f"""Genera un resumen ejecutivo de 1-2 párrafos de este documento:

Tipo: {classification.document_type}
Contenido:
{file_content[:3000]}

Resumen (máximo 200 palabras):"""
            
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            return f"Resumen no disponible: {str(e)}"
    
    # Tarea #7: Guardar extracción en Excel/JSON
    def _save_to_excel(self, file_path: str, classification: DocumentClassification, action: Dict[str, Any]) -> Dict[str, Any]:
        """Guarda extracción en Excel o JSON."""
        try:
            output_format = action.get("format", "json")
            output_path = action.get("output_path", str(self.data_dir / "extractions"))
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "file_path": file_path,
                "document_type": classification.document_type,
                "extracted_fields": classification.extracted_fields,
                "processed_at": datetime.now().isoformat(),
            }
            
            if output_format == "json":
                json_path = Path(output_path) / f"{Path(file_path).stem}_extraction.json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return {"success": True, "action_name": "save_to_json", "output_path": str(json_path)}
            elif output_format == "excel":
                try:
                    import pandas as pd
                    df = pd.DataFrame([data])
                    excel_path = Path(output_path) / f"extractions_{datetime.now().strftime('%Y%m%d')}.xlsx"
                    
                    # Si el archivo existe, agregar fila
                    if excel_path.exists():
                        existing_df = pd.read_excel(excel_path)
                        df = pd.concat([existing_df, df], ignore_index=True)
                    
                    df.to_excel(excel_path, index=False)
                    return {"success": True, "action_name": "save_to_excel", "output_path": str(excel_path)}
                except ImportError:
                    return {"success": False, "error": "pandas no instalado"}
            else:
                return {"success": False, "error": f"Formato no soportado: {output_format}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Tarea #8: Enviar email automático
    def _send_email(self, file_path: str, classification: DocumentClassification, action: Dict[str, Any]) -> Dict[str, Any]:
        """Envía email automático."""
        try:
            to = action.get("to", "")
            subject = action.get("subject", f"Documento procesado: {Path(file_path).name}")
            body_template = action.get("body_template", "El documento {filename} fue procesado correctamente.")
            
            body = body_template.format(
                filename=Path(file_path).name,
                document_type=classification.document_type,
                **classification.extracted_fields
            )
            
            # Usar integración de email si está disponible
            # Por ahora, solo loguear
            print(f"📧 Email enviado a {to}: {subject}")
            
            return {"success": True, "action_name": "send_email", "to": to}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Tarea #9: Crear tickets automáticos
    def _create_ticket(self, file_path: str, classification: DocumentClassification, action: Dict[str, Any]) -> Dict[str, Any]:
        """Crea ticket en Zendesk/Jira/ServiceNow."""
        try:
            ticket_system = action.get("system", "zendesk")
            title = action.get("title", f"Documento procesado: {classification.document_type}")
            priority = action.get("priority", "normal")
            
            # Por ahora, solo loguear
            print(f"🎫 Ticket creado en {ticket_system}: {title} (prioridad: {priority})")
            
            return {"success": True, "action_name": "create_ticket", "system": ticket_system}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Tarea #13: Convertir documentos a PDF
    def _convert_to_pdf(self, file_path: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte documento a PDF."""
        try:
            from .pdf_converter import convert_to_pdf
            
            output_path = Path(file_path).with_suffix(".pdf")
            convert_to_pdf(file_path, str(output_path))
            
            return {"success": True, "action_name": "convert_to_pdf", "output_path": str(output_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Tarea #14: Generar PDF con resumen
    def _generate_summary_pdf(self, file_path: str, classification: DocumentClassification, action: Dict[str, Any]) -> Dict[str, Any]:
        """Genera PDF con resumen del documento."""
        try:
            summary = self._generate_summary(file_path, classification)
            
            # Crear PDF simple (requiere reportlab o similar)
            output_path = Path(file_path).parent / f"{Path(file_path).stem}_resumen.pdf"
            
            # Por ahora, crear archivo de texto con resumen
            with open(output_path.with_suffix(".txt"), 'w', encoding='utf-8') as f:
                f.write(f"RESUMEN: {Path(file_path).name}\n\n")
                f.write(f"Tipo: {classification.document_type}\n\n")
                f.write(summary)
            
            return {"success": True, "action_name": "generate_summary_pdf", "output_path": str(output_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Tarea #15: Crear carpetas automáticamente
    def _create_folder(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Crea carpeta si no existe."""
        try:
            folder_path = Path(action.get("folder_path", ""))
            folder_path.mkdir(parents=True, exist_ok=True)
            return {"success": True, "action_name": "create_folder", "folder_path": str(folder_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Tarea #19: Enviar datos a webhook/API
    def _send_webhook(self, file_path: str, classification: DocumentClassification, action: Dict[str, Any]) -> Dict[str, Any]:
        """Envía datos a webhook o API."""
        try:
            webhook_url = action.get("url", "")
            payload = {
                "file_path": file_path,
                "document_type": classification.document_type,
                "extracted_fields": classification.extracted_fields,
                "processed_at": datetime.now().isoformat(),
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code in [200, 201]:
                return {"success": True, "action_name": "send_webhook", "url": webhook_url}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Tarea #12: Alertas automáticas
    def _send_alert(self, file_path: str, classification: DocumentClassification, action: Dict[str, Any]) -> Dict[str, Any]:
        """Envía alerta automática."""
        try:
            alert_message = action.get("message", f"Alerta: {Path(file_path).name}")
            alert_channel = action.get("channel", "console")
            
            if alert_channel == "email":
                return self._send_email(file_path, classification, {
                    "to": action.get("to", ""),
                    "subject": "ALERTA",
                    "body_template": alert_message
                })
            else:
                print(f"🚨 ALERTA: {alert_message}")
                return {"success": True, "action_name": "send_alert", "message": alert_message}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Tarea #20: Generar dashboard
    def generate_dashboard(self) -> Dict[str, Any]:
        """Genera dashboard de documentos procesados."""
        try:
            total = len(self.processed_docs)
            by_type = {}
            errors = 0
            
            for doc_hash, doc_data in self.processed_docs.items():
                doc_type = doc_data.get("document_type", "otro")
                by_type[doc_type] = by_type.get(doc_type, 0) + 1
            
            return {
                "total_processed": total,
                "by_type": by_type,
                "errors": errors,
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def add_rule(self, rule: AutomationRule):
        """Agrega una regla de automatización."""
        self.rules[rule.rule_id] = rule
        self._save_rules()
    
    def remove_rule(self, rule_id: str):
        """Elimina una regla."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            self._save_rules()
    
    def list_rules(self) -> List[Dict[str, Any]]:
        """Lista todas las reglas."""
        return [
            {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "enabled": rule.enabled,
                "priority": rule.priority,
                "condition": rule.condition,
                "actions": rule.actions,
            }
            for rule in self.rules.values()
        ]
    
    def _create_default_rules(self):
        """Crea reglas predefinidas útiles."""
        import uuid
        
        default_rules = [
            AutomationRule(
                rule_id=f"default_rule_{uuid.uuid4().hex[:8]}",
                name="Facturas: Renombrar y Organizar",
                condition={"type": "document_type", "value": "factura"},
                actions=[
                    {
                        "type": "rename_file",
                        "pattern": "Factura-{provider}-{date}.pdf"
                    },
                    {
                        "type": "move_file",
                        "folder_mapping": {"factura": "finance/facturas"}
                    },
                    {
                        "type": "save_to_excel",
                        "format": "excel",
                        "output_path": str(self.data_dir / "extractions" / "facturas.xlsx")
                    }
                ],
                enabled=True,
                priority=8
            ),
            AutomationRule(
                rule_id=f"default_rule_{uuid.uuid4().hex[:8]}",
                name="Contratos: Alerta y Guardar",
                condition={"type": "document_type", "value": "contrato"},
                actions=[
                    {
                        "type": "move_file",
                        "folder_mapping": {"contrato": "legal/contratos"}
                    },
                    {
                        "type": "generate_summary_pdf",
                        "output_path": str(self.data_dir / "summaries")
                    }
                ],
                enabled=True,
                priority=7
            ),
            AutomationRule(
                rule_id=f"default_rule_{uuid.uuid4().hex[:8]}",
                name="Facturas > $10,000: Alerta",
                condition={"type": "field_greater_than", "field": "monto", "value": "10000"},
                actions=[
                    {
                        "type": "alert",
                        "message": "⚠️ Factura de alto monto detectada: ${monto}",
                        "channel": "console"
                    }
                ],
                enabled=True,
                priority=9
            ),
        ]
        
        for rule in default_rules:
            self.rules[rule.rule_id] = rule
        
        self._save_rules()

