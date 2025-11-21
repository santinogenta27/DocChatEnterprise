"""Gmail integration for reading and sending emails."""

from __future__ import annotations

from typing import List, Dict, Optional
from datetime import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GmailIntegration:
    """Gmail integration for email operations."""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 
              'https://www.googleapis.com/auth/gmail.send']
    
    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path
        self.service = None
        self._credentials = None
    
    def authenticate(self, credentials_json: Dict) -> bool:
        """Authenticate with Gmail API."""
        try:
            creds = Credentials.from_authorized_user_info(credentials_json, self.SCOPES)
            self.service = build('gmail', 'v1', credentials=creds)
            self._credentials = creds
            return True
        except Exception as e:
            print(f"Gmail authentication failed: {e}")
            return False
    
    def get_emails(self, query: str = "", max_results: int = 10) -> List[Dict]:
        """Get emails from Gmail."""
        if not self.service:
            return []
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for msg in messages:
                message = self.service.users().messages().get(
                    userId='me',
                    id=msg['id']
                ).execute()
                
                payload = message.get('payload', {})
                headers = payload.get('headers', [])
                
                email_data = {
                    'id': msg['id'],
                    'subject': self._get_header(headers, 'Subject'),
                    'from': self._get_header(headers, 'From'),
                    'date': self._get_header(headers, 'Date'),
                    'snippet': message.get('snippet', '')
                }
                emails.append(email_data)
            
            return emails
        except HttpError as e:
            print(f"Error getting emails: {e}")
            return []
    
    def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send email via Gmail."""
        if not self.service:
            return False
        
        try:
            message = self._create_message(to, subject, body)
            self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            return True
        except HttpError as e:
            print(f"Error sending email: {e}")
            return False
    
    def _get_header(self, headers: List[Dict], name: str) -> str:
        """Get header value by name."""
        for header in headers:
            if header['name'] == name:
                return header['value']
        return ""
    
    def _create_message(self, to: str, subject: str, body: str) -> Dict:
        """Create email message."""
        import base64
        from email.mime.text import MIMEText
        
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw}



