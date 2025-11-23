"""
Enterprise Agentic AI con Intelligent Document Processing (IDP).

Este módulo permite a las empresas:
- Subir datos masivos
- Procesar documentos con IDP para extraer información estructurada
- Conectar Agentic AI por API
- Ejecutar tareas autónomas usando los datos procesados
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

from .config import AppConfig
from .document_processor import DocumentProcessor
from .retriever_builder import RetrieverBuilder
from .tools import (
    EmailTool, ReportTool, DatabaseTool, PresentationTool,
    IntegrationTool, TableAnalysisTool, SchedulerTool
)
from .tools.advanced_email_tool import AdvancedEmailTool
from .tools.advertising_tool import AdvertisingTool


@dataclass
class IDPResult:
    """Resultado del procesamiento IDP de un documento."""
    file_name: str
    document_type: str
    extracted_data: Dict[str, Any]
    structured_content: Dict[str, Any]
    entities: List[str]
    key_metrics: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgenticTask:
    """Tarea para el Agentic AI empresarial."""
    task_id: str
    task_type: str  # análisis, automatización, integración, etc.
    description: str
    priority: int = 5
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    result: Optional[Any] = None
    data_sources: List[str] = field(default_factory=list)


class EnterpriseAgenticAI:
    """
    Agentic AI empresarial con IDP.
    
    Permite a las empresas:
    - Subir y procesar documentos masivos con IDP
    - Extraer información estructurada automáticamente
    - Conectar por API para ejecutar tareas autónomas
    - Realizar las 50+ tareas listadas usando los datos procesados
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY requerida para Agentic AI empresarial")
        
        # LLM para IDP y tareas autónomas
        self.llm = ChatOpenAI(
            model=config.agentic_model or "gpt-4o",
            temperature=0.2,
            api_key=config.openai_api_key,
            max_tokens=4000
        )
        
        # Procesador de documentos
        self.document_processor = DocumentProcessor(config)
        
        # Retriever builder para búsqueda en documentos
        self.retriever_builder = RetrieverBuilder(config)
        
        # Herramientas disponibles para el Agentic AI
        # Usar AdvancedEmailTool en lugar de EmailTool básico
        self.tools = {
            "email": AdvancedEmailTool(config),  # Email avanzado con todas las funcionalidades
            "advanced_email": AdvancedEmailTool(config),  # Alias para acceso directo
            "advertising": AdvertisingTool(config),  # Advertising y Marketing avanzado
            "marketing": AdvertisingTool(config),  # Alias para marketing
            "report": ReportTool(config),
            "database": DatabaseTool(config),
            "presentation": PresentationTool(config),
            "integration": IntegrationTool(config),
            "table_analysis": TableAnalysisTool(config),
            "scheduler": SchedulerTool(config),
        }
        
        # Almacenamiento de documentos procesados
        self.processed_documents: List[Document] = []
        self.idp_results: Dict[str, IDPResult] = {}
        self.retriever = None
        
        # Tareas pendientes y ejecutadas
        self.tasks: Dict[str, AgenticTask] = {}
    
    def process_documents_with_idp(
        self,
        files: List[Any],
        extract_entities: bool = True,
        extract_metrics: bool = True
    ) -> Dict[str, IDPResult]:
        """
        Procesa documentos con Intelligent Document Processing (IDP).
        
        IDP extrae información estructurada de documentos no estructurados:
        - Clasificación de tipo de documento
        - Extracción de entidades (nombres, fechas, montos, etc.)
        - Extracción de métricas clave
        - Estructuración de contenido
        """
        print(f"\n{'='*60}")
        print(f"📄 PROCESAMIENTO IDP: {len(files)} documentos")
        print(f"{'='*60}\n")
        
        # Primero procesar documentos normalmente
        documents = self.document_processor.process(files)
        self.processed_documents.extend(documents)
        
        # Construir retriever con todos los documentos
        if self.processed_documents:
            self.retriever = self.retriever_builder.build_hybrid_retriever(self.processed_documents)
        
        # Procesar cada archivo con IDP
        idp_results = {}
        for idx, file_obj in enumerate(files, 1):
            try:
                file_name = getattr(file_obj, "original_name", None) or getattr(file_obj, "name", f"documento_{idx}")
                print(f"[{idx}/{len(files)}] 🔍 Procesando IDP: {Path(file_name).name}")
                
                # Obtener documentos relacionados con este archivo
                file_docs = [doc for doc in documents if doc.metadata.get("source", "").endswith(Path(file_name).name)]
                
                if not file_docs:
                    print(f"   ⚠️ No se encontraron chunks para {file_name}")
                    continue
                
                # Ejecutar IDP
                idp_result = self._extract_structured_data(
                    file_name=file_name,
                    documents=file_docs,
                    extract_entities=extract_entities,
                    extract_metrics=extract_metrics
                )
                
                idp_results[file_name] = idp_result
                self.idp_results[file_name] = idp_result
                
                print(f"   ✅ IDP completado: {len(idp_result.entities)} entidades, {len(idp_result.key_metrics)} métricas")
                
            except Exception as e:
                print(f"   ❌ Error en IDP para {file_name}: {str(e)[:100]}")
                continue
        
        print(f"\n✅ Procesamiento IDP completado: {len(idp_results)}/{len(files)} documentos procesados\n")
        return idp_results
    
    def _extract_structured_data(
        self,
        file_name: str,
        documents: List[Document],
        extract_entities: bool = True,
        extract_metrics: bool = True
    ) -> IDPResult:
        """Extrae información estructurada de documentos usando IDP."""
        
        # Construir contexto del documento
        context_parts = []
        for doc in documents[:20]:  # Limitar a 20 chunks para IDP
            content = doc.page_content[:1000]  # Limitar tamaño
            context_parts.append(content)
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Prompt para IDP
        prompt = f"""Eres un sistema de Intelligent Document Processing (IDP) experto. 
        Analiza este documento y extrae información estructurada.

        DOCUMENTO: {Path(file_name).name}
        
        CONTENIDO:
        {context[:15000]}  # Limitar contexto
        
        INSTRUCCIONES:
        1. Clasifica el tipo de documento (factura, contrato, informe, email, etc.)
        2. Extrae entidades clave: nombres de personas, empresas, fechas, montos, números de referencia, etc.
        3. Identifica métricas clave: valores numéricos importantes, porcentajes, totales, etc.
        4. Estructura el contenido: organiza la información en secciones lógicas
        
        Responde ÚNICAMENTE en formato JSON válido:
        {{
            "document_type": "tipo de documento específico",
            "entities": ["entidad1", "entidad2", ...],
            "key_metrics": {{
                "metric_name1": "valor1",
                "metric_name2": "valor2",
                ...
            }},
            "structured_content": {{
                "sections": [
                    {{"title": "título sección", "content": "contenido"}},
                    ...
                ]
            }},
            "metadata": {{
                "date": "fecha si existe",
                "author": "autor si existe",
                "organization": "organización si existe"
            }}
        }}"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            
            # Limpiar respuesta JSON
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            data = json.loads(response)
            
            return IDPResult(
                file_name=file_name,
                document_type=data.get("document_type", "unknown"),
                extracted_data=data,
                structured_content=data.get("structured_content", {}),
                entities=data.get("entities", []),
                key_metrics=data.get("key_metrics", {}),
                metadata=data.get("metadata", {})
            )
            
        except Exception as e:
            print(f"   ⚠️ Error en extracción IDP: {str(e)[:100]}")
            # Retornar resultado básico
            return IDPResult(
                file_name=file_name,
                document_type="unknown",
                extracted_data={},
                structured_content={},
                entities=[],
                key_metrics={},
                metadata={}
            )
    
    def execute_autonomous_task(
        self,
        task_description: str,
        task_type: str = "análisis",
        context: Optional[Dict[str, Any]] = None,
        use_processed_data: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecuta una tarea autónoma usando los datos procesados con IDP.
        
        Tipos de tareas soportadas:
        - análisis: Analizar datos y generar insights
        - automatización: Automatizar procesos empresariales
        - integración: Integrar con sistemas externos
        - generación: Generar contenido, informes, etc.
        - optimización: Optimizar procesos y recursos
        """
        print(f"\n{'='*60}")
        print(f"🤖 EJECUTANDO TAREA AUTÓNOMA: {task_type}")
        print(f"{'='*60}\n")
        print(f"📝 Tarea: {task_description}\n")
        
        context = context or {}
        
        # Agregar datos procesados con IDP al contexto
        if use_processed_data and self.idp_results:
            context["idp_data"] = {
                file_name: {
                    "document_type": result.document_type,
                    "entities": result.entities,
                    "key_metrics": result.key_metrics,
                    "structured_content": result.structured_content
                }
                for file_name, result in self.idp_results.items()
            }
            print(f"📊 Usando datos IDP de {len(self.idp_results)} documentos procesados")
        
        # Determinar herramientas necesarias
        selected_tools = self._select_tools_for_task(task_description, task_type)
        print(f"🔧 Herramientas seleccionadas: {', '.join(selected_tools)}\n")
        
        # Ejecutar tarea
        results = []
        for tool_name in selected_tools:
            tool = self.tools[tool_name]
            print(f"⚙️ Ejecutando herramienta: {tool_name}...")
            
            # Extraer parámetros usando LLM
            parameters = self._extract_tool_parameters(
                task_description, tool, context, task_type
            )
            
            try:
                result = tool.execute(**parameters)
                results.append({
                    "tool": tool_name,
                    "result": result,
                    "success": result.success if hasattr(result, 'success') else True
                })
                print(f"   ✅ {tool_name} completado")
            except Exception as e:
                results.append({
                    "tool": tool_name,
                    "result": None,
                    "success": False,
                    "error": str(e)
                })
                print(f"   ❌ {tool_name} falló: {str(e)[:100]}")
        
        # Generar resumen usando LLM
        summary = self._generate_task_summary(task_description, results, context)
        
        return {
            "success": any(r["success"] for r in results),
            "task_description": task_description,
            "task_type": task_type,
            "tools_used": selected_tools,
            "results": results,
            "summary": summary,
            "idp_data_used": len(self.idp_results) if use_processed_data else 0
        }
    
    def _select_tools_for_task(self, task_description: str, task_type: str) -> List[str]:
        """Selecciona herramientas apropiadas para la tarea."""
        selected = []
        task_lower = task_description.lower()
        
        # Detectar palabras clave específicas en la tarea
        if any(word in task_lower for word in ["email", "correo", "enviar", "mail", "notificar"]):
            if "email" not in selected:
                selected.append("email")
        
        if any(word in task_lower for word in ["reporte", "report", "informe", "generar reporte"]):
            if "report" not in selected:
                selected.append("report")
        
        if any(word in task_lower for word in ["presentación", "presentation", "slides", "diapositivas"]):
            if "presentation" not in selected:
                selected.append("presentation")
        
        if any(word in task_lower for word in ["programar", "schedule", "tarea programada", "cron"]):
            if "scheduler" not in selected:
                selected.append("scheduler")
        
        if any(word in task_lower for word in ["integrar", "integration", "conectar", "api"]):
            if "integration" not in selected:
                selected.append("integration")
        
        if any(word in task_lower for word in ["tabla", "table", "análisis de datos", "analizar datos"]):
            if "table_analysis" not in selected:
                selected.append("table_analysis")
        
        # Detectar advertising y marketing
        if any(word in task_lower for word in ["advertising", "publicidad", "anuncio", "ad", "campaña publicitaria", "ad campaign"]):
            if "advertising" not in selected:
                selected.append("advertising")
        
        if any(word in task_lower for word in ["marketing", "campaña marketing", "marketing campaign", "tiktok", "meta", "facebook ads", "instagram ads"]):
            if "marketing" not in selected:
                selected.append("marketing")
        
        # Si no se detectó ninguna herramienta específica, usar selección por tipo
        if not selected:
            task_type_mapping = {
                "análisis": ["table_analysis", "report"],
                "automatización": ["scheduler", "email"],
                "integración": ["integration"],
                "generación": ["report", "email", "advertising"],
                "optimización": ["table_analysis", "report", "advertising"],
                "marketing": ["advertising", "email"],
                "sales": ["email", "advertising"]
            }
            suggested_tools = task_type_mapping.get(task_type, ["report"])
            selected = suggested_tools[:1]  # Solo la primera herramienta sugerida
        
        # También verificar con can_handle para herramientas que lo soporten
        for tool_name, tool in self.tools.items():
            if tool.can_handle(task_description):
                if tool_name not in selected:
                    selected.insert(0, tool_name)  # Priorizar herramientas que can_handle
        
        return selected if selected else ["email"]  # Fallback a email
    
    def _extract_tool_parameters(
        self,
        task_description: str,
        tool: Any,
        context: Dict[str, Any],
        task_type: str
    ) -> Dict[str, Any]:
        """Extrae parámetros para herramientas usando LLM."""
        idp_context = ""
        if context.get("idp_data"):
            idp_context = f"\n\nDatos IDP disponibles:\n{json.dumps(context['idp_data'], indent=2)[:2000]}"
        
        # Parámetros específicos por herramienta
        tool_params_guide = {
            "email_sender": {
                "required": ["to", "subject", "body"],
                "description": "Para enviar emails necesitas: 'to' (email del destinatario), 'subject' (asunto), 'body' (cuerpo del mensaje). Opcional: 'campaign_name', 'personalize', 'lead_data', 'follow_up_days'"
            },
            "advanced_email": {
                "required": ["to", "subject", "body"],
                "description": """Email avanzado con funcionalidades:
                - 'to': email(s) destinatario(s)
                - 'subject': asunto
                - 'body': mensaje
                - 'campaign_name': nombre de campaña (opcional)
                - 'personalize': true/false para personalización
                - 'lead_data': datos del lead para personalizar
                - 'follow_up_days': días para follow-up automático
                - 'support_ticket_id': ID de ticket de soporte
                - 'faq_category': categoría FAQ"""
            },
            "report": {
                "required": ["data", "title"],
                "description": "Para generar reportes necesitas: 'data' (datos a reportar), 'title' (título del reporte)"
            },
            "presentation": {
                "required": ["title", "slides"],
                "description": "Para crear presentaciones necesitas: 'title' (título), 'slides' (lista de diapositivas)"
            },
            "advertising": {
                "required": ["action"],
                "description": """Para advertising y marketing necesitas:
                - 'action': acción a realizar (create_campaign, optimize_campaign, generate_creative, create_audience, analyze_performance)
                - 'campaign_name': nombre de la campaña
                - 'platform': plataforma (tiktok, meta, google_ads)
                - 'budget': presupuesto en dólares
                - 'objective': objetivo (awareness, conversions, installs, engagement)
                - 'audience': datos de audiencia (edad, intereses, ubicación, etc.)
                - 'creative_content': contenido creativo
                - 'optimization_goal': meta de optimización (ej: 'drive installs under $4.50')"""
            },
            "marketing": {
                "required": ["action"],
                "description": "Mismo que advertising - herramienta de marketing y publicidad"
            }
        }
        
        tool_name = tool.get_name()
        params_guide = tool_params_guide.get(tool_name, {})
        required_params = params_guide.get("required", [])
        params_description = params_guide.get("description", "")
        
        prompt = f"""Eres un asistente experto que extrae parámetros específicos para herramientas de Agentic AI.

TAREA DEL USUARIO: {task_description}
TIPO DE TAREA: {task_type}
HERRAMIENTA: {tool_name}
DESCRIPCIÓN: {tool.get_description()}
{params_description}

INSTRUCCIONES CRÍTICAS:
1. Analiza la tarea del usuario y extrae TODOS los parámetros necesarios
2. Para emails: extrae 'to' (destinatario), 'subject' (asunto), 'body' (mensaje)
3. Si la tarea menciona un email, úsalo como 'to'
4. Si la tarea menciona un asunto, úsalo como 'subject'
5. Si la tarea menciona un mensaje, úsalo como 'body'
6. Sé específico y exacto con los valores

{idp_context}

IMPORTANTE: Retorna ÚNICAMENTE un objeto JSON válido con los parámetros extraídos.
Ejemplo para email: {{"to": "email@ejemplo.com", "subject": "Asunto", "body": "Mensaje"}}

JSON con parámetros:"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            text = response.content.strip()
            
            # Limpiar respuesta JSON
            if text.startswith("```json"):
                text = text.replace("```json", "").replace("```", "").strip()
            elif text.startswith("```"):
                text = text.replace("```", "").strip()
            
            # Buscar JSON en la respuesta
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
            if json_match:
                params = json.loads(json_match.group(0))
                # Combinar con contexto pero priorizar parámetros extraídos
                final_params = {**context, **params}
                return final_params
            
            # Fallback: intentar extraer manualmente para emails
            if tool_name in ["email_sender", "advanced_email", "email"]:
                import re
                # Extraer email
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', task_description)
                to_email = email_match.group(0) if email_match else context.get("recipient", "")
                
                # Extraer asunto
                subject_match = re.search(r'asunto[:\s]+["\']?([^"\']+)["\']?', task_description, re.IGNORECASE)
                if not subject_match:
                    subject_match = re.search(r'subject[:\s]+["\']?([^"\']+)["\']?', task_description, re.IGNORECASE)
                subject = subject_match.group(1).strip() if subject_match else context.get("subject", "Sin asunto")
                
                # Extraer mensaje/cuerpo
                body_match = re.search(r'mensaje[:\s]+["\']?([^"\']+)["\']?', task_description, re.IGNORECASE)
                if not body_match:
                    body_match = re.search(r'message[:\s]+["\']?([^"\']+)["\']?', task_description, re.IGNORECASE)
                if not body_match:
                    body_match = re.search(r'el mensaje[:\s]+["\']?([^"\']+)["\']?', task_description, re.IGNORECASE)
                body = body_match.group(1).strip() if body_match else context.get("body", task_description)
                
                if to_email:
                    return {
                        "to": to_email,
                        "subject": subject,
                        "body": body,
                        **context
                    }
            
            # Fallback para advertising/marketing
            if tool_name in ["advertising", "marketing"]:
                import re
                # Detectar acción
                action = "create_campaign"
                if "optimizar" in task_description.lower() or "optimize" in task_description.lower():
                    action = "optimize_campaign"
                elif "crear" in task_description.lower() or "create" in task_description.lower():
                    action = "create_campaign"
                elif "generar" in task_description.lower() or "generate" in task_description.lower():
                    action = "generate_creative"
                elif "analizar" in task_description.lower() or "analyze" in task_description.lower():
                    action = "analyze_performance"
                
                # Detectar plataforma
                platform = "meta"
                if "tiktok" in task_description.lower():
                    platform = "tiktok"
                elif "google" in task_description.lower():
                    platform = "google_ads"
                
                # Extraer presupuesto
                budget_match = re.search(r'\$?(\d+(?:\.\d+)?)', task_description)
                budget = float(budget_match.group(1)) if budget_match else 100.0
                
                # Extraer objetivo
                objective = "awareness"
                if "conversión" in task_description.lower() or "conversion" in task_description.lower():
                    objective = "conversions"
                elif "instalación" in task_description.lower() or "install" in task_description.lower():
                    objective = "installs"
                elif "engagement" in task_description.lower():
                    objective = "engagement"
                
                return {
                    "action": action,
                    "platform": platform,
                    "budget": budget,
                    "objective": objective,
                    **context
                }
            
            return {"task_description": task_description, **context}
        except Exception as e:
            print(f"   ⚠️ Error extrayendo parámetros: {str(e)[:100]}")
            # Fallback básico
            return {"task_description": task_description, **context}
    
    def _generate_task_summary(
        self,
        task_description: str,
        results: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """Genera un resumen de la ejecución de la tarea."""
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        
        summary = f"## Resumen de Tarea Autónoma\n\n"
        summary += f"**Tarea:** {task_description}\n\n"
        summary += f"**Herramientas ejecutadas:** {len(results)}\n"
        summary += f"**Exitosas:** {len(successful)}\n"
        summary += f"**Fallidas:** {len(failed)}\n\n"
        
        if successful:
            summary += "### Operaciones Exitosas:\n\n"
            for r in successful:
                tool_result = r.get("result")
                if tool_result and hasattr(tool_result, 'message'):
                    summary += f"- **{r['tool']}**: {tool_result.message}\n"
                else:
                    summary += f"- **{r['tool']}**: Completado exitosamente\n"
        
        if failed:
            summary += "\n### Operaciones Fallidas:\n\n"
            for r in failed:
                error = r.get("error", "Error desconocido")
                summary += f"- **{r['tool']}**: {error}\n"
        
        if context.get("idp_data"):
            summary += f"\n**Datos IDP utilizados:** {len(context['idp_data'])} documentos\n"
        
        return summary
    
    def get_idp_summary(self) -> str:
        """Obtiene un resumen de todos los documentos procesados con IDP."""
        if not self.idp_results:
            return "No hay documentos procesados con IDP."
        
        summary = f"## Resumen IDP: {len(self.idp_results)} Documentos Procesados\n\n"
        
        for file_name, result in self.idp_results.items():
            summary += f"### {Path(file_name).name}\n\n"
            summary += f"- **Tipo:** {result.document_type}\n"
            summary += f"- **Entidades:** {len(result.entities)}\n"
            summary += f"- **Métricas:** {len(result.key_metrics)}\n"
            if result.entities:
                summary += f"- **Entidades principales:** {', '.join(result.entities[:5])}\n"
            summary += "\n"
        
        return summary
    
    # Métodos de gestión avanzada de emails
    
    def create_email_campaign(
        self,
        campaign_name: str,
        recipients: List[str],
        subject_template: str,
        body_template: str,
        schedule_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crea una nueva campaña de email."""
        email_tool = self.tools.get("advanced_email") or self.tools.get("email")
        if hasattr(email_tool, "create_campaign"):
            result = email_tool.create_campaign(
                campaign_name=campaign_name,
                recipients=recipients,
                subject_template=subject_template,
                body_template=body_template,
                schedule_date=schedule_date
            )
            return {
                "success": result.success,
                "message": result.message,
                "data": result.data
            }
        return {"success": False, "message": "Advanced email tool not available"}
    
    def add_lead(
        self,
        email: str,
        name: Optional[str] = None,
        company: Optional[str] = None,
        industry: Optional[str] = None,
        role: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Agrega un nuevo lead."""
        email_tool = self.tools.get("advanced_email") or self.tools.get("email")
        if hasattr(email_tool, "add_lead"):
            result = email_tool.add_lead(
                email=email,
                name=name,
                company=company,
                industry=industry,
                role=role,
                **kwargs
            )
            return {
                "success": result.success,
                "message": result.message,
                "data": result.data
            }
        return {"success": False, "message": "Advanced email tool not available"}
    
    def get_email_analytics(self) -> Dict[str, Any]:
        """Obtiene analytics de emails."""
        email_tool = self.tools.get("advanced_email") or self.tools.get("email")
        if hasattr(email_tool, "get_email_analytics"):
            return email_tool.get_email_analytics()
        return {}
    
    def get_campaign_stats(self, campaign_name: str) -> Dict[str, Any]:
        """Obtiene estadísticas de una campaña."""
        email_tool = self.tools.get("advanced_email") or self.tools.get("email")
        if hasattr(email_tool, "get_campaign_stats"):
            return email_tool.get_campaign_stats(campaign_name)
        return {}
    
    # Métodos de gestión avanzada de Advertising y Marketing
    
    def create_ad_campaign(
        self,
        campaign_name: str,
        platform: str,
        budget: float,
        objective: str,
        audience: Optional[Dict[str, Any]] = None,
        creative_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crea una nueva campaña publicitaria."""
        ad_tool = self.tools.get("advertising") or self.tools.get("marketing")
        if ad_tool:
            result = ad_tool.execute(
                action="create_campaign",
                campaign_name=campaign_name,
                platform=platform,
                budget=budget,
                objective=objective,
                audience=audience or {},
                creative_content=creative_content or ""
            )
            return {
                "success": result.success,
                "message": result.message,
                "data": result.data
            }
        return {"success": False, "message": "Advertising tool not available"}
    
    def optimize_ad_campaign(
        self,
        campaign_name: str,
        optimization_goal: Optional[str] = None
    ) -> Dict[str, Any]:
        """Optimiza una campaña publicitaria en tiempo real."""
        ad_tool = self.tools.get("advertising") or self.tools.get("marketing")
        if ad_tool:
            result = ad_tool.execute(
                action="optimize_campaign",
                campaign_name=campaign_name,
                optimization_goal=optimization_goal
            )
            return {
                "success": result.success,
                "message": result.message,
                "data": result.data
            }
        return {"success": False, "message": "Advertising tool not available"}
    
    def generate_ad_creative(
        self,
        objective: str,
        audience: Optional[Dict[str, Any]] = None,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Genera contenido creativo para anuncios."""
        ad_tool = self.tools.get("advertising") or self.tools.get("marketing")
        if ad_tool:
            result = ad_tool.execute(
                action="generate_creative",
                objective=objective,
                audience=audience or {},
                creative_content=content or ""
            )
            return {
                "success": result.success,
                "message": result.message,
                "data": result.data
            }
        return {"success": False, "message": "Advertising tool not available"}
    
    def analyze_ad_performance(
        self,
        campaign_name: str
    ) -> Dict[str, Any]:
        """Analiza el performance de una campaña publicitaria."""
        ad_tool = self.tools.get("advertising") or self.tools.get("marketing")
        if ad_tool:
            result = ad_tool.execute(
                action="analyze_performance",
                campaign_name=campaign_name
            )
            return {
                "success": result.success,
                "message": result.message,
                "data": result.data
            }
        return {"success": False, "message": "Advertising tool not available"}

