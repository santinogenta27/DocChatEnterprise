"""
Render startup script for Gradio app.
Simple direct launch for Render compatibility.
"""
import os
import sys

# Get port from environment (Render sets this)
PORT = int(os.environ.get("PORT", 10000))

print(f"📦 Python version: {sys.version}")
print(f"🔌 PORT environment variable: {os.environ.get('PORT', 'NOT SET')}")
print(f"🚀 Starting DocChat Enterprise on port {PORT}")

try:
    # Import the Gradio demo
    print("📥 Importing app...")
    from app import demo
    print("✅ App imported successfully")
    
    print(f"🌐 Binding to 0.0.0.0:{PORT}")
    print("🚀 Launching Gradio...")
    
    # Launch Gradio directly - this is the simplest and most reliable method
    # server_name="0.0.0.0" is REQUIRED for Render to detect the port
    demo.queue().launch(
        server_name="0.0.0.0",  # CRITICAL: Must be 0.0.0.0, not 127.0.0.1
        server_port=PORT,        # Use Render's PORT environment variable
        share=False,
        show_api=False,
        inbrowser=False
    )
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

