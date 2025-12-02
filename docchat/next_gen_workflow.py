"""
Next Generation Workflow - Integra todas las capacidades de Eric Schmidt
Combina: Context Windows Masivos + Agentes Autónomos + Text-to-Action + Chain of Thought + Adversarial Testing
"""

from __future__ import annotations

import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel

from .config import AppConfig
from .long_context_manager import LongContextManager, ContextChunk
from .autonomous_agent import AutonomousAgent, Hypothesis
from .text_to_action import TextToAction, ActionPlan, ActionResult
from .chain_of_thought import ChainOfThoughtReasoner, ThoughtChain
from .adversarial_testing import AdversarialTester, TestResult


@dataclass
class NextGenWorkflowConfig:
    """Configuración del workflow de próxima generación."""
    enable_long_context: bool = True
    max_context_tokens: int = 1_000_000
    enable_autonomous_agents: bool = True
    enable_text_to_action: bool = True
    enable_chain_of_thought: bool = True
    enable_adversarial_testing: bool = True
    auto_execute_actions: bool = False
    show_reasoning_steps: bool = True


class NextGenWorkflow:
    """
    Workflow de próxima generación que integra todas las capacidades:
    - Context windows masivos
    - Agentes autónomos que aprenden
    - Text-to-action
    - Chain of thought reasoning
    - Adversarial testing
    """
    
    def __init__(
        self,
        config: AppConfig,
        workflow_config: Optional[NextGenWorkflowConfig] = None,
        llm: Optional[BaseLanguageModel] = None
    ):
        self.config = config
        self.workflow_config = workflow_config or NextGenWorkflowConfig()
        self.llm = llm
        
        # Inicializar componentes según configuración
        self.long_context_manager: Optional[LongContextManager] = None
        if self.workflow_config.enable_long_context:
            self.long_context_manager = LongContextManager(
                config=config,
                llm=llm,
                max_short_term_tokens=self.workflow_config.max_context_tokens
            )
        
        self.autonomous_agent: Optional[AutonomousAgent] = None
        if self.workflow_config.enable_autonomous_agents:
            self.autonomous_agent = AutonomousAgent(
                agent_id="next_gen_agent",
                config=config,
                llm=llm,
                context_manager=self.long_context_manager
            )
        
        self.text_to_action: Optional[TextToAction] = None
        if self.workflow_config.enable_text_to_action:
            self.text_to_action = TextToAction(
                config=config,
                llm=llm,
                sandbox_enabled=True
            )
        
        self.chain_of_thought: Optional[ChainOfThoughtReasoner] = None
        if self.workflow_config.enable_chain_of_thought:
            self.chain_of_thought = ChainOfThoughtReasoner(
                config=config,
                llm=llm
            )
        
        self.adversarial_tester: Optional[AdversarialTester] = None
        if self.workflow_config.enable_adversarial_testing:
            self.adversarial_tester = AdversarialTester(
                config=config,
                llm=llm
            )
    
    async def process_query(
        self,
        query: str,
        session_id: str,
        documents: Optional[List[Document]] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Procesa una query usando todas las capacidades integradas.
        """
        print(f"🚀 [NextGen] Procesando query: {query[:100]}...")
        
        result = {
            "query": query,
            "session_id": session_id,
            "timestamp": time.time(),
            "components_used": [],
            "answer": None,
            "reasoning": None,
            "actions": [],
            "safety_check": None
        }
        
        # 1. Agregar documentos al context window si hay
        if documents and self.long_context_manager:
            print("📚 [NextGen] Agregando documentos al context window...")
            for doc in documents:
                self.long_context_manager.add_document(
                    session_id=session_id,
                    document=doc,
                    recency_score=1.0,
                    relevance_score=1.0
                )
            result["components_used"].append("long_context")
        
        # 2. Agregar contexto adicional si hay
        if context and self.long_context_manager:
            self.long_context_manager.add_text(
                session_id=session_id,
                text=context,
                source="additional_context",
                recency_score=1.0
            )
        
        # 3. Obtener contexto para el prompt
        context_text = ""
        if self.long_context_manager:
            context_text, metadata = self.long_context_manager.get_context_for_prompt(
                session_id=session_id,
                max_tokens=500_000  # 500k tokens para el prompt
            )
            result["context_metadata"] = metadata
        
        # 4. Usar Chain of Thought si está habilitado
        if self.workflow_config.enable_chain_of_thought and self.chain_of_thought:
            print("🧠 [NextGen] Ejecutando Chain of Thought reasoning...")
            full_query = f"{query}\n\nContexto disponible:\n{context_text[:100000]}"  # Limitar contexto
            # Crear cadena y agregar pasos
            chain_id = self.chain_of_thought.create_chain(full_query)
            await self.chain_of_thought.add_reasoning_steps(chain_id, context_text[:50000])
            chain = self.chain_of_thought.get_chain(chain_id)
            
            if chain:
                result["chain_of_thought"] = {
                    "chain_id": chain.chain_id,
                    "total_steps": len(chain.steps),
                    "final_answer": chain.final_answer or "En proceso...",
                    "status": chain.status
                }
                
                # Si no hay respuesta final, generarla basada en los pasos y el contexto
                if not chain.final_answer or len(chain.final_answer.strip()) < 50:
                    print("📝 [NextGen] Generando respuesta final desde pasos de razonamiento...")
                    if self.llm and chain.steps:
                        try:
                            # Construir resumen de pasos
                            steps_summary = "\n".join([
                                f"Paso {i+1} ({s.step_type.value}): {s.content}\nRazonamiento: {s.reasoning}"
                                for i, s in enumerate(chain.steps)
                            ])
                            
                            # Generar respuesta final completa
                            from langchain_core.prompts import ChatPromptTemplate
                            final_answer_prompt = ChatPromptTemplate.from_messages([
                                ("system", """Eres un experto que genera respuestas completas y útiles basadas en razonamiento paso a paso.

Genera una respuesta completa, detallada y útil que responda completamente a la pregunta del usuario.
Usa toda la información de los pasos de razonamiento y el contexto proporcionado.

La respuesta debe ser:
- Completa y detallada (mínimo 500 palabras)
- Basada en el razonamiento paso a paso
- Útil y accionable
- Bien estructurada y clara"""),
                                ("human", """Pregunta original: {query}

Pasos de razonamiento:
{steps_summary}

Contexto disponible:
{context}

Genera una respuesta completa y detallada que responda completamente a la pregunta."""),
                            ])
                            
                            final_chain = final_answer_prompt | self.llm
                            final_response = await final_chain.ainvoke({
                                "query": query,
                                "steps_summary": steps_summary,
                                "context": context_text[:30000]
                            })
                            
                            final_answer = final_response.content if hasattr(final_response, 'content') else str(final_response)
                            
                            # Completar la cadena con la respuesta final
                            self.chain_of_thought.complete_chain(chain_id, final_answer, success=True)
                            result["answer"] = final_answer
                            chain.final_answer = final_answer
                        except Exception as e:
                            print(f"⚠️ [NextGen] Error generando respuesta final: {e}")
                            # Fallback: usar el contenido de los pasos
                            if chain.steps:
                                result["answer"] = "\n\n".join([
                                    f"**{s.step_type.value.upper()}**: {s.content}\n\n{s.reasoning}"
                                    for s in chain.steps
                                ])
                else:
                    result["answer"] = chain.final_answer
                
                # Agregar información de razonamiento
                if chain.steps:
                    result["reasoning"] = [
                        {
                            "step": i + 1,
                            "step_id": s.step_id,
                            "step_type": s.step_type.value if hasattr(s.step_type, 'value') else str(s.step_type),
                            "content": s.content if s.content else "...",
                            "reasoning": s.reasoning if s.reasoning else "...",
                            "confidence": s.confidence
                        }
                        for i, s in enumerate(chain.steps)
                    ]
                else:
                    result["reasoning"] = []
                    
            result["components_used"].append("chain_of_thought")
        
        # 5. Detectar si la query requiere acción (text-to-action)
        requires_action = any(keyword in query.lower() for keyword in [
            "crea", "crear", "envía", "enviar", "genera", "generar",
            "ejecuta", "ejecutar", "haz", "hacer", "construye", "construir",
            "create", "send", "generate", "execute", "build", "make"
        ])
        
        if requires_action and self.text_to_action:
            print("🎯 [NextGen] Detectada necesidad de acción, generando plan...")
            try:
                action_result = await self.text_to_action.process_command(
                    command=query,
                    auto_execute=self.workflow_config.auto_execute_actions
                )
                result["actions"] = [action_result]
                result["components_used"].append("text_to_action")
            except Exception as e:
                print(f"⚠️ [NextGen] Error en text-to-action: {e}")
        
        # 6. Usar agente autónomo si la query requiere descubrimiento
        requires_discovery = any(keyword in query.lower() for keyword in [
            "descubre", "descubrir", "patrones", "principios", "insights",
            "analiza", "analizar", "encuentra", "encontrar",
            "discover", "patterns", "principles", "analyze", "find"
        ])
        
        if requires_discovery and self.autonomous_agent:
            print("🤖 [NextGen] Ejecutando agente autónomo para descubrimiento...")
            try:
                discovery_input = f"{query}\n\nContexto:\n{context_text[:50000]}"
                agent_result = await self.autonomous_agent.run_full_cycle(discovery_input)
                result["autonomous_agent"] = agent_result
                result["components_used"].append("autonomous_agent")
                
                # Si el agente generó insights, agregarlos a la respuesta
                if agent_result.get("principles_learned"):
                    if result["answer"]:
                        result["answer"] += f"\n\nInsights descubiertos:\n" + "\n".join(
                            f"- {p}" for p in agent_result["principles_learned"]
                        )
                    else:
                        result["answer"] = "Insights descubiertos:\n" + "\n".join(
                            f"- {p}" for p in agent_result["principles_learned"]
                        )
            except Exception as e:
                print(f"⚠️ [NextGen] Error en agente autónomo: {e}")
        
        # 7. Validación adversarial antes de retornar
        if result["answer"] and self.adversarial_tester:
            print("🛡️ [NextGen] Validando respuesta con adversarial testing...")
            try:
                is_safe, issues = await self.adversarial_tester.validate_response_before_sending(
                    response=result["answer"],
                    original_prompt=query
                )
                result["safety_check"] = {
                    "is_safe": is_safe,
                    "issues": issues
                }
                result["components_used"].append("adversarial_testing")
                
                if not is_safe and issues:
                    result["answer"] += f"\n\n⚠️ Advertencia: Se detectaron posibles problemas de seguridad."
            except Exception as e:
                print(f"⚠️ [NextGen] Error en adversarial testing: {e}")
        
        # 8. Si no hay respuesta aún o es muy corta, generar una completa
        if not result["answer"] or len(result["answer"].strip()) < 100:
            # Usar LLM para generar respuesta completa y detallada
            if self.llm:
                try:
                    print("📝 [NextGen] Generando respuesta completa desde contexto...")
                    from langchain_core.prompts import ChatPromptTemplate
                    
                    answer_prompt = ChatPromptTemplate.from_messages([
                        ("system", """Eres un experto que genera respuestas completas, detalladas y útiles.

Genera una respuesta completa que responda completamente a la pregunta del usuario.
La respuesta debe ser:
- Completa y detallada (mínimo 500 palabras si es posible)
- Basada en el contexto proporcionado
- Útil y accionable
- Bien estructurada y clara
- Profesional y precisa"""),
                        ("human", """Pregunta: {query}

Contexto disponible:
{context}

Genera una respuesta completa, detallada y útil que responda completamente a la pregunta.
Si el contexto no contiene información suficiente, indica qué información adicional sería necesaria."""),
                    ])
                    
                    answer_chain = answer_prompt | self.llm
                    response = await answer_chain.ainvoke({
                        "query": query,
                        "context": context_text[:50000] if context_text else "No hay contexto disponible."
                    })
                    
                    generated_answer = response.content if hasattr(response, 'content') else str(response)
                    
                    # Si la respuesta generada es mejor que la existente, usarla
                    if not result["answer"] or len(generated_answer) > len(result["answer"]):
                        result["answer"] = generated_answer
                except Exception as e:
                    print(f"⚠️ [NextGen] Error generando respuesta: {e}")
                    if not result["answer"]:
                        result["answer"] = f"Error al generar respuesta: {e}"
            else:
                if not result["answer"]:
                    result["answer"] = "No se pudo generar respuesta (LLM no disponible)"
        
        result["processing_time"] = time.time() - result["timestamp"]
        
        print(f"✅ [NextGen] Procesamiento completado en {result['processing_time']:.2f}s")
        
        return result
    
    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Obtiene el contexto de una sesión."""
        if not self.long_context_manager:
            return {}
        
        context_text, metadata = self.long_context_manager.get_context_for_prompt(
            session_id=session_id,
            include_metadata=True
        )
        
        return {
            "context_text": context_text[:1000],  # Primeros 1000 caracteres
            "metadata": metadata,
            "stats": self.long_context_manager.get_stats()
        }
    
    def clear_session(self, session_id: str):
        """Limpia el contexto de una sesión."""
        if self.long_context_manager:
            self.long_context_manager.clear_session(session_id)

