"""
NeuSym-RAG: Hybrid Neural Symbolic Retrieval with Multiview Structuring
Integra retrieval neural (vectorstore) y simbólico (SQL database) para PDF Q&A.

Basado en: "NeuSym-RAG: Hybrid Neural Symbolic Retrieval with Multiview Structuring for PDF Question Answering"
"""

from __future__ import annotations

import json
import sqlite3
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI


class ActionType(Enum):
    """Tipos de acciones que el agente puede ejecutar."""
    RETRIEVEFROMVECTORSTORE = "RetrieveFromVectorstore"
    RETRIEVEFROMDATABASE = "RetrieveFromDatabase"
    VIEWIMAGE = "ViewImage"
    CALCULATEEXPR = "CalculateExpr"
    GENERATEANSWER = "GenerateAnswer"


@dataclass
class Action:
    """Representa una acción ejecutable por el agente."""
    action_type: ActionType
    parameters: Dict[str, Any]
    thought: Optional[str] = None


@dataclass
class Observation:
    """Resultado de ejecutar una acción."""
    action_type: ActionType
    data: Any
    success: bool = True
    error: Optional[str] = None


class NeuSymRAG:
    """
    Sistema híbrido Neural-Symbolic RAG que combina:
    - Retrieval neural (vectorstore) para búsqueda semántica
    - Retrieval simbólico (SQL database) para consultas precisas
    - Multiview chunking (pages, sections, tables, figures, formulas)
    - Iterative agent interaction con acciones ejecutables
    """
    
    def __init__(
        self,
        config: Any,
        llm: BaseLanguageModel,
        vectorstore: Any,
        db_path: Optional[str] = None
    ):
        self.config = config
        self.llm = llm
        self.vectorstore = vectorstore
        self.db_path = db_path or str(Path(config.audit_log_dir) / "neusym_rag.db")
        
        # Inicializar base de datos DuckDB/SQLite
        self.db_conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_database_schema()
        
        # Historial de interacciones
        self.interaction_history: List[Dict[str, Any]] = []
        self.max_interactions = 20
        
    def _init_database_schema(self):
        """Inicializa el esquema de base de datos para almacenar PDFs parseados."""
        cursor = self.db_conn.cursor()
        
        # Tabla de metadata de papers
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                paper_id TEXT PRIMARY KEY,
                title TEXT,
                abstract TEXT,
                pub_year INTEGER,
                conference_abbreviation TEXT,
                authors TEXT,
                bibtex TEXT,
                tldr TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de páginas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                page_id TEXT PRIMARY KEY,
                paper_id TEXT,
                page_number INTEGER,
                page_content TEXT,
                page_summary TEXT,
                FOREIGN KEY (paper_id) REFERENCES metadata(paper_id)
            )
        """)
        
        # Tabla de secciones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sections (
                section_id TEXT PRIMARY KEY,
                paper_id TEXT,
                section_title TEXT,
                section_content TEXT,
                section_summary TEXT,
                page_number INTEGER,
                FOREIGN KEY (paper_id) REFERENCES metadata(paper_id)
            )
        """)
        
        # Tabla de imágenes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                image_id TEXT PRIMARY KEY,
                paper_id TEXT,
                page_number INTEGER,
                image_caption TEXT,
                image_summary TEXT,
                bounding_box TEXT,
                FOREIGN KEY (paper_id) REFERENCES metadata(paper_id)
            )
        """)
        
        # Tabla de tablas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tables (
                table_id TEXT PRIMARY KEY,
                paper_id TEXT,
                page_number INTEGER,
                table_caption TEXT,
                table_content TEXT,
                table_summary TEXT,
                bounding_box TEXT,
                FOREIGN KEY (paper_id) REFERENCES metadata(paper_id)
            )
        """)
        
        # Tabla de ecuaciones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equations (
                equation_id TEXT PRIMARY KEY,
                paper_id TEXT,
                page_number INTEGER,
                equation_content TEXT,
                FOREIGN KEY (paper_id) REFERENCES metadata(paper_id)
            )
        """)
        
        # Tabla de chunks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                paper_id TEXT,
                page_number INTEGER,
                text_content TEXT,
                chunk_index INTEGER,
                FOREIGN KEY (paper_id) REFERENCES metadata(paper_id)
            )
        """)
        
        # Tabla de referencias
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS references (
                ref_id TEXT PRIMARY KEY,
                paper_id TEXT,
                reference_content TEXT,
                FOREIGN KEY (paper_id) REFERENCES metadata(paper_id)
            )
        """)
        
        self.db_conn.commit()
    
    def parse_pdf_to_database(
        self,
        paper_id: str,
        pdf_path: str,
        metadata: Dict[str, Any],
        multiview_chunks: Dict[str, List[Any]]
    ):
        """
        Parsea un PDF y lo almacena en la base de datos con múltiples vistas.
        
        Args:
            paper_id: ID único del paper
            pdf_path: Ruta al PDF
            metadata: Metadata del paper (title, abstract, etc.)
            multiview_chunks: Diccionario con diferentes vistas:
                - pages: Lista de páginas
                - sections: Lista de secciones
                - tables: Lista de tablas
                - images: Lista de imágenes
                - equations: Lista de ecuaciones
                - chunks: Lista de chunks de texto
        """
        cursor = self.db_conn.cursor()
        
        # Insertar metadata
        cursor.execute("""
            INSERT OR REPLACE INTO metadata 
            (paper_id, title, abstract, pub_year, conference_abbreviation, authors, bibtex, tldr)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            paper_id,
            metadata.get("title"),
            metadata.get("abstract"),
            metadata.get("pub_year"),
            metadata.get("conference_abbreviation"),
            json.dumps(metadata.get("authors", [])),
            metadata.get("bibtex"),
            metadata.get("tldr")
        ))
        
        # Insertar páginas
        for page in multiview_chunks.get("pages", []):
            cursor.execute("""
                INSERT OR REPLACE INTO pages 
                (page_id, paper_id, page_number, page_content, page_summary)
                VALUES (?, ?, ?, ?, ?)
            """, (
                f"{paper_id}_page_{page.get('page_number')}",
                paper_id,
                page.get("page_number"),
                page.get("content"),
                page.get("summary")
            ))
        
        # Insertar secciones
        for section in multiview_chunks.get("sections", []):
            cursor.execute("""
                INSERT OR REPLACE INTO sections 
                (section_id, paper_id, section_title, section_content, section_summary, page_number)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                f"{paper_id}_section_{section.get('section_index')}",
                paper_id,
                section.get("title"),
                section.get("content"),
                section.get("summary"),
                section.get("page_number")
            ))
        
        # Insertar tablas
        for table in multiview_chunks.get("tables", []):
            cursor.execute("""
                INSERT OR REPLACE INTO tables 
                (table_id, paper_id, page_number, table_caption, table_content, table_summary, bounding_box)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                f"{paper_id}_table_{table.get('table_index')}",
                paper_id,
                table.get("page_number"),
                table.get("caption"),
                table.get("content"),
                table.get("summary"),
                json.dumps(table.get("bounding_box", []))
            ))
        
        # Insertar imágenes
        for image in multiview_chunks.get("images", []):
            cursor.execute("""
                INSERT OR REPLACE INTO images 
                (image_id, paper_id, page_number, image_caption, image_summary, bounding_box)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                f"{paper_id}_image_{image.get('image_index')}",
                paper_id,
                image.get("page_number"),
                image.get("caption"),
                image.get("summary"),
                json.dumps(image.get("bounding_box", []))
            ))
        
        # Insertar ecuaciones
        for equation in multiview_chunks.get("equations", []):
            cursor.execute("""
                INSERT OR REPLACE INTO equations 
                (equation_id, paper_id, page_number, equation_content)
                VALUES (?, ?, ?, ?)
            """, (
                f"{paper_id}_equation_{equation.get('equation_index')}",
                paper_id,
                equation.get("page_number"),
                equation.get("content")
            ))
        
        # Insertar chunks
        for idx, chunk in enumerate(multiview_chunks.get("chunks", [])):
            cursor.execute("""
                INSERT OR REPLACE INTO chunks 
                (chunk_id, paper_id, page_number, text_content, chunk_index)
                VALUES (?, ?, ?, ?, ?)
            """, (
                f"{paper_id}_chunk_{idx}",
                paper_id,
                chunk.get("page_number", 1),
                chunk.get("content"),
                idx
            ))
        
        self.db_conn.commit()
    
    def encode_to_vectorstore(
        self,
        paper_id: str,
        encodable_columns: List[Tuple[str, str]]
    ):
        """
        Codifica columnas encodables de la DB al vectorstore.
        
        Args:
            paper_id: ID del paper
            encodable_columns: Lista de (table_name, column_name) a codificar
        """
        cursor = self.db_conn.cursor()
        
        for table_name, column_name in encodable_columns:
            # Obtener valores de la columna
            cursor.execute(f"""
                SELECT {column_name}, page_number 
                FROM {table_name} 
                WHERE paper_id = ?
            """, (paper_id,))
            
            rows = cursor.fetchall()
            for row in rows:
                value = row[0]
                page_number = row[1] if len(row) > 1 else None
                
                if value:
                    # Crear metadata para el vectorstore
                    metadata = {
                        "paper_id": paper_id,
                        "table_name": table_name,
                        "column_name": column_name,
                        "page_number": page_number
                    }
                    
                    # Agregar al vectorstore (implementación depende del vectorstore usado)
                    # self.vectorstore.add_texts([value], metadatas=[metadata])
    
    def execute_action(self, action: Action) -> Observation:
        """Ejecuta una acción y retorna la observación."""
        try:
            if action.action_type == ActionType.RETRIEVEFROMVECTORSTORE:
                return self._retrieve_from_vectorstore(action.parameters)
            elif action.action_type == ActionType.RETRIEVEFROMDATABASE:
                return self._retrieve_from_database(action.parameters)
            elif action.action_type == ActionType.VIEWIMAGE:
                return self._view_image(action.parameters)
            elif action.action_type == ActionType.CALCULATEEXPR:
                return self._calculate_expr(action.parameters)
            elif action.action_type == ActionType.GENERATEANSWER:
                return self._generate_answer(action.parameters)
            else:
                return Observation(
                    action_type=action.action_type,
                    data=None,
                    success=False,
                    error=f"Unknown action type: {action.action_type}"
                )
        except Exception as e:
            return Observation(
                action_type=action.action_type,
                data=None,
                success=False,
                error=str(e)
            )
    
    def _retrieve_from_vectorstore(self, params: Dict[str, Any]) -> Observation:
        """Ejecuta RETRIEVEFROMVECTORSTORE action."""
        query = params.get("query", "")
        collection_name = params.get("collection_name", "default")
        table_name = params.get("table_name", "")
        column_name = params.get("column_name", "")
        filter_str = params.get("filter", "")
        limit = params.get("limit", 5)
        
        # Construir filtros de metadata
        metadata_filter = {}
        if table_name:
            metadata_filter["table_name"] = table_name
        if column_name:
            metadata_filter["column_name"] = column_name
        
        # Ejecutar búsqueda en vectorstore
        # results = self.vectorstore.similarity_search(query, k=limit, filter=metadata_filter)
        results = []  # Placeholder
        
        return Observation(
            action_type=ActionType.RETRIEVEFROMVECTORSTORE,
            data={
                "results": results,
                "query": query,
                "count": len(results)
            }
        )
    
    def _retrieve_from_database(self, params: Dict[str, Any]) -> Observation:
        """Ejecuta RETRIEVEFROMDATABASE action (SQL query)."""
        sql = params.get("sql", "")
        
        if not sql:
            return Observation(
                action_type=ActionType.RETRIEVEFROMDATABASE,
                data=None,
                success=False,
                error="SQL query is required"
            )
        
        cursor = self.db_conn.cursor()
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Convertir a formato tabular
            results = [dict(zip(columns, row)) for row in rows] if columns else rows
            
            return Observation(
                action_type=ActionType.RETRIEVEFROMDATABASE,
                data={
                    "results": results,
                    "count": len(results),
                    "columns": columns
                }
            )
        except Exception as e:
            return Observation(
                action_type=ActionType.RETRIEVEFROMDATABASE,
                data=None,
                success=False,
                error=f"SQL execution error: {str(e)}"
            )
    
    def _view_image(self, params: Dict[str, Any]) -> Observation:
        """Ejecuta VIEWIMAGE action."""
        paper_id = params.get("paper_id")
        page_number = params.get("page_number")
        bounding_box = params.get("bounding_box", [])
        
        # Obtener imagen de la base de datos
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT image_summary, bounding_box 
            FROM images 
            WHERE paper_id = ? AND page_number = ?
        """, (paper_id, page_number))
        
        result = cursor.fetchone()
        if result:
            return Observation(
                action_type=ActionType.VIEWIMAGE,
                data={
                    "image_summary": result[0],
                    "bounding_box": json.loads(result[1]) if result[1] else []
                }
            )
        else:
            return Observation(
                action_type=ActionType.VIEWIMAGE,
                data=None,
                success=False,
                error="Image not found"
            )
    
    def _calculate_expr(self, params: Dict[str, Any]) -> Observation:
        """Ejecuta CALCULATEEXPR action (calculadora simple)."""
        expr = params.get("expr", "")
        
        try:
            # Evaluar expresión de forma segura
            result = eval(expr, {"__builtins__": {}}, {})
            return Observation(
                action_type=ActionType.CALCULATEEXPR,
                data={"result": result, "expr": expr}
            )
        except Exception as e:
            return Observation(
                action_type=ActionType.CALCULATEEXPR,
                data=None,
                success=False,
                error=f"Calculation error: {str(e)}"
            )
    
    def _generate_answer(self, params: Dict[str, Any]) -> Observation:
        """Ejecuta GENERATEANSWER action (acción terminal)."""
        answer = params.get("answer", "")
        
        return Observation(
            action_type=ActionType.GENERATEANSWER,
            data={"answer": answer}
        )
    
    def iterative_retrieval(
        self,
        question: str,
        answer_format: str,
        max_interactions: int = 20
    ) -> Dict[str, Any]:
        """
        Ejecuta retrieval iterativo usando ReAct framework.
        
        El agente predice acciones, las ejecuta, observa resultados,
        y repite hasta tener suficiente contexto para responder.
        """
        self.interaction_history = []
        context = []
        
        system_prompt = f"""You are an intelligent agent with expertise in retrieving useful context from both a DuckDB database and a Milvus vectorstore through SQL execution and similarity search to answer user questions.

You will be given a natural language question concerning PDF files, along with the schema of both the database and the vectorstore. Your ultimate goal is to answer the input question with the pre-defined answer format.

Available actions:
1. RetrieveFromVectorstore(query, collection_name, table_name, column_name, filter, limit)
2. RetrieveFromDatabase(sql)
3. ViewImage(paper_id, page_number, bounding_box)
4. CalculateExpr(expr)
5. GenerateAnswer(answer) - Terminal action

Interaction format:
[Thought]: Your reasoning
[Action]: ActionType(parameters)
[Observation]: Results from action execution

Continue until you have enough information to answer, then use GenerateAnswer.
"""
        
        for turn in range(max_interactions):
            # Construir prompt con historial
            prompt = f"""{system_prompt}

[Question]: {question}
[Answer Format]: {answer_format}

Previous interactions:
{self._format_interaction_history()}

[Thought]:"""
            
            # LLM predice thought y action
            response = self.llm.invoke(prompt)
            thought, action = self._parse_llm_response(str(response.content))
            
            # Ejecutar acción
            observation = self.execute_action(action)
            
            # Guardar en historial
            interaction = {
                "turn": turn + 1,
                "thought": thought,
                "action": {
                    "type": action.action_type.value,
                    "parameters": action.parameters
                },
                "observation": {
                    "success": observation.success,
                    "data": observation.data,
                    "error": observation.error
                }
            }
            self.interaction_history.append(interaction)
            
            # Si es terminal, retornar
            if action.action_type == ActionType.GENERATEANSWER:
                return {
                    "answer": action.parameters.get("answer"),
                    "interactions": self.interaction_history,
                    "turns": turn + 1
                }
            
            # Agregar contexto
            if observation.success and observation.data:
                context.append(observation.data)
        
        # Si se agotaron las interacciones, generar respuesta final
        final_prompt = f"""Based on the following context retrieved from the database and vectorstore, answer the question.

Question: {question}
Answer Format: {answer_format}

Context:
{json.dumps(context, indent=2)}

Answer:"""
        
        final_response = self.llm.invoke(final_prompt)
        
        return {
            "answer": str(final_response.content),
            "interactions": self.interaction_history,
            "turns": max_interactions,
            "note": "Max interactions reached"
        }
    
    def _parse_llm_response(self, response: str) -> Tuple[str, Action]:
        """Parsea la respuesta del LLM para extraer thought y action."""
        # Implementación simplificada - en producción usar parsing más robusto
        lines = response.strip().split("\n")
        thought = ""
        action_type = None
        action_params = {}
        
        for line in lines:
            if line.startswith("[Thought]:"):
                thought = line.replace("[Thought]:", "").strip()
            elif line.startswith("[Action]:"):
                action_str = line.replace("[Action]:", "").strip()
                action_type, action_params = self._parse_action(action_str)
        
        if not action_type:
            # Default: GenerateAnswer si no se puede parsear
            action_type = ActionType.GENERATEANSWER
            action_params = {"answer": response}
        
        return thought, Action(
            action_type=action_type,
            parameters=action_params,
            thought=thought
        )
    
    def _parse_action(self, action_str: str) -> Tuple[ActionType, Dict[str, Any]]:
        """Parsea una cadena de acción en ActionType y parámetros."""
        # Implementación simplificada - soportar diferentes formatos
        if "RetrieveFromVectorstore" in action_str:
            # Extraer parámetros (simplificado)
            return ActionType.RETRIEVEFROMVECTORSTORE, {
                "query": "",
                "collection_name": "default",
                "table_name": "",
                "column_name": "",
                "filter": "",
                "limit": 5
            }
        elif "RetrieveFromDatabase" in action_str:
            # Extraer SQL
            sql = action_str.split("sql=")[1].split(")")[0] if "sql=" in action_str else ""
            return ActionType.RETRIEVEFROMDATABASE, {"sql": sql}
        elif "ViewImage" in action_str:
            return ActionType.VIEWIMAGE, {
                "paper_id": "",
                "page_number": 1,
                "bounding_box": []
            }
        elif "CalculateExpr" in action_str:
            expr = action_str.split("expr=")[1].split(")")[0] if "expr=" in action_str else ""
            return ActionType.CALCULATEEXPR, {"expr": expr}
        elif "GenerateAnswer" in action_str:
            answer = action_str.split("answer=")[1].split(")")[0] if "answer=" in action_str else ""
            return ActionType.GENERATEANSWER, {"answer": answer}
        
        return ActionType.GENERATEANSWER, {"answer": "Unable to parse action"}
    
    def _format_interaction_history(self) -> str:
        """Formatea el historial de interacciones para el prompt."""
        if not self.interaction_history:
            return "No previous interactions."
        
        formatted = []
        for interaction in self.interaction_history[-5:]:  # Últimas 5 interacciones
            formatted.append(f"[Thought]: {interaction['thought']}")
            formatted.append(f"[Action]: {interaction['action']['type']}({interaction['action']['parameters']})")
            formatted.append(f"[Observation]: {json.dumps(interaction['observation']['data'], indent=2)}")
        
        return "\n".join(formatted)

