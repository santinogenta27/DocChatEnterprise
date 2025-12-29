"""LangGraph Agent - Customer Service Agent Enterprise - IMPLEMENTACIÓN COMPLETA."""

from typing import Dict, Any, Literal, List, Optional
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from .state import CustomerServiceState
from .intent_classifier import IntentClassifier
from .decision_policy import DecisionPolicy
from .rag_retriever import RAGRetriever
from .react_agent import ReActAgent
from .memory_manager import MemoryManager
from .response_validator import ResponseValidator
from .tools_registry import ToolsRegistry
import json
import re


class CustomerServiceAgentGraph:
    """Agente de Customer Service basado en LangGraph - IMPLEMENTACIÓN COMPLETA."""
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        tools: Dict[str, Any] = None,
        rag_retriever: RAGRetriever = None
    ):
        self.llm = llm
        self.raw_tools = tools or {}
        
        # Inicializar componentes
        self.rag_retriever = rag_retriever or RAGRetriever()
        self.intent_classifier = IntentClassifier(llm)
        self.decision_policy = DecisionPolicy()
        self.memory_manager = MemoryManager()
        self.response_validator = ResponseValidator(llm)
        
        # Registrar tools en formato LangChain
        self.tools_registry = ToolsRegistry()
        self._register_tools()
        
        # ReAct Agent
        self.react_agent = ReActAgent(llm, self.tools_registry.get_all_tools())
        
        # System prompt base (CRÍTICO)
        self.system_prompt = """You are an enterprise-grade AI Customer Support Agent.

Rules:
- You ONLY answer using the provided business context.
- If information is missing, you say: "I don't have that information yet."
- You NEVER invent policies, prices, delivery times, or guarantees.
- You follow company policies strictly.
- You are concise, polite, professional, and solution-oriented.
- You prioritize resolution over explanation.
- If confidence < 95%, escalate to a human agent.

You can:
- Search internal knowledge
- Use tools to fetch real data
- Ask clarification questions ONLY if required

You represent the company. Every answer has legal and financial impact."""
        
        # Construir el grafo
        self.graph = self._build_graph()
        self.app = self.graph.compile()
    
    def _register_tools(self):
        """Registra todas las tools disponibles."""
        # Order tool
        if "order_tool" in self.raw_tools:
            order_status_tool = self.tools_registry.create_order_status_tool(self.raw_tools["order_tool"])
            self.tools_registry.register_tool("get_order_status", order_status_tool)
        
        # Support tool
        if "support_tool" in self.raw_tools:
            return_policy_tool = self.tools_registry.create_return_policy_tool(self.raw_tools["support_tool"])
            self.tools_registry.register_tool("get_return_policy", return_policy_tool)
            
            ticket_tool = self.tools_registry.create_ticket_tool(self.raw_tools["support_tool"])
            self.tools_registry.register_tool("create_support_ticket", ticket_tool)
        
        # Catalog tool
        if "catalog_tool" in self.raw_tools:
            product_search_tool = self.tools_registry.create_product_search_tool(self.raw_tools["catalog_tool"])
            self.tools_registry.register_tool("search_products", product_search_tool)
        
        # Cart tool
        if "cart_tool" in self.raw_tools:
            cart_management_tool = self.tools_registry.create_cart_tool(self.raw_tools["cart_tool"])
            self.tools_registry.register_tool("manage_cart", cart_management_tool)
    
    def _build_graph(self) -> StateGraph:
        """Construye el grafo LangGraph completo."""
        workflow = StateGraph(CustomerServiceState)
        
        # ========== NODOS PRINCIPALES ==========
        workflow.add_node("classify_intent", self._classify_intent_node)
        workflow.add_node("decision", self._decision_node)
        workflow.add_node("apply_decision_policy", self._apply_decision_policy_node)
        
        # ========== NODOS DE INTENCIÓN (8 intenciones = 8 nodos) ==========
        workflow.add_node("pregunta_general", self._pregunta_general_node)
        workflow.add_node("consulta_productos", self._consulta_productos_node)
        workflow.add_node("soporte_tecnico", self._soporte_tecnico_node)
        workflow.add_node("tracking_envio", self._tracking_envio_node)
        workflow.add_node("devolucion_reclamo", self._devolucion_reclamo_node)
        workflow.add_node("compra_asistencia", self._compra_asistencia_node)
        workflow.add_node("conversacion_sentimiento_negativo", self._sentimiento_negativo_node)
        workflow.add_node("escalamiento_humano", self._escalamiento_humano_node)
        
        # ========== NODOS DE DECISIÓN Y ACCIÓN ==========
        workflow.add_node("ask_clarification", self._ask_clarification_node)
        workflow.add_node("react_reasoning", self._react_reasoning_node)
        workflow.add_node("validate_response", self._validate_response_node)
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.add_node("escalate_human", self._escalate_human_node)
        workflow.add_node("reject_response", self._reject_response_node)
        
        # ========== EDGES ==========
        workflow.set_entry_point("classify_intent")
        workflow.add_edge("classify_intent", "decision")
        
        # Decision → route por intención
        workflow.add_conditional_edges(
            "decision",
            self._route_by_intent,
            {
                "pregunta_general": "pregunta_general",
                "consulta_productos": "consulta_productos",
                "soporte_tecnico": "soporte_tecnico",
                "tracking_envio": "tracking_envio",
                "devolucion_reclamo": "devolucion_reclamo",
                "compra_asistencia": "compra_asistencia",
                "conversacion_sentimiento_negativo": "conversacion_sentimiento_negativo",
                "escalamiento_humano": "escalamiento_humano",
                "escalate": "escalate_human",
                "reject": "reject_response"
            }
        )
        
        # Todos los nodos de intención → apply_decision_policy
        intent_nodes = [
            "pregunta_general", "consulta_productos", "soporte_tecnico",
            "tracking_envio", "devolucion_reclamo", "compra_asistencia",
            "conversacion_sentimiento_negativo", "escalamiento_humano"
        ]
        for node in intent_nodes:
            workflow.add_edge(node, "apply_decision_policy")
        
        # apply_decision_policy → route por decision policy
        workflow.add_conditional_edges(
            "apply_decision_policy",
            self._route_by_decision_policy,
            {
                "respond": "react_reasoning",
                "ask_clarification": "ask_clarification",
                "escalate": "escalate_human",
                "reject": "reject_response"
            }
        )
        
        # react_reasoning → validate_response
        workflow.add_edge("react_reasoning", "validate_response")
        
        # validate_response → route según validación
        workflow.add_conditional_edges(
            "validate_response",
            self._route_after_validation,
            {
                "pass": "generate_response",
                "fail": "react_reasoning",  # Reintentar
                "escalate": "escalate_human"
            }
        )
        
        # ask_clarification → generate_response
        workflow.add_edge("ask_clarification", "generate_response")
        
        # Nodos finales → END
        workflow.add_edge("generate_response", END)
        workflow.add_edge("escalate_human", END)
        workflow.add_edge("reject_response", END)
        
        return workflow
    
    # ========== NODOS DE CLASIFICACIÓN Y DECISIÓN ==========
    
    def _classify_intent_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Clasifica la intención del mensaje."""
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None
        
        if not last_message or not hasattr(last_message, 'content'):
            return {"intent": "pregunta_general", "confidence": 0.5}
        
        user_message = last_message.content
        
        # Obtener historial relevante (resumido si es necesario)
        session_id = state.get("user_id", "unknown")
        relevant_history = self.memory_manager.get_relevant_history(
            messages[:-1] if len(messages) > 1 else [],
            session_id,
            max_messages=5
        )
        
        # Clasificar
        result = self.intent_classifier.classify(
            user_message,
            conversation_history=relevant_history
        )
        
        return {
            "intent": result["intent"],
            "confidence": result["confidence"],
            "decision_history": state.get("decision_history", []) + [{
                "step": "classify_intent",
                "intent": result["intent"],
                "confidence": result["confidence"],
                "timestamp": self._get_timestamp()
            }]
        }
    
    def _decision_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Nodo de decisión inicial."""
        return {
            "conversation_state": "processing"
        }
    
    def _apply_decision_policy_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Aplica la policy de decisión después de procesar la intención."""
        decision = self.decision_policy.decide(state)
        
        return {
            "decision_history": state.get("decision_history", []) + [{
                "step": "apply_decision_policy",
                "decision": decision,
                "confidence": state.get("confidence", 0.0),
                "intent": state.get("intent"),
                "timestamp": self._get_timestamp()
            }]
        }
    
    def _route_by_intent(self, state: CustomerServiceState) -> str:
        """Route según la intención clasificada."""
        intent = state.get("intent", "pregunta_general")
        escalation_flag = state.get("escalation_flag", False)
        
        if escalation_flag:
            return "escalate"
        
        valid_intents = [
            "pregunta_general", "consulta_productos", "soporte_tecnico",
            "tracking_envio", "devolucion_reclamo", "compra_asistencia",
            "conversacion_sentimiento_negativo", "escalamiento_humano"
        ]
        
        if intent not in valid_intents:
            return "pregunta_general"
        
        return intent
    
    def _route_by_decision_policy(self, state: CustomerServiceState) -> str:
        """Route según la policy de decisión."""
        return self.decision_policy.decide(state)
    
    def _route_after_validation(self, state: CustomerServiceState) -> str:
        """Route después de validar respuesta."""
        metadata = state.get("metadata", {})
        validation_result = metadata.get("validation_result", {})
        
        if not validation_result.get("valid", True):
            # Si falló validación múltiples veces, escalar
            validation_attempts = metadata.get("validation_attempts", 0)
            if validation_attempts >= 2:
                return "escalate"
            return "fail"
        
        return "pass"
    
    # ========== NODOS DE INTENCIÓN (IMPLEMENTACIÓN COMPLETA) ==========
    
    def _pregunta_general_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Procesa preguntas generales con RAG."""
        return self._process_with_rag(state, intent="pregunta_general")
    
    def _consulta_productos_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Procesa consultas de productos - usa tools + RAG."""
        messages = state.get("messages", [])
        last_message = messages[-1].content if messages else ""
        
        # Usar tool de catálogo
        products_found = []
        if "search_products" in self.tools_registry.get_all_tools():
            try:
                tool = self.tools_registry.get_tool("search_products")
                tool_result = tool.invoke({"query": last_message, "limit": 5})
                if tool_result:
                    try:
                        products_found = json.loads(tool_result) if isinstance(tool_result, str) else tool_result
                    except:
                        products_found = []
            except Exception as e:
                print(f"⚠️ Error usando search_products: {e}")
        
        # Actualizar metadata con productos
        metadata = state.get("metadata", {})
        metadata["products"] = products_found
        
        # Procesar con RAG
        result = self._process_with_rag(state, intent="consulta_productos")
        result["metadata"] = metadata
        
        return result
    
    def _soporte_tecnico_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Procesa soporte técnico - troubleshooting guiado."""
        messages = state.get("messages", [])
        last_message = messages[-1].content if messages else ""
        
        # Buscar en RAG documentos de troubleshooting
        result = self._process_with_rag(state, intent="soporte_tecnico")
        
        # Si no hay contexto suficiente, preparar para escalamiento
        if not result.get("retrieval_context"):
            metadata = state.get("metadata", {})
            metadata["troubleshooting_attempted"] = True
            result["metadata"] = metadata
            result["confidence"] = result.get("confidence", 1.0) * 0.6  # Reducir confianza
        
        return result
    
    def _tracking_envio_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Procesa tracking de envío - usa order_tool."""
        messages = state.get("messages", [])
        last_message = messages[-1].content if messages else ""
        
        # Extraer order_id
        order_ids = re.findall(r'\b[A-Z0-9]{5,}\b', last_message.upper())
        
        order_status = None
        if order_ids and "get_order_status" in self.tools_registry.get_all_tools():
            try:
                tool = self.tools_registry.get_tool("get_order_status")
                order_status = tool.invoke(order_ids[0])
                if isinstance(order_status, str):
                    try:
                        order_status = json.loads(order_status)
                    except:
                        pass
            except Exception as e:
                print(f"⚠️ Error usando get_order_status: {e}")
        
        # Actualizar metadata
        metadata = state.get("metadata", {})
        metadata["order_status"] = order_status
        metadata["order_id_extracted"] = order_ids[0] if order_ids else None
        
        # Procesar con RAG
        result = self._process_with_rag(state, intent="tracking_envio")
        result["metadata"] = metadata
        
        # Si no se encontró orden, reducir confianza
        if not order_status or (isinstance(order_status, dict) and order_status.get("status") == "unknown"):
            result["confidence"] = result.get("confidence", 1.0) * 0.5
        
        return result
    
    def _devolucion_reclamo_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Procesa devoluciones y reclamos - usa support_tool + RAG."""
        messages = state.get("messages", [])
        last_message = messages[-1].content if messages else ""
        
        # Consultar política de devolución
        return_policy = None
        if "get_return_policy" in self.tools_registry.get_all_tools():
            try:
                tool = self.tools_registry.get_tool("get_return_policy")
                return_policy = tool.invoke("")
            except Exception as e:
                print(f"⚠️ Error usando get_return_policy: {e}")
        
        # Actualizar metadata
        metadata = state.get("metadata", {})
        metadata["return_policy"] = return_policy
        
        # Procesar con RAG
        result = self._process_with_rag(state, intent="devolucion_reclamo")
        result["metadata"] = metadata
        
        return result
    
    def _compra_asistencia_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Procesa asistencia de compra - flujo secuencial con validación."""
        messages = state.get("messages", [])
        last_message = messages[-1].content if messages else ""
        
        # Obtener estado del carrito
        cart_state = None
        if "manage_cart" in self.tools_registry.get_all_tools():
            try:
                tool = self.tools_registry.get_tool("manage_cart")
                cart_result = tool.invoke({"action": "get"})
                if cart_result:
                    try:
                        cart_state = json.loads(cart_result) if isinstance(cart_result, str) else cart_result
                    except:
                        pass
            except Exception as e:
                print(f"⚠️ Error obteniendo carrito: {e}")
        
        # Actualizar metadata con estado de compra
        metadata = state.get("metadata", {})
        metadata["cart_state"] = cart_state
        metadata["purchase_flow_step"] = self._determine_purchase_step(last_message, cart_state)
        
        # Procesar con RAG
        result = self._process_with_rag(state, intent="compra_asistencia")
        result["metadata"] = metadata
        
        return result
    
    def _sentimiento_negativo_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Procesa sentimiento negativo - prepara escalamiento."""
        metadata = state.get("metadata", {})
        sentiment_score = metadata.get("sentiment_score", 0.5)
        
        return {
            "escalation_flag": True,
            "escalation_reason": f"Sentimiento negativo detectado (score: {sentiment_score:.2f})",
            "conversation_state": "escalating",
            "confidence": 0.3  # Baja confianza para forzar escalamiento
        }
    
    def _escalamiento_humano_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Procesa solicitud explícita de escalamiento humano."""
        return {
            "escalation_flag": True,
            "escalation_reason": "Solicitud explícita de atención humana",
            "conversation_state": "escalating"
        }
    
    # ========== NODOS DE DECISIÓN Y ACCIÓN ==========
    
    def _ask_clarification_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Pide aclaración al usuario."""
        messages = state.get("messages", [])
        last_message = messages[-1].content if messages else ""
        intent = state.get("intent", "pregunta_general")
        
        # Generar pregunta de aclaración específica según intención
        clarification_prompts = {
            "tracking_envio": "Necesito el número de orden para consultar el estado de tu envío. ¿Podrías proporcionarlo?",
            "devolucion_reclamo": "Para procesar tu devolución, necesito el número de orden y el motivo. ¿Podrías proporcionar esta información?",
            "consulta_productos": "¿Podrías ser más específico sobre qué producto buscas? (marca, modelo, características)",
            "compra_asistencia": "¿En qué paso del proceso de compra necesitas ayuda? (búsqueda, carrito, checkout, pago)",
        }
        
        if intent in clarification_prompts:
            clarification = clarification_prompts[intent]
        else:
            clarification_prompt = f"""El usuario preguntó: "{last_message}"

Necesitas más información para responder correctamente. Genera UNA pregunta de aclaración concisa y específica.

Ejemplo: "¿Podrías proporcionar el número de orden para poder ayudarte?\""""

            system_msg = SystemMessage(content=self.system_prompt)
            human_msg = HumanMessage(content=clarification_prompt)
            
            response = self.llm.invoke([system_msg, human_msg])
            clarification = response.content if hasattr(response, 'content') else str(response)
        
        # Actualizar metadata
        metadata = state.get("metadata", {})
        clarification_count = metadata.get("clarification_count", 0)
        metadata["clarification_count"] = clarification_count + 1
        
        return {
            "response_text": clarification,
            "conversation_state": "asking_clarification",
            "metadata": metadata
        }
    
    def _react_reasoning_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Nodo ReAct - Reasoning + Acting completo."""
        messages = state.get("messages", [])
        last_message = messages[-1].content if messages else ""
        intent = state.get("intent", "pregunta_general")
        retrieval_context = state.get("retrieval_context", [])
        
        # Obtener historial relevante
        session_id = state.get("user_id", "unknown")
        relevant_history = self.memory_manager.get_relevant_history(
            messages[:-1] if len(messages) > 1 else [],
            session_id,
            max_messages=5
        )
        
        # Construir contexto para ReAct
        context_text = ""
        if retrieval_context:
            context_text = "\n\n".join([
                f"[{i+1}] {doc.get('content', '')[:300]}"
                for i, doc in enumerate(retrieval_context[:3])
            ])
        
        # Ejecutar ReAct
        react_query = last_message
        if context_text:
            react_query = f"Contexto disponible:\n{context_text}\n\nPregunta: {last_message}"
        
        react_result = self.react_agent.reason_and_act(
            query=react_query,
            conversation_history=relevant_history,
            max_iterations=3
        )
        
        # Actualizar estado con resultado ReAct
        metadata = state.get("metadata", {})
        metadata["react_thoughts"] = react_result.get("thoughts", [])
        metadata["react_actions"] = react_result.get("actions_taken", [])
        metadata["react_observations"] = react_result.get("observations", [])
        
        # Preparar respuesta para validación
        response_text = react_result.get("final_answer", "")
        
        return {
            "response_text": response_text,
            "metadata": metadata,
            "conversation_state": "reasoning"
        }
    
    def _validate_response_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Valida la respuesta antes de enviarla."""
        response_text = state.get("response_text", "")
        retrieval_context = state.get("retrieval_context", [])
        messages = state.get("messages", [])
        last_message = messages[-1].content if messages else ""
        
        # Validar respuesta
        validation_result = self.response_validator.validate(
            response_text=response_text,
            context=retrieval_context,
            user_query=last_message
        )
        
        # Actualizar metadata
        metadata = state.get("metadata", {})
        validation_attempts = metadata.get("validation_attempts", 0)
        metadata["validation_attempts"] = validation_attempts + 1
        metadata["validation_result"] = validation_result
        
        # Si la validación falla múltiples veces, reducir confianza
        if not validation_result.get("valid", True):
            current_confidence = state.get("confidence", 1.0)
            new_confidence = current_confidence * 0.7
            return {
                "confidence": new_confidence,
                "metadata": metadata
            }
        
        return {
            "metadata": metadata
        }
    
    def _generate_response_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Genera la respuesta final."""
        response_text = state.get("response_text", "")
        
        # Si no hay respuesta, generar una
        if not response_text:
            messages = state.get("messages", [])
            retrieval_context = state.get("retrieval_context", [])
            last_message = messages[-1].content if messages else ""
            
            # Construir contexto RAG
            context_text = ""
            if retrieval_context:
                context_text = "\n\n".join([
                    f"[{i+1}] {doc.get('content', '')[:300]}"
                    for i, doc in enumerate(retrieval_context[:3])
                ])
                context_text = f"\n\nContexto de la empresa:\n{context_text}\n"
            
            # Construir prompt
            system_msg = SystemMessage(content=self.system_prompt)
            
            prompt_parts = []
            if context_text:
                prompt_parts.append(f"Contexto disponible:{context_text}")
            
            prompt_parts.append(f"Pregunta del usuario: {last_message}")
            prompt_parts.append("\nGenera una respuesta profesional, concisa y basada SOLO en el contexto proporcionado.")
            
            human_msg = HumanMessage(content="\n".join(prompt_parts))
            
            # Llamar LLM
            response = self.llm.invoke([system_msg, human_msg])
            response_text = response.content if hasattr(response, 'content') else str(response)
        
        # Actualizar memoria con resumen si es necesario
        session_id = state.get("user_id", "unknown")
        messages = state.get("messages", [])
        if len(messages) > self.memory_manager.SUMMARY_THRESHOLD:
            self.memory_manager.update_summary(session_id, messages, self.llm)
        
        return {
            "response_text": response_text,
            "conversation_state": "completed",
            "messages": add_messages(
                state.get("messages", []),
                [AIMessage(content=response_text)]
            )
        }
    
    def _escalate_human_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Escala a agente humano - PREPARA CONTEXTO COMPLETO."""
        reason = state.get("escalation_reason", "Requiere atención humana")
        
        # Preparar resumen completo para el humano
        context_summary = self._prepare_human_handoff_summary(state)
        
        # Crear ticket si support_tool está disponible
        ticket_id = None
        if "create_support_ticket" in self.tools_registry.get_all_tools():
            try:
                tool = self.tools_registry.get_tool("create_support_ticket")
                ticket_result = tool.invoke({
                    "subject": f"Handoff: {reason}",
                    "description": context_summary,
                    "priority": "high"
                })
                if ticket_result:
                    try:
                        ticket_data = json.loads(ticket_result) if isinstance(ticket_result, str) else ticket_result
                        ticket_id = ticket_data.get("ticket_id") or ticket_data.get("id")
                    except:
                        pass
            except Exception as e:
                print(f"⚠️ Error creando ticket: {e}")
        
        response_text = f"Entiendo que necesitas ayuda adicional. Un agente humano se pondrá en contacto contigo pronto.\n\n{reason}"
        if ticket_id:
            response_text += f"\n\nTicket #{ticket_id} creado."
        
        return {
            "response_text": response_text,
            "escalation_flag": True,
            "escalation_reason": reason,
            "conversation_state": "escalated",
            "metadata": {
                **state.get("metadata", {}),
                "human_handoff_summary": context_summary,
                "ticket_id": ticket_id
            }
        }
    
    def _reject_response_node(self, state: CustomerServiceState) -> Dict[str, Any]:
        """Rechaza responder por baja confianza."""
        response_text = "Lo siento, no tengo suficiente información para responder tu pregunta. Por favor, contacta con nuestro equipo de soporte para obtener ayuda."
        
        return {
            "response_text": response_text,
            "conversation_state": "rejected",
            "escalation_flag": True,
            "escalation_reason": "Baja confianza en respuesta"
        }
    
    # ========== HELPERS ==========
    
    def _process_with_rag(self, state: CustomerServiceState, intent: str) -> Dict[str, Any]:
        """Procesa con RAG según la intención."""
        messages = state.get("messages", [])
        last_message = messages[-1].content if messages else ""
        
        # Retrieval optimizado por intención
        retrieval_results = self.rag_retriever.retrieve(
            query=last_message,
            intent=intent,
            top_k=5,
            min_similarity=0.75
        )
        
        # Calcular confianza de retrieval
        retrieval_confidence = 0.0
        if retrieval_results:
            retrieval_confidence = max(doc.get("similarity", 0.0) for doc in retrieval_results)
        
        # Actualizar confidence del estado
        current_confidence = state.get("confidence", 0.0)
        final_confidence = min(current_confidence, retrieval_confidence) if retrieval_results else current_confidence * 0.7
        
        return {
            "retrieval_context": retrieval_results,
            "retrieval_confidence": retrieval_confidence,
            "confidence": final_confidence
        }
    
    def _prepare_human_handoff_summary(self, state: CustomerServiceState) -> str:
        """Prepara resumen completo para handoff humano."""
        messages = state.get("messages", [])
        intent = state.get("intent", "unknown")
        confidence = state.get("confidence", 0.0)
        metadata = state.get("metadata", {})
        
        summary_parts = [
            f"=== RESUMEN PARA HANDOFF HUMANO ===",
            f"Intención: {intent}",
            f"Confianza: {confidence:.2f}",
            f"Mensajes en conversación: {len(messages)}",
        ]
        
        if messages:
            last_message = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
            summary_parts.append(f"\nÚltimo mensaje del usuario: {last_message}")
        
        # Agregar información de tools usadas
        react_actions = metadata.get("react_actions", [])
        if react_actions:
            summary_parts.append(f"\nHerramientas usadas:")
            for action in react_actions:
                tool_name = action.get("tool", "unknown")
                summary_parts.append(f"  - {tool_name}")
        
        # Agregar contexto recuperado
        retrieval_context = state.get("retrieval_context", [])
        if retrieval_context:
            summary_parts.append(f"\nContexto recuperado: {len(retrieval_context)} documentos")
            for i, doc in enumerate(retrieval_context[:3], 1):
                summary_parts.append(f"  [{i}] {doc.get('content', '')[:150]}...")
        
        # Agregar decisiones tomadas
        decision_history = state.get("decision_history", [])
        if decision_history:
            summary_parts.append(f"\nDecisiones tomadas:")
            for decision in decision_history[-5:]:  # Últimas 5 decisiones
                step = decision.get("step", "unknown")
                decision_value = decision.get("decision") or decision.get("intent", "N/A")
                summary_parts.append(f"  - {step}: {decision_value}")
        
        return "\n".join(summary_parts)
    
    def _determine_purchase_step(self, message: str, cart_state: Dict[str, Any] = None) -> str:
        """Determina en qué paso del flujo de compra está el usuario."""
        message_lower = message.lower()
        
        # Detectar paso según palabras clave
        if any(word in message_lower for word in ["buscar", "producto", "catálogo", "tengo", "quiero"]):
            return "search"
        elif any(word in message_lower for word in ["carrito", "agregar", "añadir"]):
            return "cart"
        elif any(word in message_lower for word in ["checkout", "pagar", "comprar", "finalizar"]):
            return "checkout"
        elif any(word in message_lower for word in ["pago", "tarjeta", "paypal", "stripe"]):
            return "payment"
        elif cart_state and cart_state.get("items"):
            return "cart"
        else:
            return "search"
    
    def _get_timestamp(self) -> str:
        """Obtiene timestamp actual."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def invoke(self, initial_state: Dict[str, Any]) -> CustomerServiceState:
        """Invoca el grafo con el estado inicial."""
        # Convertir mensajes a formato correcto
        if "user_message" in initial_state:
            from langchain_core.messages import HumanMessage
            initial_state["messages"] = [HumanMessage(content=initial_state["user_message"])]
        
        # Asegurar campos requeridos
        state_dict = {
            "user_id": initial_state.get("user_id", "unknown"),
            "channel": initial_state.get("channel", "web"),
            "intent": None,
            "confidence": 1.0,
            "conversation_state": "init",
            "messages": initial_state.get("messages", []),
            "retrieval_context": [],
            "retrieval_confidence": 0.0,
            "escalation_flag": False,
            "escalation_reason": None,
            "decision_history": [],
            "response_text": None,
            "metadata": initial_state.get("metadata", {}),
            **initial_state
        }
        
        return self.app.invoke(state_dict)
