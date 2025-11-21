"""
Herramientas que los agentes autónomos pueden usar para interactuar con los datos
"""

from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
import chromadb
import pandas as pd
import json


class AgentTool(ABC):
    """Clase base para herramientas de agentes"""
    
    @abstractmethod
    def name(self) -> str:
        """Nombre de la herramienta"""
        pass
    
    @abstractmethod
    def description(self) -> str:
        """Descripción de lo que hace la herramienta"""
        pass
    
    @abstractmethod
    def can_handle(self, step_description: str) -> bool:
        """Determina si esta herramienta puede manejar un paso"""
        pass
    
    @abstractmethod
    def execute(self, step_description: str, context: Dict, previous_results: List) -> Any:
        """Ejecuta la herramienta"""
        pass


class DataRetrievalTool(AgentTool):
    """Herramienta para recuperar datos de ChromaDB"""
    
    def __init__(self, chroma_client: chromadb.Client, collection_name: str = None):
        self.chroma_client = chroma_client
        self.collection_name = collection_name
    
    def name(self) -> str:
        return "data_retrieval"
    
    def description(self) -> str:
        return "Recupera documentos relevantes de la base de datos vectorial usando búsqueda semántica"
    
    def can_handle(self, step_description: str) -> bool:
        keywords = ["recuperar", "buscar", "encontrar", "obtener", "datos", "documentos", "información"]
        return any(keyword in step_description.lower() for keyword in keywords)
    
    def execute(self, step_description: str, context: Dict, previous_results: List) -> Any:
        """
        Ejecuta búsqueda en ChromaDB basada en la descripción del paso
        """
        # Extraer query de la descripción del paso
        query = self._extract_query_from_step(step_description)
        
        if not query:
            return {"error": "No se pudo extraer una consulta de la descripción del paso"}
        
        try:
            collection = self.chroma_client.get_collection(
                name=self.collection_name or context.get("collection_name", "general_vectors")
            )
            
            results = collection.query(
                query_texts=[query],
                n_results=context.get("top_k", 10)
            )
            
            documents = results.get("documents", [[]])[0] if results.get("documents") else []
            ids = results.get("ids", [[]])[0] if results.get("ids") else []
            distances = results.get("distances", [[]])[0] if results.get("distances") else []
            
            return {
                "query": query,
                "documents_found": len(documents),
                "documents": [
                    {
                        "id": ids[i] if i < len(ids) else f"doc_{i}",
                        "content": doc,
                        "distance": distances[i] if i < len(distances) else None
                    }
                    for i, doc in enumerate(documents)
                ]
            }
        except Exception as e:
            return {"error": f"Error en recuperación de datos: {str(e)}"}
    
    def _extract_query_from_step(self, step_description: str) -> Optional[str]:
        """Extrae la consulta de búsqueda de la descripción del paso"""
        # Buscar patrones como "buscar X", "recuperar información sobre Y"
        import re
        
        patterns = [
            r"buscar\s+(.+?)(?:\.|$|y|o)",
            r"recuperar\s+(.+?)(?:\.|$|y|o)",
            r"encontrar\s+(.+?)(?:\.|$|y|o)",
            r"obtener\s+(.+?)(?:\.|$|y|o)",
            r"sobre\s+(.+?)(?:\.|$|y|o)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, step_description.lower())
            if match:
                return match.group(1).strip()
        
        # Si no hay patrón claro, usar toda la descripción
        return step_description


class DataAnalysisTool(AgentTool):
    """Herramienta para analizar datos extraídos"""
    
    def name(self) -> str:
        return "data_analysis"
    
    def description(self) -> str:
        return "Analiza datos extraídos para encontrar patrones, tendencias o insights"
    
    def can_handle(self, step_description: str) -> bool:
        keywords = ["analizar", "examinar", "evaluar", "comparar", "patrón", "tendencia", "insight"]
        return any(keyword in step_description.lower() for keyword in keywords)
    
    def execute(self, step_description: str, context: Dict, previous_results: List) -> Any:
        """
        Analiza los datos de resultados previos
        """
        # Recopilar todos los documentos de resultados previos
        all_documents = []
        for result in previous_results:
            if isinstance(result, dict) and "documents" in result.get("result", {}):
                all_documents.extend(result["result"]["documents"])
        
        if not all_documents:
            return {"error": "No hay datos para analizar"}
        
        # Extraer información estructurada
        analysis = {
            "total_documents": len(all_documents),
            "topics_found": self._extract_topics(all_documents),
            "key_entities": self._extract_entities(all_documents),
            "summary": self._generate_summary(all_documents, step_description)
        }
        
        return analysis
    
    def _extract_topics(self, documents: List[Dict]) -> List[str]:
        """Extrae temas principales de los documentos"""
        # Implementación simplificada - en producción usaría NLP más avanzado
        topics = set()
        for doc in documents:
            content = doc.get("content", "").lower()
            # Buscar palabras clave comunes
            if "política" in content or "policy" in content:
                topics.add("Políticas")
            if "proceso" in content or "process" in content:
                topics.add("Procesos")
            if "datos" in content or "data" in content:
                topics.add("Datos")
        return list(topics)
    
    def _extract_entities(self, documents: List[Dict]) -> List[str]:
        """Extrae entidades importantes"""
        # Implementación simplificada
        entities = set()
        for doc in documents:
            content = doc.get("content", "")
            # Buscar números, fechas, nombres propios, etc.
            import re
            numbers = re.findall(r'\d+', content)
            entities.update(numbers[:5])  # Limitar cantidad
        return list(entities)[:10]
    
    def _generate_summary(self, documents: List[Dict], step_description: str) -> str:
        """Genera un resumen de los documentos"""
        total_chars = sum(len(doc.get("content", "")) for doc in documents)
        return f"Se analizaron {len(documents)} documentos con un total de aproximadamente {total_chars} caracteres. " \
               f"Análisis enfocado en: {step_description}"


class ReportGenerationTool(AgentTool):
    """Herramienta para generar reportes estructurados"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def name(self) -> str:
        return "report_generation"
    
    def description(self) -> str:
        return "Genera reportes estructurados basados en datos analizados"
    
    def can_handle(self, step_description: str) -> bool:
        keywords = ["reporte", "resumen", "generar", "crear documento", "compilar"]
        return any(keyword in step_description.lower() for keyword in keywords)
    
    def execute(self, step_description: str, context: Dict, previous_results: List) -> Any:
        """
        Genera un reporte estructurado
        """
        # Recopilar todos los datos relevantes
        all_data = {
            "task_description": step_description,
            "context": context,
            "analysis_results": previous_results
        }
        
        # Generar reporte estructurado
        report = {
            "title": self._extract_title(step_description),
            "sections": self._organize_sections(previous_results),
            "key_findings": self._extract_key_findings(previous_results),
            "recommendations": self._generate_recommendations(previous_results, step_description)
        }
        
        return report
    
    def _extract_title(self, step_description: str) -> str:
        """Extrae un título del paso"""
        # Simplificado - usar primera parte de la descripción
        return step_description.split(".")[0] if "." in step_description else step_description
    
    def _organize_sections(self, previous_results: List) -> List[Dict]:
        """Organiza los resultados en secciones"""
        sections = []
        for i, result in enumerate(previous_results, 1):
            if isinstance(result, dict):
                sections.append({
                    "section_number": i,
                    "title": result.get("description", f"Sección {i}"),
                    "content": result.get("result", {})
                })
        return sections
    
    def _extract_key_findings(self, previous_results: List) -> List[str]:
        """Extrae hallazgos clave"""
        findings = []
        for result in previous_results:
            if isinstance(result, dict) and "result" in result:
                res = result["result"]
                if isinstance(res, dict):
                    if "summary" in res:
                        findings.append(res["summary"])
                    elif "key_entities" in res:
                        findings.append(f"Entidades encontradas: {', '.join(res['key_entities'][:5])}")
        return findings[:5]  # Limitar a 5 hallazgos principales
    
    def _generate_recommendations(self, previous_results: List, task_description: str) -> List[str]:
        """Genera recomendaciones basadas en los resultados"""
        # Implementación simplificada
        recommendations = [
            "Revisar los documentos encontrados para validar la información",
            "Considerar realizar análisis adicionales si se requiere más profundidad",
            "Documentar los hallazgos para referencia futura"
        ]
        return recommendations


class ComparisonTool(AgentTool):
    """Herramienta para comparar diferentes conjuntos de datos"""
    
    def name(self) -> str:
        return "comparison"
    
    def description(self) -> str:
        return "Compara diferentes conjuntos de datos o documentos para encontrar diferencias y similitudes"
    
    def can_handle(self, step_description: str) -> bool:
        keywords = ["comparar", "diferencias", "similitudes", "contrastar", "vs", "versus"]
        return any(keyword in step_description.lower() for keyword in keywords)
    
    def execute(self, step_description: str, context: Dict, previous_results: List) -> Any:
        """
        Compara datos de diferentes fuentes
        """
        # Agrupar resultados por fuente o tipo
        grouped_results = self._group_results(previous_results)
        
        if len(grouped_results) < 2:
            return {"error": "Se necesitan al menos dos conjuntos de datos para comparar"}
        
        comparison = {
            "sources_compared": len(grouped_results),
            "similarities": self._find_similarities(grouped_results),
            "differences": self._find_differences(grouped_results),
            "summary": self._generate_comparison_summary(grouped_results)
        }
        
        return comparison
    
    def _group_results(self, previous_results: List) -> Dict[str, List]:
        """Agrupa resultados por fuente"""
        groups = {}
        for i, result in enumerate(previous_results):
            source = f"source_{i}"
            if isinstance(result, dict) and "result" in result:
                if source not in groups:
                    groups[source] = []
                groups[source].append(result["result"])
        return groups
    
    def _find_similarities(self, grouped_results: Dict[str, List]) -> List[str]:
        """Encuentra similitudes entre grupos"""
        # Implementación simplificada
        return ["Ambos grupos contienen información estructurada", 
                "Los documentos comparten temas similares"]
    
    def _find_differences(self, grouped_results: Dict[str, List]) -> List[str]:
        """Encuentra diferencias entre grupos"""
        # Implementación simplificada
        return [f"El grupo {name} tiene {len(data)} elementos" 
                for name, data in grouped_results.items()]
    
    def _generate_comparison_summary(self, grouped_results: Dict[str, List]) -> str:
        """Genera un resumen de la comparación"""
        total_items = sum(len(data) for data in grouped_results.values())
        return f"Se compararon {len(grouped_results)} fuentes con un total de {total_items} elementos analizados."


