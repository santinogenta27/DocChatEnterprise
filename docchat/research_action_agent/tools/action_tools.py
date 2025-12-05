"""Action tools: send_email, create_ticket, crm_update_record, sql_query, erp_tools."""

from __future__ import annotations

import json
import time
import uuid
import hashlib
from typing import Dict, Any, Optional, List
from langchain.tools import tool
from .base_tool import ToolResponse

# Idempotency store (in production, use Redis or DB)
_idempotency_store = {}


@tool
def send_email(
    to: List[str],
    subject: str,
    body: str,
    attachments: Optional[List[str]] = None,
    from_email: Optional[str] = None
) -> str:
    """
    Send an email.
    
    Args:
        to: List of recipient email addresses
        subject: Email subject
        body: Email body (HTML or plain text)
        attachments: Optional list of file IDs
        from_email: From email address (default: noreply@company.com)
    
    Returns:
        JSON with standard contract
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Validate inputs
        if not to or not isinstance(to, list):
            return ToolResponse(
                status="error",
                tool_name="send_email",
                request_id=request_id,
                source="smtp",
                error={
                    "code": "invalid_input",
                    "message": "Recipients list cannot be empty",
                    "details": {}
                }
            ).to_json()
        
        if not subject or not body:
            return ToolResponse(
                status="error",
                tool_name="send_email",
                request_id=request_id,
                source="smtp",
                error={
                    "code": "invalid_input",
                    "message": "Subject and body are required",
                    "details": {}
                }
            ).to_json()
        
        # Check idempotency
        idempotency_key = hashlib.md5(
            f"{to}_{subject}_{body}".encode()
        ).hexdigest()
        
        if idempotency_key in _idempotency_store:
            # Return previous result
            return ToolResponse(
                status="ok",
                data={
                    "message_id": _idempotency_store[idempotency_key]["message_id"],
                    "status": "sent",
                    "idempotent": True
                },
                tool_name="send_email",
                duration_ms=int((time.time() - start_time) * 1000),
                request_id=request_id,
                source="smtp"
            ).to_json()
        
        # In production, use actual SMTP client
        # For now, simulate email sending
        from_email = from_email or "noreply@company.com"
        
        # Rate limit check (simplified)
        # In production, check per domain rate limits
        
        # Send email (placeholder - integrate with SMTP/API)
        message_id = f"EMAIL-{hash(str(to) + subject) % 100000}"
        
        # Store for idempotency
        _idempotency_store[idempotency_key] = {
            "message_id": message_id,
            "timestamp": time.time()
        }
        
        return ToolResponse(
            status="ok",
            data={
                "message_id": message_id,
                "status": "sent",
                "recipients": to,
                "from": from_email
            },
            tool_name="send_email",
            duration_ms=int((time.time() - start_time) * 1000),
            request_id=request_id,
            source="smtp"
        ).to_json()
        
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="send_email",
            request_id=request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()


@tool
def create_ticket(
    project: str,
    summary: str,
    description: str,
    priority: str = "medium",
    labels: Optional[List[str]] = None,
    assignee: Optional[str] = None
) -> str:
    """
    Create a ticket in Jira/ServiceNow.
    
    Args:
        project: Project key (e.g., "FIN", "SUPPORT")
        summary: Ticket summary
        description: Ticket description
        priority: Priority level (low, medium, high, critical)
        labels: Optional list of labels
        assignee: Optional assignee email
    
    Returns:
        JSON with standard contract
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Validate inputs
        if not project or not summary:
            return ToolResponse(
                status="error",
                tool_name="create_ticket",
                request_id=request_id,
                source="jira",
                error={
                    "code": "invalid_input",
                    "message": "Project and summary are required",
                    "details": {}
                }
            ).to_json()
        
        # Check idempotency (avoid duplicate tickets)
        idempotency_key = hashlib.md5(
            f"{project}_{summary}_{description}".encode()
        ).hexdigest()
        
        if idempotency_key in _idempotency_store:
            return ToolResponse(
                status="ok",
                data={
                    "ticket_id": _idempotency_store[idempotency_key]["ticket_id"],
                    "url": _idempotency_store[idempotency_key].get("url", ""),
                    "status": "created",
                    "idempotent": True
                },
                tool_name="create_ticket",
                duration_ms=int((time.time() - start_time) * 1000),
                request_id=request_id,
                source="jira"
            ).to_json()
        
        # Validate assignee exists (in production, check against user directory)
        if assignee and "@" not in assignee:
            return ToolResponse(
                status="error",
                tool_name="create_ticket",
                request_id=request_id,
                source="jira",
                error={
                    "code": "invalid_assignee",
                    "message": f"Invalid assignee format: {assignee}",
                    "details": {}
                }
            ).to_json()
        
        # Create ticket (placeholder - integrate with Jira/ServiceNow API)
        ticket_id = f"{project}-{hash(summary + description) % 10000}"
        ticket_url = f"https://jira.company.com/browse/{ticket_id}"
        
        # Store for idempotency
        _idempotency_store[idempotency_key] = {
            "ticket_id": ticket_id,
            "url": ticket_url,
            "timestamp": time.time()
        }
        
        return ToolResponse(
            status="ok",
            data={
                "ticket_id": ticket_id,
                "url": ticket_url,
                "status": "created",
                "project": project,
                "priority": priority
            },
            tool_name="create_ticket",
            duration_ms=int((time.time() - start_time) * 1000),
            request_id=request_id,
            source="jira"
        ).to_json()
        
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="create_ticket",
            request_id=request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()


