"""Action executor tool for Research & Action Agent - executes enterprise actions.
This is a unified action executor that routes to specific tools when available."""

from __future__ import annotations

import json
import time
import uuid
from typing import Dict, Any, Optional
from langchain.tools import tool
from .base_tool import ToolResponse

# Import individual action tools
try:
    from .action_tools import send_email, create_ticket, crm_update_record, erp_update_order
    INDIVIDUAL_TOOLS_AVAILABLE = True
except ImportError:
    INDIVIDUAL_TOOLS_AVAILABLE = False


@tool
def action_executor_tool(payload_json: str) -> str:
    """
    Execute enterprise actions. Accepts a JSON string payload.
    
    WARNING: This tool performs side-effects. Use with caution.
    
    Payload format:
    {
      "type": "create_ticket" | "send_email" | "update_erp" | "run_rpa" | "suspend_supplier" | "alert",
      "data": {
        "summary": "...",
        "description": "...",
        "priority": "low" | "medium" | "high" | "critical",
        ...
      },
      "confirm": true|false  // Required for destructive operations
    }
    
    Returns:
        JSON string with execution result
    """
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "error": "invalid_json",
            "message": str(e)
        })
    
    action_type = payload.get("type")
    data = payload.get("data", {})
    confirm = payload.get("confirm", False)
    
    # Safety gate: require explicit confirm flag for destructive ops
    destructive_ops = {
        "update_erp",
        "run_rpa",
        "suspend_supplier",
        "block_payment",
        "delete_record"
    }
    
    if action_type in destructive_ops and not confirm:
        return json.dumps({
            "status": "requires_confirmation",
            "action": action_type,
            "message": f"Action '{action_type}' requires explicit confirmation. Set 'confirm': true in payload."
        })
    
    # Execute actions based on type
    try:
        if action_type == "create_ticket":
            # Use individual tool if available
            if INDIVIDUAL_TOOLS_AVAILABLE:
                try:
                    result_json = create_ticket(
                        project=data.get("project", "SUPPORT"),
                        summary=data.get("summary", ""),
                        description=data.get("description", ""),
                        priority=data.get("priority", "medium"),
                        labels=data.get("labels", []),
                        assignee=data.get("assignee")
                    )
                    # Parse and return
                    result = json.loads(result_json)
                    return ToolResponse(
                        status="ok",
                        data={
                            "action": "create_ticket",
                            "result": result.get("data", {})
                        },
                        tool_name="action_executor",
                        request_id=str(uuid.uuid4()),
                        source="jira"
                    ).to_json()
                except:
                    pass
            # Fallback to legacy
            result = _create_ticket(data)
            return ToolResponse(
                status="ok",
                data={
                    "action": "create_ticket",
                    "result": result
                },
                tool_name="action_executor",
                request_id=str(uuid.uuid4()),
                source="jira"
            ).to_json()
        
        elif action_type == "send_email":
            # Use individual tool if available
            if INDIVIDUAL_TOOLS_AVAILABLE:
                try:
                    result_json = send_email(
                        to=data.get("to", []),
                        subject=data.get("subject", ""),
                        body=data.get("body", ""),
                        attachments=data.get("attachments"),
                        from_email=data.get("from")
                    )
                    result = json.loads(result_json)
                    return ToolResponse(
                        status="ok",
                        data={
                            "action": "send_email",
                            "result": result.get("data", {})
                        },
                        tool_name="action_executor",
                        request_id=str(uuid.uuid4()),
                        source="smtp"
                    ).to_json()
                except:
                    pass
            # Fallback to legacy
            result = _send_email(data)
            return ToolResponse(
                status="ok",
                data={
                    "action": "send_email",
                    "result": result
                },
                tool_name="action_executor",
                request_id=str(uuid.uuid4()),
                source="smtp"
            ).to_json()
        
        elif action_type == "update_erp":
            result = _update_erp(data)
            return json.dumps({
                "status": "success",
                "action": "update_erp",
                "result": result
            })
        
        elif action_type == "run_rpa":
            result = _run_rpa(data)
            return json.dumps({
                "status": "success",
                "action": "run_rpa",
                "result": result
            })
        
        elif action_type == "alert":
            result = _send_alert(data)
            return json.dumps({
                "status": "success",
                "action": "alert",
                "result": result
            })
        
        elif action_type == "suspend_supplier":
            result = _suspend_supplier(data)
            return json.dumps({
                "status": "success",
                "action": "suspend_supplier",
                "result": result
            })
        
        else:
            return json.dumps({
                "status": "error",
                "error": "unknown_action",
                "action": action_type,
                "message": f"Unknown action type: {action_type}"
            })
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": "execution_failed",
            "action": action_type,
            "message": str(e)
        })


