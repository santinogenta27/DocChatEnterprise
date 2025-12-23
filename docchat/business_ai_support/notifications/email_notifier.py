"""Email Notifier - Sends email notifications via SMTP."""

from __future__ import annotations

from typing import Dict, Any, Optional, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr


class EmailNotifier:
    """Sends email notifications via SMTP."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize EmailNotifier.
        
        Args:
            config: Email configuration dict with:
                - smtp_server: SMTP server (default: smtp.gmail.com)
                - smtp_port: SMTP port (default: 587)
                - smtp_user: SMTP username/email
                - smtp_password: SMTP password
                - from_email: From email address
                - to_emails: List of recipient emails (or single string)
        """
        self.smtp_server = config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = config.get("smtp_port", 587)
        self.smtp_user = config.get("smtp_user", "")
        self.smtp_password = config.get("smtp_password", "")
        self.from_email = config.get("from_email", self.smtp_user)
        self.to_emails = config.get("to_emails", [])
        
        # Convert single string to list
        if isinstance(self.to_emails, str):
            self.to_emails = [self.to_emails]
        
        # Default to SMTP user if no from_email specified
        if not self.from_email and self.smtp_user:
            self.from_email = self.smtp_user
    
    def send(
        self,
        subject: str,
        body: str,
        to_emails: Optional[List[str]] = None,
        priority: str = "normal"
    ) -> bool:
        """Send email notification.
        
        Args:
            subject: Email subject
            body: Email body (can be plain text or HTML)
            to_emails: Recipient emails (uses config default if None)
            priority: Priority level (normal, high) - affects subject prefix
            
        Returns:
            True if sent successfully
        """
        recipients = to_emails or self.to_emails
        
        if not recipients:
            print("⚠️ No recipient emails configured")
            return False
        
        if not self.smtp_user or not self.smtp_password:
            print("⚠️ SMTP credentials not configured")
            return False
        
        try:
            # Add priority prefix
            if priority == "high":
                subject = f"🚨 URGENTE: {subject}"
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = formataddr(("Business AI Support", self.from_email))
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            # Add body (plain text)
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Try to add HTML version if body contains markdown-like formatting
            html_body = self._convert_markdown_to_html(body)
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg, from_addr=self.from_email, to_addrs=recipients)
            
            print(f"✅ Email enviado a {', '.join(recipients)}")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando email: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_to(
        self,
        to_email: str,
        subject: str,
        body: str,
        priority: str = "normal"
    ) -> bool:
        """Send email to a specific recipient.
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body
            priority: Priority level
            
        Returns:
            True if sent successfully
        """
        return self.send(subject=subject, body=body, to_emails=[to_email], priority=priority)
    
    def _convert_markdown_to_html(self, text: str) -> str:
        """Convert basic markdown to HTML for email."""
        html = text
        
        # Headers
        html = html.replace("### ", "<h3>").replace("\n### ", "</h3>\n<h3>")
        html = html.replace("## ", "<h2>").replace("\n## ", "</h2>\n<h2>")
        html = html.replace("# ", "<h1>").replace("\n# ", "</h1>\n<h1>")
        
        # Bold
        html = html.replace("**", "<strong>", 1)
        while "**" in html:
            html = html.replace("**", "</strong>", 1)
            if "**" in html:
                html = html.replace("**", "<strong>", 1)
        
        # Lists
        lines = html.split('\n')
        in_list = False
        result = []
        for line in lines:
            if line.strip().startswith('- '):
                if not in_list:
                    result.append('<ul>')
                    in_list = True
                result.append(f'<li>{line.strip()[2:]}</li>')
            else:
                if in_list:
                    result.append('</ul>')
                    in_list = False
                result.append(line)
        if in_list:
            result.append('</ul>')
        html = '\n'.join(result)
        
        # Line breaks
        html = html.replace('\n\n', '</p><p>')
        html = f'<p>{html}</p>'
        
        # Wrap in HTML structure
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        ul {{ margin: 10px 0; padding-left: 20px; }}
        li {{ margin: 5px 0; }}
        strong {{ color: #e74c3c; }}
    </style>
</head>
<body>
    {html}
</body>
</html>
"""
        return html

