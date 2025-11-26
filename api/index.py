"""
Vercel serverless function entry point for Gradio app.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Gradio demo
from app import demo

# Export the Gradio app for Vercel
# Gradio apps are WSGI/ASGI compatible
app = demo

