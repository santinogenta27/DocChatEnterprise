"""Research tools: extract_webpage, extract_document, summarize_text."""

from __future__ import annotations

import os
import json
import time
import uuid
from typing import Dict, Any, Optional
from pathlib import Path
from langchain.tools import tool
from .base_tool import ToolResponse

# Try to import extractors
BEAUTIFULSOUP_AVAILABLE = False
try:
    from bs4 import BeautifulSoup
    import requests
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    pass

PYPDF2_AVAILABLE = False
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    pass

DOCX_AVAILABLE = False
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    pass


@tool
def extract_webpage(url: str, max_chars: int = 50000) -> str:
    """
    Extract clean text from a webpage URL.
    
    Args:
        url: URL to extract
        max_chars: Maximum characters to extract (default: 50000)
    
    Returns:
        JSON with standard contract
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        if not url or not url.startswith(("http://", "https://")):
            return ToolResponse(
                status="error",
                tool_name="extract_webpage",
                request_id=request_id,
                source="requests",
                error={
                    "code": "invalid_url",
                    "message": "Invalid URL format",
                    "details": {}
                }
            ).to_json()
        
        if not BEAUTIFULSOUP_AVAILABLE:
            return ToolResponse(
                status="error",
                tool_name="extract_webpage",
                request_id=request_id,
                source="requests",
                error={
                    "code": "dependency_missing",
                    "message": "BeautifulSoup and requests required. Install with: pip install beautifulsoup4 requests",
                    "details": {}
                }
            ).to_json()
        
        # Fetch webpage
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Check size
        if len(response.content) > 5 * 1024 * 1024:  # 5MB
            return ToolResponse(
                status="error",
                tool_name="extract_webpage",
                request_id=request_id,
                source="requests",
                error={
                    "code": "file_too_large",
                    "message": "Webpage exceeds 5MB limit",
                    "details": {}
                }
            ).to_json()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Truncate
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        # Get title
        title = soup.title.string if soup.title else ""
        
        # Get canonical URL
        canonical = url
        link = soup.find("link", rel="canonical")
        if link and link.get("href"):
            canonical = link["href"]
        
        return ToolResponse(
            status="ok",
            data={
                "title": title,
                "text": text,
                "language": "en",  # Could use langdetect
                "readability_score": 0.7,  # Simplified
                "canonical_url": canonical
            },
            tool_name="extract_webpage",
            duration_ms=int((time.time() - start_time) * 1000),
            request_id=request_id,
            source="requests"
        ).to_json()
        
    except requests.exceptions.RequestException as e:
        return ToolResponse(
            status="error",
            tool_name="extract_webpage",
            request_id=request_id,
            source="requests",
            error={
                "code": "request_failed",
                "message": str(e),
                "details": {}
            }
        ).to_json()
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="extract_webpage",
            request_id=request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()


@tool
def extract_document(file_id: str, pages: Optional[str] = None) -> str:
    """
    Extract text from PDF/DOCX document.
    
    Args:
        file_id: File ID or path to document
        pages: Optional page range (e.g., "1-5")
    
    Returns:
        JSON with standard contract
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        file_path = Path(file_id)
        
        if not file_path.exists():
            # Try to find in documents directory
            from docchat.config import AppConfig
            config = AppConfig()
            doc_dir = config.base_path / "data" / "documents"
            file_path = doc_dir / file_id
            if not file_path.exists():
                return ToolResponse(
                    status="error",
                    tool_name="extract_document",
                    request_id=request_id,
                    source="internal",
                    error={
                        "code": "file_not_found",
                        "message": f"File not found: {file_id}",
                        "details": {}
                    }
                ).to_json()
        
        # Determine file type
        ext = file_path.suffix.lower()
        
        if ext == ".pdf":
            if not PYPDF2_AVAILABLE:
                return ToolResponse(
                    status="error",
                    tool_name="extract_document",
                    request_id=request_id,
                    source="pypdf2",
                    error={
                        "code": "dependency_missing",
                        "message": "PyPDF2 required. Install with: pip install PyPDF2",
                        "details": {}
                    }
                ).to_json()
            
            # Extract PDF
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                pages_list = []
                full_text = ""
                
                # Parse page range
                page_range = None
                if pages:
                    try:
                        if "-" in pages:
                            start, end = map(int, pages.split("-"))
                            page_range = range(start - 1, end)  # 0-indexed
                        else:
                            page_num = int(pages) - 1
                            page_range = [page_num]
                    except:
                        pass
                
                total_pages = len(pdf_reader.pages)
                pages_to_extract = page_range if page_range else range(total_pages)
                
                for page_num in pages_to_extract:
                    if 0 <= page_num < total_pages:
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        pages_list.append({
                            "page_num": page_num + 1,
                            "text": text
                        })
                        full_text += text + "\n"
                
                return ToolResponse(
                    status="ok",
                    data={
                        "full_text": full_text,
                        "pages": pages_list,
                        "tables": [],  # Would need tabula-py
                        "attachments": []
                    },
                    tool_name="extract_document",
                    duration_ms=int((time.time() - start_time) * 1000),
                    request_id=request_id,
                    source="pypdf2"
                ).to_json()
        
        elif ext in [".docx", ".doc"]:
            if not DOCX_AVAILABLE:
                return ToolResponse(
                    status="error",
                    tool_name="extract_document",
                    request_id=request_id,
                    source="python-docx",
                    error={
                        "code": "dependency_missing",
                        "message": "python-docx required. Install with: pip install python-docx",
                        "details": {}
                    }
                ).to_json()
            
            doc = DocxDocument(file_path)
            full_text = "\n".join([para.text for para in doc.paragraphs])
            
            return ToolResponse(
                status="ok",
                data={
                    "full_text": full_text,
                    "pages": [{"page_num": 1, "text": full_text}],
                    "tables": [],
                    "attachments": []
                },
                tool_name="extract_document",
                duration_ms=int((time.time() - start_time) * 1000),
                request_id=request_id,
                source="python-docx"
            ).to_json()
        
        else:
            return ToolResponse(
                status="error",
                tool_name="extract_document",
                request_id=request_id,
                source="internal",
                error={
                    "code": "unsupported_format",
                    "message": f"Unsupported file format: {ext}",
                    "details": {}
                }
            ).to_json()
            
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="extract_document",
            request_id=request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()


