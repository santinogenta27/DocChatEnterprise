"""
Agentic AI para Atención al Cliente Automática 24/7.

Este módulo permite:
- Responder automáticamente mensajes, emails, WhatsApp
- Resolver tickets de soporte de forma autónoma
- Proporcionar soporte 24/7 sin intervención humana
- Integrar con múltiples canales de comunicación
- Usar la base de conocimiento vectorizada para respuestas precisas
"""

from __future__ import annotations

import json
import os
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.retrievers import BaseRetriever

from .config import AppConfig
from .document_processor import DocumentProcessor
from .retriever_builder import RetrieverBuilder
from .auto_response_rules import AutoResponseManager, AutoResponseRule
from .tools import EmailTool, AdvancedEmailTool
from .tools.whatsapp_tool import WhatsAppTool
from .tools.ticket_tool import TicketTool
from .tools.integration_tool import IntegrationTool
from .integrations.langgraph_integration import LangGraphIntegration
from .integrations.crewai_integration import CrewAIIntegration
from .integrations.composio_integration import ComposioIntegration


@dataclass
class CustomerInquiry:
    """Consulta de cliente."""
    inquiry_id: str
    channel: str  # email, whatsapp, chat, phone
    customer_email: str
    message: str
    customer_phone: Optional[str] = None
    subject: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"  # pending, processing, resolved, escalated
    ticket_id: Optional[str] = None
    response: Optional[str] = None


@dataclass
class ServiceResponse:
    """Respuesta del servicio de atención al cliente."""
    inquiry_id: str
    response_text: str
    channel: str
    sent: bool
    ticket_created: bool
    ticket_id: Optional[str] = None
    tools_used: List[str] = field(default_factory=list)
    confidence: float = 0.0
    escalated: bool = False


