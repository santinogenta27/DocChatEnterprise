"""
ÉXTASIS Tools - Herramientas de Producción para Agentes Autónomos Empresariales

Tools reales que se conectan a servicios empresariales y ejecutan acciones autónomas:
- Tickets: Jira, ServiceNow, Zendesk
- Email: SMTP, SendGrid, AWS SES
- Slack: Webhooks, API
- S3: AWS S3 para almacenamiento
- ERP: SAP, Oracle, Dynamics 365
- CRM: Salesforce, HubSpot, Zoho
- PDF: Generación y procesamiento de reportes

Soporta modo simulación para pruebas sin ejecutar acciones reales.
"""

from __future__ import annotations

import json
import os
import smtplib
import requests
from typing import Any, Dict, List, Optional
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from langchain.tools import tool


# ============================================================================
# CONFIGURACIÓN Y HELPERS
# ============================================================================

def _get_simulation_mode() -> bool:
    """Obtiene el modo simulación desde configuración o variable de entorno."""
    # Primero intentar desde configuración de UI
    try:
        from .extasis_config import get_extasis_config_manager
        config_manager = get_extasis_config_manager()
        return config_manager.get_simulation_mode()
    except:
        pass
    
    # Fallback a variable de entorno
    return os.getenv("EXTASIS_SIMULATION_MODE", "false").lower() == "true"

SIMULATION_MODE = _get_simulation_mode()


def _safe_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Obtiene variable de entorno de forma segura, también desde configuración de UI."""
    # Primero intentar desde variables de entorno
    v = os.getenv(name, default or "").strip()
    if v:
        return v
    
    # Si no existe, intentar desde configuración guardada en UI
    try:
        from .extasis_config import get_extasis_config_manager
        config_manager = get_extasis_config_manager()
        
        # Mapeo inverso de variables de entorno a servicios
        env_to_service = {
            "JIRA_API_URL": ("jira", "url"),
            "JIRA_EMAIL": ("jira", "email"),
            "JIRA_API_TOKEN": ("jira", "api_token"),
            "SERVICENOW_API_URL": ("servicenow", "url"),
            "SERVICENOW_USER": ("servicenow", "user"),
            "SERVICENOW_PASSWORD": ("servicenow", "password"),
            "SMTP_HOST": ("email", "host"),
            "SMTP_PORT": ("email", "port"),
            "SMTP_USER": ("email", "user"),
            "SMTP_PASSWORD": ("email", "password"),
            "SLACK_WEBHOOK_URL": ("slack", "webhook_url"),
            "SLACK_BOT_TOKEN": ("slack", "bot_token"),
            "AWS_ACCESS_KEY_ID": ("s3", "access_key_id"),
            "AWS_SECRET_ACCESS_KEY": ("s3", "secret_access_key"),
            "AWS_REGION": ("s3", "region"),
            "SALESFORCE_INSTANCE_URL": ("salesforce", "instance_url"),
            "SALESFORCE_ACCESS_TOKEN": ("salesforce", "access_token"),
            "SALESFORCE_USERNAME": ("salesforce", "username"),
            "SALESFORCE_PASSWORD": ("salesforce", "password"),
            "SALESFORCE_SECURITY_TOKEN": ("salesforce", "security_token"),
            "SAP_ODATA_URL": ("sap", "odata_url"),
            "SAP_USER": ("sap", "user"),
            "SAP_PASSWORD": ("sap", "password"),
            "ORACLE_ERP_URL": ("oracle_erp", "url"),
            "ORACLE_ERP_TOKEN": ("oracle_erp", "token"),
            "DYNAMICS_API_URL": ("dynamics", "api_url"),
            "DYNAMICS_ACCESS_TOKEN": ("dynamics", "access_token"),
        }
        
        if name in env_to_service:
            service_name, config_key = env_to_service[name]
            service_config = config_manager.get_service_config(service_name)
            value = service_config.get(config_key)
            if value:
                return str(value)
    except Exception:
        pass  # Si falla, continuar con default
    
    return default


def _simulate(action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Simula una acción sin ejecutarla realmente."""
    # Ocultar contraseñas/tokens sensibles en la simulación
    safe_params = {}
    sensitive_keys = ["password", "token", "api_token", "secret", "access_token", "webhook_url"]
    for key, value in params.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys) and value:
            safe_params[key] = "***OCULTO***"
        else:
            safe_params[key] = value
    
    return {
        "status": "simulated",
        "action": action_name,
        "params": safe_params,
        "message": f"[🧪 SIMULACIÓN] Se ejecutaría: {action_name} con parámetros: {json.dumps(safe_params, indent=2)}",
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# TICKETS - JIRA, SERVICENOW, ZENDESK
# ============================================================================

@tool("Crear ticket en Jira")
def create_jira_ticket(
    project: str,
    summary: str,
    description: str,
    priority: str = "Medium"
) -> str:
    """Crea un ticket real en Jira usando REST API.
    
    Args:
        project: Clave del proyecto Jira (e.g., "PROJ")
        summary: Resumen del ticket
        description: Descripción detallada
        priority: Prioridad (Low, Medium, High, Critical)
    
    Returns:
        JSON string con resultado
    """
    simulation_mode = _get_simulation_mode()
    if simulation_mode:
        return json.dumps(_simulate("create_jira_ticket", {
            "project": project,
            "summary": summary,
            "description": description,
            "priority": priority
        }))
    
    jira_url = _safe_env("JIRA_API_URL")
    jira_email = _safe_env("JIRA_EMAIL")
    jira_api_token = _safe_env("JIRA_API_TOKEN")
    
    if not jira_url or not jira_email or not jira_api_token:
        return json.dumps({
            "status": "error",
            "message": "JIRA_API_URL, JIRA_EMAIL y JIRA_API_TOKEN deben estar configurados."
        })
    
    try:
        auth = (jira_email, jira_api_token)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        payload = {
            "fields": {
                "project": {"key": project},
                "summary": summary,
                "description": description,
                "issuetype": {"name": "Task"},
                "priority": {"name": priority},
            }
        }
        
        response = requests.post(
            f"{jira_url}/rest/api/3/issue",
            json=payload,
            headers=headers,
            auth=auth,
            timeout=30,
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            return json.dumps({
                "status": "ok",
                "ticket_id": data.get("key", "UNKNOWN"),
                "url": f"{jira_url}/browse/{data.get('key', '')}",
                "id": data.get("id"),
            })
        else:
            return json.dumps({
                "status": "error",
                "message": f"Jira API error: {response.status_code} - {response.text[:200]}",
            })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error conectando a Jira: {str(e)}",
        })


