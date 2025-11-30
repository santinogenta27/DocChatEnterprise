"""
Handler para Trello
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
import requests

from .base_handler import BaseIntegrationHandler


class TrelloHandler(BaseIntegrationHandler):
    """Handler para Trello."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """
        Busca en Trello.
        
        access_token debe ser: "api_key|api_token"
        """
        # Parsear token
        if "|" in access_token:
            api_key, api_token = access_token.split("|", 1)
        else:
            api_key = getattr(self.config, 'trello_api_key', '')
            api_token = access_token
        
        if not api_key:
            print("⚠️ Necesitás configurar TRELLO_API_KEY o incluirla en el token como 'key|token'")
            return []
        
        auth_params = {
            "key": api_key,
            "token": api_token
        }
        
        documents = []
        
        try:
            # Buscar cards
            search_url = "https://api.trello.com/1/search"
            params = {
                "query": query,
                "modelTypes": "cards",
                "cards_limit": max_results,
                **auth_params
            }
            response = requests.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                cards = response.json().get("cards", [])
                for card in cards:
                    card_id = card.get("id", "")
                    # Obtener detalles completos del card
                    card_url = f"https://api.trello.com/1/cards/{card_id}"
                    card_response = requests.get(card_url, params=auth_params, timeout=10)
                    
                    if card_response.status_code == 200:
                        card_data = card_response.json()
                        content = f"Card: {card_data.get('name', '')}\nDescription: {card_data.get('desc', '')}\nList: {card_data.get('list', {}).get('name', '')}\nBoard: {card_data.get('board', {}).get('name', '')}"
                        documents.append(Document(
                            page_content=content,
                            metadata={
                                "source": "trello - Card",
                                "card_id": card_id,
                                "card_name": card_data.get("name", ""),
                                "board": card_data.get("board", {}).get("name", ""),
                                "integration": "trello"
                            }
                        ))
        except Exception as e:
            print(f"Error buscando en Trello: {e}")
        
        return documents


