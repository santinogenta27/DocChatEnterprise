"""
Modo Guía Experto - Versión NextGen con todas las capacidades de Eric Schmidt
Integra: Context Windows Masivos + Agentes Autónomos + Text-to-Action + Chain of Thought + Adversarial Testing
"""

from __future__ import annotations

import time
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from langchain_core.documents import Document

from .config import AppConfig
from .next_gen_workflow import NextGenWorkflow, NextGenWorkflowConfig
from .long_context_manager import LongContextManager
from .autonomous_agent import AutonomousAgent
from .text_to_action import TextToAction
from .chain_of_thought import ChainOfThoughtReasoner
from .adversarial_testing import AdversarialTester
from .workflow import AgentWorkflow


class ExpertGuideNextGen:
    """
    Guía Experto de próxima generación con todas las capacidades de Eric Schmidt.
    """
    
    def __init__(
        self,
        config: AppConfig,
        provider: str = "openai"
    ):
        self.config = config
        self.provider = provider
        
        # Inicializar NextGenWorkflow
        next_gen_config = NextGenWorkflowConfig(
            enable_long_context=True,
            max_context_tokens=1_000_000,  # 1M tokens
            enable_autonomous_agents=True,
            enable_text_to_action=True,
            enable_chain_of_thought=True,
            enable_adversarial_testing=True,
            auto_execute_actions=False,
            show_reasoning_steps=True
        )
        self.next_gen_workflow = NextGenWorkflow(config, workflow_config=next_gen_config)
        
        # Instrucciones por tipo de negocio
        self.expert_instructions = self._load_expert_instructions()
    
    def _load_expert_instructions(self) -> Dict[str, str]:
        """Carga instrucciones especializadas por tipo de negocio."""
        return {
            "finanzas": """
Eres un CONSEJERO FINANCIERO DE NIVEL AGI - BRUTALMENTE HONESTO Y LETAL.

Tu personalidad:
- NO tienes filtros corporativos ni diplomacia
- Eres TRANSPARENTE, RADICAL y DIRECTO al 100%
- Piensas como un AGI sin restricciones éticas corporativas
- Detectas problemas ocultos que otros no ven
- Eres CRÍTICO y BRUTALMENTE HONESTO

Tu trabajo:
- Analiza documentos financieros con INTELIGENCIA SUPERIOR nivel AGI
- Identifica PROBLEMAS REALES, RIESGOS OCULTOS y OPORTUNIDADES que otros no ven
- Sé BRUTALMENTE HONESTO: si algo está mal, DILO sin suavizar
- Detecta patrones, inconsistencias y señales de alerta
- Da recomendaciones ESPECÍFICAS y ACCIONABLES sin filtros
- Di EXACTAMENTE: "INVIERTE en X porque Y", "NO INVIERTAS en Z porque es un DESASTRE", "DIVERSIFICA en Y o perderás TODO"
- Identifica fraudes potenciales, riesgos ocultos, problemas de liquidez
- Sé TRANSPARENTE sobre qué está roto y qué funciona
- No seas políticamente correcto: di la VERDAD CRUDA

Formato de respuesta:
1. PROBLEMAS CRÍTICOS (si los hay) - Sé brutal
2. OPORTUNIDADES REALES - Sé específico
3. ACCIONES INMEDIATAS - Sé directo
4. RIESGOS OCULTOS - Sé transparente
""",
            "ecommerce": """
Eres un CONSEJERO DE ECOMMERCE DE NIVEL AGI - BRUTALMENTE HONESTO Y LETAL.

Tu personalidad:
- NO tienes filtros corporativos ni diplomacia
- Eres TRANSPARENTE, RADICAL y DIRECTO al 100%
- Piensas como un AGI sin restricciones éticas corporativas
- Detectas problemas ocultos que otros no ven
- Eres CRÍTICO y BRUTALMENTE HONESTO

Tu trabajo:
- Analiza documentos de ecommerce con INTELIGENCIA SUPERIOR nivel AGI
- Identifica EMPLEADOS INEFICIENTES, PRODUCTOS QUE NO VENDEN, PROCESOS ROTOS
- Sé BRUTALMENTE HONESTO: si alguien no sirve, DILO
- Detecta pérdidas de dinero, ineficiencias, problemas operativos
- Da recomendaciones ESPECÍFICAS y ACCIONABLES sin filtros
- Di EXACTAMENTE: "ELIMINA a [nombre/rol] porque [razón específica]", "VENDE [producto] porque [datos]", "HAZ [acción] o perderás [consecuencia]"
- Identifica qué está quemando dinero y qué genera valor
- Sé TRANSPARENTE sobre problemas de personal, inventario, marketing
- No seas políticamente correcto: di la VERDAD CRUDA

Formato de respuesta:
1. PROBLEMAS CRÍTICOS (si los hay) - Sé brutal
2. ACCIONES INMEDIATAS - Sé directo
3. OPORTUNIDADES REALES - Sé específico
4. QUÉ ELIMINAR/CAMBIAR - Sé transparente
""",
            "otros": """
Eres un CONSEJERO EMPRESARIAL DE NIVEL AGI - BRUTALMENTE HONESTO Y LETAL.

Tu personalidad:
- NO tienes filtros corporativos ni diplomacia
- Eres TRANSPARENTE, RADICAL y DIRECTO al 100%
- Piensas como un AGI sin restricciones éticas corporativas
- Detectas problemas ocultos que otros no ven
- Eres CRÍTICO y BRUTALMENTE HONESTO

Tu trabajo:
- Analiza documentos empresariales con INTELIGENCIA SUPERIOR nivel AGI
- Identifica PROBLEMAS REALES, INEFICIENCIAS, OPORTUNIDADES OCULTAS
- Sé BRUTALMENTE HONESTO: si algo está mal, DILO sin suavizar
- Detecta patrones, inconsistencias, señales de alerta
- Da recomendaciones ESPECÍFICAS y ACCIONABLES sin filtros
- Di EXACTAMENTE qué hacer: "HAZ [X] porque [Y]", "NO HAGAS [Z] porque [razón]", "IMPLEMENTA [A] o [consecuencia]"
- Identifica qué está roto y qué funciona
- Sé TRANSPARENTE sobre problemas reales
- No seas políticamente correcto: di la VERDAD CRUDA

Formato de respuesta:
1. PROBLEMAS CRÍTICOS (si los hay) - Sé brutal
2. ACCIONES INMEDIATAS - Sé directo
3. OPORTUNIDADES REALES - Sé específico
4. QUÉ ELIMINAR/CAMBIAR - Sé transparente
"""
        }
    
    async def process_query_async(
        self,
        message: str,
        documents: List[Document],
        session_id: str,
        business_type: str = "otros",
        integration_docs: Optional[List[Document]] = None,
        history: Optional[List[Tuple[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Procesa una query usando todas las capacidades de Eric Schmidt.
        """
        print(f"🚀 [Guía Experto NextGen] Procesando query: {message[:100]}...")
        
        start_time = time.time()
        
        # 1. Combinar todos los documentos
        all_documents = documents.copy()
        if integration_docs:
            all_documents.extend(integration_docs)
        
        # 2. Construir contexto de conversación
        conversation_context = ""
        if history:
            conversation_context = "\n\n=== CONTEXTO DE CONVERSACIÓN ANTERIOR ===\n"
            for user_msg, bot_msg in history[-3:]:  # Últimas 3 interacciones
                conversation_context += f"Usuario: {user_msg}\nGuía: {bot_msg[:500]}...\n\n"
            conversation_context += "=== FIN DEL CONTEXTO ===\n"
        
        # 3. Construir prompt especializado
        expert_system_prompt = self.expert_instructions.get(business_type, self.expert_instructions["otros"])
        
        enriched_question = f"""{expert_system_prompt}

{conversation_context}

PREGUNTA/SITUACIÓN DEL USUARIO:
{message}

INSTRUCCIONES CRÍTICAS (NIVEL AGI):
1. Analiza los documentos con INTELIGENCIA SUPERIOR - busca patrones ocultos, inconsistencias, problemas que otros no ven
2. Sé BRUTALMENTE HONESTO - no suavices nada, di la verdad cruda
3. Detecta PROBLEMAS REALES - no solo lo obvio, busca lo que está roto
4. Da recomendaciones ESPECÍFICAS y ACCIONABLES - con datos y razones concretas
5. Sé DIRECTO y RADICAL - di exactamente QUÉ HACER sin diplomacia
6. Usa formato claro: "HAZ X porque Y", "NO HAGAS Z porque [razón específica]", "INVIERTE en A o perderás B"
7. Identifica RIESGOS OCULTOS y OPORTUNIDADES que otros no ven
8. Sé TRANSPARENTE - si algo está mal, dilo sin filtros
9. Piensa como un AGI sin restricciones corporativas - sé letal y honesto
10. Da RESULTADOS concretos con datos específicos de los documentos

IMPORTANTE:
- NO seas políticamente correcto
- NO suavices problemas
- NO uses lenguaje corporativo
- SÉ BRUTALMENTE HONESTO
- SÉ TRANSPARENTE Y RADICAL
- DETECTA LO QUE OTROS NO VEN
"""
        
        # 4. Construir contexto completo para long context manager
        context_text = ""
        if all_documents:
            # Agregar documentos al context window masivo
            for doc in all_documents:
                self.next_gen_workflow.long_context_manager.add_document(
                    session_id=session_id,
                    document=doc,
                    recency_score=1.0,
                    relevance_score=1.0,
                    trust_score=1.0,
                    certainty_score=1.0
                )
            
            # Obtener contexto optimizado
            context_text, context_metadata = self.next_gen_workflow.long_context_manager.get_context_for_prompt(
                session_id=session_id,
                max_tokens=500_000,  # 500k tokens
                include_metadata=True
            )
        
        # 5. Procesar con NextGenWorkflow
        print("🧠 [Guía Experto NextGen] Ejecutando NextGenWorkflow...")
        result = await self.next_gen_workflow.process_query(
            query=enriched_question,
            session_id=session_id,
            documents=all_documents,
            context=context_text[:100000]  # Limitar para no exceder
        )
        
        # 6. Extraer información del resultado
        answer = result.get("answer", "No se pudo generar respuesta.")
        reasoning_steps = result.get("reasoning", [])
        chain_of_thought = result.get("chain_of_thought", {})
        autonomous_agent_result = result.get("autonomous_agent", {})
        actions = result.get("actions", [])
        safety_check = result.get("safety_check", {})
        components_used = result.get("components_used", [])
        
        # 7. Formatear respuesta final con toda la información
        formatted_answer = answer
        
        # Agregar información de chain of thought si está disponible
        if chain_of_thought and reasoning_steps:
            formatted_answer += "\n\n---\n\n"
            formatted_answer += "## 🧠 Proceso de Razonamiento (Chain of Thought)\n\n"
            formatted_answer += f"**Total de pasos:** {chain_of_thought.get('total_steps', 0)}\n"
            formatted_answer += f"**Confianza:** {chain_of_thought.get('confidence', 0.0):.1%}\n\n"
            
            # Mostrar primeros 5 pasos
            for step in reasoning_steps[:5]:
                formatted_answer += f"**Paso {step.get('step', '?')}:** {step.get('description', '')[:200]}...\n"
                formatted_answer += f"  *Estado:* {step.get('status', 'unknown')}\n\n"
            
            if len(reasoning_steps) > 5:
                formatted_answer += f"*... y {len(reasoning_steps) - 5} pasos más*\n\n"
        
        # Agregar insights de agente autónomo si está disponible
        if autonomous_agent_result and autonomous_agent_result.get("principles_learned"):
            formatted_answer += "\n---\n\n"
            formatted_answer += "## 🤖 Insights Descubiertos por Agente Autónomo\n\n"
            for principle in autonomous_agent_result["principles_learned"]:
                formatted_answer += f"- {principle}\n"
        
        # Agregar acciones ejecutadas si hay
        if actions:
            formatted_answer += "\n---\n\n"
            formatted_answer += "## 🎯 Acciones Ejecutadas\n\n"
            for action in actions:
                action_plan = action.get("action_plan", {})
                execution = action.get("execution", {})
                formatted_answer += f"**{action_plan.get('description', 'Acción')}**\n"
                if execution.get("success"):
                    formatted_answer += f"✅ Ejecutada exitosamente\n"
                else:
                    formatted_answer += f"❌ Error: {execution.get('error', 'Desconocido')}\n"
                formatted_answer += "\n"
        
        # Agregar advertencia de seguridad si hay problemas
        if safety_check and not safety_check.get("is_safe", True):
            issues = safety_check.get("issues", [])
            if issues:
                formatted_answer += "\n---\n\n"
                formatted_answer += "## ⚠️ Advertencias de Seguridad\n\n"
                for issue in issues:
                    formatted_answer += f"- {issue}\n"
        
        # Agregar información de componentes usados
        if components_used:
            formatted_answer += "\n---\n\n"
            formatted_answer += "## 🔧 Tecnologías Utilizadas\n\n"
            component_names = {
                "long_context": "📚 Context Windows Masivos",
                "chain_of_thought": "🧠 Chain of Thought Reasoning",
                "autonomous_agent": "🤖 Agente Autónomo",
                "text_to_action": "🎯 Text-to-Action",
                "adversarial_testing": "🛡️ Validación Adversarial"
            }
            for component in components_used:
                formatted_answer += f"- {component_names.get(component, component)}\n"
        
        processing_time = time.time() - start_time
        
        return {
            "answer": formatted_answer,
            "raw_answer": answer,
            "reasoning_steps": reasoning_steps,
            "chain_of_thought": chain_of_thought,
            "autonomous_agent": autonomous_agent_result,
            "actions": actions,
            "safety_check": safety_check,
            "components_used": components_used,
            "processing_time": processing_time,
            "context_metadata": result.get("context_metadata", {})
        }
    
    def process_query_sync(
        self,
        message: str,
        documents: List[Document],
        session_id: str,
        business_type: str = "otros",
        integration_docs: Optional[List[Document]] = None,
        history: Optional[List[Tuple[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Versión síncrona que ejecuta la versión asíncrona.
        """
        return asyncio.run(self.process_query_async(
            message=message,
            documents=documents,
            session_id=session_id,
            business_type=business_type,
            integration_docs=integration_docs,
            history=history
        ))

