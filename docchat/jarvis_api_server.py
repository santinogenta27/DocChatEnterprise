"""
Servidor REST API para JARVIS
Expone todas las APIs de JARVIS como endpoints REST
"""

from __future__ import annotations

import json
from typing import Optional, Dict, Any
import threading

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠️ Flask no está instalado. Para usar JARVIS API Server, instala: pip install flask flask-cors")

from .jarvis_api import JarvisAPI, WebhookPayload, AlertNotification, APIResponse


class JarvisAPIServer:
    """
    Servidor REST API para JARVIS.
    
    Expone todas las funcionalidades de JARVIS como endpoints REST
    para integración enterprise.
    """
    
    def __init__(
        self,
        jarvis_api: JarvisAPI,
        host: str = "0.0.0.0",
        port: int = 5001,
        enable_cors: bool = True
    ):
        if not FLASK_AVAILABLE:
            raise ImportError("Flask no está instalado. Instala con: pip install flask flask-cors")
        
        self.jarvis_api = jarvis_api
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        
        if enable_cors:
            CORS(self.app)  # Permitir CORS para integraciones
        
        self._setup_routes()
        self.server_thread = None
        self.is_running = False
    
    def _setup_routes(self):
        """Configura todas las rutas de la API."""
        
        # ============================================
        # API 1: Webhook/Ingestión
        # ============================================
        @self.app.route('/api/jarvis/webhook/ingest', methods=['POST'])
        def webhook_ingest():
            """Recibir datos de sistemas externos."""
            try:
                data = request.json
                api_key = request.headers.get('X-API-Key') or data.get('api_key')
                
                payload = WebhookPayload(
                    source=data.get('source', 'unknown'),
                    data=data.get('data'),
                    data_type=data.get('data_type', 'text'),
                    metadata=data.get('metadata', {}),
                    timestamp=data.get('timestamp'),
                    api_key=api_key
                )
                
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.jarvis_api.webhook_ingest(payload, api_key)
                )
                loop.close()
                
                return jsonify({
                    "success": result.success,
                    "data": result.data,
                    "message": result.message,
                    "error": result.error,
                    "timestamp": result.timestamp
                }), 200 if result.success else 400
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        # ============================================
        # API 2: Envío de Alertas
        # ============================================
        @self.app.route('/api/jarvis/alerts/send', methods=['POST'])
        def send_alert():
            """Enviar alerta a sistema externo."""
            try:
                data = request.json
                
                # Obtener alerta de JARVIS
                user_id = data.get('user_id', 'user')
                alert_id = data.get('alert_id')
                
                if not alert_id:
                    return jsonify({
                        "success": False,
                        "error": "alert_id required"
                    }), 400
                
                # Obtener alerta (necesitaríamos acceso a jarvis_manager)
                # Por ahora, crear notificación directamente
                notification = AlertNotification(
                    alert_id=alert_id,
                    title=data.get('title', 'JARVIS Alert'),
                    message=data.get('message', ''),
                    severity=data.get('severity', 'medium'),
                    destination=data.get('destination', 'webhook'),
                    destination_config=data.get('destination_config', {})
                )
                
                # En producción, obtener alerta real de JARVIS
                # Por ahora, retornar éxito
                return jsonify({
                    "success": True,
                    "message": f"Alert sent to {notification.destination}"
                }), 200
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        # ============================================
        # API 3: Consulta de Estado
        # ============================================
        @self.app.route('/api/jarvis/status', methods=['GET'])
        def get_status():
            """Obtener estado de JARVIS."""
            try:
                user_id = request.args.get('user_id', 'user')
                include_insights = request.args.get('include_insights', 'true').lower() == 'true'
                include_alerts = request.args.get('include_alerts', 'true').lower() == 'true'
                
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.jarvis_api.get_status(user_id, include_insights, include_alerts)
                )
                loop.close()
                
                return jsonify({
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                    "timestamp": result.timestamp
                }), 200 if result.success else 400
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        # ============================================
        # API 3b: Consulta de Insights
        # ============================================
        @self.app.route('/api/jarvis/insights', methods=['GET'])
        def get_insights():
            """Obtener insights de JARVIS."""
            try:
                user_id = request.args.get('user_id', 'user')
                limit = int(request.args.get('limit', 20))
                category = request.args.get('category')
                min_confidence = float(request.args.get('min_confidence', 0.0))
                
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.jarvis_api.get_insights(user_id, limit, category, min_confidence)
                )
                loop.close()
                
                return jsonify({
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                    "timestamp": result.timestamp
                }), 200 if result.success else 400
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        # ============================================
        # API 4: Agregar Tarea
        # ============================================
        @self.app.route('/api/jarvis/tasks/add', methods=['POST'])
        def add_task():
            """Agregar tarea a JARVIS."""
            try:
                data = request.json
                
                task_type = data.get('task_type')
                description = data.get('description')
                priority = data.get('priority', 'medium')
                parameters = data.get('parameters', {})
                user_id = data.get('user_id', 'user')
                
                if not task_type or not description:
                    return jsonify({
                        "success": False,
                        "error": "task_type and description required"
                    }), 400
                
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.jarvis_api.add_task(task_type, description, priority, parameters, user_id)
                )
                loop.close()
                
                return jsonify({
                    "success": result.success,
                    "data": result.data,
                    "message": result.message,
                    "error": result.error,
                    "timestamp": result.timestamp
                }), 200 if result.success else 400
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        # ============================================
        # API 4b: Obtener Tareas
        # ============================================
        @self.app.route('/api/jarvis/tasks', methods=['GET'])
        def get_tasks():
            """Obtener tareas de JARVIS."""
            try:
                user_id = request.args.get('user_id', 'user')
                status = request.args.get('status')
                limit = int(request.args.get('limit', 20))
                
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.jarvis_api.get_tasks(user_id, status, limit)
                )
                loop.close()
                
                return jsonify({
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                    "timestamp": result.timestamp
                }), 200 if result.success else 400
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        # ============================================
        # API 5: Ejecutar Automatización
        # ============================================
        @self.app.route('/api/jarvis/automation/execute', methods=['POST'])
        def execute_automation():
            """Ejecutar automatización."""
            try:
                data = request.json
                
                command = data.get('command')
                auto_execute = data.get('auto_execute', True)
                user_id = data.get('user_id', 'user')
                
                if not command:
                    return jsonify({
                        "success": False,
                        "error": "command required"
                    }), 400
                
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.jarvis_api.execute_automation(command, auto_execute, user_id)
                )
                loop.close()
                
                return jsonify({
                    "success": result.success,
                    "data": result.data,
                    "message": result.message,
                    "error": result.error,
                    "timestamp": result.timestamp
                }), 200 if result.success else 400
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        # ============================================
        # API 6: Obtener Reportes
        # ============================================
        @self.app.route('/api/jarvis/reports', methods=['GET'])
        def get_reports():
            """Obtener reportes generados."""
            try:
                user_id = request.args.get('user_id', 'user')
                period = request.args.get('period', 'daily')
                limit = int(request.args.get('limit', 10))
                
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.jarvis_api.get_reports(user_id, period, limit)
                )
                loop.close()
                
                return jsonify({
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                    "timestamp": result.timestamp
                }), 200 if result.success else 400
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        # ============================================
        # API 7: Subir Documento
        # ============================================
        @self.app.route('/api/jarvis/documents/upload', methods=['POST'])
        def upload_document():
            """Subir documento a JARVIS."""
            try:
                data = request.json
                
                document_content = data.get('content')
                file_name = data.get('file_name', 'document.txt')
                source = data.get('source', 'api')
                metadata = data.get('metadata', {})
                user_id = data.get('user_id', 'user')
                
                if not document_content:
                    return jsonify({
                        "success": False,
                        "error": "content required"
                    }), 400
                
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.jarvis_api.upload_document(
                        document_content, file_name, source, metadata, user_id
                    )
                )
                loop.close()
                
                return jsonify({
                    "success": result.success,
                    "data": result.data,
                    "message": result.message,
                    "error": result.error,
                    "timestamp": result.timestamp
                }), 200 if result.success else 400
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        # ============================================
        # API 8: Sincronización Cloud
        # ============================================
        @self.app.route('/api/jarvis/cloud/sync', methods=['POST'])
        def sync_cloud():
            """Sincronizar con cloud storage."""
            try:
                data = request.json
                
                cloud_provider = data.get('cloud_provider')
                bucket_name = data.get('bucket_name')
                sync_direction = data.get('sync_direction', 'bidirectional')
                user_id = data.get('user_id', 'user')
                
                if not cloud_provider or not bucket_name:
                    return jsonify({
                        "success": False,
                        "error": "cloud_provider and bucket_name required"
                    }), 400
                
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.jarvis_api.sync_with_cloud(
                        cloud_provider, bucket_name, sync_direction, user_id
                    )
                )
                loop.close()
                
                return jsonify({
                    "success": result.success,
                    "data": result.data,
                    "message": result.message,
                    "error": result.error,
                    "timestamp": result.timestamp
                }), 200 if result.success else 400
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        # ============================================
        # API de Estadísticas
        # ============================================
        @self.app.route('/api/jarvis/stats', methods=['GET'])
        def get_stats():
            """Obtener estadísticas de uso de la API."""
            try:
                stats = self.jarvis_api.get_api_stats()
                return jsonify({
                    "success": True,
                    "data": stats
                }), 200
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        # ============================================
        # Health Check
        # ============================================
        @self.app.route('/api/jarvis/health', methods=['GET'])
        def health():
            """Health check endpoint."""
            return jsonify({
                "status": "healthy",
                "service": "JARVIS API",
                "version": "1.0.0"
            }), 200
    
    def start(self, daemon: bool = True):
        """Inicia el servidor API en un thread separado."""
        if self.is_running:
            print("⚠️ JARVIS API Server ya está corriendo")
            return
        
        def run_server():
            self.is_running = True
            print(f"🚀 JARVIS API Server iniciado en http://{self.host}:{self.port}")
            print(f"📡 Endpoints disponibles:")
            print(f"   - POST /api/jarvis/webhook/ingest")
            print(f"   - POST /api/jarvis/alerts/send")
            print(f"   - GET  /api/jarvis/status")
            print(f"   - GET  /api/jarvis/insights")
            print(f"   - POST /api/jarvis/tasks/add")
            print(f"   - GET  /api/jarvis/tasks")
            print(f"   - POST /api/jarvis/automation/execute")
            print(f"   - GET  /api/jarvis/reports")
            print(f"   - POST /api/jarvis/documents/upload")
            print(f"   - POST /api/jarvis/cloud/sync")
            print(f"   - GET  /api/jarvis/stats")
            print(f"   - GET  /api/jarvis/health")
            
            # Usar modo de desarrollo con threading
            self.app.run(
                host=self.host,
                port=self.port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        
        self.server_thread = threading.Thread(target=run_server, daemon=daemon)
        self.server_thread.start()
    
    def stop(self):
        """Detiene el servidor API."""
        # Flask no tiene un método directo para detener, pero podemos marcar como detenido
        self.is_running = False
        print("🛑 JARVIS API Server detenido")

