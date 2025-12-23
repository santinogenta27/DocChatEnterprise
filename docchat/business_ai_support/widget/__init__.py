"""
Business AI Support Widget Package

Provides embeddable chat widget for Business AI Support.
"""

__all__ = ['get_widget_path']

from pathlib import Path

def get_widget_path() -> Path:
    """Get the path to the widget JavaScript file."""
    return Path(__file__).parent / "business-ai-widget.js"

