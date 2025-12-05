"""SQL Generation Engine: Convierte lenguaje natural a SQL.

Este módulo implementa generación de SQL desde lenguaje natural usando:
- Schema linking con RAG (vector retrieval de tablas/columnas)
- LLM fine-tuning para SQL generation
- Validación y corrección de SQL
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    from langchain_openai import ChatOpenAI
    from langchain.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

from .data_registry import DataRegistry, TableMetadata, ColumnMetadata


@dataclass
class SQLGenerationResult:
    """Resultado de generación de SQL."""
    sql: str
    confidence: float  # 0.0 - 1.0
    tables_used: List[str]
    explanation: str
    errors: List[str] = None
    alternative_queries: List[str] = None


class SQLGenerator:
    """Generador de SQL desde lenguaje natural."""
    
    def __init__(
        self,
        config: Any,
        data_registry: DataRegistry,
        llm_provider: str = "openai",
    ):
        self.config = config
        self.data_registry = data_registry
        
        if not LLM_AVAILABLE:
            raise ImportError("langchain_openai no está disponible. Instala con: pip install langchain-openai")
        
        # Verificar que OPENAI_API_KEY esté configurada
        import os
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError(
                "OPENAI_API_KEY no está configurada. "
                "Configúrala en tu archivo .env o como variable de entorno."
            )
        
        # Inicializar LLM
        model_name = getattr(config, "sql_generation_model", "gpt-4o-mini")
        try:
            self.llm = ChatOpenAI(
                model=model_name,
                temperature=0.1,  # Baja temperatura para SQL (más determinístico)
            )
        except Exception as e:
            raise RuntimeError(
                f"Error al inicializar ChatOpenAI con modelo {model_name}: {str(e)}\n"
                "Verifica que OPENAI_API_KEY sea válida y que tengas acceso al modelo."
            ) from e
        
        # Parser de salida
        self.output_parser = StrOutputParser()
    
    def generate_sql(
        self,
        natural_language_query: str,
        source_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        max_iterations: int = 3,
    ) -> SQLGenerationResult:
        """Genera SQL desde una query en lenguaje natural.
        
        Args:
            natural_language_query: Query del usuario en lenguaje natural
            source_id: ID de fuente de datos específica (opcional)
            tenant_id: ID de tenant para filtrar
            max_iterations: Máximo de intentos si hay errores
        
        Returns:
            SQLGenerationResult con SQL generado y metadata
        """
        # Paso 1: Schema Linking - encontrar tablas y columnas relevantes
        relevant_tables = self._schema_linking(natural_language_query, source_id, tenant_id)
        
        if not relevant_tables:
            return SQLGenerationResult(
                sql="",
                confidence=0.0,
                tables_used=[],
                explanation="No se encontraron tablas relevantes para la query.",
                errors=["No tables found"],
            )
        
        # Paso 2: Generar contexto de schema
        schema_context = self.data_registry.get_schema_context(
            [f"{t.database_name}.{t.name}" for t in relevant_tables],
            include_samples=True,
        )
        
        # Paso 3: Generar SQL usando LLM
        sql_result = None
        errors = []
        
        for iteration in range(max_iterations):
            try:
                sql_result = self._generate_sql_with_llm(
                    natural_language_query,
                    schema_context,
                    previous_errors=errors,
                )
                
                # Validar SQL básico
                validation_result = self._validate_sql(sql_result.sql)
                if validation_result["valid"]:
                    break
                else:
                    errors.extend(validation_result["errors"])
            except Exception as e:
                errors.append(f"Iteration {iteration + 1} error: {str(e)}")
        
        if not sql_result:
            return SQLGenerationResult(
                sql="",
                confidence=0.0,
                tables_used=[t.name for t in relevant_tables],
                explanation="Error generando SQL después de múltiples intentos.",
                errors=errors,
            )
        
        return SQLGenerationResult(
            sql=sql_result["sql"],
            confidence=sql_result.get("confidence", 0.7),
            tables_used=[t.name for t in relevant_tables],
            explanation=sql_result.get("explanation", ""),
            errors=errors if errors else None,
            alternative_queries=sql_result.get("alternatives", []),
        )
    
    def _schema_linking(
        self,
        query: str,
        source_id: Optional[str],
        tenant_id: Optional[str],
    ) -> List[TableMetadata]:
        """Encuentra tablas y columnas relevantes para la query."""
        # Buscar tablas relevantes usando el registry
        relevant_tables = self.data_registry.search_tables(
            query=query,
            limit=5,  # Top 5 tablas más relevantes
            tenant_id=tenant_id,
        )
        
        # Si se especificó source_id, filtrar
        if source_id and source_id in self.data_registry.sources:
            source = self.data_registry.sources[source_id]
            relevant_tables = [
                t for t in relevant_tables
                if t in source.tables
            ]
        
        return relevant_tables
    
    def _generate_sql_with_llm(
        self,
        query: str,
        schema_context: str,
        previous_errors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Genera SQL usando LLM con contexto de schema."""
        
        # Construir prompt
        error_context = ""
        if previous_errors:
            error_context = f"\n\nErrores previos a evitar:\n" + "\n".join(f"- {e}" for e in previous_errors[-3:])
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Eres un experto en SQL. Tu tarea es convertir queries en lenguaje natural a SQL válido.

