"""
Sistema principal de ventas con agentes AI.
Integra LangGraph, CrewAI, AutoGen y BeeAI para optimización de campañas publicitarias.
"""
from typing import Dict, Optional
from .langgraph_workflow import SalesWorkflowOrchestrator
from .crewai_agents import SalesAgentsCrew
from .autogen_critique import SalesCritiqueSystem
from .api_stubs import AdsAPIStub
import json


class SalesAgentSystem:
    """
    Sistema completo de agentes AI para ventas.
    
    Combina:
    - LangGraph: Orquestación y workflow
    - CrewAI: Agentes especializados
    - AutoGen: Crítica y auto-corrección
    - APIs: Integración con plataformas de publicidad
    """
    
    def __init__(
        self,
        langgraph_model: str = "gpt-4o-mini",
        crewai_model: str = "watsonx/ibm/granite-3-3-8b-instruct",
        autogen_model: str = "gpt-4o-mini"
    ):
        """Inicializa el sistema completo"""
        # LangGraph orchestrator
        self.langgraph_orchestrator = SalesWorkflowOrchestrator(llm_model=langgraph_model)
        
        # CrewAI agents
        self.crewai_crew = SalesAgentsCrew(llm_model=crewai_model)
        
        # AutoGen critique system
        from autogen.llm_config import LLMConfig
        autogen_llm_config = LLMConfig(
            api_type="openai",
            model=autogen_model
        )
        self.autogen_critique = SalesCritiqueSystem(llm_config=autogen_llm_config)
        
        # APIs
        self.ads_api = AdsAPIStub()
    
    def run_complete_analysis(self, user_query: str) -> Dict:
        """
        Ejecuta análisis completo usando todos los componentes.
        
        Flujo:
        1. LangGraph: Orquesta el workflow principal
        2. CrewAI: Agentes especializados generan análisis detallado
        3. AutoGen: Sistema de crítica mejora los outputs
        4. Integración: Combina todo en reporte final
        """
        print("🚀 Iniciando sistema de agentes AI para ventas...")
        print(f"📝 Consulta: {user_query}\n")
        
        # Paso 1: Obtener datos de campañas
        print("📊 Paso 1: Obteniendo datos de campañas...")
        campaigns = self.ads_api.get_campaigns("account_123")
        campaign_data = []
        
        for camp in campaigns:
            perf = self.ads_api.get_campaign_performance(
                camp["campaign_id"],
                (None, None)
            )
            campaign_data.append({**camp, **perf})
        
        print(f"✅ Obtenidas {len(campaign_data)} campañas\n")
        
        # Paso 2: Ejecutar workflow LangGraph
        print("🔄 Paso 2: Ejecutando workflow LangGraph...")
        langgraph_result = self.langgraph_orchestrator.run(user_query)
        print("✅ Workflow LangGraph completado\n")
        
        # Paso 3: Ejecutar análisis con CrewAI
        print("👥 Paso 3: Ejecutando análisis con agentes CrewAI...")
        crewai_result = self.crewai_crew.run_complete_analysis(user_query)
        print("✅ Análisis CrewAI completado\n")
        
        # Paso 4: Crítica y mejora con AutoGen
        print("🔍 Paso 4: Ejecutando crítica y mejora con AutoGen...")
        
        # Extraer resultados de CrewAI
        analysis_text = str(crewai_result.get("result", {}).get("raw", ""))
        optimization_text = ""  # Se extraería del resultado real
        creatives_text = ""  # Se extraería del resultado real
        
        # Ejecutar crítica
        critique_result = self.autogen_critique.run_full_critique_cycle(
            analysis=analysis_text,
            optimization=optimization_text,
            creatives=creatives_text,
            campaign_data=campaign_data,
            max_iterations=2
        )
        print("✅ Crítica AutoGen completada\n")
        
        # Paso 5: Compilar resultado final
        print("📋 Paso 5: Compilando reporte final...")
        
        final_report = {
            "user_query": user_query,
            "campaign_summary": {
                "total_campaigns": len(campaign_data),
                "active_campaigns": len([c for c in campaign_data if c.get("status") == "active"]),
                "total_spend": sum(c.get("spend", 0) for c in campaign_data),
                "total_revenue": sum(c.get("revenue", 0) for c in campaign_data),
                "average_roas": sum(c.get("roas", 0) for c in campaign_data) / len(campaign_data) if campaign_data else 0
            },
            "langgraph_workflow": {
                "analysis": langgraph_result.get("analysis_result", ""),
                "optimization": langgraph_result.get("optimization_result", ""),
                "creatives": langgraph_result.get("creative_result", ""),
                "final_report": langgraph_result.get("final_report", "")
            },
            "crewai_analysis": {
                "result": str(crewai_result.get("result", "")),
                "campaign_data_analyzed": len(crewai_result.get("campaign_data", []))
            },
            "autogen_critique": {
                "final_analysis": critique_result.get("final_analysis", ""),
                "critiques": critique_result.get("critiques", []),
                "improvements": critique_result.get("improvements", []),
                "final_validation": critique_result.get("final_validation", {}),
                "approved": critique_result.get("approved", False),
                "iterations": critique_result.get("iterations", 0)
            },
            "recommendations": self._extract_recommendations(
                langgraph_result,
                crewai_result,
                critique_result
            ),
            "next_actions": self._generate_next_actions(campaign_data, critique_result)
        }
        
        print("✅ Reporte final compilado\n")
        print("=" * 80)
        print("🎯 ANÁLISIS COMPLETO FINALIZADO")
        print("=" * 80)
        
        return final_report
    
    def _extract_recommendations(
        self,
        langgraph_result: Dict,
        crewai_result: Dict,
        critique_result: Dict
    ) -> list:
        """Extrae recomendaciones clave de todos los componentes"""
        recommendations = []
        
        # De LangGraph
        if langgraph_result.get("optimization_result"):
            recommendations.append({
                "source": "LangGraph Optimizer",
                "recommendation": "Revisar optimizaciones sugeridas en workflow",
                "priority": "high"
            })
        
        # De CrewAI
        if crewai_result.get("result"):
            recommendations.append({
                "source": "CrewAI Agents",
                "recommendation": "Implementar estrategias sugeridas por agentes especializados",
                "priority": "high"
            })
        
        # De AutoGen
        if critique_result.get("approved"):
            recommendations.append({
                "source": "AutoGen Validator",
                "recommendation": "Outputs validados y listos para implementación",
                "priority": "high"
            })
        
        return recommendations
    
    def _generate_next_actions(
        self,
        campaign_data: list,
        critique_result: Dict
    ) -> list:
        """Genera acciones siguientes basadas en análisis"""
        actions = []
        
        if critique_result.get("approved"):
            actions.append("✅ Outputs validados - Proceder con implementación")
            actions.append("📊 Monitorear métricas de campañas optimizadas")
            actions.append("🔄 Ejecutar A/B tests de creativos sugeridos")
            actions.append("💰 Implementar reasignaciones de presupuesto")
        else:
            actions.append("⚠️ Revisar validación - Puede requerir iteración adicional")
            actions.append("🔍 Revisar críticas y mejoras sugeridas")
        
        return actions
    
    def get_campaign_insights(self, campaign_id: str) -> Dict:
        """Obtiene insights específicos de una campaña"""
        perf = self.ads_api.get_campaign_performance(campaign_id, (None, None))
        campaigns = self.ads_api.get_campaigns("account_123")
        campaign = next((c for c in campaigns if c["campaign_id"] == campaign_id), None)
        
        if not campaign:
            return {"error": "Campaña no encontrada"}
        
        return {
            "campaign": {**campaign, **perf},
            "insights": {
                "performance_tier": "high" if perf.get("roas", 0) > 3.0 else "medium" if perf.get("roas", 0) > 2.0 else "low",
                "recommendation": "Aumentar presupuesto" if perf.get("roas", 0) > 3.0 else "Optimizar targeting" if perf.get("roas", 0) > 2.0 else "Pausar o revisar"
            }
        }
    
    def optimize_single_campaign(self, campaign_id: str, new_budget: Optional[float] = None) -> Dict:
        """Optimiza una campaña específica"""
        insights = self.get_campaign_insights(campaign_id)
        
        if "error" in insights:
            return insights
        
        campaign = insights["campaign"]
        current_budget = campaign.get("budget", 0)
        
        if new_budget is None:
            # Calcular presupuesto óptimo basado en ROAS
            roas = campaign.get("roas", 0)
            if roas > 3.0:
                new_budget = current_budget * 1.5  # Aumentar 50%
            elif roas > 2.0:
                new_budget = current_budget * 1.2  # Aumentar 20%
            else:
                new_budget = current_budget * 0.8  # Reducir 20%
        
        # Actualizar presupuesto (stub)
        self.ads_api.update_campaign_budget(campaign_id, new_budget)
        
        return {
            "campaign_id": campaign_id,
            "old_budget": current_budget,
            "new_budget": new_budget,
            "change_percent": ((new_budget - current_budget) / current_budget) * 100,
            "reason": insights["insights"]["recommendation"]
        }


