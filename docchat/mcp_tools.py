"""
MCP Tools - Herramientas MCP predefinidas para sistemas comunes
Permite a JARVIS conectarse con Slack, Salesforce, APIs, bases de datos, etc.
"""

from __future__ import annotations

import json
import requests
import sqlite3
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from .mcp_server import MCPTool, MCPServer

logger = logging.getLogger(__name__)


# ============================================================================
# SLACK MCP TOOLS
# ============================================================================

def create_slack_tools(slack_token: Optional[str] = None) -> List[MCPTool]:
    """Crea herramientas MCP para Slack."""
    
    async def send_slack_message(channel: str, message: str, **kwargs) -> Dict[str, Any]:
        """Envía un mensaje a un canal de Slack."""
        if not slack_token:
            return {"error": "Slack token no configurado"}
        
        try:
            url = "https://slack.com/api/chat.postMessage"
            headers = {
                "Authorization": f"Bearer {slack_token}",
                "Content-Type": "application/json"
            }
            data = {
                "channel": channel,
                "text": message,
                **kwargs
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            result = response.json()
            
            if result.get("ok"):
                return {
                    "success": True,
                    "ts": result.get("ts"),
                    "channel": channel,
                    "message": "Mensaje enviado exitosamente"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Error desconocido")
                }
        
        except Exception as e:
            logger.error(f"❌ [MCP Slack] Error enviando mensaje: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_slack_channels(**kwargs) -> Dict[str, Any]:
        """Lista canales de Slack."""
        if not slack_token:
            return {"error": "Slack token no configurado"}
        
        try:
            url = "https://slack.com/api/conversations.list"
            headers = {
                "Authorization": f"Bearer {slack_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers, params=kwargs, timeout=10)
            result = response.json()
            
            if result.get("ok"):
                channels = result.get("channels", [])
                return {
                    "success": True,
                    "channels": [
                        {
                            "id": ch.get("id"),
                            "name": ch.get("name"),
                            "is_private": ch.get("is_private", False)
                        }
                        for ch in channels
                    ]
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Error desconocido")
                }
        
        except Exception as e:
            logger.error(f"❌ [MCP Slack] Error listando canales: {e}")
            return {"success": False, "error": str(e)}
    
    return [
        MCPTool(
            name="slack_send_message",
            description="Envía un mensaje a un canal de Slack",
            input_schema={
                "type": "object",
                "properties": {
                    "channel": {
                        "type": "string",
                        "description": "ID o nombre del canal de Slack"
                    },
                    "message": {
                        "type": "string",
                        "description": "Mensaje a enviar"
                    }
                },
                "required": ["channel", "message"]
            },
            handler=send_slack_message,
            category="slack",
            requires_auth=True,
            auth_type="oauth"
        ),
        MCPTool(
            name="slack_list_channels",
            description="Lista todos los canales de Slack disponibles",
            input_schema={
                "type": "object",
                "properties": {}
            },
            handler=list_slack_channels,
            category="slack",
            requires_auth=True,
            auth_type="oauth"
        )
    ]


# ============================================================================
# SALESFORCE MCP TOOLS
# ============================================================================

def create_salesforce_tools(
    instance_url: Optional[str] = None,
    access_token: Optional[str] = None
) -> List[MCPTool]:
    """Crea herramientas MCP para Salesforce."""
    
    async def query_salesforce(soql: str, **kwargs) -> Dict[str, Any]:
        """Ejecuta una consulta SOQL en Salesforce."""
        if not instance_url or not access_token:
            return {"error": "Salesforce no configurado (instance_url o access_token faltante)"}
        
        try:
            url = f"{instance_url}/services/data/v58.0/query"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            params = {"q": soql}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            result = response.json()
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "totalSize": result.get("totalSize", 0),
                    "records": result.get("records", [])
                }
            else:
                return {
                    "success": False,
                    "error": result.get("message", "Error desconocido")
                }
        
        except Exception as e:
            logger.error(f"❌ [MCP Salesforce] Error en query: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_salesforce_record(
        object_type: str,
        fields: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Crea un registro en Salesforce."""
        if not instance_url or not access_token:
            return {"error": "Salesforce no configurado"}
        
        try:
            url = f"{instance_url}/services/data/v58.0/sobjects/{object_type}/"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, json=fields, timeout=30)
            result = response.json()
            
            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "id": result.get("id"),
                    "message": "Registro creado exitosamente"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("message", "Error desconocido")
                }
        
        except Exception as e:
            logger.error(f"❌ [MCP Salesforce] Error creando registro: {e}")
            return {"success": False, "error": str(e)}
    
    return [
        MCPTool(
            name="salesforce_query",
            description="Ejecuta una consulta SOQL en Salesforce",
            input_schema={
                "type": "object",
                "properties": {
                    "soql": {
                        "type": "string",
                        "description": "Consulta SOQL a ejecutar"
                    }
                },
                "required": ["soql"]
            },
            handler=query_salesforce,
            category="salesforce",
            requires_auth=True,
            auth_type="oauth"
        ),
        MCPTool(
            name="salesforce_create_record",
            description="Crea un nuevo registro en Salesforce",
            input_schema={
                "type": "object",
                "properties": {
                    "object_type": {
                        "type": "string",
                        "description": "Tipo de objeto (Account, Contact, Lead, etc.)"
                    },
                    "fields": {
                        "type": "object",
                        "description": "Campos del registro a crear"
                    }
                },
                "required": ["object_type", "fields"]
            },
            handler=create_salesforce_record,
            category="salesforce",
            requires_auth=True,
            auth_type="oauth"
        )
    ]


# ============================================================================
# GENERIC API MCP TOOLS
# ============================================================================

def create_generic_api_tools() -> List[MCPTool]:
    """Crea herramientas MCP genéricas para cualquier API REST."""
    
    async def call_api(
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Llama a cualquier API REST."""
        try:
            method = method.upper()
            request_headers = headers or {}
            
            if method == "GET":
                response = requests.get(url, headers=request_headers, params=kwargs, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=request_headers, json=body, timeout=30)
            elif method == "PUT":
                response = requests.put(url, headers=request_headers, json=body, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=request_headers, timeout=30)
            else:
                return {"success": False, "error": f"Método HTTP no soportado: {method}"}
            
            try:
                result = response.json()
            except:
                result = {"text": response.text}
            
            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "data": result,
                "headers": dict(response.headers)
            }
        
        except Exception as e:
            logger.error(f"❌ [MCP API] Error llamando API: {e}")
            return {"success": False, "error": str(e)}
    
    return [
        MCPTool(
            name="api_call",
            description="Llama a cualquier API REST (GET, POST, PUT, DELETE)",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL de la API"
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE"],
                        "default": "GET",
                        "description": "Método HTTP"
                    },
                    "headers": {
                        "type": "object",
                        "description": "Headers HTTP (opcional)"
                    },
                    "body": {
                        "type": "object",
                        "description": "Body de la request (para POST/PUT)"
                    }
                },
                "required": ["url"]
            },
            handler=call_api,
            category="api",
            requires_auth=False
        )
    ]