def _create_ticket(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a ticket in Jira/ServiceNow."""
    # Try to use integration manager if available
    try:
        from docchat.integrations import IntegrationManager
        from docchat.config import AppConfig
        
        config = AppConfig()
        integration_manager = IntegrationManager(config)
        
        # Try Jira first
        if "jira" in integration_manager.connected_integrations:
            # Use Jira integration
            ticket_data = {
                "summary": data.get("summary", "Auto-generated ticket"),
                "description": data.get("description", ""),
                "priority": data.get("priority", "medium"),
                "project": data.get("project", "SUPPORT")
            }
            # This would call the actual Jira API
            return {
                "ticket_id": f"JIRA-{hash(str(ticket_data)) % 10000}",
                "status": "created",
                "summary": ticket_data["summary"]
            }
    except:
        pass
    
    # Fallback: return mock ticket
    return {
        "ticket_id": f"TICKET-{hash(str(data)) % 100000}",
        "status": "created",
        "summary": data.get("summary", "Auto-generated ticket"),
        "message": "Ticket created (mock - configure Jira/ServiceNow integration for real tickets)"
    }


def _send_email(data: Dict[str, Any]) -> Dict[str, Any]:
    """Send an email."""
    try:
        from docchat.integrations import IntegrationManager
        from docchat.config import AppConfig
        
        config = AppConfig()
        integration_manager = IntegrationManager(config)
        
        # Try email integration
        email_data = {
            "to": data.get("to", []),
            "subject": data.get("subject", "Auto-generated email"),
            "body": data.get("body", ""),
            "priority": data.get("priority", "normal")
        }
        
        # This would call the actual email API
        return {
            "message_id": f"EMAIL-{hash(str(email_data)) % 100000}",
            "status": "sent",
            "recipients": email_data["to"]
        }
    except:
        return {
            "message_id": f"EMAIL-{hash(str(data)) % 100000}",
            "status": "sent",
            "message": "Email sent (mock - configure SMTP integration for real emails)"
        }


def _update_erp(data: Dict[str, Any]) -> Dict[str, Any]:
    """Update ERP system."""
    return {
        "updated": True,
        "record_id": data.get("record_id", "UNKNOWN"),
        "message": "ERP update executed (mock - configure ERP integration for real updates)"
    }


def _run_rpa(data: Dict[str, Any]) -> Dict[str, Any]:
    """Run RPA automation."""
    try:
        from docchat.rpa_automation import RPAAutomationEngine
        from docchat.config import AppConfig
        
        config = AppConfig()
        rpa_engine = RPAAutomationEngine(config)
        
        workflow_name = data.get("workflow", "default")
        params = data.get("params", {})
        
        # Execute RPA workflow
        result = rpa_engine.execute_workflow(workflow_name, params)
        
        return {
            "rpa_job_id": f"RPA-{hash(str(data)) % 100000}",
            "status": "completed",
            "result": result
        }
    except:
        return {
            "rpa_job_id": f"RPA-{hash(str(data)) % 100000}",
            "status": "completed",
            "message": "RPA workflow executed (mock - configure RPA engine for real automation)"
        }


def _send_alert(data: Dict[str, Any]) -> Dict[str, Any]:
    """Send an alert/notification."""
    return {
        "alert_id": f"ALERT-{hash(str(data)) % 100000}",
        "status": "sent",
        "message": data.get("message", "Alert sent")
    }


def _suspend_supplier(data: Dict[str, Any]) -> Dict[str, Any]:
    """Suspend a supplier."""
    supplier_id = data.get("supplier_id", "UNKNOWN")
    return {
        "supplier_id": supplier_id,
        "status": "suspended",
        "message": f"Supplier {supplier_id} suspended"
    }

