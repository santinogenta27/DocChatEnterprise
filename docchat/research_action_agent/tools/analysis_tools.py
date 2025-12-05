"""Analysis tools: risk_score, parse_metrics, calculate_kpis."""

from __future__ import annotations

import json
import time
import uuid
import re
from typing import Dict, Any, Optional, List
from langchain.tools import tool
from .base_tool import ToolResponse


@tool
def risk_score(
    supplier_id: str,
    features: Dict[str, Any]
) -> str:
    """
    Calculate risk score for a supplier/entity.
    
    Args:
        supplier_id: ID of the supplier/entity
        features: Dict with on_time_rate, late_payments, compliance_flags, etc.
    
    Returns:
        JSON with standard contract including score (0-100), category, drivers
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Extract features
        on_time_rate = features.get("on_time_rate", 1.0)
        late_payments = features.get("late_payments", 0)
        compliance_flags = features.get("compliance_flags", 0)
        contract_issues = features.get("contract_issues", 0)
        
        # Rule-based blocking
        if compliance_flags > 0:
            score = 30  # High risk
            category = "high"
            drivers = [
                {"name": "compliance_flags", "weight": 1.0, "value": compliance_flags, "impact": "blocking"}
            ]
        else:
            # Calculate score (0-100, lower is riskier)
            # Base score from on-time rate
            base_score = on_time_rate * 70  # Max 70 points
            
            # Deduct for late payments
            payment_penalty = min(late_payments * 10, 30)  # Max 30 point penalty
            
            # Deduct for contract issues
            contract_penalty = min(contract_issues * 5, 20)  # Max 20 point penalty
            
            score = max(0, base_score - payment_penalty - contract_penalty)
            
            # Categorize
            if score > 75:
                category = "low"
            elif score >= 45:
                category = "medium"
            else:
                category = "high"
            
            # Drivers
            drivers = [
                {"name": "on_time_rate", "weight": 0.7, "value": on_time_rate, "impact": f"{base_score:.1f} points"},
                {"name": "late_payments", "weight": 0.2, "value": late_payments, "impact": f"-{payment_penalty:.1f} points"},
                {"name": "contract_issues", "weight": 0.1, "value": contract_issues, "impact": f"-{contract_penalty:.1f} points"}
            ]
        
        return ToolResponse(
            status="ok",
            data={
                "score": int(score),
                "category": category,
                "drivers": drivers
            },
            tool_name="risk_score",
            duration_ms=int((time.time() - start_time) * 1000),
            request_id=request_id,
            source="rule_based"
        ).to_json()
        
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="risk_score",
            request_id=request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()


@tool
def parse_metrics(
    text_or_json: str,
    schema: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Parse and extract metrics from text or JSON.
    
    Args:
        text_or_json: Text or JSON string to parse
        schema: Optional schema defining what to extract
    
    Returns:
        JSON with standard contract including metrics dict
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Try to parse as JSON first
        try:
            data = json.loads(text_or_json)
            if isinstance(data, dict):
                # Extract numeric values
                metrics = {}
                warnings = []
                
                for key, value in data.items():
                    if isinstance(value, (int, float)):
                        metrics[key] = float(value)
                    elif isinstance(value, str):
                        # Try to extract number
                        numbers = re.findall(r'-?\d+\.?\d*', value)
                        if numbers:
                            try:
                                metrics[key] = float(numbers[0])
                            except:
                                warnings.append(f"Could not parse {key}: {value}")
                
                return ToolResponse(
                    status="ok",
                    data={
                        "metrics": metrics,
                        "warnings": warnings
                    },
                    tool_name="parse_metrics",
                    duration_ms=int((time.time() - start_time) * 1000),
                    request_id=request_id,
                    source="json_parser"
                ).to_json()
        except:
            pass
        
        # Parse as text
        metrics = {}
        warnings = []
        
        # Extract currency amounts
        currency_pattern = r'\$[\d,]+\.?\d*'
        currency_matches = re.findall(currency_pattern, text_or_json)
        if currency_matches:
            for match in currency_matches:
                value = match.replace('$', '').replace(',', '')
                try:
                    metrics["currency_amount"] = float(value)
                except:
                    pass
        
        # Extract percentages
        percent_pattern = r'\d+\.?\d*%'
        percent_matches = re.findall(percent_pattern, text_or_json)
        if percent_matches:
            for match in percent_matches:
                value = match.replace('%', '')
                try:
                    metrics["percentage"] = float(value)
                except:
                    pass
        
        # Extract numbers
        number_pattern = r'-?\d+\.?\d*'
        numbers = re.findall(number_pattern, text_or_json)
        if numbers:
            try:
                metrics["numeric_value"] = float(numbers[0])
            except:
                pass
        
        return ToolResponse(
            status="ok",
            data={
                "metrics": metrics,
                "warnings": warnings if warnings else []
            },
            tool_name="parse_metrics",
            duration_ms=int((time.time() - start_time) * 1000),
            request_id=request_id,
            source="text_parser"
        ).to_json()
        
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="parse_metrics",
            request_id=request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()


@tool
def calculate_kpis(
    raw_data: Dict[str, Any],
    kpi_list: List[str]
) -> str:
    """
    Calculate KPIs from raw data.
    
    Args:
        raw_data: Dict with raw data
        kpi_list: List of KPI names to calculate (e.g., ["mrr", "lifetime_value"])
    
    Returns:
        JSON with standard contract including calculated KPIs
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        kpis = {}
        derivation = {}
        
        # MRR (Monthly Recurring Revenue)
        if "mrr" in kpi_list:
            revenue = raw_data.get("monthly_revenue", 0)
            kpis["mrr"] = float(revenue)
            derivation["mrr"] = f"monthly_revenue = {revenue}"
        
        # Lifetime Value
        if "lifetime_value" in kpi_list:
            avg_revenue = raw_data.get("avg_monthly_revenue", 0)
            avg_lifetime_months = raw_data.get("avg_lifetime_months", 12)
            ltv = avg_revenue * avg_lifetime_months
            kpis["lifetime_value"] = ltv
            derivation["lifetime_value"] = f"{avg_revenue} * {avg_lifetime_months} = {ltv}"
        
        # Churn Rate
        if "churn_rate" in kpi_list:
            lost_customers = raw_data.get("lost_customers", 0)
            total_customers = raw_data.get("total_customers", 1)
            if total_customers > 0:
                churn = (lost_customers / total_customers) * 100
                kpis["churn_rate"] = churn
                derivation["churn_rate"] = f"({lost_customers} / {total_customers}) * 100 = {churn}%"
        
        return ToolResponse(
            status="ok",
            data={
                "kpis": kpis,
                "derivation": derivation
            },
            tool_name="calculate_kpis",
            duration_ms=int((time.time() - start_time) * 1000),
            request_id=request_id,
            source="kpi_calculator"
        ).to_json()
        
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="calculate_kpis",
            request_id=request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()