# ============================================================================
# DATABASE MCP TOOLS
# ============================================================================

def create_database_tools(connection_string: Optional[str] = None) -> List[MCPTool]:
    """Crea herramientas MCP para bases de datos."""
    
    async def execute_sql_query(query: str, **kwargs) -> Dict[str, Any]:
        """Ejecuta una consulta SQL."""
        if not connection_string:
            return {"error": "Connection string no configurado"}
        
        try:
            # Por ahora solo soportamos SQLite
            # Se puede extender a PostgreSQL, MySQL, etc.
            conn = sqlite3.connect(connection_string)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(query)
            
            if query.strip().upper().startswith("SELECT"):
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                result = [
                    {col: row[col] for col in columns}
                    for row in rows
                ]
            else:
                conn.commit()
                result = {"rows_affected": cursor.rowcount}
            
            conn.close()
            
            return {
                "success": True,
                "data": result
            }
        
        except Exception as e:
            logger.error(f"❌ [MCP Database] Error ejecutando query: {e}")
            return {"success": False, "error": str(e)}
    
    return [
        MCPTool(
            name="database_query",
            description="Ejecuta una consulta SQL en la base de datos",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Consulta SQL a ejecutar"
                    }
                },
                "required": ["query"]
            },
            handler=execute_sql_query,
            category="database",
            requires_auth=True,
            auth_type="connection_string"
        )
    ]