class CustomerServiceAgent:
    """
    Agentic AI para atención al cliente automática 24/7.
    
    Características:
    - Resolución autónoma de consultas
    - Soporte multi-canal (email, WhatsApp, chat)
    - Integración con base de conocimiento RAG
    - Gestión automática de tickets
    - Escalación inteligente cuando es necesario
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY requerida para Customer Service Agent")
        
        # LLM para procesamiento de consultas
        self.llm = ChatOpenAI(
            model=config.agentic_model or "gpt-4o",
            temperature=0.3,  # Más conservador para customer service
            api_key=config.openai_api_key,
            max_tokens=2000
        )
        
        # Procesador de documentos y retriever
        self.document_processor = DocumentProcessor(config)
        self.retriever_builder = RetrieverBuilder(config)
        self.retriever: Optional[BaseRetriever] = None
        
        # Herramientas disponibles
        self.tools = {
            "email": AdvancedEmailTool(config),
            "whatsapp": WhatsAppTool(config),
            "ticket": TicketTool(config),
            "integration": IntegrationTool(config),
        }
        
        # Integraciones avanzadas
        try:
            self.langgraph = LangGraphIntegration(config, llm=self.llm)
            print("✅ LangGraph integrado en Customer Service Agent")
        except Exception as e:
            print(f"⚠️ LangGraph no disponible en Customer Service Agent: {e}")
            self.langgraph = None
        
        try:
            self.crewai = CrewAIIntegration(config)
            print("✅ CrewAI integrado en Customer Service Agent")
        except Exception as e:
            print(f"⚠️ CrewAI no disponible en Customer Service Agent: {e}")
            self.crewai = None
        
        try:
            self.composio = ComposioIntegration(config)
            print("✅ Composio integrado en Customer Service Agent")
        except Exception as e:
            print(f"⚠️ Composio no disponible en Customer Service Agent: {e}")
            self.composio = None
        
        # Configuración de monitoreo continuo
        self.monitoring_enabled = os.getenv("CS_MONITORING_ENABLED", "false").lower() == "true"
        self.monitoring_interval = int(os.getenv("CS_MONITORING_INTERVAL", "60"))  # segundos
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # Umbral de confianza para escalación
        self.confidence_threshold = float(os.getenv("CS_CONFIDENCE_THRESHOLD", "0.5"))
        
        # Canales configurados para monitoreo
        self.monitored_channels = {
            "email": os.getenv("CS_MONITOR_EMAIL", "false").lower() == "true",
            "whatsapp": os.getenv("CS_MONITOR_WHATSAPP", "false").lower() == "true",
            "slack": os.getenv("CS_MONITOR_SLACK", "false").lower() == "true",
            "teams": os.getenv("CS_MONITOR_TEAMS", "false").lower() == "true",
            "web": os.getenv("CS_MONITOR_WEB", "false").lower() == "true"
        }
        
        # Sistema de reglas automáticas
        self.auto_response_manager = AutoResponseManager(config)
        
        # Almacenamiento de consultas y documentos
        self.inquiries: Dict[str, CustomerInquiry] = {}
        self.processed_documents: List[Document] = []
        self.conversation_history: Dict[str, List[Dict[str, str]]] = {}
        
        # Estadísticas
        self.stats = {
            "total_inquiries": 0,
            "resolved_autonomously": 0,
            "escalated": 0,
            "tickets_created": 0,
            "average_resolution_time": 0.0
        }
    
    def load_knowledge_base(self, files: List[Any]) -> None:
        """
        Carga documentos para la base de conocimiento.
        Estos documentos se usarán para responder consultas de clientes.
        """
        print(f"\n📚 Cargando base de conocimiento para Customer Service: {len(files)} documentos")
        
        documents = self.document_processor.process(files)
        self.processed_documents.extend(documents)
        
        if self.processed_documents:
            self.retriever = self.retriever_builder.build_hybrid_retriever(self.processed_documents)
            print(f"✅ Base de conocimiento cargada: {len(self.processed_documents)} chunks disponibles")
    
    def process_inquiry(
        self,
        channel: str,
        customer_email: str,
        message: str,
        customer_phone: Optional[str] = None,
        subject: Optional[str] = None,
        use_knowledge_base: bool = True
    ) -> ServiceResponse:
        """
        Procesa una consulta de cliente y genera respuesta automática.
        
        Args:
            channel: Canal de comunicación (email, whatsapp, chat)
            customer_email: Email del cliente
            message: Mensaje del cliente
            customer_phone: Teléfono del cliente (opcional)
            subject: Asunto (para emails)
            use_knowledge_base: Si usar la base de conocimiento RAG
        
        Returns:
            ServiceResponse con la respuesta generada
        """
        inquiry_id = f"INQ-{int(time.time())}-{len(self.inquiries)}"
        
        # Crear registro de consulta
        inquiry = CustomerInquiry(
            inquiry_id=inquiry_id,
            channel=channel,
            customer_email=customer_email,
            customer_phone=customer_phone,
            subject=subject,
            message=message,
            status="processing"
        )
        self.inquiries[inquiry_id] = inquiry
        self.stats["total_inquiries"] += 1
        
        print(f"\n{'='*60}")
        print(f"📞 NUEVA CONSULTA DE CLIENTE")
        print(f"{'='*60}")
        print(f"Canal: {channel}")
        print(f"Cliente: {customer_email}")
        print(f"Mensaje: {message[:100]}...")
        print()
        
        try:
            # 0. PRIMERO: Verificar reglas automáticas de respuesta
            customer_data = {
                "email": customer_email,
                "phone": customer_phone,
                "channel": channel
            }
            
            matching_rule = self.auto_response_manager.evaluate_message(
                channel=channel,
                message=message,
                customer_data=customer_data
            )
            
            if matching_rule:
                print(f"🤖 REGLA AUTOMÁTICA ACTIVADA: {matching_rule.name}")
                print(f"   Trigger: {matching_rule.trigger_type} = {matching_rule.trigger_value}")
                
                # Usar respuesta automática
                response_text = self.auto_response_manager.generate_response(
                    rule=matching_rule,
                    message=message,
                    customer_data=customer_data
                )
                
                # Si la respuesta es AI-generated, mejorarla con LLM
                if matching_rule.response_type == "ai_generated":
                    response_text = self._enhance_ai_response(response_text, message, context_docs=[])
                
                intent_analysis = {
                    "intent": "auto_response",
                    "urgency": "low",
                    "confidence": 1.0,
                    "rule_used": matching_rule.rule_id
                }
                context_docs = []
            else:
                # 1. Analizar la consulta y determinar intención
                intent_analysis = self._analyze_intent(message, customer_email)
                print(f"🎯 Intención detectada: {intent_analysis.get('intent', 'unknown')}")
                print(f"   Urgencia: {intent_analysis.get('urgency', 'medium')}")
                print(f"   Confianza: {intent_analysis.get('confidence', 0.0):.2f}")
                
                # 2. Buscar información relevante en la base de conocimiento
                context_docs = []
                if use_knowledge_base and self.retriever:
                    context_docs = self.retriever.get_relevant_documents(message)
                    print(f"📚 Documentos relevantes encontrados: {len(context_docs)}")
                
                # 3. Generar respuesta usando LLM
                response_text = self._generate_response(
                    message=message,
                    customer_email=customer_email,
                    intent=intent_analysis,
                    context_docs=context_docs,
                    channel=channel
                )
            
            # 4. Determinar acciones a tomar
            actions = self._determine_actions(
                intent=intent_analysis,
                response_text=response_text,
                customer_email=customer_email,
                customer_phone=customer_phone,
                channel=channel
            )
            
            # 5. Ejecutar acciones (enviar respuesta, crear ticket, etc.)
            ticket_id = None
            tools_used = []
            sent = False
            
            # Enviar respuesta por el canal correspondiente
            if actions.get("send_response"):
                sent = self._send_response(
                    channel=channel,
                    to=customer_email if channel == "email" else customer_phone or customer_email,
                    subject=subject or f"Respuesta a tu consulta - {inquiry_id}",
                    message=response_text,
                    tools_used=tools_used
                )
            
            # Crear ticket si es necesario
            if actions.get("create_ticket"):
                ticket_result = self.tools["ticket"].execute(
                    action="create",
                    customer_email=customer_email,
                    subject=subject or intent_analysis.get("intent", "Consulta de cliente"),
                    description=message,
                    priority=intent_analysis.get("urgency", "medium")
                )
                if ticket_result.success:
                    ticket_id = ticket_result.data.get("ticket_id")
                    inquiry.ticket_id = ticket_id
                    self.stats["tickets_created"] += 1
                    tools_used.append("ticket")
            
            # Obtener confianza del análisis de intención
            confidence = intent_analysis.get("confidence", 0.0)
            
            # Actualizar estado y escalar si es necesario
            if actions.get("escalate") or confidence < self.confidence_threshold:
                inquiry.status = "escalated"
                self.stats["escalated"] += 1
                # Escalar a humano si la confianza es baja
                if confidence < self.confidence_threshold:
                    # Crear respuesta temporal para escalación
                    temp_response = ServiceResponse(
                        inquiry_id=inquiry_id,
                        response_text=response_text,
                        channel=channel,
                        sent=sent,
                        ticket_created=actions.get("create_ticket", False),
                        ticket_id=ticket_id,
                        tools_used=tools_used,
                        confidence=confidence,
                        escalated=True
                    )
                    self._escalate_to_human(
                        temp_response,
                        {
                            "from": customer_email,
                            "email": customer_email,
                            "message": message,
                            "phone": customer_phone
                        }
                    )
            else:
                inquiry.status = "resolved"
                inquiry.response = response_text
                self.stats["resolved_autonomously"] += 1
            
            # Guardar en historial de conversación
            if customer_email not in self.conversation_history:
                self.conversation_history[customer_email] = []
            self.conversation_history[customer_email].append({
                "role": "user",
                "content": message,
                "timestamp": inquiry.timestamp
            })
            self.conversation_history[customer_email].append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now().isoformat()
            })
            
            # Determinar si se escaló (puede haber cambiado después de _escalate_to_human)
            final_escalated = actions.get("escalate", False) or confidence < self.confidence_threshold
            
            # Crear respuesta
            service_response = ServiceResponse(
                inquiry_id=inquiry_id,
                response_text=response_text,
                channel=channel,
                sent=sent,
                ticket_created=actions.get("create_ticket", False),
                ticket_id=ticket_id,
                tools_used=tools_used,
                confidence=confidence,
                escalated=final_escalated
            )
            
            print(f"\n✅ Consulta procesada exitosamente")
            print(f"   Respuesta enviada: {'Sí' if sent else 'No'}")
            print(f"   Ticket creado: {'Sí' if ticket_id else 'No'}")
            print(f"   Escalado: {'Sí' if service_response.escalated else 'No'}")
            print()
            
            return service_response
        
        except Exception as e:
            print(f"\n❌ Error procesando consulta: {str(e)}")
            import traceback
            traceback.print_exc()
            
            inquiry.status = "error"
            return ServiceResponse(
                inquiry_id=inquiry_id,
                response_text=f"Lo sentimos, hubo un error procesando tu consulta. Por favor, intenta nuevamente o contacta a soporte.",
                channel=channel,
                sent=False,
                ticket_created=False,
                confidence=0.0,
                escalated=True
            )
    
    def _analyze_intent(self, message: str, customer_email: str) -> Dict[str, Any]:
        """Analiza la intención y urgencia de la consulta."""
        prompt = f"""Analiza esta consulta de cliente y determina:

