"""
Vercel serverless function entry point for Gradio app.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import and run the app
from app import demo

# Export the Gradio app for Vercel
app = demo.app

