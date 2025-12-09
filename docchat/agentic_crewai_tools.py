"""Tools personalizados para CrewAI integrados con el action layer existente.

Conecta CrewAI con las herramientas empresariales reales:
- Jira, ServiceNow, Slack, Teams
- Email, SQL, ERP
- File operations, PDF export
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

try:
    from crewai.tools import BaseTool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    # Crear clase base dummy
    class BaseTool(BaseModel):
        name: str = ""
        description: str = ""
        def _run(self, *args, **kwargs):
            return "CrewAI no disponible"

# Importar action layer existente
from .research_action_agent.action_layer import (
    jira_create_ticket,
    servicenow_create_incident,
    send_email_smtp,
    slack_send_message,
    teams_send_message,
    http_request,
    file_writer,
    export_pdf_report,
    sql_executor,
    erp_get_order,
    erp_update_order,
)


class JiraCreateTicketInput(BaseModel):
    """Input para crear ticket en Jira."""
    project: str = Field(description="Proyecto de Jira (ej: PROJ)")
    summary: str = Field(description="Resumen del ticket")
    description: str = Field(description="Descripción detallada del ticket")
    priority: str = Field(default="Medium", description="Prioridad: Low, Medium, High, Critical")


if CREWAI_AVAILABLE:
    class JiraCreateTicketTool(BaseTool):
        """Tool para crear tickets en Jira."""
        name: str = "jira_create_ticket"
        description: str = (
            "Crea un ticket en Jira. "
            "Úsalo cuando necesites crear un ticket de seguimiento, bug, o tarea."
        )
        args_schema: type[BaseModel] = JiraCreateTicketInput
        
        def _run(self, project: str, summary: str, description: str, priority: str = "Medium") -> str:
            """Ejecuta la creación del ticket."""
            result = jira_create_ticket(project, summary, description, priority)
            if result.get("status") == "ok":
                return f"Ticket creado exitosamente: {result.get('ticket_id')} - {result.get('url', '')}"
            else:
                return f"Error: {result.get('message', 'Error desconocido')}"
else:
    class JiraCreateTicketTool(BaseTool):
        pass


class SlackSendMessageInput(BaseModel):
    """Input para enviar mensaje a Slack."""
    channel: str = Field(description="Canal de Slack (ej: #general)")
    text: str = Field(description="Mensaje a enviar")


if CREWAI_AVAILABLE:
    class SlackSendMessageTool(BaseTool):
        """Tool para enviar mensajes a Slack."""
        name: str = "slack_send_message"
        description: str = (
            "Envía un mensaje a un canal de Slack. "
            "Úsalo para notificaciones, alertas o comunicaciones."
        )
        args_schema: type[BaseModel] = SlackSendMessageInput
        
        def _run(self, channel: str, text: str) -> str:
            """Ejecuta el envío del mensaje."""
            result = slack_send_message(channel, text)
            if result.get("status") == "ok":
                return f"Mensaje enviado a {channel} exitosamente"
            else:
                return f"Error: {result.get('message', 'Error desconocido')}"
else:
    class SlackSendMessageTool(BaseTool):
        pass


class TeamsSendMessageInput(BaseModel):
    """Input para enviar mensaje a Microsoft Teams."""
    text: str = Field(description="Mensaje a enviar")


if CREWAI_AVAILABLE:
    class TeamsSendMessageTool(BaseTool):
        """Tool para enviar mensajes a Microsoft Teams."""
        name: str = "teams_send_message"
        description: str = (
            "Envía un mensaje a Microsoft Teams vía webhook. "
            "Úsalo para notificaciones y alertas."
        )
        args_schema: type[BaseModel] = TeamsSendMessageInput
        
        def _run(self, text: str) -> str:
            """Ejecuta el envío del mensaje."""
            result = teams_send_message(text)
            if result.get("status") == "ok":
                return "Mensaje enviado a Teams exitosamente"
            else:
                return f"Error: {result.get('message', 'Error desconocido')}"
else:
    class TeamsSendMessageTool(BaseTool):
        pass


class EmailSendInput(BaseModel):
    """Input para enviar email."""
    to: List[str] = Field(description="Lista de destinatarios")
    subject: str = Field(description="Asunto del email")
    body: str = Field(description="Cuerpo del email")
    from_email: Optional[str] = Field(default=None, description="Remitente (opcional)")


if CREWAI_AVAILABLE:
    class EmailSendTool(BaseTool):
        """Tool para enviar emails."""
        name: str = "send_email"
        description: str = (
            "Envía un email vía SMTP. "
            "Úsalo para comunicaciones formales, reportes o notificaciones importantes."
        )
        args_schema: type[BaseModel] = EmailSendInput
        
        def _run(self, to: List[str], subject: str, body: str, from_email: Optional[str] = None) -> str:
            """Ejecuta el envío del email."""
            result = send_email_smtp(to, subject, body, from_email)
            if result.get("status") == "ok":
                return f"Email enviado a {', '.join(to)} exitosamente"
            else:
                return f"Error: {result.get('message', 'Error desconocido')}"
else:
    class EmailSendTool(BaseTool):
        pass


class SQLQueryInput(BaseModel):
    """Input para ejecutar query SQL."""
    query: str = Field(description="Query SQL a ejecutar (solo SELECT)")
    mode: str = Field(default="read", description="Modo: read o write")


if CREWAI_AVAILABLE:
    class SQLQueryTool(BaseTool):
        """Tool para ejecutar queries SQL."""
        name: str = "sql_query"
        description: str = (
            "Ejecuta una query SQL en la base de datos. "
            "Solo permite queries SELECT (read-only). "
            "Úsalo para consultar datos empresariales."
        )
        args_schema: type[BaseModel] = SQLQueryInput
        
        def _run(self, query: str, mode: str = "read") -> str:
            """Ejecuta la query SQL."""
            result = sql_executor(query, mode)
            if result.get("status") == "ok":
                rows = result.get("rows", [])
                return f"Query ejecutada exitosamente. Filas retornadas: {len(rows)}\n{str(rows)[:500]}"
            else:
                return f"Error: {result.get('message', 'Error desconocido')}"
else:
    class SQLQueryTool(BaseTool):
        pass


class FileWriteInput(BaseModel):
    """Input para escribir archivo."""
    path: str = Field(description="Ruta del archivo (relativa al directorio de trabajo)")
    content: str = Field(description="Contenido a escribir")


if CREWAI_AVAILABLE:
    class FileWriteTool(BaseTool):
        """Tool para escribir archivos."""
        name: str = "write_file"
        description: str = (
            "Escribe contenido a un archivo. "
            "Úsalo para guardar reportes, logs o datos procesados."
        )
        args_schema: type[BaseModel] = FileWriteInput
        
        def _run(self, path: str, content: str) -> str:
            """Ejecuta la escritura del archivo."""
            result = file_writer(path, content)
            if result.get("status") == "ok":
                return f"Archivo escrito exitosamente: {result.get('path')}"
            else:
                return f"Error: {result.get('message', 'Error desconocido')}"
else:
    class FileWriteTool(BaseTool):
        pass


class PDFExportInput(BaseModel):
    """Input para exportar PDF."""
    file_path: str = Field(description="Ruta del archivo PDF a generar")
    html_content: str = Field(description="Contenido HTML o texto para el PDF")


if CREWAI_AVAILABLE:
    class PDFExportTool(BaseTool):
        """Tool para exportar PDFs."""
        name: str = "export_pdf"
        description: str = (
            "Genera un reporte PDF profesional desde contenido HTML o texto. "
            "Úsalo para crear reportes ejecutivos, documentos formales o presentaciones."
        )
        args_schema: type[BaseModel] = PDFExportInput
        
        def _run(self, file_path: str, html_content: str) -> str:
            """Ejecuta la exportación del PDF."""
            result = export_pdf_report(file_path, html_content)
            if result.get("status") == "ok":
                return f"PDF generado exitosamente: {result.get('path')}"
            else:
                return f"Error: {result.get('message', 'Error desconocido')}"
else:
    class PDFExportTool(BaseTool):
        pass


def get_crewai_tools() -> List[Any]:
    """Retorna lista de tools personalizados para CrewAI."""
    if not CREWAI_AVAILABLE:
        return []
    tools = [
        JiraCreateTicketTool(),
        SlackSendMessageTool(),
        TeamsSendMessageTool(),
        EmailSendTool(),
        SQLQueryTool(),
        FileWriteTool(),
        PDFExportTool(),
    ]
    return tools


def get_tool_by_name(tool_name: str) -> Optional[Any]:
    """Obtiene un tool por nombre."""
    if not CREWAI_AVAILABLE:
        return None
    tools = get_crewai_tools()
    for tool in tools:
        if tool.name == tool_name:
            return tool
    return None
