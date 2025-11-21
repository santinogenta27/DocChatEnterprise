"""
Procesador Automático de Datos
Detecta automáticamente qué hacer con los datos subidos y ejecuta agentes autónomos
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import json
from openai import OpenAI
from .agent_orchestrator import AgentOrchestrator


class AutoDataProcessor:
    """
    Procesa datos automáticamente y ejecuta agentes sin intervención del usuario
    """
    
    def __init__(self, orchestrator: AgentOrchestrator, llm_client: OpenAI):
        self.orchestrator = orchestrator
        self.llm_client = llm_client
        self.auto_tasks = []
    
    def detect_data_type(self, file_path: str, sample_data: Any = None) -> Dict[str, Any]:
        """
        Detecta automáticamente el tipo de datos y qué análisis hacer
        """
        file_ext = file_path.lower().split('.')[-1] if '.' in file_path else ''
        
        # Leer muestra de datos
        if sample_data is None:
            try:
                if file_ext == 'csv':
                    df = pd.read_csv(file_path, nrows=10)
                    sample_data = df.to_dict('records')
                elif file_ext == 'txt':
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        sample_data = f.read(1000)
                else:
                    sample_data = str(file_path)
            except:
                sample_data = str(file_path)
        
        # Usar LLM para detectar tipo y sugerir tareas
        prompt = f"""
        Analiza estos datos y determina:
        1. Tipo de datos (políticas, contratos, reportes, datos financieros, etc.)
        2. Qué análisis automáticos serían útiles
        3. Qué información clave extraer
        
        Datos de muestra:
        {str(sample_data)[:500]}
        
        Responde en JSON:
        {{
            "data_type": "tipo de dato",
            "auto_tasks": ["tarea 1", "tarea 2", "tarea 3"],
            "key_insights_to_extract": ["insight 1", "insight 2"]
        }}
        """
        
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            result = json.loads(response.choices[0].message.content)
            return result
        except:
            # Fallback si falla el LLM
            return {
                "data_type": "documento general",
                "auto_tasks": [
                    "Extraer información clave",
                    "Identificar temas principales",
                    "Generar resumen ejecutivo"
                ],
                "key_insights_to_extract": ["temas principales", "información importante"]
            }
    
    def generate_auto_tasks(self, data_type: str, auto_tasks_suggested: List[str], 
                           file_name: str) -> List[Dict[str, str]]:
        """
        Genera tareas automáticas específicas basadas en el tipo de datos
        """
        tasks = []
        
        # Tareas base que siempre se ejecutan
        base_tasks = [
            {
                "name": "Análisis de Contenido",
                "description": f"Analiza el contenido de {file_name} y extrae información clave",
                "priority": "high"
            },
            {
                "name": "Extracción de Temas",
                "description": f"Identifica los temas principales en {file_name}",
                "priority": "high"
            },
            {
                "name": "Resumen Ejecutivo",
                "description": f"Genera un resumen ejecutivo de {file_name}",
                "priority": "medium"
            }
        ]
        
        # Agregar tareas específicas según el tipo de datos
        if "política" in data_type.lower() or "policy" in data_type.lower():
            base_tasks.append({
                "name": "Análisis de Políticas",
                "description": f"Extrae y analiza las políticas mencionadas en {file_name}",
                "priority": "high"
            })
        
        if "contrato" in data_type.lower() or "contract" in data_type.lower():
            base_tasks.append({
                "name": "Análisis de Contrato",
                "description": f"Identifica cláusulas clave y términos importantes en {file_name}",
                "priority": "high"
            })
        
        if "financiero" in data_type.lower() or "financial" in data_type.lower():
            base_tasks.append({
                "name": "Análisis Financiero",
                "description": f"Extrae métricas y datos financieros de {file_name}",
                "priority": "high"
            })
        
        # Agregar tareas sugeridas por el LLM
        for suggested_task in auto_tasks_suggested[:3]:  # Limitar a 3
            base_tasks.append({
                "name": suggested_task,
                "description": f"{suggested_task} para {file_name}",
                "priority": "medium"
            })
        
        return base_tasks
    
    def process_file_automatically(self, file_path: str, collection_name: str = "general_vectors") -> Dict[str, Any]:
        """
        Procesa un archivo automáticamente: detecta tipo, genera tareas y ejecuta agentes
        """
        file_name = file_path.split('/')[-1] if '/' in file_path else file_path.split('\\')[-1]
        
        # 1. Detectar tipo de datos
        detection = self.detect_data_type(file_path)
        data_type = detection.get("data_type", "documento general")
        suggested_tasks = detection.get("auto_tasks", [])
        
        # 2. Generar tareas automáticas
        auto_tasks = self.generate_auto_tasks(data_type, suggested_tasks, file_name)
        
        # 3. Ejecutar tareas automáticamente
        results = {
            "file_name": file_name,
            "data_type": data_type,
            "tasks_executed": [],
            "summary": {}
        }
        
        # Ejecutar tareas de alta prioridad primero
        high_priority = [t for t in auto_tasks if t["priority"] == "high"]
        medium_priority = [t for t in auto_tasks if t["priority"] == "medium"]
        
        all_tasks = high_priority + medium_priority
        
        for task in all_tasks[:5]:  # Limitar a 5 tareas para no exceder tiempo/costo
            try:
                result = self.orchestrator.execute_task_autonomously(
                    task_description=task["description"],
                    context={
                        "collection_name": collection_name,
                        "file_name": file_name,
                        "data_type": data_type,
                        "top_k": 10
                    }
                )
                
                results["tasks_executed"].append({
                    "task_name": task["name"],
                    "status": result["status"],
                    "output": result.get("output", {}).get("final_output", "") if result.get("output") else ""
                })
                
            except Exception as e:
                results["tasks_executed"].append({
                    "task_name": task["name"],
                    "status": "failed",
                    "error": str(e)
                })
        
        # 4. Generar resumen consolidado
        results["summary"] = self._generate_consolidated_summary(results)
        
        return results
    
    def _generate_consolidated_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera un resumen consolidado de todos los análisis automáticos
        """
        successful_tasks = [t for t in results["tasks_executed"] if t["status"] == "completed"]
        
        if not successful_tasks:
            return {
                "status": "no_results",
                "message": "No se pudieron completar análisis automáticos"
            }
        
        # Combinar outputs de todas las tareas exitosas
        all_outputs = "\n\n".join([
            f"**{t['task_name']}:**\n{t.get('output', '')}"
            for t in successful_tasks if t.get('output')
        ])
        
        # Generar resumen final usando LLM
        prompt = f"""
        Crea un resumen ejecutivo consolidado de estos análisis automáticos:
        
        {all_outputs}
        
        El resumen debe:
        1. Ser conciso (máximo 300 palabras)
        2. Destacar los hallazgos más importantes
        3. Ser fácil de entender
        4. Incluir insights clave
        """
        
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            summary_text = response.choices[0].message.content
            
            return {
                "status": "success",
                "summary_text": summary_text,
                "tasks_completed": len(successful_tasks),
                "total_tasks": len(results["tasks_executed"])
            }
        except:
            return {
                "status": "partial",
                "summary_text": all_outputs[:500] + "...",
                "tasks_completed": len(successful_tasks),
                "total_tasks": len(results["tasks_executed"])
            }

