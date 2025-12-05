"""Control tools: validate_action, write_audit_log."""

from __future__ import annotations

import json
import time
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from langchain.tools import tool
from .base_tool import ToolResponse

# Destructive operations that require confirmation
DESTRUCTIVE_OPS = {
    "update_erp",
    "run_rpa",
    "suspend_supplier",
    "block_payment",
    "delete_record",
    "update_crm",
    "sql_query"  # If mode is "write"
}

# RBAC rules (simplified - in production use proper RBAC system)
RBAC_RULES = {
    "admin": {
        "allowed_actions": ["*"],  # All actions
        "require_confirmation": False
    },
    "analyst": {
        "allowed_actions": ["search_web", "search_docs", "create_ticket", "send_email"],
        "require_confirmation": True
    },
    "viewer": {
        "allowed_actions": ["search_web", "search_docs"],
        "require_confirmation": True
    }
}


@tool
def validate_action(
    proposed_action: Dict[str, Any],
    user_role: str = "analyst"
) -> str:
    """
    Validate if an action is allowed and safe to execute.
    
    Args:
        proposed_action: Dict with type and payload
        user_role: User role (admin, analyst, viewer)
    
    Returns:
        JSON with standard contract including allowed, reasons, require_confirmation
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        action_type = proposed_action.get("type", "")
        payload = proposed_action.get("payload", {})
        
        # Check RBAC
        role_rules = RBAC_RULES.get(user_role, RBAC_RULES["viewer"])
        allowed_actions = role_rules["allowed_actions"]
        
        allowed = False
        reasons = []
        require_confirmation = role_rules.get("require_confirmation", True)
        
        # Check if action is in allowed list
        if "*" in allowed_actions or action_type in allowed_actions:
            allowed = True
            reasons.append(f"Action '{action_type}' allowed for role '{user_role}'")
        else:
            allowed = False
            reasons.append(f"Action '{action_type}' not allowed for role '{user_role}'")
            return ToolResponse(
                status="ok",
                data={
                    "allowed": False,
                    "reasons": reasons,
                    "require_confirmation": False
                },
                tool_name="validate_action",
                duration_ms=int((time.time() - start_time) * 1000),
                request_id=request_id,
                source="rbac"
            ).to_json()
        
        # Check if action is destructive
        if action_type in DESTRUCTIVE_OPS:
            require_confirmation = True
            reasons.append(f"Action '{action_type}' is destructive and requires confirmation")
        
        # Additional business rules
        # Example: Check budget limits
        if action_type == "update_erp" and "amount" in payload:
            amount = payload.get("amount", 0)
            if amount > 10000:
                require_confirmation = True
                reasons.append(f"Amount {amount} exceeds threshold, requires confirmation")
        
        # Check supplier blocklist
        if action_type == "suspend_supplier":
            supplier_id = payload.get("supplier_id", "")
            # In production, check against blocklist
            reasons.append(f"Suspending supplier {supplier_id} requires confirmation")
        
        return ToolResponse(
            status="ok",
            data={
                "allowed": allowed,
                "reasons": reasons,
                "require_confirmation": require_confirmation
            },
            tool_name="validate_action",
            duration_ms=int((time.time() - start_time) * 1000),
            request_id=request_id,
            source="rbac"
        ).to_json()
        
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="validate_action",
            request_id=request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()


@tool
def write_audit_log(
    request_id: str,
    tool: str,
    payload: Dict[str, Any],
    actor: str = "agent",
    result: Optional[Dict[str, Any]] = None
) -> str:
    """
    Write audit log entry for compliance and traceability.
    
    Args:
        request_id: Request ID for traceability
        tool: Tool name that was called
        payload: Input payload
        actor: "agent" or "user"
        result: Result from tool execution
    
    Returns:
        JSON with standard contract
    """
    start_time = time.time()
    log_request_id = str(uuid.uuid4())
    
    try:
        # Save to audit database
        from ..utils.audit import save_audit_log
        
        log_entry = {
            "request_id": request_id,
            "tool": tool,
            "payload": payload,
            "actor": actor,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Save audit log
        save_audit_log(
            query=f"Tool: {tool}",
            mode=actor,
            log=log_entry,
            final_result=result,
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
        
        return ToolResponse(
            status="ok",
            data={
                "log_id": log_request_id,
                "status": "logged"
            },
            tool_name="write_audit_log",
            duration_ms=int((time.time() - start_time) * 1000),
            request_id=log_request_id,
            source="audit_db"
        ).to_json()
        
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="write_audit_log",
            request_id=log_request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()

