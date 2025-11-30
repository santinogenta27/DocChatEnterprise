"""
Handler para Microsoft (Teams, Outlook, OneDrive)
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
import requests

from .base_handler import BaseIntegrationHandler


class MicrosoftHandler(BaseIntegrationHandler):
    """Handler para Microsoft Teams, Outlook y OneDrive."""
    
    def search(self, query: str, access_token: str, max_results: int = 10) -> List[Document]:
        """Busca en Microsoft apps."""
        documents = []
        
        # Buscar en Outlook (emails)
        try:
            outlook_docs = self._search_outlook(query, access_token, max_results // 3)
            documents.extend(outlook_docs)
        except Exception as e:
            print(f"Error buscando en Outlook: {e}")
        
        # Buscar en OneDrive
        try:
            onedrive_docs = self._search_onedrive(query, access_token, max_results // 3)
            documents.extend(onedrive_docs)
        except Exception as e:
            print(f"Error buscando en OneDrive: {e}")
        
        # Buscar en Teams
        try:
            teams_docs = self._search_teams(query, access_token, max_results // 3)
            documents.extend(teams_docs)
        except Exception as e:
            print(f"Error buscando en Teams: {e}")
        
        return documents[:max_results]
    
    def _search_outlook(self, query: str, access_token: str, max_results: int) -> List[Document]:
        """Busca en Outlook."""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        search_url = "https://graph.microsoft.com/v1.0/me/messages"
        params = {"$search": f'"{query}"', "$top": max_results}
        
        response = requests.get(search_url, headers=headers, params=params)
        if response.status_code != 200:
            return []
        
        messages = response.json().get("value", [])
        documents = []
        
        for msg in messages[:max_results]:
            try:
                content = msg.get("body", {}).get("content", "")
                if content:
                    documents.append(Document(
                        page_content=content[:5000],
                        metadata={
                            "source": "outlook",
                            "message_id": msg.get("id", ""),
                            "subject": msg.get("subject", ""),
                            "integration": "outlook"
                        }
                    ))
            except Exception as e:
                print(f"Error procesando mensaje Outlook: {e}")
        
        return documents
    
    def _search_onedrive(self, query: str, access_token: str, max_results: int) -> List[Document]:
        """Busca en OneDrive."""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        search_url = "https://graph.microsoft.com/v1.0/me/drive/root/search"
        params = {"q": query, "top": max_results}
        
        response = requests.get(search_url, headers=headers, params=params)
        if response.status_code != 200:
            return []
        
        files = response.json().get("value", [])
        documents = []
        
        for file in files[:max_results]:
            try:
                file_id = file.get("id", "")
                download_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content"
                content_response = requests.get(download_url, headers=headers)
                
                if content_response.status_code == 200:
                    documents.append(Document(
                        page_content=content_response.text[:5000],
                        metadata={
                            "source": "onedrive",
                            "file_id": file_id,
                            "file_name": file.get("name", ""),
                            "integration": "onedrive"
                        }
                    ))
            except Exception as e:
                print(f"Error procesando archivo OneDrive: {e}")
        
        return documents
    
    def _search_teams(self, query: str, access_token: str, max_results: int) -> List[Document]:
        """Busca en Microsoft Teams."""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Obtener chats y mensajes
        chats_url = "https://graph.microsoft.com/v1.0/me/chats"
        response = requests.get(chats_url, headers=headers)
        
        if response.status_code != 200:
            return []
        
        chats = response.json().get("value", [])
        documents = []
        
        for chat in chats[:max_results]:
            try:
                chat_id = chat.get("id", "")
                messages_url = f"https://graph.microsoft.com/v1.0/me/chats/{chat_id}/messages"
                messages_response = requests.get(messages_url, headers=headers, params={"$top": 10})
                
                if messages_response.status_code == 200:
                    messages = messages_response.json().get("value", [])
                    for msg in messages:
                        if query.lower() in msg.get("body", {}).get("content", "").lower():
                            documents.append(Document(
                                page_content=msg.get("body", {}).get("content", ""),
                                metadata={
                                    "source": "teams",
                                    "message_id": msg.get("id", ""),
                                    "chat_id": chat_id,
                                    "integration": "teams"
                                }
                            ))
            except Exception as e:
                print(f"Error procesando chat Teams: {e}")
        
        return documents[:max_results]
    
    def refresh_token(self, refresh_token: str) -> Optional[str]:
        """Refresca token de Microsoft."""
        client_id = getattr(self.config, 'microsoft_client_id', '')
        client_secret = getattr(self.config, 'microsoft_client_secret', '')
        
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        response = requests.post("https://login.microsoftonline.com/common/oauth2/v2.0/token", data=data)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None