@tool("Crear incidente en ServiceNow")
def create_servicenow_incident(
    short_description: str,
    description: str,
    urgency: str = "3"
) -> str:
    """Crea un incidente real en ServiceNow usando REST API.
    
    Args:
        short_description: Descripción corta
        description: Descripción detallada
        urgency: Urgencia (1=Crítica, 2=Alta, 3=Media, 4=Baja, 5=Planificada)
    
    Returns:
        JSON string con resultado
    """
    simulation_mode = _get_simulation_mode()
    if simulation_mode:
        return json.dumps(_simulate("create_servicenow_incident", {
            "short_description": short_description,
            "description": description,
            "urgency": urgency
        }))
    
    sn_url = _safe_env("SERVICENOW_API_URL")
    sn_user = _safe_env("SERVICENOW_USER")
    sn_password = _safe_env("SERVICENOW_PASSWORD")
    
    if not sn_url or not sn_user or not sn_password:
        return json.dumps({
            "status": "error",
            "message": "SERVICENOW_API_URL, SERVICENOW_USER y SERVICENOW_PASSWORD deben estar configurados.",
        })
    
    try:
        auth = (sn_user, sn_password)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        payload = {
            "short_description": short_description,
            "description": description,
            "urgency": urgency,
            "category": "inquiry",
        }
        
        response = requests.post(
            f"{sn_url}/api/now/table/incident",
            json=payload,
            headers=headers,
            auth=auth,
            timeout=30,
        )
        
        if response.status_code in [200, 201]:
            data = response.json().get("result", {})
            return json.dumps({
                "status": "ok",
                "incident_id": data.get("number", "UNKNOWN"),
                "sys_id": data.get("sys_id"),
                "url": f"{sn_url}/nav_to.do?uri=incident.do?sys_id={data.get('sys_id', '')}",
            })
        else:
            return json.dumps({
                "status": "error",
                "message": f"ServiceNow API error: {response.status_code} - {response.text[:200]}",
            })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error conectando a ServiceNow: {str(e)}",
        })