1. Intención principal (ej: pregunta, queja, solicitud, problema técnico, reembolso, etc.)
2. Urgencia (low, medium, high, critical)
3. Confianza de resolución automática (0.0 a 1.0)
4. Si requiere escalación a humano (true/false)
5. Emoción detectada (neutral, frustrado, satisfecho, urgente, etc.)

Consulta del cliente:
{message}

Email del cliente: {customer_email}

Responde en formato JSON:
{{
    "intent": "tipo de intención",
    "urgency": "low|medium|high|critical",
    "confidence": 0.0-1.0,
    "requires_escalation": true/false,
    "emotion": "emoción detectada",
    "key_topics": ["tema1", "tema2"]
}}
"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            # Intentar parsear JSON
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            intent_data = json.loads(response)
            return intent_data
        except:
            # Fallback si no se puede parsear
            return {
                "intent": "general_inquiry",
                "urgency": "medium",
                "confidence": 0.7,
                "requires_escalation": False,
                "emotion": "neutral",
                "key_topics": []
            }
    
    def _generate_response(
        self,
        message: str,
        customer_email: str,
        intent: Dict[str, Any],
        context_docs: List[Document],
        channel: str
    ) -> str:
        """Genera respuesta usando LLM y contexto de documentos."""
        
        # Construir contexto de documentos
        context_text = ""
        if context_docs:
            context_text = "\n\nInformación relevante de la base de conocimiento:\n"
            for i, doc in enumerate(context_docs[:5], 1):  # Máximo 5 documentos
                source = doc.metadata.get("source", "documento")
                context_text += f"\n[{i}] {doc.page_content[:500]}...\n(Fuente: {source})\n"
        
        # Obtener historial de conversación si existe
        history_context = ""
        if customer_email in self.conversation_history:
            recent_history = self.conversation_history[customer_email][-4:]  # Últimas 2 interacciones
            history_context = "\n\nHistorial de conversación previa:\n"
            for msg in recent_history:
                role = "Cliente" if msg["role"] == "user" else "Asistente"
                history_context += f"{role}: {msg['content'][:200]}...\n"
        
        prompt = f"""Eres un asistente de atención al cliente profesional y empático. Tu tarea es responder consultas de clientes de manera clara, útil y amigable.

INFORMACIÓN DEL CLIENTE:
- Email: {customer_email}
- Canal: {channel}
- Intención detectada: {intent.get('intent', 'unknown')}
- Urgencia: {intent.get('urgency', 'medium')}
- Emoción: {intent.get('emotion', 'neutral')}

CONSULTA DEL CLIENTE:
{message}
{context_text}
{history_context}

INSTRUCCIONES:
1. Responde de manera profesional, empática y clara
2. Si tienes información relevante en el contexto, úsala para dar una respuesta precisa
3. Si no tienes suficiente información, sé honesto pero ofrece alternativas
4. Mantén un tono amigable pero profesional
5. Si el cliente está frustrado, muestra empatía
6. Si puedes resolver el problema, proporciona pasos claros
7. Si no puedes resolverlo completamente, ofrece escalar a un agente humano
8. Responde en español
9. Sé conciso pero completo (máximo 300 palabras)

RESPUESTA:"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            return response
        except Exception as e:
            return f"Gracias por tu consulta. Hemos recibido tu mensaje y un agente se pondrá en contacto contigo pronto. Tu consulta ha sido registrada."
    
    def _determine_actions(
        self,
        intent: Dict[str, Any],
        response_text: str,
        customer_email: str,
        customer_phone: Optional[str],
        channel: str
    ) -> Dict[str, Any]:
        """Determina qué acciones tomar basado en la intención y respuesta."""
        actions = {
            "send_response": True,
            "create_ticket": False,
            "escalate": False
        }
        
        # Crear ticket si es urgente o requiere seguimiento
        if intent.get("urgency") in ["high", "critical"]:
            actions["create_ticket"] = True
        
        if intent.get("requires_escalation", False):
            actions["escalate"] = True
            actions["create_ticket"] = True
        
        # Crear ticket si la confianza es baja (usar umbral configurado)
        if intent.get("confidence", 1.0) < self.confidence_threshold:
            actions["create_ticket"] = True
            actions["escalate"] = True
        
        # Escalar si requiere escalación explícita o confianza muy baja
        if intent.get("requires_escalation", False) or intent.get("confidence", 1.0) < (self.confidence_threshold * 0.7):
            actions["escalate"] = True
            actions["create_ticket"] = True
        
        return actions
    
    def _send_response(
        self,
        channel: str,
        to: str,
        subject: str,
        message: str,
        tools_used: List[str]
    ) -> bool:
        """Envía respuesta por el canal correspondiente."""
        try:
            if channel == "email":
                result = self.tools["email"].execute(
                    to=to,
                    subject=subject,
                    body=message
                )
                if result.success:
                    tools_used.append("email")
                return result.success
            
            elif channel == "whatsapp":
                result = self.tools["whatsapp"].execute(
                    to=to,
                    message=message
                )
                if result.success:
                    tools_used.append("whatsapp")
                return result.success
            
            else:  # chat u otros canales
                # Para chat, solo retornamos True (la respuesta se muestra en la UI)
                return True
        
        except Exception as e:
            print(f"Error enviando respuesta por {channel}: {str(e)}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del servicio."""
        total = self.stats["total_inquiries"]
        if total > 0:
            resolution_rate = (self.stats["resolved_autonomously"] / total) * 100
            escalation_rate = (self.stats["escalated"] / total) * 100
        else:
            resolution_rate = 0.0
            escalation_rate = 0.0
        
        return {
            **self.stats,
            "resolution_rate": f"{resolution_rate:.1f}%",
            "escalation_rate": f"{escalation_rate:.1f}%",
            "knowledge_base_documents": len(self.processed_documents)
        }
    
    def _enhance_ai_response(
        self,
        base_response: str,
        original_message: str,
        context_docs: List[Document] = None
    ) -> str:
        """Mejora una respuesta AI con contexto adicional."""
        try:
            context = base_response
            if context_docs:
                context += "\n\nContexto adicional:\n"
                for doc in context_docs[:3]:
                    context += f"- {doc.page_content[:200]}...\n"
            
            prompt = f"""Mejora esta respuesta automática para que sea más personalizada y útil:

Mensaje del cliente: {original_message}

Respuesta base: {base_response}

Genera una respuesta mejorada que:
1. Sea más personalizada
2. Responda directamente al mensaje del cliente
3. Sea amigable y profesional
4. Mantenga el tono de la respuesta base

Respuesta mejorada:"""
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as e:
            print(f"Error mejorando respuesta AI: {e}")
            return base_response
    
    def start_monitoring_loop(self):
        """
        Inicia el loop de monitoreo continuo (Agent Loop).
        Este loop monitorea automáticamente todos los canales configurados
        y procesa mensajes entrantes sin intervención humana.
        """
        if self.monitoring_active:
            print("⚠️ Monitoreo ya está activo")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="CustomerServiceMonitoring"
        )
        self.monitoring_thread.start()
        print(f"✅ Agent Loop iniciado - Monitoreando canales cada {self.monitoring_interval} segundos")
    
    def stop_monitoring_loop(self):
        """Detiene el loop de monitoreo continuo."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        print("🛑 Agent Loop detenido")
    
    def _monitoring_loop(self):
        """
        Loop principal del agente que monitorea canales continuamente.
        Este es el "agent loop" que procesa mensajes automáticamente.
        """
        print(f"\n🔄 [Agent Loop] Iniciando monitoreo continuo...")
        print(f"   Canales activos: {[k for k, v in self.monitored_channels.items() if v]}")
        
        while self.monitoring_active:
            try:
                # Monitorear cada canal configurado
                if self.monitored_channels.get("email"):
                    self._monitor_email_channel()
                
                if self.monitored_channels.get("whatsapp"):
                    self._monitor_whatsapp_channel()
                
                if self.monitored_channels.get("slack"):
                    self._monitor_slack_channel()
                
                if self.monitored_channels.get("teams"):
                    self._monitor_teams_channel()
                
                if self.monitored_channels.get("web"):
                    self._monitor_web_channel()
                
                # Esperar antes del siguiente ciclo
                time.sleep(self.monitoring_interval)
            
            except Exception as e:
                print(f"❌ Error en Agent Loop: {e}")
                time.sleep(self.monitoring_interval)
    
    def _monitor_email_channel(self):
        """Monitorea emails entrantes y los procesa automáticamente."""
        try:
            # Aquí se integraría con IMAP/Gmail API para leer emails
            # Por ahora, es un placeholder que puede ser extendido
            # con integración real de email
            
            # Ejemplo: Si hay un webhook configurado, se puede usar
            # para recibir notificaciones de nuevos emails
            
            pass  # Implementación específica depende de la integración de email
            
        except Exception as e:
            print(f"⚠️ Error monitoreando email: {e}")
    
    def _monitor_whatsapp_channel(self):
        """Monitorea mensajes de WhatsApp y los procesa automáticamente."""
        try:
            # Integración con WhatsApp Business API para leer mensajes
            # Por ahora, placeholder para extensión futura
            
            pass  # Implementación específica depende de la integración de WhatsApp
            
        except Exception as e:
            print(f"⚠️ Error monitoreando WhatsApp: {e}")
    
    def _monitor_slack_channel(self):
        """Monitorea mensajes de Slack y los procesa automáticamente."""
        try:
            # Integración con Slack API para leer mensajes de canales
            # Por ahora, placeholder
            
            pass  # Implementación específica depende de la integración de Slack
            
        except Exception as e:
            print(f"⚠️ Error monitoreando Slack: {e}")
    
    def _monitor_teams_channel(self):
        """Monitorea mensajes de Teams y los procesa automáticamente."""
        try:
            # Integración con Microsoft Teams API
            # Por ahora, placeholder
            
            pass  # Implementación específica depende de la integración de Teams
            
        except Exception as e:
            print(f"⚠️ Error monitoreando Teams: {e}")
    
    def _monitor_web_channel(self):
        """Monitorea consultas web (formularios, chat widgets, etc.)."""
        try:
            # Monitoreo de formularios web, chat widgets, etc.
            # Por ahora, placeholder
            
            pass  # Implementación específica depende de la integración web
            
        except Exception as e:
            print(f"⚠️ Error monitoreando web: {e}")
    
    def process_incoming_message(
        self,
        channel: str,
        message_data: Dict[str, Any]
    ) -> ServiceResponse:
        """
        Procesa un mensaje entrante automáticamente (usado por el Agent Loop).
        
        Args:
            channel: Canal de origen (email, whatsapp, slack, teams, web)
            message_data: Datos del mensaje {
                "from": email/phone/user_id,
                "message": texto del mensaje,
                "subject": asunto (opcional),
                "thread_id": ID de conversación (opcional)
            }
        """
        try:
            # Extraer datos del mensaje
            customer_email = message_data.get("from") or message_data.get("email") or message_data.get("customer_email", "unknown@example.com")
            message = message_data.get("message") or message_data.get("text") or message_data.get("body", "")
            subject = message_data.get("subject")
            customer_phone = message_data.get("phone") or message_data.get("customer_phone")
            
            if not message or not message.strip():
                return ServiceResponse(
                    inquiry_id="",
                    response_text="",
                    channel=channel,
                    sent=False,
                    ticket_created=False,
                    confidence=0.0,
                    escalated=False
                )
            
            print(f"\n📨 [Agent Loop] Nuevo mensaje recibido en {channel}")
            print(f"   De: {customer_email}")
            print(f"   Mensaje: {message[:100]}...")
            
            # Procesar la consulta usando el método existente
            response = self.process_inquiry(
                channel=channel,
                customer_email=customer_email,
                message=message,
                customer_phone=customer_phone,
                subject=subject,
                use_knowledge_base=True
            )
            
            # Si la confianza es baja, escalar automáticamente
            if response.confidence < self.confidence_threshold and not response.escalated:
                print(f"⚠️ [Agent Loop] Confianza baja ({response.confidence:.2f}), escalando a humano...")
                self._escalate_to_human(response, message_data)
                response.escalated = True
            
            return response
        
        except Exception as e:
            print(f"❌ Error procesando mensaje entrante: {e}")
            return ServiceResponse(
                inquiry_id="",
                response_text="",
                channel=channel,
                sent=False,
                ticket_created=False,
                confidence=0.0,
                escalated=True
            )
    
    def _escalate_to_human(
        self,
        response: ServiceResponse,
        original_message_data: Dict[str, Any]
    ):
        """
        Escala una consulta a un agente humano.
        Envía notificaciones a Slack/Teams y crea ticket de alta prioridad.
        """
        try:
            escalation_message = f"""
