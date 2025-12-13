"""Action Layer - Capa de acciones ejecutables reales."""

from __future__ import annotations

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path


class ActionType(str, Enum):
    """Tipos de acciones ejecutables."""
    CREATE_TICKET = "create_ticket"
    SEND_EMAIL = "send_email"
    PRODUCE_JSON = "produce_json"
    GENERATE_REPORT_HTML = "generate_report_html"
    SAVE_TO_DB = "save_to_db"
    EMIT_ALERT = "emit_alert"
    CREATE_EXCEL = "create_excel"
    UPDATE_ERP = "update_erp"
    UPDATE_CRM = "update_crm"
    SEND_SLACK = "send_slack"
    SEND_TEAMS = "send_teams"


@dataclass
class ActionResult:
    """Resultado de una acción ejecutada."""
    action_type: ActionType
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el resultado a diccionario."""
        return {
            "action_type": self.action_type.value,
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


class ActionLayer:
    """
    Capa de acciones ejecutables reales.
    
    Proporciona métodos para ejecutar acciones concretas como:
    - Crear tickets
    - Enviar emails
    - Generar reportes
    - Guardar en base de datos
    - Enviar alertas
    """
    
    def __init__(self, config: Any, dry_run: bool = False):
        """
        Inicializa la capa de acciones.
        
        Args:
            config: Configuración de la aplicación
            dry_run: Si True, simula acciones sin ejecutarlas realmente
        """
        self.config = config
        self.dry_run = dry_run
        self.action_history: List[ActionResult] = []
    
    def create_ticket(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        assignee: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ActionResult:
        """
        Crea un ticket en el sistema de tickets (Jira, Linear, etc.).
        
        Args:
            title: Título del ticket
            description: Descripción del ticket
            priority: Prioridad (low, medium, high, critical)
            assignee: Usuario asignado (opcional)
            metadata: Metadatos adicionales
            
        Returns:
            ActionResult con el resultado de la acción
        """
        if self.dry_run:
            return ActionResult(
                action_type=ActionType.CREATE_TICKET,
                success=True,
                message=f"[DRY RUN] Ticket creado: {title}",
                data={"ticket_id": "DRY_RUN_123", "title": title},
                timestamp=datetime.now()
            )
        
        try:
            # TODO: Integrar con API real de tickets (Jira, Linear, etc.)
            # Por ahora simulamos la creación
            ticket_id = f"TICKET_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            result = ActionResult(
                action_type=ActionType.CREATE_TICKET,
                success=True,
                message=f"Ticket creado exitosamente: {ticket_id}",
                data={
                    "ticket_id": ticket_id,
                    "title": title,
                    "priority": priority,
                    "assignee": assignee,
                    "metadata": metadata
                },
                timestamp=datetime.now()
            )
            self.action_history.append(result)
            return result
            
        except Exception as e:
            result = ActionResult(
                action_type=ActionType.CREATE_TICKET,
                success=False,
                message=f"Error al crear ticket: {str(e)}",
                error=str(e),
                timestamp=datetime.now()
            )
            self.action_history.append(result)
            return result
    
    def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
        cc: Optional[List[str]] = None
    ) -> ActionResult:
        """
        Envía un email.
        
        Args:
            to: Lista de destinatarios
            subject: Asunto del email
            body: Cuerpo del email (puede ser HTML)
            attachments: Lista de rutas de archivos adjuntos
            cc: Lista de destinatarios en copia
            
        Returns:
            ActionResult con el resultado
        """
        if self.dry_run:
            return ActionResult(
                action_type=ActionType.SEND_EMAIL,
                success=True,
                message=f"[DRY RUN] Email enviado a {', '.join(to)}",
                data={"to": to, "subject": subject},
                timestamp=datetime.now()
            )
        
        try:
            # TODO: Integrar con servicio de email real (SMTP, SendGrid, etc.)
            email_id = f"EMAIL_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            result = ActionResult(
                action_type=ActionType.SEND_EMAIL,
                success=True,
                message=f"Email enviado exitosamente: {email_id}",
                data={
                    "email_id": email_id,
                    "to": to,
                    "cc": cc or [],
                    "subject": subject,
                    "attachments": attachments or []
                },
                timestamp=datetime.now()
            )
            self.action_history.append(result)
            return result
            
        except Exception as e:
            result = ActionResult(
                action_type=ActionType.SEND_EMAIL,
                success=False,
                message=f"Error al enviar email: {str(e)}",
                error=str(e),
                timestamp=datetime.now()
            )
            self.action_history.append(result)
            return result
    
    def produce_json(
        self,
        data: Dict[str, Any],
        output_path: Optional[str] = None,
        filename: Optional[str] = None
    ) -> ActionResult:
        """
        Produce un archivo JSON con los datos proporcionados.
        
        Args:
            data: Datos a serializar
            output_path: Ruta donde guardar (opcional)
            filename: Nombre del archivo (opcional)
            
        Returns:
            ActionResult con la ruta del archivo generado
        """
        try:
            if filename is None:
                filename = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            if output_path is None:
                output_path = str(Path(self.config.memory_dir) / "outputs" / filename)
            else:
                output_path = str(Path(output_path) / filename)
            
            # Crear directorio si no existe
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Guardar JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            result = ActionResult(
                action_type=ActionType.PRODUCE_JSON,
                success=True,
                message=f"JSON generado exitosamente: {output_path}",
                data={"file_path": output_path, "size": Path(output_path).stat().st_size},
                timestamp=datetime.now()
            )
            self.action_history.append(result)
            return result
            
        except Exception as e:
            result = ActionResult(
                action_type=ActionType.PRODUCE_JSON,
                success=False,
                message=f"Error al generar JSON: {str(e)}",
                error=str(e),
                timestamp=datetime.now()
            )
            self.action_history.append(result)
            return result
    
    def generate_report_html(
        self,
        title: str,
        content: str,
        output_path: Optional[str] = None,
        filename: Optional[str] = None
    ) -> ActionResult:
        """
        Genera un reporte HTML.
        
        Args:
            title: Título del reporte
            content: Contenido HTML del reporte
            output_path: Ruta donde guardar
            filename: Nombre del archivo
            
        Returns:
            ActionResult con la ruta del archivo
        """
        try:
            if filename is None:
                filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            
            if output_path is None:
                output_path = str(Path(self.config.memory_dir) / "reports" / filename)
            else:
                output_path = str(Path(output_path) / filename)
            
            # Crear directorio si no existe
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Generar HTML completo
            html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .metadata {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .content {{
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="metadata">
        <strong>Generado:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        <strong>Sistema:</strong> ADVICE GOD - Agentic AI Workflows
    </div>
    <div class="content">
        {content}
    </div>
</body>
</html>"""
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            result = ActionResult(
                action_type=ActionType.GENERATE_REPORT_HTML,
                success=True,
                message=f"Reporte HTML generado: {output_path}",
                data={"file_path": output_path, "size": Path(output_path).stat().st_size},
                timestamp=datetime.now()
            )
            self.action_history.append(result)
            return result
            
        except Exception as e:
            result = ActionResult(
                action_type=ActionType.GENERATE_REPORT_HTML,
                success=False,
                message=f"Error al generar reporte HTML: {str(e)}",
                error=str(e),
                timestamp=datetime.now()
            )
            self.action_history.append(result)
            return result
    
    def save_to_db(
        self,
        table: str,
        data: Dict[str, Any],
        operation: str = "insert"
    ) -> ActionResult:
        """
        Guarda datos en base de datos.
        
        Args:
            table: Nombre de la tabla
            data: Datos a guardar
            operation: Operación (insert, update, upsert)
            
        Returns:
            ActionResult con el resultado
        """
        if self.dry_run:
            return ActionResult(
                action_type=ActionType.SAVE_TO_DB,
                success=True,
                message=f"[DRY RUN] Datos guardados en {table}",
                data={"table": table, "operation": operation},
                timestamp=datetime.now()
            )
        
        try:
            # TODO: Integrar con base de datos real
            record_id = f"REC_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            result = ActionResult(
                action_type=ActionType.SAVE_TO_DB,
                success=True,
                message=f"Datos guardados en {table}: {record_id}",
                data={"table": table, "record_id": record_id, "operation": operation},
                timestamp=datetime.now()
            )
            self.action_history.append(result)
            return result
            
        except Exception as e:
            result = ActionResult(
                action_type=ActionType.SAVE_TO_DB,
                success=False,
                message=f"Error al guardar en DB: {str(e)}",
                error=str(e),
                timestamp=datetime.now()
            )
            self.action_history.append(result)
            return result
    
    def emit_alert(
        self,
        level: str,
        message: str,
        channel: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ActionResult:
        """
        Emite una alerta.
        
        Args:
            level: Nivel de alerta (info, warning, error, critical)
            message: Mensaje de la alerta
            channel: Canal de alerta (slack, email, teams, etc.)
            metadata: Metadatos adicionales
            
        Returns:
            ActionResult con el resultado
        """
        try:
            alert_id = f"ALERT_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Si hay canal específico, enviar allí
            if channel == "slack":
                self.send_slack(channel="#alerts", message=f"[{level.upper()}] {message}")
            elif channel == "teams":
                self.send_teams(message=f"[{level.upper()}] {message}")
            elif channel == "email":
                self.send_email(
                    to=[self.config.admin_email] if hasattr(self.config, 'admin_email') else [],
                    subject=f"ALERT [{level.upper()}]",
                    body=message
                )
            
            result = ActionResult(
                action_type=ActionType.EMIT_ALERT,
                success=True,
                message=f"Alerta emitida: {alert_id}",
                data={"alert_id": alert_id, "level": level, "channel": channel},
                timestamp=datetime.now()
            )
            self.action_history.append(result)
            return result
            
        except Exception as e:
            result = ActionResult(
                action_type=ActionType.EMIT_ALERT,
                success=False,
                message=f"Error al emitir alerta: {str(e)}",
                error=str(e),
                timestamp=datetime.now()
            )
            self.action_history.append(result)
            return result
    
    def send_slack(
        self,
        channel: str,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> ActionResult:
        """Envía mensaje a Slack."""
        if self.dry_run:
            return ActionResult(
                action_type=ActionType.SEND_SLACK,
                success=True,
                message=f"[DRY RUN] Mensaje enviado a Slack #{channel}",
                data={"channel": channel},
                timestamp=datetime.now()
            )
        
        # TODO: Integrar con Slack API real
        result = ActionResult(
            action_type=ActionType.SEND_SLACK,
            success=True,
            message=f"Mensaje enviado a Slack: #{channel}",
            data={"channel": channel, "message": message},
            timestamp=datetime.now()
        )
        self.action_history.append(result)
        return result
    
    def send_teams(self, message: str, title: Optional[str] = None) -> ActionResult:
        """Envía mensaje a Microsoft Teams."""
        if self.dry_run:
            return ActionResult(
                action_type=ActionType.SEND_TEAMS,
                success=True,
                message="[DRY RUN] Mensaje enviado a Teams",
                timestamp=datetime.now()
            )
        
        # TODO: Integrar con Teams API real
        result = ActionResult(
            action_type=ActionType.SEND_TEAMS,
            success=True,
            message="Mensaje enviado a Teams",
            data={"message": message, "title": title},
            timestamp=datetime.now()
        )
        self.action_history.append(result)
        return result
    
    def get_action_history(self) -> List[Dict[str, Any]]:
        """Obtiene el historial de acciones ejecutadas."""
        return [action.to_dict() for action in self.action_history]










