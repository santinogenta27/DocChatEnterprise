"""Notion integration for accessing and updating pages."""

from __future__ import annotations

from typing import List, Dict, Optional
import requests


class NotionIntegration:
    """Notion integration."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        } if api_key else {}
    
    def get_pages(self, database_id: str) -> List[Dict]:
        """Get pages from Notion database."""
        if not self.api_key:
            return []
        
        try:
            response = requests.post(
                f"{self.base_url}/databases/{database_id}/query",
                headers=self.headers,
                json={}
            )
            response.raise_for_status()
            data = response.json()
            return data.get('results', [])
        except Exception as e:
            print(f"Error getting Notion pages: {e}")
            return []
    
    def create_page(self, database_id: str, properties: Dict) -> Optional[Dict]:
        """Create page in Notion database."""
        if not self.api_key:
            return None
        
        try:
            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json={
                    "parent": {"database_id": database_id},
                    "properties": properties
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error creating Notion page: {e}")
            return None
    
    def update_page(self, page_id: str, properties: Dict) -> bool:
        """Update Notion page."""
        if not self.api_key:
            return False
        
        try:
            response = requests.patch(
                f"{self.base_url}/pages/{page_id}",
                headers=self.headers,
                json={"properties": properties}
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error updating Notion page: {e}")
            return False