🚨 **ESCALACIÓN A HUMANO REQUERIDA**

**Consulta ID:** {response.inquiry_id}
**Canal:** {response.channel}
**Confianza:** {response.confidence:.1%}
**Cliente:** {original_message_data.get('from', 'Unknown')}

**Mensaje Original:**
{original_message_data.get('message', '')[:500]}

**Respuesta Generada (baja confianza):**
{response.response_text[:300]}

**Acción Requerida:** Revisar y responder manualmente
"""
            
            # Enviar notificación a Slack si está configurado
            slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
            if slack_webhook:
                self.tools["integration"].execute(
                    platform="slack",
                    message=escalation_message,
                    title="Escalación de Soporte",
                    webhook_url=slack_webhook
                )
            
            # Enviar notificación a Teams si está configurado
            teams_webhook = os.getenv("TEAMS_WEBHOOK_URL")
            if teams_webhook:
                self.tools["integration"].execute(
                    platform="teams",
                    message=escalation_message,
                    title="Escalación de Soporte",
                    webhook_url=teams_webhook
                )
            
            # Crear ticket de alta prioridad
            if not response.ticket_created:
                ticket_result = self.tools["ticket"].execute(
                    action="create",
                    customer_email=original_message_data.get("from", "unknown@example.com"),
                    subject=f"[ESCALADO] Consulta requiere atención humana - {response.inquiry_id}",
                    description=escalation_message,
                    priority="high"
                )
                if ticket_result.success:
                    response.ticket_id = ticket_result.data.get("ticket_id")
                    response.ticket_created = True
            
            print(f"✅ Escalación completada - Notificaciones enviadas")
        
        except Exception as e:
            print(f"⚠️ Error en escalación: {e}")
    
    def receive_webhook_message(self, webhook_data: Dict[str, Any]) -> ServiceResponse:
        """
        Recibe mensajes vía webhook (para integración con sistemas externos).
        
        Formato esperado:
        {
            "channel": "email|whatsapp|slack|teams|web",
            "from": "email/phone/user_id",
            "message": "texto del mensaje",
            "subject": "asunto (opcional)",
            "phone": "teléfono (opcional)",
            "metadata": {}
        }
        """
        try:
            channel = webhook_data.get("channel", "web")
            message_data = {
                "from": webhook_data.get("from"),
                "email": webhook_data.get("from"),  # Para compatibilidad
                "message": webhook_data.get("message") or webhook_data.get("text") or webhook_data.get("body"),
                "subject": webhook_data.get("subject"),
                "phone": webhook_data.get("phone"),
                "customer_phone": webhook_data.get("phone"),
                "metadata": webhook_data.get("metadata", {})
            }
            
            return self.process_incoming_message(channel, message_data)
        
        except Exception as e:
            print(f"❌ Error procesando webhook: {e}")
            return ServiceResponse(
                inquiry_id="",
                response_text="",
                channel=webhook_data.get("channel", "web"),
                sent=False,
                ticket_created=False,
                confidence=0.0,
                escalated=True
            )
    
    # ============================================
    # MÉTODOS CON LANGRAPH - Workflows Avanzados
    # ============================================
    
    def create_support_resolution_workflow(self, inquiry_id: str) -> Dict[str, Any]:
        """
        Crea un workflow LangGraph para resolución de consultas.
        
        Workflow:
        1. Analizar intención
        2. Buscar en conocimiento
        3. Generar respuesta
        4. Evaluar confianza
        5. Enviar respuesta o escalar
        """
        if not self.langgraph:
            return {"success": False, "error": "LangGraph no está disponible"}
        
        try:
            inquiry = self.inquiries.get(inquiry_id)
            if not inquiry:
                return {"success": False, "error": "Consulta no encontrada"}
            
            def analyze_intent_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Analizar intención"""
                intent = self._analyze_intent(
                    state["data"]["message"],
                    state["data"]["customer_email"]
                )
                state["data"]["intent"] = intent
                return state
            
            def search_knowledge_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Buscar en base de conocimiento"""
                if self.retriever:
                    docs = self.retriever.get_relevant_documents(state["data"]["message"])
                    state["data"]["knowledge_docs"] = [doc.page_content for doc in docs[:5]]
                return state
            
            def generate_response_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Generar respuesta"""
                response = self._generate_response(
                    message=state["data"]["message"],
                    customer_email=state["data"]["customer_email"],
                    intent=state["data"].get("intent", {}),
                    context_docs=[Document(page_content=d) for d in state["data"].get("knowledge_docs", [])],
                    channel=state["data"]["channel"]
                )
                state["data"]["response"] = response
                return state
            
            def evaluate_confidence_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Evaluar confianza"""
                confidence = state["data"].get("intent", {}).get("confidence", 0.0)
                state["data"]["confidence"] = confidence
                state["data"]["should_escalate"] = confidence < self.confidence_threshold
                return state
            
            def send_or_escalate_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Nodo: Enviar respuesta o escalar"""
                if state["data"].get("should_escalate"):
                    # Escalar
                    self._escalate_to_human(
                        ServiceResponse(
                            inquiry_id=inquiry_id,
                            response_text=state["data"].get("response", ""),
                            channel=state["data"]["channel"],
                            sent=False,
                            ticket_created=True,
                            confidence=state["data"].get("confidence", 0.0),
                            escalated=True
                        ),
                        {
                            "from": state["data"]["customer_email"],
                            "message": state["data"]["message"]
                        }
                    )
                    state["data"]["escalated"] = True
                else:
                    # Enviar respuesta
                    self._send_response(
                        channel=state["data"]["channel"],
                        to=state["data"]["customer_email"],
                        subject=state["data"].get("subject", "Respuesta a tu consulta"),
                        message=state["data"].get("response", ""),
                        tools_used=[]
                    )
                    state["data"]["sent"] = True
                return state
            
            # Crear workflow
            nodes = {
                "analyze": analyze_intent_node,
                "search": search_knowledge_node,
                "generate": generate_response_node,
                "evaluate": evaluate_confidence_node,
                "send_or_escalate": send_or_escalate_node
            }
            
            edges = [
                ("analyze", "search"),
                ("search", "generate"),
                ("generate", "evaluate"),
                ("evaluate", "send_or_escalate")
            ]
            
            workflow_id = f"support_{inquiry_id}"
            workflow = self.langgraph.create_workflow(
                workflow_id=workflow_id,
                nodes=nodes,
                edges=edges,
                entry_point="analyze",
                exit_point="send_or_escalate"
            )
            
            # Ejecutar workflow
            result = self.langgraph.execute_workflow(
                workflow_id=workflow_id,
                initial_data={
                    "inquiry_id": inquiry_id,
                    "message": inquiry.message,
                    "customer_email": inquiry.customer_email,
                    "channel": inquiry.channel,
                    "subject": inquiry.subject
                }
            )
            
            return result
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================
    # MÉTODOS CON CREWAI - Multi-Agent Collaboration
    # ============================================
    
    def create_support_crew(self) -> Dict[str, Any]:
        """
        Crea un crew de agentes CrewAI para soporte al cliente.
        
        Agentes:
        - Intent Analyzer: Analiza intención y urgencia
        - Knowledge Researcher: Busca en base de conocimiento
        - Response Generator: Genera respuestas personalizadas
        - Quality Validator: Valida calidad de respuesta
        """
        if not self.crewai:
            return {"success": False, "error": "CrewAI no está disponible"}
        
        try:
            # Crear agentes especializados
            intent_analyzer = self.crewai.create_agent(
                agent_id="intent_analyzer",
                role="Customer Intent Analyst",
                goal="Analyze customer inquiries to understand intent, urgency, and emotion",
                backstory="""You are an expert at understanding customer needs. You can 
                identify what customers really want, how urgent their request is, and 
                what emotion they're expressing. You help route inquiries appropriately.""",
                verbose=True
            )
            
            knowledge_researcher = self.crewai.create_agent(
                agent_id="knowledge_researcher",
                role="Knowledge Base Researcher",
                goal="Find relevant information from knowledge base to answer customer questions",
                backstory="""You are an expert at searching and finding information. You 
                know how to use knowledge bases, documentation, and FAQs to find accurate 
                answers to customer questions.""",
                verbose=True
            )
            
            response_generator = self.crewai.create_agent(
                agent_id="response_generator",
                role="Customer Support Response Specialist",
                goal="Generate empathetic, accurate, and helpful responses to customer inquiries",
                backstory="""You are an expert customer support agent. You write clear, 
                empathetic responses that solve customer problems. You're professional, 
                friendly, and always aim to help.""",
                verbose=True
            )
            
            quality_validator = self.crewai.create_agent(
                agent_id="quality_validator",
                role="Response Quality Validator",
                goal="Validate that responses are accurate, complete, and appropriate",
                backstory="""You are an expert at quality assurance. You review responses 
                to ensure they're accurate, complete, helpful, and appropriate. You catch 
                errors and suggest improvements.""",
                verbose=True
            )
            
            # Crear tareas
            analysis_task = self.crewai.create_task(
                description="Analyze the customer inquiry to understand intent, urgency, and emotion",
                agent=intent_analyzer,
                expected_output="Intent analysis with urgency level and emotion detected"
            )
            
            research_task = self.crewai.create_task(
                description="Search knowledge base for relevant information to answer the customer",
                agent=knowledge_researcher,
                expected_output="Relevant information from knowledge base"
            )
            
            generation_task = self.crewai.create_task(
                description="Generate a helpful, empathetic response to the customer inquiry",
                agent=response_generator,
                expected_output="Complete response ready to send to customer"
            )
            
            validation_task = self.crewai.create_task(
                description="Validate the response for accuracy, completeness, and quality",
                agent=quality_validator,
                expected_output="Validated response with quality score"
            )
            
            # Crear crew
            crew = self.crewai.create_crew(
                crew_id="support_crew",
                agents=[intent_analyzer, knowledge_researcher, response_generator, quality_validator],
                tasks=[analysis_task, research_task, generation_task, validation_task],
                process="sequential",
                verbose=True
            )
            
            return {
                "success": True,
                "crew_id": "support_crew",
                "agents": ["intent_analyzer", "knowledge_researcher", "response_generator", "quality_validator"],
                "message": "Support crew creado exitosamente"
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute_support_crew(self, customer_message: str, customer_email: str) -> Dict[str, Any]:
        """Ejecuta el crew de soporte para responder una consulta."""
        if not self.crewai:
            return {"success": False, "error": "CrewAI no está disponible"}
        
        try:
            # Asegurar que el crew existe
            if "support_crew" not in self.crewai.crews:
                self.create_support_crew()
            
            # Ejecutar crew
            result = self.crewai.execute_crew(
                crew_id="support_crew",
                inputs={
                    "customer_message": customer_message,
                    "customer_email": customer_email,
                    "knowledge_base_available": self.retriever is not None
                }
            )
            
            return result
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================
    # MÉTODOS CON COMPOSIO - 250+ Integraciones
    # ============================================
    
    def connect_support_system(self, system_name: str) -> Dict[str, Any]:
        """Conecta un sistema de soporte usando Composio."""
        if not self.composio:
            return {"success": False, "error": "Composio no está disponible"}
        
        try:
            # Mapear sistemas de soporte
            system_map = {
                "zendesk": "zendesk",
                "freshdesk": "freshdesk",
                "servicenow": "servicenow",
                "jira": "jira",
                "salesforce": "salesforce",
                "hubspot": "hubspot"
            }
            
            app_name = system_map.get(system_name.lower(), system_name.lower())
            result = self.composio.connect_app(app_name)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_ticket_via_composio(
        self,
        inquiry_id: str,
        system: str = "zendesk"
    ) -> Dict[str, Any]:
        """
        Crea un ticket en un sistema de soporte usando Composio.
        
        Args:
            inquiry_id: ID de la consulta
            system: Sistema (zendesk, freshdesk, servicenow, jira)
        """
        if not self.composio:
            return {"success": False, "error": "Composio no está disponible"}
        
        try:
            inquiry = self.inquiries.get(inquiry_id)
            if not inquiry:
                return {"success": False, "error": "Consulta no encontrada"}
            
            # Conectar sistema si no está conectado
            if system not in self.composio.connected_apps:
                connect_result = self.connect_support_system(system)
                if not connect_result.get("success"):
                    return connect_result
            
            # Mapear acciones según sistema
            action_map = {
                "zendesk": "create_ticket",
                "freshdesk": "create_ticket",
                "servicenow": "create_incident",
                "jira": "create_issue"
            }
            
            action_name = action_map.get(system, "create_ticket")
            
            # Preparar parámetros
            parameters = {
                "subject": inquiry.subject or f"Support Request - {inquiry_id}",
                "description": inquiry.message,
                "requester_email": inquiry.customer_email,
                "priority": "normal"
            }
            
            # Ejecutar acción
            result = self.composio.execute_action(
                app_name=system,
                action_name=action_name,
                parameters=parameters
            )
            
            if result.get("success"):
                # Actualizar inquiry con ticket ID
                if "result" in result and isinstance(result["result"], dict):
                    ticket_id = result["result"].get("id") or result["result"].get("ticket_id")
                    if ticket_id:
                        inquiry.ticket_id = str(ticket_id)
            
            return result
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_composio_support_apps(self) -> List[Dict[str, Any]]:
        """Obtiene apps de soporte disponibles en Composio."""
        if not self.composio:
            return []
        
        try:
            all_apps = self.composio.get_available_apps()
            support_apps = [
                app for app in all_apps
                if any(keyword in app.get("name", "").lower() for keyword in 
                       ["zendesk", "freshdesk", "servicenow", "jira", "support", "ticket", "helpdesk"])
            ]
            return support_apps
        except Exception as e:
            print(f"Error obteniendo apps de soporte: {e}")
            return []

