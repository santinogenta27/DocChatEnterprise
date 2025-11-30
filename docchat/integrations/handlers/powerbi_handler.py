"""
Handler para Microsoft Power BI
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
import requests

from .base_handler import BaseIntegrationHandler


class PowerBIHandler(BaseIntegrationHandler):
    """Handler para Microsoft Power BI."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """Busca en Power BI (reports, dashboards, datasets)."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        documents = []
        
        try:
            # Buscar reports
            reports_url = "https://api.powerbi.com/v1.0/myorg/reports"
            response = requests.get(reports_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                reports = response.json().get("value", [])
                for report in reports:
                    report_name = report.get("name", "")
                    if query.lower() in report_name.lower():
                        content = f"Report: {report_name}\nDescription: {report.get('description', 'N/A')}\nWeb URL: {report.get('webUrl', 'N/A')}"
                        documents.append(Document(
                            page_content=content,
                            metadata={
                                "source": "powerbi - Report",
                                "report_id": report.get("id", ""),
                                "report_name": report_name,
                                "integration": "powerbi"
                            }
                        ))
            
            # Buscar dashboards
            dashboards_url = "https://api.powerbi.com/v1.0/myorg/dashboards"
            response = requests.get(dashboards_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                dashboards = response.json().get("value", [])
                for dashboard in dashboards:
                    dashboard_name = dashboard.get("displayName", "")
                    if query.lower() in dashboard_name.lower():
                        content = f"Dashboard: {dashboard_name}\nWeb URL: {dashboard.get('webUrl', 'N/A')}"
                        documents.append(Document(
                            page_content=content,
                            metadata={
                                "source": "powerbi - Dashboard",
                                "dashboard_id": dashboard.get("id", ""),
                                "dashboard_name": dashboard_name,
                                "integration": "powerbi"
                            }
                        ))
        except Exception as e:
            print(f"Error buscando en Power BI: {e}")
        
        return documents[:max_results]