# ============================================================================
# EMAIL MCP TOOLS
# ============================================================================

def create_email_tools(smtp_config: Optional[Dict[str, Any]] = None) -> List[MCPTool]:
    """Crea herramientas MCP para envío de emails."""
    
    async def send_email(
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Envía un email."""
        if not smtp_config:
            return {"error": "SMTP no configurado"}
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg["From"] = from_email or smtp_config.get("from_email")
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            
            server = smtplib.SMTP(
                smtp_config.get("smtp_server"),
                smtp_config.get("smtp_port", 587)
            )
            server.starttls()
            server.login(
                smtp_config.get("username"),
                smtp_config.get("password")
            )
            server.send_message(msg)
            server.quit()
            
            return {
                "success": True,
                "message": f"Email enviado a {to}"
            }
        
        except Exception as e:
            logger.error(f"❌ [MCP Email] Error enviando email: {e}")
            return {"success": False, "error": str(e)}
    
    return [
        MCPTool(
            name="email_send",
            description="Envía un email",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Dirección de email destinatario"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Asunto del email"
                    },
                    "body": {
                        "type": "string",
                        "description": "Cuerpo del email"
                    },
                    "from_email": {
                        "type": "string",
                        "description": "Dirección de email remitente (opcional)"
                    }
                },
                "required": ["to", "subject", "body"]
            },
            handler=send_email,
            category="email",
            requires_auth=True,
            auth_type="smtp"
        )
    ]


# ============================================================================
# HELPER FUNCTION TO REGISTER ALL TOOLS
# ============================================================================

def register_common_mcp_tools(
    server: MCPServer,
    integrations_config: Optional[Dict[str, Any]] = None
):
    """
    Registra todas las herramientas MCP comunes en un servidor.
    
    Args:
        server: Instancia de MCPServer
        integrations_config: Configuración de integraciones
            {
                "slack": {"token": "..."},
                "salesforce": {"instance_url": "...", "access_token": "..."},
                "database": {"connection_string": "..."},
                "email": {"smtp_config": {...}}
            }
    """
    integrations_config = integrations_config or {}
    
    # Registrar herramientas Slack
    if "slack" in integrations_config:
        slack_tools = create_slack_tools(
            slack_token=integrations_config["slack"].get("token")
        )
        for tool in slack_tools:
            server.register_tool(tool)
    
    # Registrar herramientas Salesforce
    if "salesforce" in integrations_config:
        sf_config = integrations_config["salesforce"]
        sf_tools = create_salesforce_tools(
            instance_url=sf_config.get("instance_url"),
            access_token=sf_config.get("access_token")
        )
        for tool in sf_tools:
            server.register_tool(tool)
    
    # Registrar herramientas genéricas de API (siempre disponibles)
    api_tools = create_generic_api_tools()
    for tool in api_tools:
        server.register_tool(tool)
    
    # Registrar herramientas de base de datos
    if "database" in integrations_config:
        db_tools = create_database_tools(
            connection_string=integrations_config["database"].get("connection_string")
        )
        for tool in db_tools:
            server.register_tool(tool)
    
    # Registrar herramientas de email
    if "email" in integrations_config:
        email_tools = create_email_tools(
            smtp_config=integrations_config["email"].get("smtp_config")
        )
        for tool in email_tools:
            server.register_tool(tool)
    
    logger.info(f"✅ [MCP] {len(server.tools)} herramientas registradas en servidor MCP")

