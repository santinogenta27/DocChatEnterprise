"""Document processing tools: extract_tables_from_pdf, generate_pdf_report."""

from __future__ import annotations

import json
import time
import uuid
from typing import Dict, Any, Optional, List
from pathlib import Path
from langchain.tools import tool
from .base_tool import ToolResponse

# Try to import table extraction libraries
TABULA_AVAILABLE = False
try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    pass

CAMELOT_AVAILABLE = False
try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    pass

REPORTLAB_AVAILABLE = False
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    pass


@tool
def extract_tables_from_pdf(
    file_id: str,
    page_range: Optional[str] = None
) -> str:
    """
    Extract tables from PDF and convert to JSON.
    
    Args:
        file_id: File ID or path to PDF
        page_range: Optional page range (e.g., "1-10")
    
    Returns:
        JSON with standard contract including tables array
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
                    tool_name="extract_tables_from_pdf",
                    request_id=request_id,
                    source="tabula",
                    error={
                        "code": "file_not_found",
                        "message": f"File not found: {file_id}",
                        "details": {}
                    }
                ).to_json()
        
        if file_path.suffix.lower() != ".pdf":
            return ToolResponse(
                status="error",
                tool_name="extract_tables_from_pdf",
                request_id=request_id,
                source="tabula",
                error={
                    "code": "invalid_format",
                    "message": "File must be a PDF",
                    "details": {}
                }
            ).to_json()
        
        # Parse page range
        pages = None
        if page_range:
            try:
                if "-" in page_range:
                    start, end = map(int, page_range.split("-"))
                    pages = list(range(start, end + 1))
                else:
                    pages = [int(page_range)]
            except:
                pass
        
        tables = []
        
        # Try Tabula first
        if TABULA_AVAILABLE:
            try:
                tabula_tables = tabula.read_pdf(
                    str(file_path),
                    pages=pages if pages else "all",
                    multiple_tables=True
                )
                
                for idx, df in enumerate(tabula_tables):
                    # Convert DataFrame to JSON
                    table_data = {
                        "table_id": f"table_{idx + 1}",
                        "columns": list(df.columns),
                        "rows": df.values.tolist(),
                        "confidence": 0.85  # Tabula confidence
                    }
                    tables.append(table_data)
                
            except Exception as e:
                # Try Camelot as fallback
                if CAMELOT_AVAILABLE:
                    try:
                        camelot_tables = camelot.read_pdf(
                            str(file_path),
                            pages=page_range if page_range else "1-end"
                        )
                        
                        for idx, table in enumerate(camelot_tables):
                            df = table.df
                            table_data = {
                                "table_id": f"table_{idx + 1}",
                                "columns": list(df.columns),
                                "rows": df.values.tolist(),
                                "confidence": table.accuracy
                            }
                            tables.append(table_data)
                    except:
                        pass
        
        if not tables:
            return ToolResponse(
                status="error",
                tool_name="extract_tables_from_pdf",
                request_id=request_id,
                source="tabula",
                error={
                    "code": "extraction_failed",
                    "message": "No tables found or extraction libraries not available. Install with: pip install tabula-py camelot-py[cv]",
                    "details": {}
                }
            ).to_json()
        
        return ToolResponse(
            status="ok",
            data={
                "tables": tables,
                "count": len(tables)
            },
            tool_name="extract_tables_from_pdf",
            duration_ms=int((time.time() - start_time) * 1000),
            request_id=request_id,
            source="tabula"
        ).to_json()
        
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="extract_tables_from_pdf",
            request_id=request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()


@tool
def generate_pdf_report(
    report_json: Dict[str, Any],
    template: str = "onepager",
    callback_url: Optional[str] = None
) -> str:
    """
    Generate PDF report from structured JSON data.
    
    Args:
        report_json: Structured report data
        template: Template name ("onepager" or "detailed")
        callback_url: Optional callback URL for async generation
    
    Returns:
        JSON with standard contract including file_id and URL
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        if not report_json:
            return ToolResponse(
                status="error",
                tool_name="generate_pdf_report",
                request_id=request_id,
                source="reportlab",
                error={
                    "code": "invalid_input",
                    "message": "report_json is required",
                    "details": {}
                }
            ).to_json()
        
        if not REPORTLAB_AVAILABLE:
            return ToolResponse(
                status="error",
                tool_name="generate_pdf_report",
                request_id=request_id,
                source="reportlab",
                error={
                    "code": "dependency_missing",
                    "message": "reportlab required. Install with: pip install reportlab",
                    "details": {}
                }
            ).to_json()
        
        # Generate PDF (simplified - in production use proper templates)
        from docchat.config import AppConfig
        config = AppConfig()
        output_dir = config.base_path / "data" / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        file_id = f"report_{int(time.time())}.pdf"
        file_path = output_dir / file_id
        
        # Create PDF (simplified)
        c = canvas.Canvas(str(file_path), pagesize=letter)
        width, height = letter
        
        # Add title
        title = report_json.get("title", "Report")
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, title)
        
        # Add content
        y = height - 100
        c.setFont("Helvetica", 12)
        
        # Add summary
        summary = report_json.get("summary", "")
        if summary:
            text_lines = summary.split("\n")
            for line in text_lines[:20]:  # Limit lines
                if y < 100:
                    c.showPage()
                    y = height - 50
                c.drawString(50, y, line[:80])  # Truncate long lines
                y -= 20
        
        c.save()
        
        # Generate signed URL (placeholder)
        url = f"/reports/{file_id}"
        
        # Get page count (simplified)
        pages = 1  # In production, count actual pages
        
        return ToolResponse(
            status="ok",
            data={
                "file_id": file_id,
                "url": url,
                "pages": pages,
                "template": template
            },
            tool_name="generate_pdf_report",
            duration_ms=int((time.time() - start_time) * 1000),
            request_id=request_id,
            source="reportlab"
        ).to_json()
        
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="generate_pdf_report",
            request_id=request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()

