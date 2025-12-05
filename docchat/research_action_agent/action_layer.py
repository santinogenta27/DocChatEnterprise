"""Action Layer empresarial para Research & Action Agent.

Implementaciones REALES que se conectan a servicios externos:
- Jira (REST API)
- ServiceNow (REST API)
- Email (SMTP)
- Slack (Webhooks)
- Teams (Webhooks)
- Salesforce (REST API)
- AWS S3
- ERP (SAP, Odoo, Dynamics)
- SQL (SQLAlchemy)
- PDF (ReportLab)

Configuración mediante variables de entorno.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import os
import json
import base64
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def _safe_env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name, default or "").strip()
    return v or None


def jira_create_ticket(project: str, summary: str, description: str, priority: str = "Medium") -> Dict[str, Any]:
    """Crea un ticket real en Jira usando REST API."""
    jira_url = _safe_env("JIRA_API_URL")
    jira_email = _safe_env("JIRA_EMAIL")
    jira_api_token = _safe_env("JIRA_API_TOKEN")
    
    if not jira_url or not jira_email or not jira_api_token:
        return {
            "status": "error",
            "message": "JIRA_API_URL, JIRA_EMAIL y JIRA_API_TOKEN deben estar configurados.",
        }
    
    try:
        # Autenticación básica
        auth = (jira_email, jira_api_token)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        # Crear ticket
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
            return {
                "status": "ok",
                "ticket_id": data.get("key", "UNKNOWN"),
                "url": f"{jira_url}/browse/{data.get('key', '')}",
                "id": data.get("id"),
            }
        else:
            return {
                "status": "error",
                "message": f"Jira API error: {response.status_code} - {response.text[:200]}",
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error conectando a Jira: {str(e)}",
        }


def servicenow_create_incident(short_description: str, description: str, urgency: str = "3") -> Dict[str, Any]:
    """Crea un incidente real en ServiceNow usando REST API."""
    sn_url = _safe_env("SERVICENOW_API_URL")
    sn_user = _safe_env("SERVICENOW_USER")
    sn_password = _safe_env("SERVICENOW_PASSWORD")
    
    if not sn_url or not sn_user or not sn_password:
        return {
            "status": "error",
            "message": "SERVICENOW_API_URL, SERVICENOW_USER y SERVICENOW_PASSWORD deben estar configurados.",
        }
    
    try:
        # Autenticación básica
        auth = (sn_user, sn_password)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        # Crear incidente
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
            return {
                "status": "ok",
                "incident_id": data.get("number", "UNKNOWN"),
                "sys_id": data.get("sys_id"),
                "url": f"{sn_url}/nav_to.do?uri=incident.do?sys_id={data.get('sys_id', '')}",
            }
        else:
            return {
                "status": "error",
                "message": f"ServiceNow API error: {response.status_code} - {response.text[:200]}",
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error conectando a ServiceNow: {str(e)}",
        }


def send_email_smtp(to: List[str], subject: str, body: str, from_email: Optional[str] = None) -> Dict[str, Any]:
    """Envía un email real usando SMTP."""
    smtp_host = _safe_env("SMTP_HOST")
    smtp_port = int(_safe_env("SMTP_PORT") or "587")
    smtp_user = _safe_env("SMTP_USER")
    smtp_password = _safe_env("SMTP_PASSWORD")
    from_addr = from_email or smtp_user
    
    if not smtp_host or not smtp_user or not smtp_password:
        return {
            "status": "error",
            "message": "SMTP_HOST, SMTP_USER y SMTP_PASSWORD deben estar configurados.",
        }
    
    try:
        # Crear mensaje
        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        # Conectar y enviar
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        return {
            "status": "ok",
            "message_id": f"email-{datetime.now().isoformat()}",
            "to": to,
            "subject": subject,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error enviando email: {str(e)}",
        }


def slack_send_message(channel: str, text: str) -> Dict[str, Any]:
    """Envía un mensaje real a Slack usando Webhook."""
    webhook = _safe_env("SLACK_WEBHOOK_URL")
    if not webhook:
        return {
            "status": "error",
            "message": "SLACK_WEBHOOK_URL debe estar configurada.",
        }
    
    try:
        payload = {
            "channel": channel,
            "text": text,
            "username": "DocChat Agent",
            "icon_emoji": ":robot_face:",
        }
        
        response = requests.post(webhook, json=payload, timeout=10)
        
        if response.status_code == 200:
            return {
                "status": "ok",
                "channel": channel,
                "text": text,
            }
        else:
            return {
                "status": "error",
                "message": f"Slack webhook error: {response.status_code} - {response.text[:200]}",
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error enviando a Slack: {str(e)}",
        }


def teams_send_message(text: str) -> Dict[str, Any]:
    """Envía un mensaje real a Microsoft Teams usando Incoming Webhook."""
    webhook = _safe_env("TEAMS_WEBHOOK_URL")
    if not webhook:
        return {
            "status": "error",
            "message": "TEAMS_WEBHOOK_URL debe estar configurada.",
        }
    
    try:
        # Formato de mensaje para Teams
        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": "DocChat Agent Notification",
            "themeColor": "0078D4",
            "title": "DocChat Agent",
            "text": text,
        }
        
        response = requests.post(webhook, json=payload, timeout=10)
        
        if response.status_code == 200:
            return {
                "status": "ok",
                "text": text,
            }
        else:
            return {
                "status": "error",
                "message": f"Teams webhook error: {response.status_code} - {response.text[:200]}",
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error enviando a Teams: {str(e)}",
        }


def http_request(method: str, url: str, headers: Optional[Dict[str, str]] = None, body: Optional[Any] = None) -> Dict[str, Any]:
    """Ejecuta una petición HTTP real."""
    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers or {},
            json=body if isinstance(body, dict) else None,
            data=body if not isinstance(body, dict) else None,
            timeout=30,
        )
        
        return {
            "status": "ok" if response.status_code < 400 else "error",
            "status_code": response.status_code,
            "method": method,
            "url": url,
            "response": response.text[:1000] if response.text else "",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error en HTTP request: {str(e)}",
            "method": method,
            "url": url,
        }


def file_writer(path: str, content: str) -> Dict[str, Any]:
    """Escribe contenido a un archivo en disco (ruta relativa segura)."""
    try:
        safe_base = os.path.abspath(os.getcwd())
        abs_path = os.path.abspath(path)
        if not abs_path.startswith(safe_base):
            return {
                "status": "error",
                "message": "Ruta fuera del directorio permitido.",
            }
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "ok", "path": abs_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def export_pdf_report(file_path: str, html_content: str) -> Dict[str, Any]:
    """Genera un PDF simple a partir de contenido HTML/Texto.

    Implementación segura y progresiva:
    - Si reportlab está disponible, crea un PDF real.
    - Si no, guarda el contenido como .txt y avisa que es fallback.
    """
    try:
        base_dir = os.path.abspath(os.getcwd())
        abs_path = os.path.abspath(file_path)
        if not abs_path.startswith(base_dir):
            return {
                "status": "error",
                "message": "Ruta fuera del directorio permitido para export_pdf_report.",
            }

        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        try:
            # Intentar usar reportlab si está disponible
            from reportlab.lib.pagesizes import A4  # type: ignore
            from reportlab.pdfgen import canvas  # type: ignore

            c = canvas.Canvas(abs_path, pagesize=A4)
            width, height = A4

            # Render muy simple: partir en líneas y dibujar texto
            textobject = c.beginText(40, height - 40)
            for line in html_content.splitlines():
                textobject.textLine(line[:200])  # recortar líneas muy largas
            c.drawText(textobject)
            c.showPage()
            c.save()

            return {
                "status": "ok",
                "path": abs_path,
                "engine": "reportlab",
            }
        except Exception:
            # Fallback: guardar como texto plano si no hay reportlab
            txt_path = abs_path if abs_path.lower().endswith(".txt") else abs_path + ".txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            return {
                "status": "ok",
                "path": txt_path,
                "engine": "text-fallback",
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


def sql_executor(query: str, mode: str = "read") -> Dict[str, Any]:
    """Ejecuta SQL real usando SQLAlchemy."""
    db_url = _safe_env("DATABASE_URL")
    if not db_url:
        return {
            "status": "error",
            "message": "DATABASE_URL debe estar configurada (ej: postgresql://user:pass@host:5432/db).",
        }
    
    try:
        from sqlalchemy import create_engine, text
        
        engine = create_engine(db_url)
        
        if mode == "write" and not query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            return {
                "status": "error",
                "message": "Modo write requiere INSERT/UPDATE/DELETE.",
            }
        
        with engine.connect() as conn:
            result = conn.execute(text(query))
            
            if mode == "read":
                rows = [dict(row._mapping) for row in result]
                return {
                    "status": "ok",
                    "rows": rows,
                    "count": len(rows),
                }
            else:
                conn.commit()
                return {
                    "status": "ok",
                    "rows_affected": result.rowcount,
                }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error ejecutando SQL: {str(e)}",
        }


def erp_get_order(order_id: str) -> Dict[str, Any]:
    """Obtiene una orden de ERP (SAP, Odoo, Dynamics)."""
    erp_type = _safe_env("ERP_TYPE", "odoo").lower()
    
    if erp_type == "odoo":
        return _erp_odoo_get_order(order_id)
    elif erp_type == "sap":
        return _erp_sap_get_order(order_id)
    elif erp_type == "dynamics":
        return _erp_dynamics_get_order(order_id)
    else:
        return {
            "status": "error",
            "message": f"ERP_TYPE '{erp_type}' no soportado. Use: odoo, sap, dynamics",
        }


def erp_update_order(order_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza una orden en ERP."""
    erp_type = _safe_env("ERP_TYPE", "odoo").lower()
    
    if erp_type == "odoo":
        return _erp_odoo_update_order(order_id, updates)
    elif erp_type == "sap":
        return _erp_sap_update_order(order_id, updates)
    elif erp_type == "dynamics":
        return _erp_dynamics_update_order(order_id, updates)
    else:
        return {
            "status": "error",
            "message": f"ERP_TYPE '{erp_type}' no soportado.",
        }


