"""
Agent Template Library - Biblioteca de templates pre-construidos
Templates listos para usar para casos de uso comunes
"""

from __future__ import annotations

from typing import Dict, Any, List
from .agent_builder_core import AgentDefinition, AgentTemplate, AgentType, AgentCapability


class AgentTemplateLibrary:
    """
    Biblioteca de templates de agentes pre-construidos
    Basado en casos de uso comunes de RAG, Multimodal, y Agentic AI
    """
    
    @staticmethod
    def get_template(template_id: str) -> AgentTemplate:
        """Obtiene un template por ID"""
        templates = AgentTemplateLibrary.get_all_templates()
        if template_id not in templates:
            raise ValueError(f"Template {template_id} no encontrado")
        return templates[template_id]
    
    @staticmethod
    def get_all_templates() -> Dict[str, AgentTemplate]:
        """Retorna todos los templates disponibles"""
        return {
            "customer_support": AgentTemplateLibrary._customer_support_template(),
            "data_analyst": AgentTemplateLibrary._data_analyst_template(),
            "content_generator": AgentTemplateLibrary._content_generator_template(),
            "document_qa": AgentTemplateLibrary._document_qa_template(),
            "code_assistant": AgentTemplateLibrary._code_assistant_template(),
            "research_agent": AgentTemplateLibrary._research_agent_template(),
            "multimodal_analyzer": AgentTemplateLibrary._multimodal_analyzer_template(),
            "workflow_orchestrator": AgentTemplateLibrary._workflow_orchestrator_template()
        }
    
    @staticmethod
    def _customer_support_template() -> AgentTemplate:
        """Template para agente de soporte al cliente"""
        definition = AgentDefinition(
            name="Customer Support Agent",
            description="Agente especializado en atención al cliente con RAG para conocimiento de productos",
            agent_type=AgentType.RAG,
            capabilities=[
                AgentCapability.TEXT_PROCESSING,
                AgentCapability.DOCUMENT_RETRIEVAL
            ],
            system_prompt="""Eres un agente de soporte al cliente experto y amigable.
Tu objetivo es ayudar a los clientes resolviendo sus dudas y problemas de manera eficiente.
Usa el conocimiento de la base de datos para proporcionar respuestas precisas.
Sé empático, profesional y siempre busca la mejor solución para el cliente.""",
            rag_enabled=True,
            vector_databases=["chroma"],
            retriever_type="hybrid",
            top_k=5,
            rerank_enabled=True,
            memory_enabled=True,
            conversation_history_limit=20,
            temperature=0.7,
            output_format="text"
        )
        
        return AgentTemplate(
            template_id="customer_support",
            name="Customer Support Agent",
            description="Agente de soporte al cliente con conocimiento de productos",
            category="customer_support",
            agent_definition=definition,
            use_cases=[
                "Responder preguntas de clientes",
                "Resolver problemas técnicos",
                "Proporcionar información de productos",
                "Gestionar quejas y reembolsos"
            ],
            estimated_cost_per_1k_requests=2.0,
            complexity_level="beginner"
        )
    
    @staticmethod
    def _data_analyst_template() -> AgentTemplate:
        """Template para agente analista de datos"""
        definition = AgentDefinition(
            name="Data Analyst Agent",
            description="Agente que analiza datos estructurados y genera visualizaciones",
            agent_type=AgentType.AGENTIC,
            capabilities=[
                AgentCapability.DATABASE_QUERY,
                AgentCapability.CODE_EXECUTION,
                AgentCapability.TEXT_PROCESSING
            ],
            system_prompt="""Eres un analista de datos experto.
Analiza datos, genera visualizaciones, y proporciona insights accionables.
Puedes ejecutar queries SQL, generar gráficos, y crear reportes.""",
            framework="langgraph",
            tools=[
                {"type": "sql_query", "name": "SQL Query Tool"},
                {"type": "dataframe_analysis", "name": "DataFrame Analysis"},
                {"type": "visualization", "name": "Chart Generator"}
            ],
            temperature=0.3,  # Más determinístico para análisis
            output_format="structured"
        )
        
        return AgentTemplate(
            template_id="data_analyst",
            name="Data Analyst Agent",
            description="Agente analista de datos con capacidades SQL y visualización",
            category="data_analysis",
            agent_definition=definition,
            use_cases=[
                "Análisis de datos empresariales",
                "Generación de reportes",
                "Visualización de datos",
                "Queries SQL complejas"
            ],
            estimated_cost_per_1k_requests=3.0,
            complexity_level="intermediate"
        )
    
    @staticmethod
    def _content_generator_template() -> AgentTemplate:
        """Template para generador de contenido"""
        definition = AgentDefinition(
            name="Content Generator Agent",
            description="Agente que genera contenido creativo (texto, imágenes, videos)",
            agent_type=AgentType.MULTIMODAL,
            capabilities=[
                AgentCapability.TEXT_PROCESSING,
                AgentCapability.IMAGE_PROCESSING,
                AgentCapability.VIDEO_PROCESSING
            ],
            system_prompt="""Eres un generador de contenido creativo y versátil.
Generas contenido de alta calidad en múltiples formatos: texto, imágenes, y videos.
Tu contenido es original, engaging, y relevante para la audiencia objetivo.""",
            multimodal_enabled=True,
            supported_media_types=["text", "image", "video"],
            temperature=0.9,  # Más creativo
            output_format="text"
        )
        
        return AgentTemplate(
            template_id="content_generator",
            name="Content Generator Agent",
            description="Generador de contenido multimodal (texto, imágenes, videos)",
            category="content_generation",
            agent_definition=definition,
            use_cases=[
                "Generación de artículos de blog",
                "Creación de imágenes para marketing",
                "Generación de videos promocionales",
                "Contenido para redes sociales"
            ],
            estimated_cost_per_1k_requests=15.0,  # Más caro por multimodal
            complexity_level="intermediate"
        )
    
    @staticmethod
    def _document_qa_template() -> AgentTemplate:
        """Template para Q&A sobre documentos"""
        definition = AgentDefinition(
            name="Document Q&A Agent",
            description="Agente especializado en responder preguntas sobre documentos usando RAG avanzado",
            agent_type=AgentType.RAG,
            capabilities=[
                AgentCapability.DOCUMENT_RETRIEVAL,
                AgentCapability.TEXT_PROCESSING
            ],
            system_prompt="""Eres un experto en análisis de documentos.
Respondes preguntas precisas basándote en el contenido de los documentos indexados.
Siempre citas las fuentes y proporcionas respuestas fundamentadas en el contenido.""",
            rag_enabled=True,
            vector_databases=["chroma", "faiss"],
            retriever_type="hybrid",
            top_k=10,
            rerank_enabled=True,
            use_chain_of_thought=True,
            temperature=0.5,
            output_format="text"
        )
        
        return AgentTemplate(
            template_id="document_qa",
            name="Document Q&A Agent",
            description="Agente de preguntas y respuestas sobre documentos con RAG avanzado",
            category="document_analysis",
            agent_definition=definition,
            use_cases=[
                "Q&A sobre documentos legales",
                "Análisis de contratos",
                "Búsqueda en documentos técnicos",
                "Extracción de información de PDFs"
            ],
            estimated_cost_per_1k_requests=2.5,
            complexity_level="beginner"
        )
    
    @staticmethod
    def _code_assistant_template() -> AgentTemplate:
        """Template para asistente de código"""
        definition = AgentDefinition(
            name="Code Assistant Agent",
            description="Agente que ayuda con programación, debugging, y generación de código",
            agent_type=AgentType.AGENTIC,
            capabilities=[
                AgentCapability.CODE_EXECUTION,
                AgentCapability.TEXT_PROCESSING,
                AgentCapability.WEB_SEARCH
            ],
            system_prompt="""Eres un asistente de programación experto.
Ayudas con código, debugging, optimización, y mejores prácticas.
Generas código limpio, bien documentado, y siguiendo estándares de la industria.""",
            framework="langchain",
            tools=[
                {"type": "code_execution", "name": "Python Executor"},
                {"type": "web_search", "name": "Documentation Search"}
            ],
            temperature=0.2,  # Más determinístico para código
            output_format="text"
        )
        
        return AgentTemplate(
            template_id="code_assistant",
            name="Code Assistant Agent",
            description="Asistente de programación con ejecución de código",
            category="development",
            agent_definition=definition,
            use_cases=[
                "Generación de código",
                "Debugging y optimización",
                "Refactoring",
                "Documentación de código"
            ],
            estimated_cost_per_1k_requests=3.0,
            complexity_level="intermediate"
        )
    
    @staticmethod
    def _research_agent_template() -> AgentTemplate:
        """Template para agente de investigación"""
        definition = AgentDefinition(
            name="Research Agent",
            description="Agente que realiza investigación profunda usando web search y RAG",
            agent_type=AgentType.HYBRID,
            capabilities=[
                AgentCapability.WEB_SEARCH,
                AgentCapability.DOCUMENT_RETRIEVAL,
                AgentCapability.TEXT_PROCESSING
            ],
            system_prompt="""Eres un investigador experto.
Realizas investigación profunda, verificas fuentes, y sintetizas información de múltiples fuentes.
Proporcionas análisis completo y bien fundamentado.""",
            rag_enabled=True,
            vector_databases=["chroma"],
            retriever_type="semantic",
            top_k=10,
            tools=[
                {"type": "web_search", "name": "Web Search"},
                {"type": "document_retrieval", "name": "Knowledge Base"}
            ],
            use_chain_of_thought=True,
            use_self_consistency=True,
            temperature=0.6,
            output_format="structured"
        )
        
        return AgentTemplate(
            template_id="research_agent",
            name="Research Agent",
            description="Agente de investigación con web search y RAG",
            category="research",
            agent_definition=definition,
            use_cases=[
                "Investigación de mercado",
                "Análisis competitivo",
                "Recopilación de información",
                "Síntesis de múltiples fuentes"
            ],
            estimated_cost_per_1k_requests=5.0,
            complexity_level="advanced"
        )
    
    @staticmethod
    def _multimodal_analyzer_template() -> AgentTemplate:
        """Template para analizador multimodal"""
        definition = AgentDefinition(
            name="Multimodal Analyzer Agent",
            description="Agente que analiza texto, imágenes, audio, y video",
            agent_type=AgentType.MULTIMODAL,
            capabilities=[
                AgentCapability.TEXT_PROCESSING,
                AgentCapability.IMAGE_PROCESSING,
                AgentCapability.AUDIO_PROCESSING,
                AgentCapability.VIDEO_PROCESSING
            ],
            system_prompt="""Eres un analizador multimodal experto.
Procesas y analizas contenido en múltiples formatos: texto, imágenes, audio, y video.
Proporcionas análisis detallado y insights accionables.""",
            multimodal_enabled=True,
            supported_media_types=["text", "image", "audio", "video"],
            temperature=0.7,
            output_format="structured"
        )
        
        return AgentTemplate(
            template_id="multimodal_analyzer",
            name="Multimodal Analyzer Agent",
            description="Analizador de contenido multimodal (texto, imagen, audio, video)",
            category="multimodal",
            agent_definition=definition,
            use_cases=[
                "Análisis de imágenes",
                "Transcripción y análisis de audio",
                "Análisis de video",
                "Análisis de contenido multimedia"
            ],
            estimated_cost_per_1k_requests=20.0,
            complexity_level="advanced"
        )
    
    @staticmethod
    def _workflow_orchestrator_template() -> AgentTemplate:
        """Template para orquestador de workflows"""
        definition = AgentDefinition(
            name="Workflow Orchestrator Agent",
            description="Agente que orquesta workflows complejos con múltiples agentes",
            agent_type=AgentType.AGENTIC,
            capabilities=[
                AgentCapability.MULTI_AGENT_COLLABORATION,
                AgentCapability.TEXT_PROCESSING,
                AgentCapability.API_INTEGRATION
            ],
            system_prompt="""Eres un orquestador de workflows experto.
Coordinas múltiples agentes y tareas para completar objetivos complejos.
Gestionas el flujo de trabajo, manejo de errores, y optimización de recursos.""",
            framework="langgraph",
            workflow_definition={
                "type": "stateful",
                "nodes": ["planning", "execution", "validation", "reporting"],
                "edges": [
                    {"from": "planning", "to": "execution"},
                    {"from": "execution", "to": "validation"},
                    {"from": "validation", "to": "reporting"}
                ]
            },
            temperature=0.5,
            output_format="structured"
        )
        
        return AgentTemplate(
            template_id="workflow_orchestrator",
            name="Workflow Orchestrator Agent",
            description="Orquestador de workflows complejos con múltiples agentes",
            category="orchestration",
            agent_definition=definition,
            use_cases=[
                "Automatización de procesos empresariales",
                "Coordinación de múltiples agentes",
                "Workflows complejos",
                "Integración de sistemas"
            ],
            estimated_cost_per_1k_requests=10.0,
            complexity_level="advanced"
        )
