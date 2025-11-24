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
import time
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
            
            # Actualizar estado
            if actions.get("escalate"):
                inquiry.status = "escalated"
                self.stats["escalated"] += 1
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
            
            # Crear respuesta
            service_response = ServiceResponse(
                inquiry_id=inquiry_id,
                response_text=response_text,
                channel=channel,
                sent=sent,
                ticket_created=actions.get("create_ticket", False),
                ticket_id=ticket_id,
                tools_used=tools_used,
                confidence=intent_analysis.get("confidence", 0.0),
                escalated=actions.get("escalate", False)
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
        
        # Crear ticket si la confianza es baja
        if intent.get("confidence", 1.0) < 0.5:
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

