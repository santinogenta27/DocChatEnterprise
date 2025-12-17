"""
Ejemplo de uso del sistema de agentes AI para ventas.
Demuestra cómo usar el sistema completo para análisis de campañas.
"""
from sales_agent_system import SalesAgentSystem
import json


def example_basic_analysis():
    """Ejemplo básico de análisis"""
    print("=" * 80)
    print("EJEMPLO 1: Análisis Básico de Campañas")
    print("=" * 80)
    
    system = SalesAgentSystem()
    
    result = system.run_complete_analysis(
        "Analiza mis campañas publicitarias y proporciona recomendaciones para mejorar ROI"
    )
    
    print("\n📊 Resumen:")
    print(f"  - Campañas analizadas: {result['campaign_summary']['total_campaigns']}")
    print(f"  - Gasto total: ${result['campaign_summary']['total_spend']:,.2f}")
    print(f"  - Ingresos: ${result['campaign_summary']['total_revenue']:,.2f}")
    print(f"  - ROAS promedio: {result['campaign_summary']['average_roas']:.2f}")
    
    return result


def example_single_campaign_optimization():
    """Ejemplo de optimización de una campaña específica"""
    print("\n" + "=" * 80)
    print("EJEMPLO 2: Optimización de Campaña Individual")
    print("=" * 80)
    
    system = SalesAgentSystem()
    
    # Obtener insights de una campaña
    insights = system.get_campaign_insights("camp_1")
    
    if "error" not in insights:
        print(f"\n📈 Campaña: {insights['campaign'].get('name', 'N/A')}")
        print(f"  - ROAS: {insights['campaign'].get('roas', 0):.2f}")
        print(f"  - Tier de rendimiento: {insights['insights']['performance_tier']}")
        print(f"  - Recomendación: {insights['insights']['recommendation']}")
        
        # Optimizar presupuesto
        optimization = system.optimize_single_campaign("camp_1")
        print(f"\n💰 Optimización:")
        print(f"  - Presupuesto anterior: ${optimization['old_budget']:.2f}")
        print(f"  - Presupuesto nuevo: ${optimization['new_budget']:.2f}")
        print(f"  - Cambio: {optimization['change_percent']:.1f}%")
        print(f"  - Razón: {optimization['reason']}")


def example_langgraph_only():
    """Ejemplo usando solo LangGraph workflow"""
    print("\n" + "=" * 80)
    print("EJEMPLO 3: Solo Workflow LangGraph")
    print("=" * 80)
    
    from sales_agent_system.langgraph_workflow import SalesWorkflowOrchestrator
    
    orchestrator = SalesWorkflowOrchestrator()
    
    result = orchestrator.run(
        "Analiza el rendimiento de mis campañas y sugiere optimizaciones"
    )
    
    print("\n📋 Resultados del Workflow:")
    print(f"\n✅ Análisis completado: {len(result.get('analysis_result', ''))} caracteres")
    print(f"✅ Optimización completada: {len(result.get('optimization_result', ''))} caracteres")
    print(f"✅ Creativos generados: {len(result.get('creative_result', ''))} caracteres")
    print(f"✅ Reporte final: {len(result.get('final_report', ''))} caracteres")
    
    if result.get('errors'):
        print(f"\n⚠️ Errores encontrados: {len(result['errors'])}")
        for error in result['errors']:
            print(f"  - {error}")


def example_crewai_only():
    """Ejemplo usando solo agentes CrewAI"""
    print("\n" + "=" * 80)
    print("EJEMPLO 4: Solo Agentes CrewAI")
    print("=" * 80)
    
    from sales_agent_system.crewai_agents import SalesAgentsCrew
    
    crew = SalesAgentsCrew()
    
    result = crew.run_complete_analysis(
        "Proporciona un análisis detallado de mis campañas publicitarias"
    )
    
    print("\n👥 Resultados de Agentes CrewAI:")
    print(f"  - Campañas analizadas: {len(result.get('campaign_data', []))}")
    print(f"  - Resultado generado: {len(str(result.get('result', '')))} caracteres")


def example_autogen_critique():
    """Ejemplo usando solo sistema de crítica AutoGen"""
    print("\n" + "=" * 80)
    print("EJEMPLO 5: Solo Sistema de Crítica AutoGen")
    print("=" * 80)
    
    from sales_agent_system.autogen_critique import SalesCritiqueSystem
    from sales_agent_system.api_stubs import AdsAPIStub
    
    critique_system = SalesCritiqueSystem()
    ads_api = AdsAPIStub()
    
    # Obtener datos de campañas
    campaigns = ads_api.get_campaigns("account_123")
    campaign_data = []
    for camp in campaigns:
        perf = ads_api.get_campaign_performance(camp["campaign_id"], (None, None))
        campaign_data.append({**camp, **perf})
    
    # Análisis de ejemplo
    sample_analysis = """
    Análisis de campañas:
    - Campaña 1: ROAS de 2.5, necesita optimización
    - Campaña 2: ROAS de 4.0, está funcionando bien
    - Recomendación: Aumentar presupuesto en Campaña 2
    """
    
    # Ejecutar crítica
    critique_result = critique_system.run_full_critique_cycle(
        analysis=sample_analysis,
        optimization="Aumentar presupuesto en campañas de alto rendimiento",
        creatives="Headlines orientados a conversión",
        campaign_data=campaign_data,
        max_iterations=2
    )
    
    print("\n🔍 Resultados de Crítica:")
    print(f"  - Iteraciones: {critique_result['iterations']}")
    print(f"  - Aprobado: {critique_result['approved']}")
    print(f"  - Críticas realizadas: {len(critique_result.get('critiques', []))}")
    print(f"  - Mejoras aplicadas: {len(critique_result.get('improvements', []))}")


def main():
    """Ejecuta todos los ejemplos"""
    print("\n" + "=" * 80)
    print("SISTEMA DE AGENTES AI PARA VENTAS - EJEMPLOS DE USO")
    print("=" * 80)
    
    try:
        # Ejemplo 1: Análisis completo
        example_basic_analysis()
        
        # Ejemplo 2: Optimización individual
        example_single_campaign_optimization()
        
        # Ejemplo 3: Solo LangGraph
        # example_langgraph_only()
        
        # Ejemplo 4: Solo CrewAI
        # example_crewai_only()
        
        # Ejemplo 5: Solo AutoGen
        # example_autogen_critique()
        
        print("\n" + "=" * 80)
        print("✅ TODOS LOS EJEMPLOS COMPLETADOS")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