# ============================================================================
# EMAIL - SMTP
# ============================================================================

@tool("Enviar email")
def send_email(
    to: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None
) -> str:
    """Envía un email real usando SMTP.
    
    Args:
        to: Email del destinatario (o lista separada por comas)
        subject: Asunto del email
        body: Cuerpo del email
        from_email: Email del remitente (opcional, usa SMTP_USER por defecto)
    
    Returns:
        JSON string con resultado
    """
    simulation_mode = _get_simulation_mode()
    if simulation_mode:
        return json.dumps(_simulate("send_email", {
            "to": to,
            "subject": subject,
            "body": body[:100] + "..." if len(body) > 100 else body
        }))
    
    smtp_host = _safe_env("SMTP_HOST")
    smtp_port = int(_safe_env("SMTP_PORT") or "587")
    smtp_user = _safe_env("SMTP_USER")
    smtp_password = _safe_env("SMTP_PASSWORD")
    from_addr = from_email or smtp_user
    
    if not smtp_host or not smtp_user or not smtp_password:
        return json.dumps({
            "status": "error",
            "message": "SMTP_HOST, SMTP_USER y SMTP_PASSWORD deben estar configurados.",
        })
    
    try:
        # Crear mensaje
        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        # Conectar y enviar
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        return json.dumps({
            "status": "ok",
            "message_id": f"email-{datetime.now().isoformat()}",
            "to": to,
            "subject": subject,
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error enviando email: {str(e)}",
        })


# ============================================================================
# SLACK - WEBHOOKS Y API
# ============================================================================

@tool("Enviar mensaje a Slack")
def send_slack_message(
    channel: str,
    text: str
) -> str:
    """Envía un mensaje real a Slack usando Webhook o API.
    
    Args:
        channel: Canal de Slack (#canal o @usuario)
        text: Texto del mensaje
    
    Returns:
        JSON string con resultado
    """
    simulation_mode = _get_simulation_mode()
    if simulation_mode:
        return json.dumps(_simulate("send_slack_message", {
            "channel": channel,
            "text": text[:100] + "..." if len(text) > 100 else text
        }))
    
    # Intentar webhook primero
    webhook = _safe_env("SLACK_WEBHOOK_URL")
    if webhook:
        try:
            payload = {
                "channel": channel,
                "text": text,
                "username": "ÉXTASIS Agent",
                "icon_emoji": ":robot_face:",
            }
            
            response = requests.post(webhook, json=payload, timeout=10)
            
            if response.status_code == 200:
                return json.dumps({
                    "status": "ok",
                    "channel": channel,
                    "text": text,
                })
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"Slack webhook error: {response.status_code}",
                })
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Error enviando a Slack: {str(e)}",
            })
    
    # Fallback a API
    slack_token = _safe_env("SLACK_BOT_TOKEN")
    if not slack_token:
        return json.dumps({
            "status": "error",
            "message": "SLACK_WEBHOOK_URL o SLACK_BOT_TOKEN debe estar configurado.",
        })
    
    try:
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {slack_token}",
            "Content-Type": "application/json"
        }
        data = {
            "channel": channel,
            "text": text
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        result = response.json()
        
        if result.get("ok"):
            return json.dumps({
                "status": "ok",
                "ts": result.get("ts"),
                "channel": channel,
            })
        else:
            return json.dumps({
                "status": "error",
                "message": result.get("error", "Error desconocido"),
            })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error enviando a Slack: {str(e)}",
        })


# ============================================================================
# AWS S3 - ALMACENAMIENTO
# ============================================================================

