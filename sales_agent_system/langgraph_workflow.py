"""
Workflow LangGraph para orquestación del sistema de ventas con agentes AI.
Implementa el patrón de routing y parallelización para coordinar múltiples agentes.
"""
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import operator
from .models import AgentState, SalesAnalysisReport, CampaignData
from .api_stubs import AdsAPIStub, CRMAPIStub, AnalyticsAPIStub
import json


class SalesWorkflowState(TypedDict):
    """Estado del workflow de ventas"""
    user_query: str
    campaign_data: Annotated[list, operator.add]
    analysis_result: str
    optimization_result: str
    creative_result: str
    critique_result: str
    final_report: str
    errors: Annotated[list, operator.add]
    iteration_count: int
    should_continue: bool


class SalesWorkflowOrchestrator:
    """Orquestador principal del workflow de ventas"""
    
    def __init__(self, llm_model: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(model=llm_model, temperature=0)
        self.ads_api = AdsAPIStub()
        self.crm_api = CRMAPIStub()
        self.analytics_api = AnalyticsAPIStub()
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Construye el grafo del workflow"""
        workflow = StateGraph(SalesWorkflowState)
        
        # Agregar nodos
        workflow.add_node("fetch_data", self._fetch_campaign_data)
        workflow.add_node("analyze_performance", self._analyze_performance)
        workflow.add_node("optimize_budget", self._optimize_budget)
        workflow.add_node("generate_creatives", self._generate_creatives)
        workflow.add_node("critique_and_improve", self._critique_and_improve)
        workflow.add_node("compile_report", self._compile_final_report)
        workflow.add_node("router", self._route_decision)
        
        # Definir flujo
        workflow.set_entry_point("fetch_data")
        workflow.add_edge("fetch_data", "analyze_performance")
        workflow.add_edge("analyze_performance", "optimize_budget")
        
        # Paralelización: optimización y generación de creativos en paralelo
        workflow.add_edge("optimize_budget", "generate_creatives")
        workflow.add_edge("generate_creatives", "critique_and_improve")
        
        # Routing condicional después de crítica
        workflow.add_conditional_edges(
            "critique_and_improve",
            self._should_iterate,
            {
                "iterate": "optimize_budget",
                "finalize": "compile_report"
            }
        )
        
        workflow.add_edge("compile_report", END)
        
        return workflow.compile()
    
    def _fetch_campaign_data(self, state: SalesWorkflowState) -> dict:
        """Nodo: Obtener datos de campañas"""
        try:
            campaigns = self.ads_api.get_campaigns("account_123")
            campaign_data = []
            
            for camp in campaigns:
                perf = self.ads_api.get_campaign_performance(
                    camp["campaign_id"],
                    (None, None)
                )
                campaign_data.append({
                    **camp,
                    **perf
                })
            
            return {
                "campaign_data": campaign_data,
                "errors": []
            }
        except Exception as e:
            return {
                "campaign_data": [],
                "errors": [f"Error fetching data: {str(e)}"]
            }
    
    def _analyze_performance(self, state: SalesWorkflowState) -> dict:
        """Nodo: Analizar rendimiento de campañas"""
        try:
            prompt = f"""
Eres un analista de ventas experto. Analiza el rendimiento de las siguientes campañas:

{json.dumps(state.get('campaign_data', []), indent=2)}

Proporciona:
1. Identificación de campañas de alto rendimiento
2. Identificación de campañas de bajo rendimiento
3. Análisis de métricas clave (ROAS, CPA, CTR)
4. Tendencias y patrones identificados

Formato tu respuesta de manera estructurada y accionable.
"""
            
            messages = [
                SystemMessage(content="Eres un experto analista de ventas y marketing digital."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            return {
                "analysis_result": response.content,
                "errors": []
            }
        except Exception as e:
            return {
                "analysis_result": "",
                "errors": [f"Error in analysis: {str(e)}"]
            }
    
    def _optimize_budget(self, state: SalesWorkflowState) -> dict:
        """Nodo: Optimizar presupuesto"""
        try:
            prompt = f"""
Eres un especialista en optimización de presupuestos publicitarios.

Análisis previo:
{state.get('analysis_result', '')}

Datos de campañas:
{json.dumps(state.get('campaign_data', []), indent=2)}

Proporciona recomendaciones de optimización de presupuesto:
1. Reasignación de presupuesto entre campañas
2. Justificación de cada cambio
3. Impacto esperado en ROI
4. Priorización de acciones

Formato: Lista estructurada de recomendaciones con presupuestos específicos.
"""
            
            messages = [
                SystemMessage(content="Eres un experto en optimización de presupuestos publicitarios."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            return {
                "optimization_result": response.content,
                "errors": []
            }
        except Exception as e:
            return {
                "optimization_result": "",
                "errors": [f"Error in optimization: {str(e)}"]
            }
    
    def _generate_creatives(self, state: SalesWorkflowState) -> dict:
        """Nodo: Generar sugerencias de creativos"""
        try:
            prompt = f"""
Eres un copywriter publicitario experto.

Análisis de rendimiento:
{state.get('analysis_result', '')}

Datos de campañas:
{json.dumps(state.get('campaign_data', []), indent=2)}

Genera sugerencias de creativos publicitarios:
1. Headlines atractivos y orientados a conversión
2. Descripciones persuasivas
3. Calls-to-action efectivos
4. Justificación basada en datos

Formato: Lista de creativos con explicación de por qué funcionarán.
"""
            
            messages = [
                SystemMessage(content="Eres un copywriter publicitario experto con enfoque en conversión."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            return {
                "creative_result": response.content,
                "errors": []
            }
        except Exception as e:
            return {
                "creative_result": "",
                "errors": [f"Error in creative generation: {str(e)}"]
            }
    
    def _critique_and_improve(self, state: SalesWorkflowState) -> dict:
        """Nodo: Criticar y mejorar outputs (patrón AutoGen)"""
        try:
            prompt = f"""
Eres un crítico experto de estrategias de ventas y marketing.

Análisis de rendimiento:
{state.get('analysis_result', '')}

Optimizaciones propuestas:
{state.get('optimization_result', '')}

Creativos sugeridos:
{state.get('creative_result', '')}

Tu tarea:
1. Identifica debilidades o inconsistencias
2. Sugiere mejoras específicas
3. Valida la coherencia entre análisis, optimización y creativos
4. Proporciona feedback constructivo

Si encuentras problemas significativos, indica que se necesita iteración.
Si todo está bien, indica que se puede finalizar.
"""
            
            messages = [
                SystemMessage(content="Eres un crítico experto que mejora estrategias de ventas."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            # Determinar si necesita iteración
            content_lower = response.content.lower()
            needs_iteration = any(word in content_lower for word in [
                "iterar", "mejorar", "corregir", "problema", "error", "inconsistencia"
            ])
            
            return {
                "critique_result": response.content,
                "should_continue": not needs_iteration,
                "iteration_count": state.get("iteration_count", 0) + (1 if needs_iteration else 0),
                "errors": []
            }
        except Exception as e:
            return {
                "critique_result": "",
                "should_continue": True,
                "errors": [f"Error in critique: {str(e)}"]
            }
    
    def _should_iterate(self, state: SalesWorkflowState) -> str:
        """Función de routing: decidir si iterar o finalizar"""
        iteration_count = state.get("iteration_count", 0)
        should_continue = state.get("should_continue", True)
        max_iterations = 3
        
        if iteration_count >= max_iterations:
            return "finalize"
        
        if should_continue:
            return "finalize"
        else:
            return "iterate"
    
    def _compile_final_report(self, state: SalesWorkflowState) -> dict:
        """Nodo: Compilar reporte final"""
        try:
            prompt = f"""
Compila un reporte ejecutivo completo de análisis de ventas con:

1. Resumen ejecutivo
2. Análisis de rendimiento:
{state.get('analysis_result', '')}

3. Optimizaciones recomendadas:
{state.get('optimization_result', '')}

4. Creativos sugeridos:
{state.get('creative_result', '')}

5. Feedback y mejoras:
{state.get('critique_result', '')}

6. Próximos pasos accionables

Formato el reporte de manera profesional, estructurada y lista para implementación.
"""
            
            messages = [
                SystemMessage(content="Eres un consultor de ventas que compila reportes ejecutivos."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            return {
                "final_report": response.content,
                "errors": []
            }
        except Exception as e:
            return {
                "final_report": "",
                "errors": [f"Error compiling report: {str(e)}"]
            }
    
    def run(self, user_query: str) -> dict:
        """Ejecuta el workflow completo"""
        initial_state = {
            "user_query": user_query,
            "campaign_data": [],
            "analysis_result": "",
            "optimization_result": "",
            "creative_result": "",
            "critique_result": "",
            "final_report": "",
            "errors": [],
            "iteration_count": 0,
            "should_continue": False
        }
        
        result = self.workflow.invoke(initial_state)
        return result

