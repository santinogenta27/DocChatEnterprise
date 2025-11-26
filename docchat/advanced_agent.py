"""Advanced autonomous agent that can execute complete workflows."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from .config import AppConfig
from .tools import (
    EmailTool, ReportTool, DatabaseTool, PresentationTool,
    IntegrationTool, TableAnalysisTool, SchedulerTool
)
from .mass_processor import MassDocumentProcessor
from .retriever_builder import RetrieverBuilder
from .workflow import AgentWorkflow


class AdvancedAutonomousAgent:
    """Advanced agent that can execute complete workflows autonomously."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.llm = ChatOpenAI(
            model=config.agentic_model,
            temperature=0.3,
            api_key=config.openai_api_key
        )
        
        # Initialize tools
        self.tools = {
            "email": EmailTool(config),
            "report": ReportTool(config),
            "database": DatabaseTool(config),
            "presentation": PresentationTool(config),
            "integration": IntegrationTool(config),
            "table_analysis": TableAnalysisTool(config),
            "scheduler": SchedulerTool(config),
        }
        
        # Initialize document processors
        self.mass_processor = MassDocumentProcessor(config)
        self.retriever_builder = RetrieverBuilder(config)
        self.workflow = AgentWorkflow(config)
    
    def execute_complete_workflow(
        self,
        task_description: str,
        files: Optional[List] = None,
        output_format: str = "all",  # "all", "report", "presentation", "excel"
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a complete workflow: analyze documents + generate outputs.
        
        Example tasks:
        - "Analiza estos 80 PDFs y genera informe + PPT + Excel con los hallazgos"
        - "Procesa todos los documentos y crea un reporte ejecutivo"
        """
        results = {
            "task": task_description,
            "status": "processing",
            "outputs": [],
            "errors": []
        }
        
        try:
            # Step 1: Process documents if provided
            documents_data = None
            if files:
                # Process documents using massive batch processor
                # Files from Gradio are file objects, pass them directly
                chunks, metadata, analysis = self.mass_processor.process_massive_batch(
                    files,
                    enable_comparison=True
                )
                
                documents_data = {
                    "chunks": chunks,
                    "metadata": metadata,
                    "analysis": analysis
                }
                
                # Step 2: Generate insights using RAG
                insights = self._generate_insights(chunks, task_description)
                documents_data["insights"] = insights
            
            # Step 3: Generate outputs based on format
            if output_format == "all" or output_format == "report":
                report_result = self._generate_complete_report(
                    task_description,
                    documents_data,
                    format="excel"
                )
                if report_result.success and report_result.data:
                    results["outputs"].append({
                        "type": "report",
                        "path": report_result.data.get("path") if isinstance(report_result.data, dict) else str(report_result.data),
                        "format": "excel"
                    })
                elif not report_result.success:
                    results["errors"].append(f"Error generando reporte: {report_result.message}")
            
            if output_format == "all" or output_format == "presentation":
                presentation_result = self._generate_presentation(
                    task_description,
                    documents_data
                )
                if presentation_result.success and presentation_result.data:
                    results["outputs"].append({
                        "type": "presentation",
                        "path": presentation_result.data.get("path") if isinstance(presentation_result.data, dict) else str(presentation_result.data)
                    })
                elif not presentation_result.success:
                    results["errors"].append(f"Error generando presentación: {presentation_result.message}")
            
            if output_format == "all" or output_format == "excel":
                excel_result = self._generate_excel_analysis(
                    task_description,
                    documents_data
                )
                if excel_result.success and excel_result.data:
                    results["outputs"].append({
                        "type": "excel",
                        "path": excel_result.data.get("path") if isinstance(excel_result.data, dict) else str(excel_result.data)
                    })
                elif not excel_result.success:
                    results["errors"].append(f"Error generando Excel: {excel_result.message}")
            
            results["status"] = "completed"
            results["summary"] = f"Generated {len(results['outputs'])} output files"
            
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(str(e))
        
        return results
    
    def _generate_insights(self, chunks: List, task_description: str) -> Dict:
        """Generate insights from documents using RAG."""
        if not chunks:
            return {}
        
        # Build retriever
        retriever = self.retriever_builder.build_hybrid_retriever(chunks)
        
        # Generate insights query
        insights_query = f"""
        Basado en los documentos proporcionados, genera insights clave sobre: {task_description}
        
        Proporciona:
        1. Hallazgos principales
        2. Tendencias identificadas
        3. Recomendaciones
        4. Datos numéricos importantes
        5. Conclusiones
        """
        
        result = self.workflow.run(insights_query, retriever)
        
        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "relevance": result["relevance"]
        }
    
    def _generate_complete_report(
        self,
        task_description: str,
        documents_data: Optional[Dict],
        format: str = "excel"
    ) -> Dict:
        """Generate a complete report."""
        report_tool = self.tools["report"]
        
        # Prepare report data
        report_data = {
            "task": task_description,
            "generated_at": datetime.now().isoformat(),
            "summary": "Análisis completo de documentos"
        }
        
        if documents_data:
            report_data.update({
                "total_documents": len(documents_data.get("metadata", [])),
                "total_chunks": len(documents_data.get("chunks", [])),
                "insights": documents_data.get("insights", {}),
                "comparative_analysis": documents_data.get("analysis")
            })
        
        # Generate report
        output_dir = self.config.cache_dir / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = report_tool.execute(
            data=report_data,
            format=format,
            output_path=str(output_path),
            title=f"Reporte: {task_description[:50]}"
        )
        
        return result
    
    def _generate_presentation(
        self,
        task_description: str,
        documents_data: Optional[Dict]
    ) -> Dict:
        """Generate presentation slides."""
        presentation_tool = self.tools["presentation"]
        
        # Generate slides content
        slides = []
        
        # Title slide
        slides.append({
            "title": "Análisis de Documentos",
            "content": task_description,
            "notes": "Presentación generada automáticamente"
        })
        
        if documents_data:
            # Summary slide
            metadata = documents_data.get("metadata", [])
            if isinstance(metadata, list):
                total_docs = len(metadata)
            else:
                total_docs = 0
            
            slides.append({
                "title": "Resumen",
                "content": f"Total documentos analizados: {total_docs}\nTotal chunks: {len(documents_data.get('chunks', []))}",
                "notes": "Estadísticas del análisis"
            })
            
            # Insights slide
            insights = documents_data.get("insights", {})
            if insights.get("answer"):
                slides.append({
                    "title": "Hallazgos Principales",
                    "content": insights["answer"][:500],
                    "notes": "Insights generados por IA"
                })
        
        # Generate presentation
        output_dir = self.config.cache_dir / "presentations"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"presentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = presentation_tool.execute(
            title="Análisis de Documentos",
            slides=slides,
            output_path=str(output_path)
        )
        
        return result
    
    def _generate_excel_analysis(
        self,
        task_description: str,
        documents_data: Optional[Dict]
    ) -> Dict:
        """Generate Excel analysis."""
        report_tool = self.tools["report"]
        
        # Prepare Excel data
        excel_data = []
        
        if documents_data:
            metadata = documents_data.get("metadata", [])
            if isinstance(metadata, list):
                for meta in metadata:
                    if hasattr(meta, 'file_name'):
                        # DocumentMetadata object
                        excel_data.append({
                            "Documento": meta.file_name,
                            "Chunks": meta.chunk_count,
                            "Tamaño (MB)": round(meta.size_mb, 2),
                            "Tiempo (s)": round(meta.processing_time, 2),
                            "Estado": "OK" if not meta.errors else "Error"
                        })
                    elif isinstance(meta, dict):
                        # Dictionary format
                        excel_data.append({
                            "Documento": meta.get("file_name", "Unknown"),
                            "Chunks": meta.get("chunk_count", 0),
                            "Tamaño (MB)": round(meta.get("size_mb", 0), 2),
                            "Tiempo (s)": round(meta.get("processing_time", 0), 2),
                            "Estado": "OK" if not meta.get("errors") else "Error"
                        })
        
        # Generate Excel
        output_dir = self.config.cache_dir / "analysis"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = report_tool.execute(
            data=excel_data,
            format="excel",
            output_path=str(output_path),
            title="Análisis de Documentos"
        )
        
        return result

