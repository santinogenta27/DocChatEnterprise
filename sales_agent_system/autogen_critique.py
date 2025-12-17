"""
Módulo AutoGen para crítica y auto-corrección de outputs de agentes.
Implementa el patrón de debate y mejora iterativa.
"""
from autogen import ConversableAgent, GroupChat, GroupChatManager
from autogen.llm_config import LLMConfig
from typing import Dict, List, Optional
import json


class SalesCritiqueSystem:
    """Sistema de crítica y auto-corrección usando AutoGen"""
    
    def __init__(self, llm_config: Optional[LLMConfig] = None):
        if llm_config is None:
            self.llm_config = LLMConfig(
                api_type="openai",
                model="gpt-4o-mini"
            )
        else:
            self.llm_config = llm_config
        
        self.critic_agent = self._create_critic_agent()
        self.optimizer_agent = self._create_optimizer_agent()
        self.validator_agent = self._create_validator_agent()
    
    def _create_critic_agent(self) -> ConversableAgent:
        """Agente crítico que identifica problemas"""
        return ConversableAgent(
            name="critic",
            system_message="""Eres un crítico experto de estrategias de ventas y marketing.
            Tu rol es identificar:
            1. Debilidades en análisis de datos
            2. Inconsistencias en recomendaciones
            3. Oportunidades perdidas
            4. Riesgos no considerados
            5. Falta de evidencia en afirmaciones
            
            Sé constructivo pero riguroso. Proporciona feedback específico y accionable.
            """,
            llm_config=self.llm_config,
            human_input_mode="NEVER"
        )
    
    def _create_optimizer_agent(self) -> ConversableAgent:
        """Agente que mejora basándose en crítica"""
        return ConversableAgent(
            name="optimizer",
            system_message="""Eres un optimizador de estrategias de ventas.
            Tu rol es:
            1. Tomar feedback del crítico
            2. Mejorar análisis y recomendaciones
            3. Corregir inconsistencias
            4. Agregar evidencia faltante
            5. Refinar estrategias para mayor impacto
            
            Siempre justifica tus mejoras con datos y mejores prácticas.
            """,
            llm_config=self.llm_config,
            human_input_mode="NEVER"
        )
    
    def _create_validator_agent(self) -> ConversableAgent:
        """Agente validador que verifica calidad final"""
        return ConversableAgent(
            name="validator",
            system_message="""Eres un validador de calidad de estrategias de ventas.
            Verifica que:
            1. Todas las recomendaciones sean accionables
            2. Los datos sean consistentes
            3. Las mejoras del optimizador sean válidas
            4. El resultado final sea de calidad producción
            5. No haya contradicciones
            
            Si encuentras problemas, solicita más iteraciones.
            Si todo está bien, aprueba el resultado.
            """,
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            is_termination_msg=lambda x: "APPROVED" in (x.get("content", "") or "").upper() or 
                                        "FINAL" in (x.get("content", "") or "").upper()
        )
    
    def critique_analysis(self, analysis_result: str, campaign_data: List[Dict]) -> Dict:
        """Critica un análisis de campañas"""
        prompt = f"""
Analiza y critica el siguiente análisis de campañas publicitarias:

ANÁLISIS A CRITICAR:
{analysis_result}

DATOS DE CAMPAÑAS:
{json.dumps(campaign_data, indent=2)}

Proporciona crítica constructiva identificando:
1. Debilidades en el análisis
2. Métricas o datos no considerados
3. Recomendaciones que faltan o son débiles
4. Inconsistencias lógicas
5. Oportunidades de mejora

Sé específico y proporciona ejemplos concretos.
"""
        
        critique_result = self.critic_agent.initiate_chat(
            recipient=self.critic_agent,
            message=prompt,
            max_turns=1
        )
        
        return {
            "critique": critique_result.chat_history[-1]["content"],
            "needs_improvement": True
        }
    
    def improve_based_on_critique(
        self, 
        original_analysis: str, 
        critique: str,
        campaign_data: List[Dict]
    ) -> Dict:
        """Mejora análisis basándose en crítica"""
        prompt = f"""
Mejora el siguiente análisis basándote en la crítica proporcionada:

ANÁLISIS ORIGINAL:
{original_analysis}

CRÍTICA RECIBIDA:
{critique}

DATOS DE CAMPAÑAS:
{json.dumps(campaign_data, indent=2)}

Proporciona una versión mejorada que:
1. Aborde todos los puntos de la crítica
2. Corrija inconsistencias identificadas
3. Agregue análisis faltante
4. Mejore recomendaciones débiles
5. Mantenga lo que estaba bien

Justifica cada mejora.
"""
        
        improved_result = self.optimizer_agent.initiate_chat(
            recipient=self.optimizer_agent,
            message=prompt,
            max_turns=1
        )
        
        return {
            "improved_analysis": improved_result.chat_history[-1]["content"],
            "improvements_made": True
        }
    
    def validate_final_output(
        self,
        analysis: str,
        optimization: str,
        creatives: str,
        campaign_data: List[Dict]
    ) -> Dict:
        """Valida el output final completo"""
        prompt = f"""
Valida la calidad del siguiente conjunto de outputs de estrategia de ventas:

ANÁLISIS:
{analysis}

OPTIMIZACIONES:
{optimization}

CREATIVOS:
{creatives}

DATOS DE CAMPAÑAS:
{json.dumps(campaign_data, indent=2)}

Verifica:
1. Consistencia entre todos los outputs
2. Accionabilidad de todas las recomendaciones
3. Calidad de producción
4. Ausencia de contradicciones
5. Completitud de la estrategia

Si todo está bien, responde con "APPROVED - Listo para producción"
Si hay problemas, identifícalos específicamente.
"""
        
        validation_result = self.validator_agent.initiate_chat(
            recipient=self.validator_agent,
            message=prompt,
            max_turns=1
        )
        
        validation_content = validation_result.chat_history[-1]["content"]
        is_approved = "APPROVED" in validation_content.upper()
        
        return {
            "validation": validation_content,
            "approved": is_approved,
            "ready_for_production": is_approved
        }
    
    def run_full_critique_cycle(
        self,
        analysis: str,
        optimization: str,
        creatives: str,
        campaign_data: List[Dict],
        max_iterations: int = 2
    ) -> Dict:
        """Ejecuta ciclo completo de crítica y mejora"""
        current_analysis = analysis
        current_optimization = optimization
        current_creatives = creatives
        
        iteration = 0
        all_critiques = []
        all_improvements = []
        
        while iteration < max_iterations:
            iteration += 1
            
            # Criticar análisis
            critique_result = self.critique_analysis(current_analysis, campaign_data)
            all_critiques.append(critique_result["critique"])
            
            # Mejorar basándose en crítica
            improvement_result = self.improve_based_on_critique(
                current_analysis,
                critique_result["critique"],
                campaign_data
            )
            current_analysis = improvement_result["improved_analysis"]
            all_improvements.append(improvement_result)
            
            # Validar
            validation = self.validate_final_output(
                current_analysis,
                current_optimization,
                current_creatives,
                campaign_data
            )
            
            if validation["approved"]:
                break
        
        return {
            "final_analysis": current_analysis,
            "final_optimization": current_optimization,
            "final_creatives": current_creatives,
            "critiques": all_critiques,
            "improvements": all_improvements,
            "final_validation": validation,
            "iterations": iteration,
            "approved": validation["approved"]
        }
    
    def run_group_chat_critique(
        self,
        analysis: str,
        optimization: str,
        creatives: str,
        campaign_data: List[Dict]
    ) -> Dict:
        """Ejecuta crítica usando GroupChat de AutoGen"""
        prompt = f"""
Revisa y mejora colaborativamente la siguiente estrategia de ventas:

ANÁLISIS:
{analysis}

OPTIMIZACIONES:
{optimization}

CREATIVOS:
{creatives}

DATOS:
{json.dumps(campaign_data, indent=2)}

Trabajen juntos para:
1. Identificar mejoras necesarias
2. Corregir problemas
3. Validar calidad final
4. Asegurar consistencia

Cuando estén satisfechos, el validador debe responder "APPROVED - Listo para producción"
"""
        
        groupchat = GroupChat(
            agents=[self.critic_agent, self.optimizer_agent, self.validator_agent],
            messages=[],
            max_round=6,
            speaker_selection_method="auto"
        )
        
        manager = GroupChatManager(
            name="critique_manager",
            groupchat=groupchat,
            llm_config=self.llm_config
        )
        
        result = self.critic_agent.initiate_chat(
            recipient=manager,
            message=prompt,
            max_turns=6,
            summary_method="reflection_with_llm"
        )
        
        return {
            "group_chat_result": result.summary,
            "chat_history": result.chat_history,
            "approved": "APPROVED" in result.summary.upper() if result.summary else False
        }