@tool
def crm_update_record(
    record_type: str,
    record_id: str,
    fields: Dict[str, Any]
) -> str:
    """
    Update a record in CRM (HubSpot/Salesforce).
    
    Args:
        record_type: Type of record (contact, company, deal, etc.)
        record_id: Record ID
        fields: Dict of fields to update
    
    Returns:
        JSON with standard contract
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Validate inputs
        if not record_type or not record_id or not fields:
            return ToolResponse(
                status="error",
                tool_name="crm_update_record",
                request_id=request_id,
                source="crm",
                error={
                    "code": "invalid_input",
                    "message": "record_type, record_id, and fields are required",
                    "details": {}
                }
            ).to_json()
        
        # Validate record type
        valid_types = ["contact", "company", "deal", "ticket", "product"]
        if record_type not in valid_types:
            return ToolResponse(
                status="error",
                tool_name="crm_update_record",
                request_id=request_id,
                source="crm",
                error={
                    "code": "invalid_record_type",
                    "message": f"Record type must be one of: {valid_types}",
                    "details": {}
                }
            ).to_json()
        
        # Update record (placeholder - integrate with HubSpot/Salesforce API)
        updated_fields = list(fields.keys())
        
        return ToolResponse(
            status="ok",
            data={
                "updated": True,
                "record_id": record_id,
                "record_type": record_type,
                "updated_fields": updated_fields
            },
            tool_name="crm_update_record",
            duration_ms=int((time.time() - start_time) * 1000),
            request_id=request_id,
            source="hubspot"  # or "salesforce"
        ).to_json()
        
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="crm_update_record",
            request_id=request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()


@tool
def sql_query(
    query: str,
    mode: str = "read",
    params: Optional[Dict[str, Any]] = None
) -> str:
    """
    Execute SQL query (read or write mode).
    
    WARNING: In auto mode, never accept raw user SQL. Use parameterized templates.
    
    Args:
        query: SQL query string (parameterized)
        mode: "read" or "write"
        params: Optional parameters for parameterized query
    
    Returns:
        JSON with standard contract
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Security: Never accept raw user SQL in auto mode
        # In production, use whitelisted query templates
        
        # Validate mode
        if mode not in ["read", "write"]:
            return ToolResponse(
                status="error",
                tool_name="sql_query",
                request_id=request_id,
                source="database",
                error={
                    "code": "invalid_mode",
                    "message": "Mode must be 'read' or 'write'",
                    "details": {}
                }
            ).to_json()
        
        # Check for dangerous SQL patterns
        dangerous_patterns = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "GRANT"]
        query_upper = query.upper()
        
        if mode == "read" and any(pattern in query_upper for pattern in dangerous_patterns):
            return ToolResponse(
                status="error",
                tool_name="sql_query",
                request_id=request_id,
                source="database",
                error={
                    "code": "dangerous_query",
                    "message": "Read mode does not allow DROP/DELETE/ALTER operations",
                    "details": {}
                }
            ).to_json()
        
        # Timeout settings
        timeout = 2 if mode == "read" else 5
        
        # Execute query (placeholder - integrate with actual DB)
        # In production, use parameterized queries and connection pooling
        
        # Limit rows returned
        max_rows = 10000
        
        # Simulate query execution
        rows = []
        rowcount = 0
        
        # In production:
        # with db_connection(timeout=timeout) as conn:
        #     cursor = conn.execute(query, params or {})
        #     rows = cursor.fetchmany(max_rows)
        #     rowcount = cursor.rowcount
        
        return ToolResponse(
            status="ok",
            data={
                "rows": rows[:max_rows],  # Limit to max_rows
                "rowcount": rowcount,
                "truncated": rowcount > max_rows
            },
            tool_name="sql_query",
            duration_ms=int((time.time() - start_time) * 1000),
            request_id=request_id,
            source="database"
        ).to_json()
        
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="sql_query",
            request_id=request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()


