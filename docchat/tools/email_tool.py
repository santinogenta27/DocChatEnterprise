"""Email tool for sending automated emails."""

from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List, Optional
import os

from .base_tool import BaseTool, ToolResult


class EmailTool(BaseTool):
    """Tool for sending emails based on document analysis."""
    
    def __init__(self, config: Any):
        super().__init__(config)
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
    
    def get_name(self) -> str:
        return "email_sender"
    
    def get_description(self) -> str:
        return "Send emails with analysis results, reports, or notifications"
    
    def get_keywords(self) -> List[str]:
        return ["email", "enviar correo", "notificar", "enviar", "mail", "correo electrónico"]
    
    def execute(
        self,
        to: str | List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        **kwargs
    ) -> ToolResult:
        """Send an email."""
        try:
            # Validate
            if not self.smtp_user or not self.smtp_password:
                return ToolResult(
                    success=False,
                    data=None,
                    message="SMTP credentials not configured",
                    metadata={}
                )
            
            if not to:
                return ToolResult(
                    success=False,
                    data=None,
                    message="Recipient email address required",
                    metadata={}
                )
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            
            if isinstance(to, str):
                msg['To'] = to
                recipients = [to]
            else:
                msg['To'] = ", ".join(to)
                recipients = to
            
            # Add body
            if html_body:
                part1 = MIMEText(body, 'plain')
                part2 = MIMEText(html_body, 'html')
                msg.attach(part1)
                msg.attach(part2)
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg, to_addrs=recipients)
            
            return ToolResult(
                success=True,
                data={"sent_to": recipients, "subject": subject},
                message=f"Email sent successfully to {len(recipients)} recipient(s)",
                metadata={"smtp_server": self.smtp_server}
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to send email: {str(e)}",
                metadata={"error": str(e)}
            )



