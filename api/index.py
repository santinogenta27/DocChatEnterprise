"""
Vercel serverless function entry point for Gradio app.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import the Gradio demo
    from app import demo
    
    # Get the FastAPI app from Gradio
    app = demo.app if hasattr(demo, 'app') else demo
    
except Exception as e:
    # Fallback: create a simple error handler
    def app(environ, start_response):
        status = '200 OK'
        headers = [('Content-type', 'text/html; charset=utf-8')]
        start_response(status, headers)
        return [f"""
        <html>
        <body>
            <h1>Error loading Gradio app</h1>
            <p>Error: {str(e)}</p>
            <p>Gradio apps work better on Railway or Render for persistent servers.</p>
        </body>
        </html>
        """.encode('utf-8')]

