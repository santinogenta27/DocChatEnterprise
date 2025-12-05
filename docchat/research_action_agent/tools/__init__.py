"""Tools for Research & Action Agent - 17 Essential Tools."""

# Research Tools
from .web_search import search_web
from .research_tools import extract_webpage, extract_document, summarize_text
from .rag_query import rag_query_tool

# Analysis Tools
from .analysis_tools import risk_score, parse_metrics, calculate_kpis

# Document Tools
from .document_tools import extract_tables_from_pdf, generate_pdf_report

# Action Tools
from .calculator import calculator_tool
from .action_tools import (
    send_email,
    create_ticket,
    crm_update_record,
    sql_query,
    erp_get_order_status,
    erp_update_order
)
from .action_executor import action_executor_tool  # Keep for backward compatibility

# Control Tools
from .control_tools import validate_action, write_audit_log

# Alias for backward compatibility
search_tool = search_web

TOOLS_REGISTRY = {
    # Research Tools (5)
    "search_web": search_web,
    "extract_webpage": extract_webpage,
    "search_docs": rag_query_tool,
    "extract_document": extract_document,
    "summarize_text": summarize_text,
    
    # Analysis Tools (3)
    "parse_metrics": parse_metrics,
    "risk_score": risk_score,
    "calculate_kpis": calculate_kpis,
    
    # Document Tools (2)
    "extract_tables_from_pdf": extract_tables_from_pdf,
    "generate_pdf_report": generate_pdf_report,
    
    # Action Tools (7)
    "calculator": calculator_tool,
    "send_email": send_email,
    "create_ticket": create_ticket,
    "crm_update_record": crm_update_record,
    "sql_query": sql_query,
    "erp_get_order_status": erp_get_order_status,
    "erp_update_order": erp_update_order,
    "action_executor": action_executor_tool,  # Backward compatibility
    
    # Control Tools (2)
    "validate_action": validate_action,
    "write_audit_log": write_audit_log,
}

__all__ = [
    # Research (5)
    "search_web",
    "extract_webpage",
    "rag_query_tool",
    "extract_document",
    "summarize_text",
    # Analysis (3)
    "risk_score",
    "parse_metrics",
    "calculate_kpis",
    # Document (2)
    "extract_tables_from_pdf",
    "generate_pdf_report",
    # Action (8)
    "calculator_tool",
    "send_email",
    "create_ticket",
    "crm_update_record",
    "sql_query",
    "erp_get_order_status",
    "erp_update_order",
    "action_executor_tool",
    # Control (2)
    "validate_action",
    "write_audit_log",
    # Registry
    "TOOLS_REGISTRY"
]

