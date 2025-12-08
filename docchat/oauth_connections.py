"""OAuth Connections - Conexiones reales con Gmail, Drive, Outlook, etc.

Sistema de OAuth para conectar fuentes externas y sincronizar PDFs automáticamente.
"""

from __future__ import annotations

import os
import json
import base64
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlencode, parse_qs, urlparse
import hashlib
import mimetypes

from .config import AppConfig


class OAuthProvider:
    """Clase base para proveedores de OAuth."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.tokens_dir = Path(config.memory_dir) / "oauth_tokens"
        self.tokens_dir.mkdir(parents=True, exist_ok=True)
    
    def get_auth_url(self) -> str:
        """Genera URL de autorización."""
        raise NotImplementedError
    
    def exchange_code(self, code: str) -> Dict[str, Any]:
        """Intercambia código por tokens."""
        raise NotImplementedError
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresca el access token."""
        raise NotImplementedError
    
    def save_tokens(self, user_id: str, tokens: Dict[str, Any]):
        """Guarda tokens de forma segura."""
        token_file = self.tokens_dir / f"{self.provider_name}_{user_id}.json"
        tokens['saved_at'] = datetime.now().isoformat()
        with open(token_file, 'w') as f:
            json.dump(tokens, f)
    
    def load_tokens(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Carga tokens guardados."""
        token_file = self.tokens_dir / f"{self.provider_name}_{user_id}.json"
        if token_file.exists():
            with open(token_file, 'r') as f:
                return json.load(f)
        return None
    
    def delete_tokens(self, user_id: str):
        """Elimina tokens."""
        token_file = self.tokens_dir / f"{self.provider_name}_{user_id}.json"
        if token_file.exists():
            token_file.unlink()


class GoogleOAuth(OAuthProvider):
    """OAuth para Google (Gmail y Drive)."""
    
    provider_name = "google"
    
    # URLs de OAuth de Google
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    
    # Scopes necesarios
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",  # Leer emails
        "https://www.googleapis.com/auth/drive.readonly",  # Leer Drive
        "https://www.googleapis.com/auth/userinfo.email",  # Email del usuario
    ]
    
    def __init__(self, config: AppConfig):
        super().__init__(config)
        # Credenciales de OAuth (el usuario debe configurarlas)
        self.client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:7860/oauth/google/callback")
    
    def is_configured(self) -> bool:
        """Verifica si las credenciales están configuradas."""
        return bool(self.client_id and self.client_secret)
    
    def get_auth_url(self, state: str = "default") -> str:
        """Genera URL de autorización de Google."""
        if not self.is_configured():
            return ""
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "access_type": "offline",  # Para obtener refresh_token
            "prompt": "consent",  # Forzar pantalla de consentimiento
            "state": state
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    def exchange_code(self, code: str) -> Dict[str, Any]:
        """Intercambia código de autorización por tokens."""
        if not self.is_configured():
            return {"error": "Google OAuth no configurado"}
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri
        }
        
        response = requests.post(self.TOKEN_URL, data=data)
        if response.status_code == 200:
            tokens = response.json()
            return {
                "success": True,
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "expires_in": tokens.get("expires_in"),
                "token_type": tokens.get("token_type")
            }
        else:
            return {"error": f"Error obteniendo tokens: {response.text}"}
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresca el access token."""
        if not self.is_configured():
            return {"error": "Google OAuth no configurado"}
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        response = requests.post(self.TOKEN_URL, data=data)
        if response.status_code == 200:
            tokens = response.json()
            return {
                "success": True,
                "access_token": tokens.get("access_token"),
                "expires_in": tokens.get("expires_in")
            }
        else:
            return {"error": f"Error refrescando token: {response.text}"}


class MicrosoftOAuth(OAuthProvider):
    """OAuth para Microsoft (Outlook y OneDrive)."""
    
    provider_name = "microsoft"
    
    # URLs de OAuth de Microsoft
    AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    
    # Scopes necesarios
    SCOPES = [
        "https://graph.microsoft.com/Mail.Read",  # Leer emails
        "https://graph.microsoft.com/Files.Read",  # Leer OneDrive
        "https://graph.microsoft.com/User.Read",  # Info del usuario
        "offline_access"  # Para refresh token
    ]
    
    def __init__(self, config: AppConfig):
        super().__init__(config)
        self.client_id = os.getenv("MICROSOFT_CLIENT_ID", "")
        self.client_secret = os.getenv("MICROSOFT_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:7860/oauth/microsoft/callback")
    
    def is_configured(self) -> bool:
        """Verifica si las credenciales están configuradas."""
        return bool(self.client_id and self.client_secret)
    
    def get_auth_url(self, state: str = "default") -> str:
        """Genera URL de autorización de Microsoft."""
        if not self.is_configured():
            return ""
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "response_mode": "query",
            "state": state
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    def exchange_code(self, code: str) -> Dict[str, Any]:
        """Intercambia código por tokens."""
        if not self.is_configured():
            return {"error": "Microsoft OAuth no configurado"}
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.SCOPES)
        }
        
        response = requests.post(self.TOKEN_URL, data=data)
        if response.status_code == 200:
            tokens = response.json()
            return {
                "success": True,
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "expires_in": tokens.get("expires_in")
            }
        else:
            return {"error": f"Error obteniendo tokens: {response.text}"}
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresca el access token."""
        if not self.is_configured():
            return {"error": "Microsoft OAuth no configurado"}
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(self.SCOPES)
        }
        
        response = requests.post(self.TOKEN_URL, data=data)
        if response.status_code == 200:
            tokens = response.json()
            return {
                "success": True,
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token", refresh_token),
                "expires_in": tokens.get("expires_in")
            }
        else:
            return {"error": f"Error refrescando token: {response.text}"}


class DropboxOAuth(OAuthProvider):
    """OAuth para Dropbox."""
    
    provider_name = "dropbox"
    
    AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
    TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"
    
    def __init__(self, config: AppConfig):
        super().__init__(config)
        self.client_id = os.getenv("DROPBOX_CLIENT_ID", "")
        self.client_secret = os.getenv("DROPBOX_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("DROPBOX_REDIRECT_URI", "http://localhost:7860/oauth/dropbox/callback")
    
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)
    
    def get_auth_url(self, state: str = "default") -> str:
        if not self.is_configured():
            return ""
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "token_access_type": "offline",
            "state": state
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    def exchange_code(self, code: str) -> Dict[str, Any]:
        if not self.is_configured():
            return {"error": "Dropbox OAuth no configurado"}
        
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri
        }
        
        auth = (self.client_id, self.client_secret)
        response = requests.post(self.TOKEN_URL, data=data, auth=auth)
        
        if response.status_code == 200:
            tokens = response.json()
            return {
                "success": True,
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "expires_in": tokens.get("expires_in")
            }
        else:
            return {"error": f"Error obteniendo tokens: {response.text}"}


# ==================== SINCRONIZADORES DE PDFs ====================

class GmailPDFSync:
    """Sincroniza PDFs desde Gmail."""
    
    GMAIL_API_URL = "https://gmail.googleapis.com/gmail/v1"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}
    
    def get_emails_with_pdfs(self, max_results: int = 100) -> List[Dict[str, Any]]:
        """Obtiene emails que tienen adjuntos PDF."""
        # Buscar emails con adjuntos PDF
        query = "has:attachment filename:pdf"
        url = f"{self.GMAIL_API_URL}/users/me/messages"
        params = {"q": query, "maxResults": max_results}
        
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            print(f"Error buscando emails: {response.text}")
            return []
        
        data = response.json()
        messages = data.get("messages", [])
        return messages
    
    def get_pdf_attachments(self, message_id: str) -> List[Dict[str, Any]]:
        """Obtiene los adjuntos PDF de un email."""
        url = f"{self.GMAIL_API_URL}/users/me/messages/{message_id}"
        params = {"format": "full"}
        
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            return []
        
        message = response.json()
        attachments = []
        
        # Obtener info del remitente y asunto
        headers = message.get("payload", {}).get("headers", [])
        sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "unknown")
        subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "Sin asunto")
        date = next((h["value"] for h in headers if h["name"].lower() == "date"), "")
        
        # Buscar partes con adjuntos
        def find_attachments(parts):
            found = []
            for part in parts:
                filename = part.get("filename", "")
                if filename.lower().endswith(".pdf"):
                    found.append({
                        "filename": filename,
                        "attachment_id": part.get("body", {}).get("attachmentId"),
                        "size": part.get("body", {}).get("size", 0),
                        "mime_type": part.get("mimeType", "application/pdf"),
                        "sender": sender,
                        "subject": subject,
                        "date": date,
                        "message_id": message_id
                    })
                # Buscar recursivamente en partes anidadas
                if "parts" in part:
                    found.extend(find_attachments(part["parts"]))
            return found
        
        payload = message.get("payload", {})
        if "parts" in payload:
            attachments = find_attachments(payload["parts"])
        
        return attachments
    
    def download_attachment(self, message_id: str, attachment_id: str) -> Optional[bytes]:
        """Descarga un adjunto."""
        url = f"{self.GMAIL_API_URL}/users/me/messages/{message_id}/attachments/{attachment_id}"
        
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            return None
        
        data = response.json()
        # El contenido viene en base64 URL-safe
        attachment_data = data.get("data", "")
        # Convertir de base64 URL-safe a bytes
        attachment_data = attachment_data.replace("-", "+").replace("_", "/")
        # Agregar padding si es necesario
        padding = 4 - len(attachment_data) % 4
        if padding != 4:
            attachment_data += "=" * padding
        
        return base64.b64decode(attachment_data)
    
    def sync_all_pdfs(self, save_dir: Path, max_emails: int = 100) -> Dict[str, Any]:
        """Sincroniza todos los PDFs de Gmail."""
        save_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "total_emails": 0,
            "total_pdfs": 0,
            "downloaded": [],
            "errors": []
        }
        
        # Obtener emails con PDFs
        emails = self.get_emails_with_pdfs(max_results=max_emails)
        results["total_emails"] = len(emails)
        
        for email in emails:
            message_id = email.get("id")
            attachments = self.get_pdf_attachments(message_id)
            
            for att in attachments:
                try:
                    # Descargar el PDF
                    content = self.download_attachment(message_id, att["attachment_id"])
                    if content:
                        # Determinar categoría basada en el asunto/remitente
                        category = self._categorize_pdf(att)
                        category_dir = save_dir / category
                        category_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Guardar archivo
                        filename = att["filename"]
                        file_path = category_dir / filename
                        
                        # Evitar duplicados
                        counter = 1
                        original_stem = file_path.stem
                        while file_path.exists():
                            file_path = category_dir / f"{original_stem}_{counter}.pdf"
                            counter += 1
                        
                        with open(file_path, 'wb') as f:
                            f.write(content)
                        
                        results["downloaded"].append({
                            "filename": file_path.name,
                            "path": str(file_path),
                            "size": len(content),
                            "sender": att["sender"],
                            "subject": att["subject"],
                            "category": category
                        })
                        results["total_pdfs"] += 1
                except Exception as e:
                    results["errors"].append({
                        "filename": att.get("filename", "unknown"),
                        "error": str(e)
                    })
        
        return results
    
    def _categorize_pdf(self, attachment_info: Dict[str, Any]) -> str:
        """Categoriza un PDF basado en su nombre, remitente o asunto."""
        filename = attachment_info.get("filename", "").lower()
        subject = attachment_info.get("subject", "").lower()
        sender = attachment_info.get("sender", "").lower()
        
        # Palabras clave para categorías
        if any(word in filename or word in subject for word in ["factura", "invoice", "recibo", "receipt"]):
            return "facturas"
        elif any(word in filename or word in subject for word in ["contrato", "contract", "acuerdo", "agreement"]):
            return "contratos"
        elif any(word in filename or word in subject for word in ["reporte", "report", "informe"]):
            return "reportes"
        elif any(word in filename or word in subject for word in ["estado", "statement", "cuenta"]):
            return "estados_cuenta"
        else:
            return "otros"


class GoogleDrivePDFSync:
    """Sincroniza PDFs desde Google Drive."""
    
    DRIVE_API_URL = "https://www.googleapis.com/drive/v3"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}
    
    def get_pdf_files(self, max_results: int = 100) -> List[Dict[str, Any]]:
        """Obtiene lista de PDFs en Drive."""
        url = f"{self.DRIVE_API_URL}/files"
        params = {
            "q": "mimeType='application/pdf' and trashed=false",
            "pageSize": max_results,
            "fields": "files(id,name,size,createdTime,modifiedTime,parents)"
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            print(f"Error listando archivos: {response.text}")
            return []
        
        data = response.json()
        return data.get("files", [])
    
    def download_file(self, file_id: str) -> Optional[bytes]:
        """Descarga un archivo de Drive."""
        url = f"{self.DRIVE_API_URL}/files/{file_id}"
        params = {"alt": "media"}
        
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            return response.content
        return None
    
    def sync_all_pdfs(self, save_dir: Path, max_files: int = 100) -> Dict[str, Any]:
        """Sincroniza todos los PDFs de Drive."""
        save_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "total_files": 0,
            "downloaded": [],
            "errors": []
        }
        
        files = self.get_pdf_files(max_results=max_files)
        results["total_files"] = len(files)
        
        for file_info in files:
            try:
                content = self.download_file(file_info["id"])
                if content:
                    filename = file_info["name"]
                    file_path = save_dir / filename
                    
                    # Evitar duplicados
                    counter = 1
                    original_stem = file_path.stem
                    while file_path.exists():
                        file_path = save_dir / f"{original_stem}_{counter}.pdf"
                        counter += 1
                    
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    
                    results["downloaded"].append({
                        "filename": file_path.name,
                        "path": str(file_path),
                        "size": len(content),
                        "drive_id": file_info["id"]
                    })
            except Exception as e:
                results["errors"].append({
                    "filename": file_info.get("name", "unknown"),
                    "error": str(e)
                })
        
        return results


class OutlookPDFSync:
    """Sincroniza PDFs desde Outlook."""
    
    GRAPH_API_URL = "https://graph.microsoft.com/v1.0"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}
    
    def get_emails_with_pdfs(self, max_results: int = 100) -> List[Dict[str, Any]]:
        """Obtiene emails con adjuntos PDF."""
        url = f"{self.GRAPH_API_URL}/me/messages"
        params = {
            "$filter": "hasAttachments eq true",
            "$top": max_results,
            "$select": "id,subject,from,receivedDateTime,hasAttachments"
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            print(f"Error buscando emails: {response.text}")
            return []
        
        data = response.json()
        return data.get("value", [])
    
    def get_pdf_attachments(self, message_id: str) -> List[Dict[str, Any]]:
        """Obtiene adjuntos PDF de un email."""
        url = f"{self.GRAPH_API_URL}/me/messages/{message_id}/attachments"
        
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            return []
        
        data = response.json()
        attachments = []
        
        for att in data.get("value", []):
            if att.get("name", "").lower().endswith(".pdf"):
                attachments.append({
                    "id": att.get("id"),
                    "filename": att.get("name"),
                    "size": att.get("size", 0),
                    "content_bytes": att.get("contentBytes"),  # Base64
                    "message_id": message_id
                })
        
        return attachments
    
    def sync_all_pdfs(self, save_dir: Path, max_emails: int = 100) -> Dict[str, Any]:
        """Sincroniza todos los PDFs de Outlook."""
        save_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "total_emails": 0,
            "total_pdfs": 0,
            "downloaded": [],
            "errors": []
        }
        
        emails = self.get_emails_with_pdfs(max_results=max_emails)
        results["total_emails"] = len(emails)
        
        for email in emails:
            message_id = email.get("id")
            attachments = self.get_pdf_attachments(message_id)
            
            for att in attachments:
                try:
                    if att.get("content_bytes"):
                        content = base64.b64decode(att["content_bytes"])
                        
                        filename = att["filename"]
                        file_path = save_dir / filename
                        
                        counter = 1
                        original_stem = file_path.stem
                        while file_path.exists():
                            file_path = save_dir / f"{original_stem}_{counter}.pdf"
                            counter += 1
                        
                        with open(file_path, 'wb') as f:
                            f.write(content)
                        
                        results["downloaded"].append({
                            "filename": file_path.name,
                            "path": str(file_path),
                            "size": len(content),
                            "subject": email.get("subject", "")
                        })
                        results["total_pdfs"] += 1
                except Exception as e:
                    results["errors"].append({
                        "filename": att.get("filename", "unknown"),
                        "error": str(e)
                    })
        
        return results


class OneDrivePDFSync:
    """Sincroniza PDFs desde OneDrive."""
    
    GRAPH_API_URL = "https://graph.microsoft.com/v1.0"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}
    
    def get_pdf_files(self, max_results: int = 100) -> List[Dict[str, Any]]:
        """Obtiene lista de PDFs en OneDrive."""
        # Buscar archivos PDF
        url = f"{self.GRAPH_API_URL}/me/drive/root/search(q='.pdf')"
        params = {"$top": max_results}
        
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            print(f"Error buscando archivos: {response.text}")
            return []
        
        data = response.json()
        # Filtrar solo PDFs
        files = [f for f in data.get("value", []) if f.get("name", "").lower().endswith(".pdf")]
        return files
    
    def download_file(self, item_id: str) -> Optional[bytes]:
        """Descarga un archivo de OneDrive."""
        url = f"{self.GRAPH_API_URL}/me/drive/items/{item_id}/content"
        
        response = requests.get(url, headers=self.headers, allow_redirects=True)
        if response.status_code == 200:
            return response.content
        return None
    
    def sync_all_pdfs(self, save_dir: Path, max_files: int = 100) -> Dict[str, Any]:
        """Sincroniza todos los PDFs de OneDrive."""
        save_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "total_files": 0,
            "downloaded": [],
            "errors": []
        }
        
        files = self.get_pdf_files(max_results=max_files)
        results["total_files"] = len(files)
        
        for file_info in files:
            try:
                content = self.download_file(file_info["id"])
                if content:
                    filename = file_info["name"]
                    file_path = save_dir / filename
                    
                    counter = 1
                    original_stem = file_path.stem
                    while file_path.exists():
                        file_path = save_dir / f"{original_stem}_{counter}.pdf"
                        counter += 1
                    
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    
                    results["downloaded"].append({
                        "filename": file_path.name,
                        "path": str(file_path),
                        "size": len(content)
                    })
            except Exception as e:
                results["errors"].append({
                    "filename": file_info.get("name", "unknown"),
                    "error": str(e)
                })
        
        return results


class DropboxPDFSync:
    """Sincroniza PDFs desde Dropbox."""
    
    API_URL = "https://api.dropboxapi.com/2"
    CONTENT_URL = "https://content.dropboxapi.com/2"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}
    
    def get_pdf_files(self, path: str = "") -> List[Dict[str, Any]]:
        """Obtiene lista de PDFs en Dropbox."""
        url = f"{self.API_URL}/files/search_v2"
        headers = {**self.headers, "Content-Type": "application/json"}
        
        data = {
            "query": ".pdf",
            "options": {
                "filename_only": True,
                "max_results": 100
            }
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            print(f"Error buscando archivos: {response.text}")
            return []
        
        result = response.json()
        files = []
        for match in result.get("matches", []):
            metadata = match.get("metadata", {}).get("metadata", {})
            if metadata.get("name", "").lower().endswith(".pdf"):
                files.append(metadata)
        
        return files
    
    def download_file(self, path: str) -> Optional[bytes]:
        """Descarga un archivo de Dropbox."""
        url = f"{self.CONTENT_URL}/files/download"
        headers = {
            **self.headers,
            "Dropbox-API-Arg": json.dumps({"path": path})
        }
        
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            return response.content
        return None
    
    def sync_all_pdfs(self, save_dir: Path, max_files: int = 100) -> Dict[str, Any]:
        """Sincroniza todos los PDFs de Dropbox."""
        save_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "total_files": 0,
            "downloaded": [],
            "errors": []
        }
        
        files = self.get_pdf_files()[:max_files]
        results["total_files"] = len(files)
        
        for file_info in files:
            try:
                path = file_info.get("path_lower") or file_info.get("path_display")
                if path:
                    content = self.download_file(path)
                    if content:
                        filename = file_info["name"]
                        file_path = save_dir / filename
                        
                        counter = 1
                        original_stem = file_path.stem
                        while file_path.exists():
                            file_path = save_dir / f"{original_stem}_{counter}.pdf"
                            counter += 1
                        
                        with open(file_path, 'wb') as f:
                            f.write(content)
                        
                        results["downloaded"].append({
                            "filename": file_path.name,
                            "path": str(file_path),
                            "size": len(content)
                        })
            except Exception as e:
                results["errors"].append({
                    "filename": file_info.get("name", "unknown"),
                    "error": str(e)
                })
        
        return results


# ==================== MANAGER PRINCIPAL ====================

class RealConnectionsManager:
    """Manager principal de conexiones reales con OAuth."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.sync_dir = Path(config.memory_dir) / "synced_documents"
        self.sync_dir.mkdir(parents=True, exist_ok=True)
        
        # Inicializar proveedores OAuth
        self.google_oauth = GoogleOAuth(config)
        self.microsoft_oauth = MicrosoftOAuth(config)
        self.dropbox_oauth = DropboxOAuth(config)
        
        # Estado de conexiones
        self.connections_file = self.sync_dir / "real_connections.json"
        self.connections = self._load_connections()
    
    def _load_connections(self) -> Dict[str, Any]:
        """Carga conexiones guardadas."""
        if self.connections_file.exists():
            with open(self.connections_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_connections(self):
        """Guarda conexiones."""
        with open(self.connections_file, 'w') as f:
            json.dump(self.connections, f, indent=2)
    
    def get_oauth_status(self) -> Dict[str, Any]:
        """Obtiene el estado de configuración de OAuth."""
        return {
            "google": {
                "configured": self.google_oauth.is_configured(),
                "services": ["Gmail", "Google Drive"],
                "setup_instructions": "Configura GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET en las variables de entorno"
            },
            "microsoft": {
                "configured": self.microsoft_oauth.is_configured(),
                "services": ["Outlook", "OneDrive"],
                "setup_instructions": "Configura MICROSOFT_CLIENT_ID y MICROSOFT_CLIENT_SECRET en las variables de entorno"
            },
            "dropbox": {
                "configured": self.dropbox_oauth.is_configured(),
                "services": ["Dropbox"],
                "setup_instructions": "Configura DROPBOX_CLIENT_ID y DROPBOX_CLIENT_SECRET en las variables de entorno"
            }
        }
    
    def get_auth_url(self, provider: str, user_id: str = "default") -> str:
        """Obtiene URL de autorización para un proveedor."""
        if provider == "google":
            return self.google_oauth.get_auth_url(state=user_id)
        elif provider == "microsoft":
            return self.microsoft_oauth.get_auth_url(state=user_id)
        elif provider == "dropbox":
            return self.dropbox_oauth.get_auth_url(state=user_id)
        return ""
    
    def handle_oauth_callback(self, provider: str, code: str, user_id: str = "default") -> Dict[str, Any]:
        """Maneja el callback de OAuth."""
        if provider == "google":
            result = self.google_oauth.exchange_code(code)
            if result.get("success"):
                self.google_oauth.save_tokens(user_id, result)
                self.connections[f"google_{user_id}"] = {
                    "provider": "google",
                    "connected_at": datetime.now().isoformat(),
                    "status": "connected"
                }
                self._save_connections()
        elif provider == "microsoft":
            result = self.microsoft_oauth.exchange_code(code)
            if result.get("success"):
                self.microsoft_oauth.save_tokens(user_id, result)
                self.connections[f"microsoft_{user_id}"] = {
                    "provider": "microsoft",
                    "connected_at": datetime.now().isoformat(),
                    "status": "connected"
                }
                self._save_connections()
        elif provider == "dropbox":
            result = self.dropbox_oauth.exchange_code(code)
            if result.get("success"):
                self.dropbox_oauth.save_tokens(user_id, result)
                self.connections[f"dropbox_{user_id}"] = {
                    "provider": "dropbox",
                    "connected_at": datetime.now().isoformat(),
                    "status": "connected"
                }
                self._save_connections()
        else:
            result = {"error": "Proveedor no soportado"}
        
        return result
    
    def sync_pdfs(self, source: str, user_id: str = "default", max_files: int = 100) -> Dict[str, Any]:
        """Sincroniza PDFs de una fuente."""
        # Obtener tokens
        if source in ["gmail", "google_drive"]:
            tokens = self.google_oauth.load_tokens(user_id)
            if not tokens:
                return {"error": "No conectado a Google. Autoriza primero."}
            access_token = tokens.get("access_token")
        elif source in ["outlook", "onedrive"]:
            tokens = self.microsoft_oauth.load_tokens(user_id)
            if not tokens:
                return {"error": "No conectado a Microsoft. Autoriza primero."}
            access_token = tokens.get("access_token")
        elif source == "dropbox":
            tokens = self.dropbox_oauth.load_tokens(user_id)
            if not tokens:
                return {"error": "No conectado a Dropbox. Autoriza primero."}
            access_token = tokens.get("access_token")
        else:
            return {"error": f"Fuente no soportada: {source}"}
        
        # Crear directorio para la fuente
        source_dir = self.sync_dir / source
        
        # Sincronizar según la fuente
        if source == "gmail":
            syncer = GmailPDFSync(access_token)
            return syncer.sync_all_pdfs(source_dir, max_emails=max_files)
        elif source == "google_drive":
            syncer = GoogleDrivePDFSync(access_token)
            return syncer.sync_all_pdfs(source_dir, max_files=max_files)
        elif source == "outlook":
            syncer = OutlookPDFSync(access_token)
            return syncer.sync_all_pdfs(source_dir, max_emails=max_files)
        elif source == "onedrive":
            syncer = OneDrivePDFSync(access_token)
            return syncer.sync_all_pdfs(source_dir, max_files=max_files)
        elif source == "dropbox":
            syncer = DropboxPDFSync(access_token)
            return syncer.sync_all_pdfs(source_dir, max_files=max_files)
        
        return {"error": "Sincronizador no disponible"}
    
    def is_connected(self, provider: str, user_id: str = "default") -> bool:
        """Verifica si hay una conexión activa."""
        connection_key = f"{provider}_{user_id}"
        if connection_key in self.connections:
            # Verificar que existen tokens
            if provider == "google":
                return self.google_oauth.load_tokens(user_id) is not None
            elif provider == "microsoft":
                return self.microsoft_oauth.load_tokens(user_id) is not None
            elif provider == "dropbox":
                return self.dropbox_oauth.load_tokens(user_id) is not None
        return False
    
    def disconnect(self, provider: str, user_id: str = "default") -> Dict[str, Any]:
        """Desconecta un proveedor."""
        connection_key = f"{provider}_{user_id}"
        
        if provider == "google":
            self.google_oauth.delete_tokens(user_id)
        elif provider == "microsoft":
            self.microsoft_oauth.delete_tokens(user_id)
        elif provider == "dropbox":
            self.dropbox_oauth.delete_tokens(user_id)
        
        if connection_key in self.connections:
            del self.connections[connection_key]
            self._save_connections()
        
        return {"success": True, "message": f"{provider} desconectado"}


