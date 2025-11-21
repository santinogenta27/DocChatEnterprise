"""Google Drive integration for document access."""

from __future__ import annotations

from typing import List, Dict, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class DriveIntegration:
    """Google Drive integration."""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path
        self.service = None
    
    def authenticate(self, credentials_json: Dict) -> bool:
        """Authenticate with Drive API."""
        try:
            creds = Credentials.from_authorized_user_info(credentials_json, self.SCOPES)
            self.service = build('drive', 'v3', credentials=creds)
            return True
        except Exception as e:
            print(f"Drive authentication failed: {e}")
            return False
    
    def list_files(self, folder_id: Optional[str] = None, max_results: int = 100) -> List[Dict]:
        """List files from Google Drive."""
        if not self.service:
            return []
        
        try:
            query = f"'{folder_id}' in parents" if folder_id else None
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, mimeType, modifiedTime)"
            ).execute()
            
            return results.get('files', [])
        except HttpError as e:
            print(f"Error listing files: {e}")
            return []
    
    def download_file(self, file_id: str, output_path: str) -> bool:
        """Download file from Drive."""
        if not self.service:
            return False
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            with open(output_path, 'wb') as f:
                f.write(request.execute())
            return True
        except HttpError as e:
            print(f"Error downloading file: {e}")
            return False



