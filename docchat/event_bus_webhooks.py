"""
Event Bus Webhooks - Endpoints para recibir eventos externos
Permite integración con sistemas externos mediante webhooks.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime
import json


def create_webhook_handler(event_bus_mode):
    """
    Crea handlers de webhook para Flask/Gradio.
    
    Returns:
        Dict con funciones handler
    """
    
    def handle_webhook(event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handler genérico para webhooks.
        
        Ejemplo de uso en Flask:
            @app.route('/webhook/event', methods=['POST'])
            def webhook_endpoint():
                data = request.json
                return handle_webhook(data.get('type'), data.get('data'))
        """
        try:
            result = event_bus_mode.handle_webhook_event(event_type, event_data)
            return result
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def handle_google_drive_webhook(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handler específico para Google Drive webhooks."""
        return handle_webhook('document_updated', {
            'doc_id': event_data.get('file_id'),
            'source': 'google_drive',
            'change_type': event_data.get('change_type', 'modified'),
            'file_name': event_data.get('file_name')
        })
    
    def handle_sharepoint_webhook(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handler específico para SharePoint webhooks."""
        return handle_webhook('document_updated', {
            'doc_id': event_data.get('item_id'),
            'source': 'sharepoint',
            'change_type': event_data.get('change_type', 'modified'),
            'file_name': event_data.get('file_name')
        })
    
    def handle_generic_webhook(source: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handler genérico para cualquier fuente."""
        event_type = event_data.get('type', 'data_change')
        return handle_webhook(event_type, {
            'source': source,
            **event_data
        })
    
    return {
        'handle_webhook': handle_webhook,
        'handle_google_drive_webhook': handle_google_drive_webhook,
        'handle_sharepoint_webhook': handle_sharepoint_webhook,
        'handle_generic_webhook': handle_generic_webhook
    }


# Ejemplo de integración con Flask
FLASK_WEBHOOK_EXAMPLE = """
# En tu app Flask, agregar:

from docchat.event_bus_mode import get_event_bus_mode
from docchat.event_bus_webhooks import create_webhook_handler

# Obtener instancia de Event Bus Mode
event_bus_mode = get_event_bus_mode(config, processor, retriever_builder, context_manager)
webhook_handlers = create_webhook_handler(event_bus_mode)

# Endpoint genérico
@app.route('/webhook/event', methods=['POST'])
def webhook_event():
    data = request.json
    return jsonify(webhook_handlers['handle_webhook'](
        data.get('type', 'data_change'),
        data.get('data', {})
    ))

# Endpoint específico para Google Drive
@app.route('/webhook/google-drive', methods=['POST'])
def webhook_google_drive():
    data = request.json
    return jsonify(webhook_handlers['handle_google_drive_webhook'](data))

# Endpoint específico para SharePoint
@app.route('/webhook/sharepoint', methods=['POST'])
def webhook_sharepoint():
    data = request.json
    return jsonify(webhook_handlers['handle_sharepoint_webhook'](data))

# Endpoint genérico para cualquier fuente
@app.route('/webhook/<source>', methods=['POST'])
def webhook_source(source):
    data = request.json
    return jsonify(webhook_handlers['handle_generic_webhook'](source, data))
"""


# Ejemplo de integración con sistemas externos
EXTERNAL_INTEGRATION_EXAMPLE = """
# Para suscribirse a webhooks de Google Drive:

event_bus_mode = get_event_bus_mode(config, processor, retriever_builder, context_manager)

# Suscribirse a webhooks
result = event_bus_mode.subscribe_to_external_webhook(
    source='google_drive',
    callback_url='https://tu-servidor.com/webhook/google-drive'
)

# Sincronización mejorada (polling más frecuente)
result = event_bus_mode.sync_document_source(
    source='google_drive',
    interval=60  # 1 minuto en vez de 15 minutos
)
"""

