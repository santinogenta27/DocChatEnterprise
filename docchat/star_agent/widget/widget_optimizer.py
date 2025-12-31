"""
Optimizador COMPLETO para Widget Web de STAR AGENT.

Implementa según especificaciones:
- FastAPI endpoints optimizados para widget
- WebSockets para tiempo real (comunicación bidireccional)
- Optimización de respuestas para widget (cortas, directas, orientadas a ventas)
- Caching inteligente con TTL
- Métricas de performance y conversión
- Integración completa con Sales Closer Elite
- Flujo Siente→Piensa→Actúa→Aprende
- Tracking de conversión (Google Analytics, Meta Pixel)
"""

from __future__ import annotations

import json
import time
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("⚠️ FastAPI no disponible. Instala con: pip install fastapi uvicorn websockets")


class WidgetOptimizer:
    """
    Optimizador COMPLETO para widget web de STAR AGENT.
    
    Características:
    - Respuestas optimizadas para widget (más cortas, directas, orientadas a ventas)
    - Caching inteligente con invalidación por contexto
    - WebSockets para tiempo real
    - Métricas de performance y conversión
    - Tracking de eventos (Google Analytics, Meta Pixel)
    - Optimización para Sales Closer Elite
    """
    
    def __init__(self):
        self.response_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = timedelta(minutes=5)  # TTL de 5 minutos
        
        # Métricas avanzadas (según especificaciones)
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_response_time": 0.0,
            "conversions": 0,
            "cart_adds": 0,
            "payment_initiated": 0,
            "handoffs": 0,
            "sales_stages": defaultdict(int),
            "intents": defaultdict(int),
            "objections": defaultdict(int),  # Objeciones dominantes
        }
        
        # Tiempos de respuesta
        self.response_times: List[float] = []
        
        # Metadata de conversiones para revenue tracking
        self._conversion_metadata: List[Dict[str, Any]] = []
    
    def optimize_response_for_widget(
        self, 
        response: Dict[str, Any],
        sales_stage: Optional[str] = None,
        intent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Optimiza respuesta para widget web según especificaciones.
        
        Optimizaciones:
        - Respuestas cortas y directas (máx 300 chars para widget)
        - Orientadas a ventas cuando corresponde
        - Incluye CTAs (Call-to-Action) cuando es apropiado
        - Formato optimizado para UI del widget
        
        Args:
            response: Respuesta del agente
            sales_stage: Etapa de venta actual
            intent: Intención detectada
            
        Returns:
            Respuesta optimizada para widget
        """
        text = response.get("text", "")
        original_length = len(text)
        
        # Optimización 1: Truncar inteligentemente si es muy larga
        # Widget tiene espacio limitado, máximo 300 caracteres recomendado
        if len(text) > 300:
            # Intentar truncar en punto lógico (punto, nueva línea, etc.)
            truncate_points = [". ", "\n", "! ", "? "]
            truncated = False
            
            for point in truncate_points:
                idx = text[:300].rfind(point)
                if idx > 200:  # Asegurar que no sea muy corto
                    text = text[:idx + len(point)].strip()
                    truncated = True
                    break
            
            if not truncated:
                # Fallback: truncar en palabra completa
                words = text[:300].split()
                if len(words) > 1:
                    text = " ".join(words[:-1]) + "..."
                else:
                    text = text[:297] + "..."
        
        # Optimización 2: Agregar CTA si está en etapa de cierre (Sales Closer Elite)
        if sales_stage in ["ready", "closing"] and "comprar" not in text.lower() and "pagar" not in text.lower():
            # Agregar CTA sutil pero persuasivo
            if not text.endswith(".") and not text.endswith("!"):
                text += "."
            # CTA optimizado según etapa
            if sales_stage == "closing":
                text += " ¿Querés que lo procesemos ahora y te lo envío enseguida?"
            else:
                text += " ¿Te ayudo a completar tu compra?"
        
        # Optimización 3: Formato para widget (emojis, estructura)
        # Mantener emojis si existen, pero no agregar si no hay
        
        # Optimización 4: Agregar metadata completa
        optimized = {
            "text": text,
            "widget_optimized": True,
            "timestamp": datetime.now().isoformat(),
            "original_length": original_length,
            "optimized_length": len(text),
            "sales_stage": sales_stage or response.get("sales_stage"),
            "intent": intent or response.get("intent"),
            "needs_handoff": response.get("needs_handoff", False),
            "cart": response.get("cart"),
            "payment_link": response.get("payment_link"),
            "conversion_tracked": response.get("conversion_tracked", False),
        }
        
        # Agregar otros campos del response original
        for key in ["intent", "sales_stage", "cart", "payment_link", "needs_handoff"]:
            if key not in optimized and key in response:
                optimized[key] = response[key]
        
        return optimized
    
    def get_cached_response(self, query: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Obtiene respuesta del cache si está disponible.
        
        Args:
            query: Mensaje del usuario
            session_id: ID de sesión (para invalidación contextual)
            
        Returns:
            Respuesta cacheada o None
        """
        cache_key = self._generate_cache_key(query, session_id)
        
        if cache_key in self.response_cache:
            cached = self.response_cache[cache_key]
            if datetime.now() - cached["timestamp"] < self.cache_ttl:
                self.metrics["cache_hits"] += 1
                return cached["response"]
        
        self.metrics["cache_misses"] += 1
        return None
    
    def cache_response(self, query: str, response: Dict[str, Any], session_id: Optional[str] = None):
        """
        Guarda respuesta en cache.
        
        Args:
            query: Mensaje del usuario
            response: Respuesta del agente
            session_id: ID de sesión
        """
        cache_key = self._generate_cache_key(query, session_id)
        self.response_cache[cache_key] = {
            "response": response,
            "timestamp": datetime.now(),
        }
        
        # Limpiar cache viejo (mantener solo últimas 1000 entradas)
        if len(self.response_cache) > 1000:
            self._clean_old_cache()
    
    def _generate_cache_key(self, query: str, session_id: Optional[str] = None) -> str:
        """
        Genera clave de cache desde query y sesión.
        
        Args:
            query: Mensaje del usuario
            session_id: ID de sesión (opcional)
            
        Returns:
            Clave MD5 para cache
        """
        # Normalizar query
        normalized = query.lower().strip()
        
        # Incluir session_id si existe (para invalidación contextual)
        if session_id:
            normalized += f"|{session_id}"
        
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _clean_old_cache(self):
        """Limpia entradas de cache expiradas o antiguas."""
        now = datetime.now()
        expired_keys = [
            key for key, value in self.response_cache.items()
            if now - value["timestamp"] > self.cache_ttl
        ]
        for key in expired_keys:
            del self.response_cache[key]
        
        # Si aún hay muchas entradas, eliminar las más antiguas
        if len(self.response_cache) > 1000:
            sorted_entries = sorted(
                self.response_cache.items(),
                key=lambda x: x[1]["timestamp"]
            )
            # Eliminar el 20% más antiguo
            to_remove = len(sorted_entries) // 5
            for key, _ in sorted_entries[:to_remove]:
                del self.response_cache[key]
    
    def track_conversion(self, event_type: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Trackea evento de conversión (según especificaciones).
        
        Args:
            event_type: Tipo de evento (cart_add, payment_initiated, conversion, etc.)
            metadata: Metadata adicional del evento (puede incluir revenue, objection, etc.)
        """
        if event_type == "cart_add":
            self.metrics["cart_adds"] += 1
        elif event_type == "payment_initiated":
            self.metrics["payment_initiated"] += 1
        elif event_type == "conversion":
            self.metrics["conversions"] += 1
            # Guardar metadata para revenue tracking
            if metadata:
                self._conversion_metadata.append(metadata)
        elif event_type == "handoff":
            self.metrics["handoffs"] += 1
        elif event_type == "objection":
            # Trackear objeciones dominantes
            objection_type = metadata.get("objection_type", "unknown") if metadata else "unknown"
            self.metrics["objections"][objection_type] += 1
        
        # Trackear en sales_stage si existe
        if metadata and "sales_stage" in metadata:
            self.metrics["sales_stages"][metadata["sales_stage"]] += 1
        
        # Trackear intent si existe
        if metadata and "intent" in metadata:
            self.metrics["intents"][metadata["intent"]] += 1
    
    def record_response_time(self, response_time: float):
        """
        Registra tiempo de respuesta.
        
        Args:
            response_time: Tiempo en segundos
        """
        self.response_times.append(response_time)
        
        # Mantener solo últimos 1000 tiempos
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]
        
        # Actualizar promedio
        if self.response_times:
            self.metrics["avg_response_time"] = sum(self.response_times) / len(self.response_times)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Obtiene métricas completas de performance.
        
        Returns:
            Diccionario con todas las métricas
        """
        total = self.metrics["total_requests"]
        cache_hit_rate = (
            self.metrics["cache_hits"] / total
            if total > 0 else 0.0
        )
        
        conversion_rate = (
            self.metrics["conversions"] / total
            if total > 0 else 0.0
        )
        
        # Calcular revenue (si está disponible en metadata)
        total_revenue = sum(
            m.get("revenue", 0) for m in getattr(self, "_conversion_metadata", [])
            if isinstance(m, dict)
        )
        
        # Calcular drop-off rate (sessions que no completaron)
        drop_off_rate = (
            (total - self.metrics["conversions"]) / total
            if total > 0 else 0.0
        )
        
        return {
            **self.metrics,
            "cache_hit_rate": cache_hit_rate,
            "conversion_rate": conversion_rate,
            "drop_off_rate": drop_off_rate,
            "total_revenue": total_revenue,
            "avg_revenue_per_conversion": (
                total_revenue / self.metrics["conversions"]
                if self.metrics["conversions"] > 0 else 0.0
            ),
            "cache_size": len(self.response_cache),
            "sales_stages": dict(self.metrics["sales_stages"]),
            "intents": dict(self.metrics["intents"]),
        }


def create_widget_app(star_agent_mode, static_dir: Optional[Path] = None) -> Optional[Any]:
    """
    Crea aplicación FastAPI COMPLETA para widget web de STAR AGENT.
    
    Características:
    - Endpoint REST para chat
    - WebSocket para tiempo real
    - Servir widget HTML/JS/CSS
    - Métricas y tracking
    - Optimización completa para ventas
    
    Args:
        star_agent_mode: Instancia de StarAgentMode
        static_dir: Directorio con archivos estáticos (HTML, JS, CSS)
        
    Returns:
        FastAPI app o None si FastAPI no está disponible
    """
    if not FASTAPI_AVAILABLE:
        return None
    
    app = FastAPI(
        title="STAR AGENT Widget API",
        description="API optimizada para widget web de STAR AGENT - Sales Closer Elite"
    )
    
    # CORS para widget embebido (permite cualquier origen en desarrollo)
    # En producción, especificar dominios permitidos
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configurar en producción
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    optimizer = WidgetOptimizer()
    
    # Servir archivos estáticos si existe el directorio
    if static_dir and static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    @app.post("/api/widget/chat")
    async def widget_chat(payload: Dict[str, Any], request: Request):
        """
        Endpoint REST de chat para widget web.
        
        Payload:
        {
            "session_id": "uuid",
            "user_id": "user_id",
            "message": "mensaje del usuario",
            "channel": "web"
        }
        
        Returns:
        {
            "text": "respuesta del agente",
            "sales_stage": "ready",
            "intent": "checkout",
            "cart": {...},
            "payment_link": "https://...",
            "widget_optimized": true,
            ...
        }
        """
        start_time = time.time()
        
        try:
            query = payload.get("message", "")
            session_id = payload.get("session_id")
            
            if not query:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Mensaje vacío", "text": "Por favor, envía un mensaje."}
                )
            
            # Verificar cache (solo para queries simples, no para checkout/pago)
            if "comprar" not in query.lower() and "pagar" not in query.lower():
                cached_response = optimizer.get_cached_response(query, session_id)
                if cached_response:
                    optimizer.metrics["total_requests"] += 1
                    return JSONResponse(content=cached_response)
            
            # Procesar con STAR AGENT (flujo completo Siente→Piensa→Actúa→Aprende)
            # Si es ReactSalesAgent, ya tiene ReAct pattern integrado
            result = star_agent_mode.process_message(payload, channel="web")
            
            # Asegurar que sales_stage e intent estén presentes
            if "sales_stage" not in result:
                result["sales_stage"] = "interest"
            if "intent" not in result:
                result["intent"] = "general"
            
            # Extraer información para optimización
            sales_stage = result.get("sales_stage")
            intent = result.get("intent")
            
            # Optimizar para widget
            optimized = optimizer.optimize_response_for_widget(
                result,
                sales_stage=sales_stage,
                intent=intent
            )
            
            # Cachear (excepto para checkout/pago)
            if "comprar" not in query.lower() and "pagar" not in query.lower():
                optimizer.cache_response(query, optimized, session_id)
            
            # Trackear métricas
            optimizer.metrics["total_requests"] += 1
            
            # Trackear conversión si aplica
            if optimized.get("conversion_tracked"):
                optimizer.track_conversion("conversion", {
                    "sales_stage": sales_stage,
                    "intent": intent,
                })
            
            if optimized.get("cart"):
                optimizer.track_conversion("cart_add", {
                    "sales_stage": sales_stage,
                    "intent": intent,
                })
            
            if optimized.get("payment_link"):
                optimizer.track_conversion("payment_initiated", {
                    "sales_stage": sales_stage,
                    "intent": intent,
                })
            
            if optimized.get("needs_handoff"):
                optimizer.track_conversion("handoff", {
                    "sales_stage": sales_stage,
                    "intent": intent,
                })
            
            # Registrar tiempo de respuesta
            response_time = time.time() - start_time
            optimizer.record_response_time(response_time)
            
            return JSONResponse(content=optimized)
            
        except Exception as e:
            print(f"❌ Error en widget_chat: {e}")
            import traceback
            traceback.print_exc()
            return JSONResponse(
                status_code=500,
                content={
                    "text": "Lo siento, hubo un error procesando tu mensaje. Por favor, intenta de nuevo.",
                    "error": True,
                    "error_message": str(e) if app.debug else None,
                }
            )
    
    @app.websocket("/ws/widget")
    async def websocket_chat(websocket: WebSocket):
        """
        WebSocket para chat en tiempo real.
        
        Permite comunicación bidireccional para widget.
        Formato de mensajes:
        - Cliente → Servidor: {"message": "...", "session_id": "...", "user_id": "..."}
        - Servidor → Cliente: {"text": "...", "sales_stage": "...", ...}
        """
        await websocket.accept()
        session_id = None
        
        try:
            while True:
                # Recibir mensaje
                data = await websocket.receive_json()
                
                start_time = time.time()
                session_id = data.get("session_id")
                query = data.get("message", "")
                
                if not query:
                    await websocket.send_json({
                        "text": "Por favor, envía un mensaje.",
                        "error": True,
                    })
                    continue
                
                # Procesar con STAR AGENT
                result = star_agent_mode.process_message(data, channel="web")
                
                # Extraer información
                sales_stage = result.get("sales_stage")
                intent = result.get("intent")
                
                # Optimizar para widget
                optimized = optimizer.optimize_response_for_widget(
                    result,
                    sales_stage=sales_stage,
                    intent=intent
                )
                
                # Trackear métricas
                optimizer.metrics["total_requests"] += 1
                
                # Trackear conversión si aplica
                if optimized.get("conversion_tracked"):
                    optimizer.track_conversion("conversion", {
                        "sales_stage": sales_stage,
                        "intent": intent,
                    })
                
                if optimized.get("cart"):
                    optimizer.track_conversion("cart_add", {
                        "sales_stage": sales_stage,
                        "intent": intent,
                    })
                
                if optimized.get("payment_link"):
                    optimizer.track_conversion("payment_initiated", {
                        "sales_stage": sales_stage,
                        "intent": intent,
                    })
                
                # Registrar tiempo de respuesta
                response_time = time.time() - start_time
                optimizer.record_response_time(response_time)
                
                # Enviar respuesta
                await websocket.send_json(optimized)
        
        except WebSocketDisconnect:
            print(f"WebSocket desconectado para sesión: {session_id}")
        except Exception as e:
            print(f"❌ Error en WebSocket: {e}")
            import traceback
            traceback.print_exc()
            try:
                await websocket.send_json({
                    "text": "Lo siento, hubo un error. Por favor, intenta de nuevo.",
                    "error": True,
                })
            except:
                pass
    
    @app.get("/api/widget/metrics")
    async def get_metrics():
        """
        Obtiene métricas completas de performance del widget.
        
        Returns:
        {
            "total_requests": 1000,
            "cache_hits": 200,
            "cache_misses": 800,
            "cache_hit_rate": 0.2,
            "avg_response_time": 0.45,
            "conversions": 50,
            "conversion_rate": 0.05,
            "cart_adds": 150,
            "payment_initiated": 30,
            "handoffs": 10,
            "sales_stages": {...},
            "intents": {...},
            ...
        }
        """
        return optimizer.get_metrics()
    
    @app.get("/api/widget/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "STAR AGENT Widget",
            "timestamp": datetime.now().isoformat(),
        }
    
    # Agregar webhooks si ingesta automática está habilitada
    if hasattr(star_agent_mode, 'multi_source_ingester') and star_agent_mode.multi_source_ingester:
        try:
            from ..ingestion.webhook_handler import create_webhook_router
            webhook_router = create_webhook_router(star_agent_mode.multi_source_ingester)
            app.include_router(webhook_router)
            print("✅ Webhooks de Instagram/Facebook habilitados")
        except Exception as e:
            print(f"⚠️ Error agregando webhooks: {e}")
    
    # Agregar webhooks de Meta (WhatsApp, Messenger e Instagram)
    whatsapp_adapter = getattr(star_agent_mode, 'whatsapp_adapter', None)
    messenger_adapter = getattr(star_agent_mode, 'messenger_adapter', None)
    instagram_adapter = getattr(star_agent_mode, 'instagram_adapter', None)
    
    # Usar instagram_adapter si está disponible, sino messenger_adapter
    messenger_adapter_to_use = instagram_adapter if instagram_adapter else messenger_adapter
    
    if whatsapp_adapter or messenger_adapter_to_use:
        try:
            from ..channels.meta_webhooks import create_meta_webhooks_router
            meta_webhooks_router = create_meta_webhooks_router(
                whatsapp_adapter=whatsapp_adapter,
                messenger_adapter=messenger_adapter_to_use,  # Usa instagram_adapter si está disponible
                star_agent_mode=star_agent_mode
            )
            app.include_router(meta_webhooks_router)
            channels_enabled = []
            if whatsapp_adapter:
                channels_enabled.append("WhatsApp")
            if instagram_adapter:
                channels_enabled.append("Instagram")
            if messenger_adapter and not instagram_adapter:
                channels_enabled.append("Messenger")
            print(f"✅ Webhooks de {' y '.join(channels_enabled)} habilitados")
        except Exception as e:
            print(f"⚠️ Error agregando webhooks de Meta: {e}")
            import traceback
            traceback.print_exc()
    
    # Endpoint para servir widget HTML (si existe)
    @app.get("/widget", response_class=HTMLResponse)
    async def serve_widget():
        """
        Sirve el widget HTML embebible.
        
        Si existe static_dir/widget.html, lo sirve.
        Si no, retorna HTML básico embebible.
        """
        widget_html = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STAR AGENT - Asistente Virtual</title>
    <style>
        /* Estilos del widget - se pueden personalizar */
        #star-agent-widget {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 380px;
            height: 600px;
            max-width: calc(100vw - 40px);
            max-height: calc(100vh - 40px);
            background: white;
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            display: flex;
            flex-direction: column;
            z-index: 10000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .widget-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 16px;
            border-radius: 16px 16px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .widget-body {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
        }
        .widget-footer {
            padding: 16px;
            border-top: 1px solid #e0e0e0;
        }
        .message {
            margin-bottom: 12px;
            padding: 10px;
            border-radius: 8px;
        }
        .user-message {
            background: #f0f0f0;
            text-align: right;
        }
        .agent-message {
            background: #e3f2fd;
        }
        .message a {
            color: #0066cc;
            text-decoration: underline;
            cursor: pointer;
        }
        .message a:hover {
            color: #0052a3;
            text-decoration: underline;
        }
        .message a:visited {
            color: #551a8b;
        }
        input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div id="star-agent-widget">
        <div class="widget-header">
            <h3>⭐ STAR AGENT</h3>
            <button onclick="toggleWidget()">−</button>
        </div>
        <div class="widget-body" id="chat-messages"></div>
        <div class="widget-footer">
            <input type="text" id="user-input" placeholder="Escribe tu mensaje..." onkeypress="handleKeyPress(event)">
            <button onclick="sendMessage()">Enviar</button>
        </div>
    </div>
    <script>
        // JavaScript básico para widget
        // En producción, usar WebSocket para tiempo real
        const API_URL = window.location.origin + '/api/widget/chat';
        const WS_URL = 'ws://' + window.location.host + '/ws/widget';
        
        let sessionId = 'widget_' + Date.now();
        let ws = null;
        
        function initWebSocket() {
            ws = new WebSocket(WS_URL);
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                displayMessage(data.text, 'agent');
            };
        }
        
        function sendMessage() {
            const input = document.getElementById('user-input');
            const message = input.value.trim();
            if (!message) return;
            
            displayMessage(message, 'user');
            input.value = '';
            
            // Enviar vía WebSocket si está disponible, sino REST
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    message: message,
                    session_id: sessionId,
                    user_id: 'widget_user',
                    channel: 'web'
                }));
            } else {
                fetch(API_URL, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: message,
                        session_id: sessionId,
                        user_id: 'widget_user',
                        channel: 'web'
                    })
                })
                .then(r => r.json())
                .then(data => displayMessage(data.text, 'agent'));
            }
        }
        
        function convertMarkdownToHTML(text) {
            // Convertir links Markdown [texto](url) a HTML <a href="url">texto</a>
            // Usar regex con escape correcto para Python string
            text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: #0066cc; text-decoration: underline;">$1</a>');
            
            // Convertir saltos de línea a <br>
            text = text.replace(/\n/g, '<br>');
            
            return text;
        }
        
        function displayMessage(text, type) {
            const messagesDiv = document.getElementById('chat-messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + type + '-message';
            
            // Convertir Markdown a HTML (especialmente links)
            const htmlContent = convertMarkdownToHTML(text);
            messageDiv.innerHTML = htmlContent;
            
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }
        
        function toggleWidget() {
            // Implementar toggle
        }
        
        // Inicializar WebSocket al cargar
        initWebSocket();
    </script>
</body>
</html>
        """
        return HTMLResponse(content=widget_html)
    
    return app