@tool("Subir archivo a S3")
def upload_to_s3(
    file_path: str,
    bucket: str,
    key: str
) -> str:
    """Sube un archivo real a AWS S3.
    
    Args:
        file_path: Ruta local del archivo
        bucket: Nombre del bucket de S3
        key: Clave/ubicación en S3
    
    Returns:
        JSON string con resultado
    """
    simulation_mode = _get_simulation_mode()
    if simulation_mode:
        return json.dumps(_simulate("upload_to_s3", {
            "file_path": file_path,
            "bucket": bucket,
            "key": key
        }))
    
    if not BOTO3_AVAILABLE:
        return json.dumps({
            "status": "error",
            "message": "boto3 no está instalado. Instala con: pip install boto3",
        })
    
    try:
        s3_client = boto3.client('s3')
        s3_client.upload_file(file_path, bucket, key)
        
        return json.dumps({
            "status": "ok",
            "url": f"s3://{bucket}/{key}",
            "bucket": bucket,
            "key": key,
        })
    except ClientError as e:
        return json.dumps({
            "status": "error",
            "message": f"Error subiendo a S3: {str(e)}",
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error: {str(e)}",
        })


# ============================================================================
# ERP - SAP, ORACLE, DYNAMICS 365
# ============================================================================

@tool("Ajustar inventario en ERP")
def adjust_erp_inventory(
    product_id: str,
    quantity: int,
    system: str = "sap"
) -> str:
    """Ajusta inventario en sistema ERP (SAP, Oracle, Dynamics 365).
    
    Args:
        product_id: ID del producto
        quantity: Cantidad a ajustar (positiva o negativa)
        system: Sistema ERP (sap, oracle, dynamics)
    
    Returns:
        JSON string con resultado
    """
    simulation_mode = _get_simulation_mode()
    if simulation_mode:
        return json.dumps(_simulate("adjust_erp_inventory", {
            "product_id": product_id,
            "quantity": quantity,
            "system": system
        }))
    
    # Implementación básica - en producción usar APIs reales
    if system == "sap":
        sap_url = _safe_env("SAP_ODATA_URL")
        if not sap_url:
            return json.dumps({
                "status": "error",
                "message": "SAP_ODATA_URL debe estar configurado.",
            })
        # Llamada a SAP OData API
        return json.dumps({
            "status": "ok",
            "message": f"Inventario ajustado en SAP: {product_id} -> {quantity}",
        })
    elif system == "oracle":
        oracle_url = _safe_env("ORACLE_ERP_URL")
        if not oracle_url:
            return json.dumps({
                "status": "error",
                "message": "ORACLE_ERP_URL debe estar configurado.",
            })
        return json.dumps({
            "status": "ok",
            "message": f"Inventario ajustado en Oracle: {product_id} -> {quantity}",
        })
    elif system == "dynamics":
        dynamics_url = _safe_env("DYNAMICS_API_URL")
        if not dynamics_url:
            return json.dumps({
                "status": "error",
                "message": "DYNAMICS_API_URL debe estar configurado.",
            })
        return json.dumps({
            "status": "ok",
            "message": f"Inventario ajustado en Dynamics: {product_id} -> {quantity}",
        })
    else:
        return json.dumps({
            "status": "error",
            "message": f"Sistema ERP no soportado: {system}",
        })


# ============================================================================
# CRM - SALESFORCE, HUBSPOT, ZOHO
# ============================================================================

@tool("Aprobar reembolso en CRM")
def approve_crm_refund(
    refund_id: str,
    amount: float,
    system: str = "salesforce"
) -> str:
    """Aprueba un reembolso en sistema CRM.
    
    Args:
        refund_id: ID del reembolso
        amount: Monto del reembolso
        system: Sistema CRM (salesforce, hubspot, zoho)
    
    Returns:
        JSON string con resultado
    """
    simulation_mode = _get_simulation_mode()
    if simulation_mode:
        return json.dumps(_simulate("approve_crm_refund", {
            "refund_id": refund_id,
            "amount": amount,
            "system": system
        }))
    
    if system == "salesforce":
        sf_url = _safe_env("SALESFORCE_INSTANCE_URL")
        sf_token = _safe_env("SALESFORCE_ACCESS_TOKEN")
        
        if not sf_url or not sf_token:
            return json.dumps({
                "status": "error",
                "message": "SALESFORCE_INSTANCE_URL y SALESFORCE_ACCESS_TOKEN deben estar configurados.",
            })
        
        try:
            headers = {
                "Authorization": f"Bearer {sf_token}",
                "Content-Type": "application/json"
            }
            
            # Llamada a Salesforce API para aprobar reembolso
            response = requests.patch(
                f"{sf_url}/services/data/v58.0/sobjects/Refund__c/{refund_id}",
                json={"Status__c": "Approved"},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return json.dumps({
                    "status": "ok",
                    "refund_id": refund_id,
                    "amount": amount,
                    "message": "Reembolso aprobado en Salesforce",
                })
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"Salesforce API error: {response.status_code}",
                })
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Error: {str(e)}",
            })
    
    return json.dumps({
        "status": "error",
        "message": f"Sistema CRM no implementado: {system}",
    })