def _erp_odoo_get_order(order_id: str) -> Dict[str, Any]:
    """Obtiene orden de Odoo."""
    odoo_url = _safe_env("ODOO_URL")
    odoo_db = _safe_env("ODOO_DB")
    odoo_user = _safe_env("ODOO_USER")
    odoo_password = _safe_env("ODOO_PASSWORD")
    
    if not all([odoo_url, odoo_db, odoo_user, odoo_password]):
        return {"status": "error", "message": "Configuración Odoo incompleta."}
    
    try:
        # Autenticación Odoo
        auth_url = f"{odoo_url}/xmlrpc/2/common"
        import xmlrpc.client
        common = xmlrpc.client.ServerProxy(auth_url)
        uid = common.authenticate(odoo_db, odoo_user, odoo_password, {})
        
        if not uid:
            return {"status": "error", "message": "Autenticación Odoo fallida."}
        
        # Obtener orden
        models = xmlrpc.client.ServerProxy(f"{odoo_url}/xmlrpc/2/object")
        orders = models.execute_kw(
            odoo_db, uid, odoo_password,
            "sale.order", "search_read",
            [[["name", "=", order_id]]],
            {"fields": ["name", "state", "amount_total", "partner_id"]}
        )
        
        if orders:
            return {"status": "ok", "order": orders[0]}
        else:
            return {"status": "error", "message": f"Orden {order_id} no encontrada."}
    except Exception as e:
        return {"status": "error", "message": f"Error Odoo: {str(e)}"}


