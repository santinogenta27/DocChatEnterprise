"""
Handler para Notion
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
import requests

from .base_handler import BaseIntegrationHandler


class NotionHandler(BaseIntegrationHandler):
    """Handler para Notion."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """Busca en Notion."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        documents = []
        
        try:
            # Buscar páginas
            search_url = "https://api.notion.com/v1/search"
            payload = {
                "query": query,
                "page_size": max_results
            }
            
            response = requests.post(search_url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                results = response.json().get("results", [])
                for page in results:
                    page_id = page.get("id", "")
                    title = ""
                    
                    # Extraer título
                    properties = page.get("properties", {})
                    for prop_name, prop_data in properties.items():
                        if prop_data.get("type") == "title":
                            title_content = prop_data.get("title", [])
                            if title_content:
                                title = title_content[0].get("plain_text", "")
                    
                    # Obtener contenido de la página
                    blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
                    blocks_response = requests.get(blocks_url, headers=headers, timeout=10)
                    
                    content = title + "\n\n"
                    if blocks_response.status_code == 200:
                        blocks = blocks_response.json().get("results", [])
                        for block in blocks:
                            block_type = block.get("type", "")
                            block_data = block.get(block_type, {})
                            
                            if block_type == "paragraph":
                                text_content = block_data.get("rich_text", [])
                                for text in text_content:
                                    content += text.get("plain_text", "") + " "
                            elif block_type == "heading_1" or block_type == "heading_2" or block_type == "heading_3":
                                text_content = block_data.get("rich_text", [])
                                for text in text_content:
                                    content += text.get("plain_text", "") + "\n"
                    
                    if content.strip():
                        documents.append(Document(
                            page_content=content[:5000],
                            metadata={
                                "source": f"notion - {title or 'Sin título'}",
                                "page_id": page_id,
                                "title": title,
                                "integration": "notion"
                            }
                        ))
        except Exception as e:
            print(f"Error buscando en Notion: {e}")
        
        return documents