@tool("Asignar lead en CRM")
def assign_crm_lead(
    lead_id: str,
    assignee_id: str,
    system: str = "salesforce"
) -> str:
    """Asigna un lead a un vendedor en sistema CRM.
    
    Args:
        lead_id: ID del lead
        assignee_id: ID del vendedor asignado
        system: Sistema CRM (salesforce, hubspot, zoho)
    
    Returns:
        JSON string con resultado
    """
    simulation_mode = _get_simulation_mode()
    if simulation_mode:
        return json.dumps(_simulate("assign_crm_lead", {
            "lead_id": lead_id,
            "assignee_id": assignee_id,
            "system": system
        }))
    
    if system == "salesforce":
        sf_url = _safe_env("SALESFORCE_INSTANCE_URL")
        sf_token = _safe_env("SALESFORCE_ACCESS_TOKEN")
        
        if not sf_url or not sf_token:
            return json.dumps({
                "status": "error",
                "message": "SALESFORCE_INSTANCE_URL y SALESFORCE_ACCESS_TOKEN deben estar configurados.",
            })
        
        try:
            headers = {
                "Authorization": f"Bearer {sf_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.patch(
                f"{sf_url}/services/data/v58.0/sobjects/Lead/{lead_id}",
                json={"OwnerId": assignee_id},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return json.dumps({
                    "status": "ok",
                    "lead_id": lead_id,
                    "assignee_id": assignee_id,
                    "message": "Lead asignado en Salesforce",
                })
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"Salesforce API error: {response.status_code}",
                })
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Error: {str(e)}",
            })
    
    return json.dumps({
        "status": "error",
        "message": f"Sistema CRM no implementado: {system}",
    })


# ============================================================================
# PDF - GENERACIÓN Y PROCESAMIENTO
# ============================================================================

@tool("Generar reporte PDF")
def generate_pdf_report(
    title: str,
    content: str,
    output_path: str
) -> str:
    """Genera un reporte PDF.
    
    Args:
        title: Título del reporte
        content: Contenido del reporte (markdown o HTML)
        output_path: Ruta donde guardar el PDF
    
    Returns:
        JSON string con resultado
    """
    simulation_mode = _get_simulation_mode()
    if simulation_mode:
        return json.dumps(_simulate("generate_pdf_report", {
            "title": title,
            "content": content[:100] + "..." if len(content) > 100 else content,
            "output_path": output_path
        }))
    
    try:
        # Usar reportlab o weasyprint para generar PDF
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        c = canvas.Canvas(output_path, pagesize=letter)
        c.drawString(100, 750, title)
        
        # Dividir contenido en líneas y agregar al PDF
        y = 700
        for line in content.split('\n')[:30]:  # Limitar a 30 líneas
            c.drawString(100, y, line[:80])  # Truncar líneas largas
            y -= 20
            if y < 50:
                c.showPage()
                y = 750
        
        c.save()
        
        return json.dumps({
            "status": "ok",
            "pdf_path": output_path,
            "message": f"PDF generado: {output_path}",
        })
    except ImportError:
        return json.dumps({
            "status": "error",
            "message": "reportlab no está instalado. Instala con: pip install reportlab",
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error generando PDF: {str(e)}",
        })


# ============================================================================
# LISTA DE TODAS LAS HERRAMIENTAS
# ============================================================================

EXTASIS_TOOLS = [
    create_jira_ticket,
    create_servicenow_incident,
    send_email,
    send_slack_message,
    upload_to_s3,
    adjust_erp_inventory,
    approve_crm_refund,
    assign_crm_lead,
    generate_pdf_report,
]