def _erp_odoo_update_order(order_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza orden en Odoo."""
    odoo_url = _safe_env("ODOO_URL")
    odoo_db = _safe_env("ODOO_DB")
    odoo_user = _safe_env("ODOO_USER")
    odoo_password = _safe_env("ODOO_PASSWORD")
    
    if not all([odoo_url, odoo_db, odoo_user, odoo_password]):
        return {"status": "error", "message": "Configuración Odoo incompleta."}
    
    try:
        import xmlrpc.client
        common = xmlrpc.client.ServerProxy(f"{odoo_url}/xmlrpc/2/common")
        uid = common.authenticate(odoo_db, odoo_user, odoo_password, {})
        
        models = xmlrpc.client.ServerProxy(f"{odoo_url}/xmlrpc/2/object")
        order_ids = models.execute_kw(
            odoo_db, uid, odoo_password,
            "sale.order", "search", [[["name", "=", order_id]]]
        )
        
        if order_ids:
            models.execute_kw(
                odoo_db, uid, odoo_password,
                "sale.order", "write", [order_ids, updates]
            )
            return {"status": "ok", "order_id": order_id, "updated": True}
        else:
            return {"status": "error", "message": f"Orden {order_id} no encontrada."}
    except Exception as e:
        return {"status": "error", "message": f"Error actualizando Odoo: {str(e)}"}


def _erp_sap_get_order(order_id: str) -> Dict[str, Any]:
    """Obtiene orden de SAP OData."""
    sap_url = _safe_env("SAP_ODATA_URL")
    sap_user = _safe_env("SAP_USER")
    sap_password = _safe_env("SAP_PASSWORD")
    
    if not all([sap_url, sap_user, sap_password]):
        return {"status": "error", "message": "Configuración SAP incompleta."}
    
    try:
        auth = (sap_user, sap_password)
        response = requests.get(
            f"{sap_url}/SalesOrderSet('{order_id}')",
            auth=auth,
            timeout=30,
        )
        
        if response.status_code == 200:
            return {"status": "ok", "order": response.json().get("d", {})}
        else:
            return {"status": "error", "message": f"SAP error: {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"Error SAP: {str(e)}"}


def _erp_sap_update_order(order_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza orden en SAP."""
    sap_url = _safe_env("SAP_ODATA_URL")
    sap_user = _safe_env("SAP_USER")
    sap_password = _safe_env("SAP_PASSWORD")
    
    if not all([sap_url, sap_user, sap_password]):
        return {"status": "error", "message": "Configuración SAP incompleta."}
    
    try:
        auth = (sap_user, sap_password)
        headers = {"Content-Type": "application/json"}
        response = requests.patch(
            f"{sap_url}/SalesOrderSet('{order_id}')",
            json=updates,
            headers=headers,
            auth=auth,
            timeout=30,
        )
        
        if response.status_code in [200, 204]:
            return {"status": "ok", "order_id": order_id, "updated": True}
        else:
            return {"status": "error", "message": f"SAP error: {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"Error actualizando SAP: {str(e)}"}


def _erp_dynamics_get_order(order_id: str) -> Dict[str, Any]:
    """Obtiene orden de Dynamics 365."""
    dynamics_url = _safe_env("DYNAMICS_API_URL")
    dynamics_token = _safe_env("DYNAMICS_ACCESS_TOKEN")
    
    if not all([dynamics_url, dynamics_token]):
        return {"status": "error", "message": "Configuración Dynamics incompleta."}
    
    try:
        headers = {
            "Authorization": f"Bearer {dynamics_token}",
            "Accept": "application/json",
        }
        response = requests.get(
            f"{dynamics_url}/api/data/v9.2/salesorders({order_id})",
            headers=headers,
            timeout=30,
        )
        
        if response.status_code == 200:
            return {"status": "ok", "order": response.json()}
        else:
            return {"status": "error", "message": f"Dynamics error: {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"Error Dynamics: {str(e)}"}


def _erp_dynamics_update_order(order_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza orden en Dynamics 365."""
    dynamics_url = _safe_env("DYNAMICS_API_URL")
    dynamics_token = _safe_env("DYNAMICS_ACCESS_TOKEN")
    
    if not all([dynamics_url, dynamics_token]):
        return {"status": "error", "message": "Configuración Dynamics incompleta."}
    
    try:
        headers = {
            "Authorization": f"Bearer {dynamics_token}",
            "Content-Type": "application/json",
        }
        response = requests.patch(
            f"{dynamics_url}/api/data/v9.2/salesorders({order_id})",
            json=updates,
            headers=headers,
            timeout=30,
        )
        
        if response.status_code in [200, 204]:
            return {"status": "ok", "order_id": order_id, "updated": True}
        else:
            return {"status": "error", "message": f"Dynamics error: {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"Error actualizando Dynamics: {str(e)}"}


def salesforce_create_record(object_type: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """Crea un registro en Salesforce."""
    sf_instance = _safe_env("SALESFORCE_INSTANCE_URL")
    sf_token = _safe_env("SALESFORCE_ACCESS_TOKEN")
    
    if not all([sf_instance, sf_token]):
        return {
            "status": "error",
            "message": "SALESFORCE_INSTANCE_URL y SALESFORCE_ACCESS_TOKEN deben estar configurados.",
        }
    
    try:
        headers = {
            "Authorization": f"Bearer {sf_token}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            f"{sf_instance}/services/data/v58.0/sobjects/{object_type}/",
            json=fields,
            headers=headers,
            timeout=30,
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            return {
                "status": "ok",
                "id": data.get("id"),
                "success": data.get("success", True),
            }
        else:
            return {
                "status": "error",
                "message": f"Salesforce error: {response.status_code} - {response.text[:200]}",
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error conectando a Salesforce: {str(e)}",
        }


def s3_upload_file(bucket: str, key: str, content: str, content_type: str = "text/plain") -> Dict[str, Any]:
    """Sube un archivo a AWS S3."""
    aws_access_key = _safe_env("AWS_ACCESS_KEY_ID")
    aws_secret_key = _safe_env("AWS_SECRET_ACCESS_KEY")
    aws_region = _safe_env("AWS_REGION", "us-east-1")
    
    if not all([aws_access_key, aws_secret_key]):
        return {
            "status": "error",
            "message": "AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY deben estar configurados.",
        }
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region,
        )
        
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType=content_type,
        )
        
        return {
            "status": "ok",
            "bucket": bucket,
            "key": key,
            "url": f"s3://{bucket}/{key}",
        }
    except ImportError:
        return {
            "status": "error",
            "message": "boto3 no instalado. Instala con: pip install boto3",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error subiendo a S3: {str(e)}",
        }


__all__ = [
    "jira_create_ticket",
    "servicenow_create_incident",
    "send_email_smtp",
    "slack_send_message",
    "teams_send_message",
    "http_request",
    "file_writer",
    "export_pdf_report",
    "sql_executor",
    "erp_get_order",
    "erp_update_order",
    "salesforce_create_record",
    "s3_upload_file",
]