Instrucciones:
1. Analiza la query del usuario y el schema proporcionado
2. Genera SQL válido y eficiente
3. Usa solo las tablas y columnas del schema proporcionado
4. Incluye JOINs cuando sea necesario
5. Usa agregaciones (COUNT, SUM, AVG, etc.) cuando la query lo requiera
6. Respeta los tipos de datos y relaciones (PRIMARY KEY, FOREIGN KEY)
7. Retorna SOLO el SQL, sin explicaciones adicionales en el SQL mismo

Formato de respuesta:
SQL: [tu SQL aquí]
EXPLANATION: [breve explicación de qué hace el SQL]
"""),
            ("human", """Schema de la base de datos:

{schema_context}

Query del usuario: {query}
{error_context}

Genera el SQL correspondiente:"""),
        ])
        
        chain = prompt_template | self.llm | self.output_parser
        
        try:
            response = chain.invoke({
                "schema_context": schema_context,
                "query": query,
                "error_context": error_context,
            })
            
            # Parsear respuesta
            sql = ""
            explanation = ""
            
            # Extraer SQL
            sql_match = re.search(r"SQL:\s*(.+?)(?=EXPLANATION:|$)", response, re.DOTALL)
            if sql_match:
                sql = sql_match.group(1).strip()
            else:
                # Si no hay formato, asumir que todo es SQL
                sql = response.strip()
            
            # Extraer explicación
            exp_match = re.search(r"EXPLANATION:\s*(.+?)$", response, re.DOTALL)
            if exp_match:
                explanation = exp_match.group(1).strip()
            
            # Limpiar SQL (remover markdown code blocks si existen)
            sql = re.sub(r"```sql\s*", "", sql)
            sql = re.sub(r"```\s*", "", sql)
            sql = sql.strip()
            
            return {
                "sql": sql,
                "explanation": explanation,
                "confidence": 0.8,  # Por ahora fijo, podría calcularse
            }
        except Exception as e:
            raise Exception(f"Error generando SQL con LLM: {str(e)}")
    
    def _validate_sql(self, sql: str) -> Dict[str, Any]:
        """Valida SQL básico (sintaxis, keywords peligrosos, etc.)."""
        errors = []
        warnings = []
        
        if not sql or not sql.strip():
            errors.append("SQL vacío")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        sql_upper = sql.upper().strip()
        
        # Verificar keywords peligrosos (solo permitir SELECT por ahora)
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE"]
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                errors.append(f"Keyword peligroso detectado: {keyword}. Solo se permiten queries SELECT.")
        
        # Verificar que tenga SELECT
        if "SELECT" not in sql_upper:
            errors.append("SQL debe contener SELECT")
        
        # Verificar paréntesis balanceados
        if sql.count("(") != sql.count(")"):
            errors.append("Paréntesis no balanceados")
        
        # Verificar comillas balanceadas (básico)
        single_quotes = sql.count("'") - sql.count("\\'")
        if single_quotes % 2 != 0:
            warnings.append("Posibles comillas no balanceadas")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    def explain_sql(self, sql: str) -> str:
        """Genera explicación en lenguaje natural de un SQL."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Eres un experto en SQL. Explica qué hace este query SQL en lenguaje natural, de forma clara y concisa."),
            ("human", "SQL:\n{sql}\n\nExplica qué hace este query:"),
        ])
        
        chain = prompt | self.llm | self.output_parser
        try:
            explanation = chain.invoke({"sql": sql})
            return explanation
        except Exception as e:
            return f"Error generando explicación: {str(e)}"


