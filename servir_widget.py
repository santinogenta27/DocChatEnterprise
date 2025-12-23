"""Servidor HTTP simple para servir test_widget.html y evitar problemas CORS con file://"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
from pathlib import Path

class CORSRequestHandler(SimpleHTTPRequestHandler):
    """Handler con CORS habilitado"""
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    port = 8080
    server_address = ('', port)
    httpd = HTTPServer(server_address, CORSRequestHandler)
    
    print(f"🌐 Servidor HTTP iniciado en http://localhost:{port}")
    print(f"📄 Abre: http://localhost:{port}/test_widget.html")
    print(f"📦 Asegúrate de que api_server.py esté corriendo en http://localhost:7864")
    print("\n⚠️ Presiona Ctrl+C para detener el servidor\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n✅ Servidor detenido")
        httpd.shutdown()
















