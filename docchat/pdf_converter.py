"""
Conversor simple a PDF para modo Chatbot / multiformato.

Objetivo: dado un archivo de texto / documento de oficina soportado,
generar un PDF temporal que luego se puede procesar como en Enterprise API.

NOTA: Implementación minimalista basada en `reportlab` para contenido
de texto plano. Para formatos binarios complejos (docx, pptx, xlsx, etc.)
se puede extender usando librerías específicas o una instalación de LibreOffice.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from reportlab.lib.pagesizes import A4  # type: ignore
from reportlab.pdfgen import canvas  # type: ignore


TEXT_EXTENSIONS: Iterable[str] = {
    ".txt",
    ".md",
    ".rtf",
    ".log",
    ".csv",
    ".tsv",
    ".ini",
    ".cfg",
    ".env",
    ".yaml",
    ".yml",
    ".json",
    ".xml",
    ".html",
    ".htm",
    ".mhtml",
    ".tex",
    ".srt",
    ".vtt",
    ".py",
    ".js",
    ".ts",
    ".java",
    ".cpp",
    ".c",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".css",
    ".sql",
    ".sh",
    ".bat",
}


def convert_to_pdf(input_path: Path, output_path: Path) -> Path:
    """
    Convierte un archivo soportado a un PDF muy simple.

    Para ahora tratamos la mayoría como texto plano: leemos el contenido
    y lo volcamos en una página PDF.
    """
    ext = input_path.suffix.lower()
    if ext not in TEXT_EXTENSIONS:
        # Para formatos no soportados aún, simplemente copiamos PDF existente
        if ext == ".pdf":
            output_path.write_bytes(input_path.read_bytes())
            return output_path
        # Fallback: tratar como texto igualmente

    text = input_path.read_text(encoding="utf-8", errors="ignore")

    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    x_margin = 40
    y = height - 50
    for line in text.splitlines():
        c.drawString(x_margin, y, line[:150])  # truncar líneas muy largas
        y -= 14
        if y < 40:
            c.showPage()
            y = height - 50
    c.save()
    return output_path


__all__ = ["convert_to_pdf", "TEXT_EXTENSIONS"]