@tool
def erp_get_order_status(order_id: str) -> str:
    """
    Get order status from ERP system.
    
    Args:
        order_id: Order ID
    
    Returns:
        JSON with standard contract
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        if not order_id:
            return ToolResponse(
                status="error",
                tool_name="erp_get_order_status",
                request_id=request_id,
                source="erp",
                error={
                    "code": "invalid_input",
                    "message": "Order ID is required",
                    "details": {}
                }
            ).to_json()
        
        # Get order status (placeholder - integrate with SAP/Netsuite/Odoo API)
        order_status = {
            "order_id": order_id,
            "status": "pending",
            "amount": 0.0,
            "currency": "USD",
            "created_at": "",
            "updated_at": ""
        }
        
        return ToolResponse(
            status="ok",
            data=order_status,
            tool_name="erp_get_order_status",
            duration_ms=int((time.time() - start_time) * 1000),
            request_id=request_id,
            source="sap"  # or "netsuite", "odoo"
        ).to_json()
        
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="erp_get_order_status",
            request_id=request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()


@tool
def erp_update_order(
    order_id: str,
    updates: Dict[str, Any],
    confirm: bool = False
) -> str:
    """
    Update order in ERP system.
    
    Args:
        order_id: Order ID
        updates: Dict of fields to update
        confirm: Explicit confirmation required (default: False)
    
    Returns:
        JSON with standard contract
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        if not order_id or not updates:
            return ToolResponse(
                status="error",
                tool_name="erp_update_order",
                request_id=request_id,
                source="erp",
                error={
                    "code": "invalid_input",
                    "message": "Order ID and updates are required",
                    "details": {}
                }
            ).to_json()
        
        # Require confirmation for destructive operations
        if not confirm:
            return ToolResponse(
                status="requires_confirmation",
                data={
                    "proposed_action": {
                        "type": "erp_update_order",
                        "order_id": order_id,
                        "updates": updates
                    }
                },
                tool_name="erp_update_order",
                duration_ms=int((time.time() - start_time) * 1000),
                request_id=request_id,
                source="sap"
            ).to_json()
        
        # Update order (placeholder - integrate with ERP API)
        # Use idempotency token for safe retries
        
        return ToolResponse(
            status="ok",
            data={
                "updated": True,
                "order_id": order_id,
                "updated_fields": list(updates.keys())
            },
            tool_name="erp_update_order",
            duration_ms=int((time.time() - start_time) * 1000),
            request_id=request_id,
            source="sap"
        ).to_json()
        
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="erp_update_order",
            request_id=request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()