@tool
def summarize_text(text: str, max_tokens: int = 500, style: str = "concise") -> str:
    """
    Summarize text using LLM.
    
    Args:
        text: Text to summarize
        max_tokens: Maximum tokens in summary (default: 500)
        style: "concise" or "detailed" (default: "concise")
    
    Returns:
        JSON with standard contract
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        if not text or len(text.strip()) < 50:
            return ToolResponse(
                status="error",
                tool_name="summarize_text",
                request_id=request_id,
                source="llm",
                error={
                    "code": "text_too_short",
                    "message": "Text must be at least 50 characters",
                    "details": {}
                }
            ).to_json()
        
        # For short text, use extractive summary
        if len(text) < 300:
            # Simple extractive: take first and last sentences
            sentences = text.split(". ")
            if len(sentences) > 2:
                summary = ". ".join([sentences[0], sentences[-1]]) + "."
            else:
                summary = text
            
            return ToolResponse(
                status="ok",
                data={
                    "summary": summary,
                    "highlights": sentences[:3],
                    "read_time_sec": len(text) / 200  # ~200 words per minute
                },
                tool_name="summarize_text",
                duration_ms=int((time.time() - start_time) * 1000),
                request_id=request_id,
                source="extractive"
            ).to_json()
        
        # For longer text, use LLM (would need to inject LLM)
        # For now, return a placeholder
        return ToolResponse(
            status="ok",
            data={
                "summary": f"[Summary placeholder - LLM integration needed. Original text: {len(text)} chars]",
                "highlights": [],
                "read_time_sec": len(text) / 200
            },
            tool_name="summarize_text",
            duration_ms=int((time.time() - start_time) * 1000),
            request_id=request_id,
            source="llm_placeholder"
        ).to_json()
        
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="summarize_text",
            request_id=request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()

