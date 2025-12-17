"""
Agentes CrewAI especializados en ventas y optimización de campañas publicitarias.
Cada agente tiene un rol específico y herramientas para ejecutar acciones.
"""
from crewai import Agent, Task, Crew, Process
from crewai import LLM
from crewai_tools import SerperDevTool
from typing import List, Dict
from .models import (
    CampaignData, OptimizationRecommendation, 
    CreativeSuggestion, BudgetAllocation, SalesAnalysisReport
)
from .api_stubs import AdsAPIStub, CompetitorAnalysisStub
import os


class SalesAgentsCrew:
    """Crew de agentes especializados en ventas"""
    
    def __init__(self, llm_model: str = "watsonx/ibm/granite-3-3-8b-instruct"):
        # Configurar LLM
        os.environ.setdefault("WATSONX_API_BASE", "https://us-south.ml.cloud.ibm.com")
        os.environ.setdefault("WX_PROJECT_ID", "skills-network")
        
        self.llm = LLM(model=llm_model)
        self.ads_api = AdsAPIStub()
        self.competitor_api = CompetitorAnalysisStub()
        
        # Inicializar herramientas
        self.search_tool = SerperDevTool() if os.getenv('SERPER_API_KEY') else None
        
        # Crear agentes
        self.ads_analyst = self._create_ads_analyst()
        self.budget_optimizer = self._create_budget_optimizer()
        self.creative_generator = self._create_creative_generator()
        self.strategy_advisor = self._create_strategy_advisor()
    
    def _create_ads_analyst(self) -> Agent:
        """Agente especializado en análisis de campañas publicitarias"""
        tools = []
        if self.search_tool:
            tools.append(self.search_tool)
        
        return Agent(
            role="Analista de Campañas Publicitarias",
            goal="Analizar el rendimiento de campañas publicitarias e identificar oportunidades de optimización",
            backstory="""Eres un analista senior con 10+ años de experiencia en marketing digital.
            Especializado en Google Ads, Meta Ads y otras plataformas. Tu expertise incluye:
            - Análisis de métricas de rendimiento (ROAS, CPA, CTR)
            - Identificación de campañas de alto y bajo rendimiento
            - Análisis de tendencias y patrones
            - Recomendaciones basadas en datos
            """,
            tools=tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
    
    def _create_budget_optimizer(self) -> Agent:
        """Agente especializado en optimización de presupuestos"""
        return Agent(
            role="Optimizador de Presupuestos Publicitarios",
            goal="Optimizar la asignación de presupuesto entre campañas para maximizar ROI",
            backstory="""Eres un especialista en optimización de presupuestos con experiencia en:
            - Reasignación estratégica de presupuestos
            - Análisis de ROI por campaña
            - Optimización de bidding strategies
            - Maximización de retorno de inversión
            Trabajas con datos reales y proporcionas recomendaciones accionables.
            """,
            tools=[],
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
    
    def _create_creative_generator(self) -> Agent:
        """Agente especializado en generación de creativos publicitarios"""
        tools = []
        if self.search_tool:
            tools.append(self.search_tool)
        
        return Agent(
            role="Generador de Creativos Publicitarios",
            goal="Crear headlines, descripciones y CTAs efectivos para campañas publicitarias",
            backstory="""Eres un copywriter publicitario experto con enfoque en conversión.
            Tu expertise incluye:
            - Creación de headlines orientados a conversión
            - Escritura de descripciones persuasivas
            - Diseño de calls-to-action efectivos
            - A/B testing de creativos
            - Análisis de competencia para inspiración
            """,
            tools=tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
    
    def _create_strategy_advisor(self) -> Agent:
        """Agente asesor de estrategia de ventas"""
        return Agent(
            role="Asesor de Estrategia de Ventas",
            goal="Proporcionar recomendaciones estratégicas de alto nivel para mejorar ventas",
            backstory="""Eres un consultor senior de estrategia de ventas y marketing.
            Con experiencia en:
            - Desarrollo de estrategias de crecimiento
            - Análisis de mercado y competencia
            - Optimización de embudos de ventas
            - Integración de múltiples canales
            - Planificación estratégica a largo plazo
            """,
            tools=[],
            llm=self.llm,
            verbose=True,
            allow_delegation=True
        )
    
    def create_analysis_task(self, campaign_data: List[Dict]) -> Task:
        """Tarea de análisis de campañas"""
        return Task(
            description=f"""
Analiza el rendimiento de las siguientes campañas publicitarias:

{self._format_campaign_data(campaign_data)}

Proporciona:
1. Identificación de campañas de alto rendimiento (top 3)
2. Identificación de campañas de bajo rendimiento que necesitan optimización
3. Análisis detallado de métricas clave (ROAS, CPA, CTR, CPC)
4. Tendencias y patrones identificados
5. Recomendaciones prioritarias de acción

Formato tu análisis de manera estructurada y accionable.
""",
            expected_output="Análisis estructurado con identificación de top performers, underperformers, métricas clave y recomendaciones",
            agent=self.ads_analyst,
            output_pydantic=SalesAnalysisReport
        )
    
    def create_optimization_task(self, analysis_context: Task) -> Task:
        """Tarea de optimización de presupuesto"""
        return Task(
            description="""
Basándote en el análisis de campañas, proporciona recomendaciones de optimización de presupuesto:

1. Reasignación de presupuesto entre campañas
2. Justificación de cada cambio basada en datos
3. Impacto esperado en ROI para cada ajuste
4. Priorización de acciones (alta, media, baja)
5. Timeline recomendado para implementación

Asegúrate de que las recomendaciones sean específicas, cuantificables y accionables.
""",
            expected_output="Lista de recomendaciones de optimización de presupuesto con justificaciones y ROI esperado",
            agent=self.budget_optimizer,
            context=[analysis_context]
        )
    
    def create_creative_task(self, analysis_context: Task) -> Task:
        """Tarea de generación de creativos"""
        return Task(
            description="""
Genera sugerencias de creativos publicitarios basadas en el análisis de rendimiento:

1. Headlines atractivos y orientados a conversión (3-5 opciones)
2. Descripciones persuasivas que destaquen beneficios
3. Calls-to-action efectivos
4. Justificación de cada creativo basada en:
   - Análisis de rendimiento de campañas similares
   - Mejores prácticas de la industria
   - Psicología de conversión
5. Recomendaciones de A/B testing

Asegúrate de que los creativos sean específicos para cada tipo de campaña identificada.
""",
            expected_output="Lista de creativos publicitarios con headlines, descripciones, CTAs y justificaciones",
            agent=self.creative_generator,
            context=[analysis_context]
        )
    
    def create_strategy_task(self, analysis_context: Task, optimization_context: Task) -> Task:
        """Tarea de asesoría estratégica"""
        return Task(
            description="""
Proporciona recomendaciones estratégicas de alto nivel basadas en el análisis y optimizaciones:

1. Estrategia general de crecimiento
2. Oportunidades de mercado identificadas
3. Amenazas y riesgos a considerar
4. Recomendaciones de canales adicionales
5. Plan de acción a 30, 60 y 90 días
6. KPIs a monitorear

Integra todas las recomendaciones previas en una estrategia cohesiva.
""",
            expected_output="Estrategia completa de ventas con plan de acción y KPIs",
            agent=self.strategy_advisor,
            context=[analysis_context, optimization_context]
        )
    
    def _format_campaign_data(self, campaign_data: List[Dict]) -> str:
        """Formatea datos de campañas para prompts"""
        formatted = []
        for camp in campaign_data:
            formatted.append(f"""
Campaña: {camp.get('name', 'N/A')}
ID: {camp.get('campaign_id', 'N/A')}
Estado: {camp.get('status', 'N/A')}
Presupuesto: ${camp.get('budget', 0):.2f}
Impresiones: {camp.get('impressions', 0):,}
Clics: {camp.get('clicks', 0):,}
Conversiones: {camp.get('conversions', 0):,}
Gasto: ${camp.get('spend', 0):.2f}
Ingresos: ${camp.get('revenue', 0):.2f}
ROAS: {camp.get('roas', 0):.2f}
CTR: {camp.get('ctr', 0):.2f}%
CPA: ${camp.get('cpa', 0):.2f}
""")
        return "\n".join(formatted)
    
    def run_complete_analysis(self, user_query: str) -> Dict:
        """Ejecuta análisis completo con todos los agentes"""
        # Obtener datos de campañas
        campaigns = self.ads_api.get_campaigns("account_123")
        campaign_data = []
        
        for camp in campaigns:
            perf = self.ads_api.get_campaign_performance(
                camp["campaign_id"],
                (None, None)
            )
            campaign_data.append({**camp, **perf})
        
        # Crear tareas
        analysis_task = self.create_analysis_task(campaign_data)
        optimization_task = self.create_optimization_task(analysis_task)
        creative_task = self.create_creative_task(analysis_task)
        strategy_task = self.create_strategy_task(analysis_task, optimization_task)
        
        # Crear crew
        crew = Crew(
            agents=[
                self.ads_analyst,
                self.budget_optimizer,
                self.creative_generator,
                self.strategy_advisor
            ],
            tasks=[
                analysis_task,
                optimization_task,
                creative_task,
                strategy_task
            ],
            process=Process.sequential,
            verbose=True
        )
        
        # Ejecutar
        result = crew.kickoff(inputs={"user_query": user_query})
        
        return {
            "result": result,
            "campaign_data": campaign_data
        }



