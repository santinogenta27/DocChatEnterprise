"""Slack integration for notifications and data access."""

from __future__ import annotations

from typing import List, Dict, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackIntegration:
    """Slack integration."""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.client = WebClient(token=token) if token else None
    
    def send_message(self, channel: str, text: str, blocks: Optional[List] = None) -> bool:
        """Send message to Slack channel."""
        if not self.client:
            return False
        
        try:
            self.client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks
            )
            return True
        except SlackApiError as e:
            print(f"Error sending Slack message: {e}")
            return False
    
    def get_channel_messages(self, channel: str, limit: int = 100) -> List[Dict]:
        """Get messages from Slack channel."""
        if not self.client:
            return []
        
        try:
            result = self.client.conversations_history(
                channel=channel,
                limit=limit
            )
            return result.get('messages', [])
        except SlackApiError as e:
            print(f"Error getting messages: {e}")
            return []
    
    def upload_file(self, channel: str, file_path: str, title: str = "") -> bool:
        """Upload file to Slack."""
        if not self.client:
            return False
        
        try:
            self.client.files_upload_v2(
                channel=channel,
                file=file_path,
                title=title
            )
            return True
        except SlackApiError as e:
            print(f"Error uploading file: {e}")
            return False