def main():
    """Función principal para ejecutar el sistema"""
    # Inicializar sistema
    system = SalesAgentSystem()
    
    # Ejecutar análisis completo
    user_query = "Analiza mis campañas publicitarias y proporciona recomendaciones para mejorar ROI"
    
    result = system.run_complete_analysis(user_query)
    
    # Mostrar resultados
    print("\n" + "=" * 80)
    print("📊 RESUMEN EJECUTIVO")
    print("=" * 80)
    print(f"\n📈 Campañas analizadas: {result['campaign_summary']['total_campaigns']}")
    print(f"💰 Gasto total: ${result['campaign_summary']['total_spend']:,.2f}")
    print(f"💵 Ingresos totales: ${result['campaign_summary']['total_revenue']:,.2f}")
    print(f"📊 ROAS promedio: {result['campaign_summary']['average_roas']:.2f}")
    print(f"✅ Validación: {'Aprobado' if result['autogen_critique']['approved'] else 'Requiere revisión'}")
    print(f"🔄 Iteraciones de mejora: {result['autogen_critique']['iterations']}")
    
    print("\n" + "=" * 80)
    print("🎯 RECOMENDACIONES")
    print("=" * 80)
    for rec in result['recommendations']:
        print(f"\n• [{rec['source']}] {rec['recommendation']} (Prioridad: {rec['priority']})")
    
    print("\n" + "=" * 80)
    print("📋 PRÓXIMOS PASOS")
    print("=" * 80)
    for action in result['next_actions']:
        print(f"\n{action}")
    
    return result


if __name__ == "__main__":
    result = main()



