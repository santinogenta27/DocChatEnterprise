"""
Handler para Asana
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
import requests

from .base_handler import BaseIntegrationHandler


class AsanaHandler(BaseIntegrationHandler):
    """Handler para Asana."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """Busca en Asana (tasks, projects)."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        documents = []
        
        try:
            # Buscar tasks
            search_url = "https://app.asana.com/api/1.0/tasks/search"
            params = {
                "text": query,
                "opt_fields": "name,notes,due_on,assignee.name,projects.name",
                "limit": max_results
            }
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                tasks = response.json().get("data", [])
                for task in tasks:
                    content = f"Task: {task.get('name', '')}\nNotes: {task.get('notes', '')}\nDue: {task.get('due_on', 'N/A')}\nAssignee: {task.get('assignee', {}).get('name', 'Unassigned')}"
                    documents.append(Document(
                        page_content=content,
                        metadata={
                            "source": "asana - Task",
                            "task_id": task.get("gid", ""),
                            "task_name": task.get("name", ""),
                            "integration": "asana"
                        }
                    ))
        except Exception as e:
            print(f"Error buscando en Asana: {e}")
        
        return documents


