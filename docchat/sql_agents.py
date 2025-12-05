"""Multi-Agent SQL Framework: Creator, Runner, Enhancer.

Implementa un framework de múltiples agentes especializados para:
- SQL Creator: Genera SQL inicial
- SQL Runner: Ejecuta y valida SQL
- SQL Enhancer: Mejora SQL basado en feedback
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .sql_generation import SQLGenerator, SQLGenerationResult
from .data_registry import DataRegistry


@dataclass
class SQLExecutionResult:
    """Resultado de ejecución de SQL."""
    success: bool
    rows: List[Dict[str, Any]] = None
    row_count: int = 0
    execution_time_ms: float = 0.0
    error: Optional[str] = None
    sql_executed: str = ""


class SQLRunner:
    """Agente especializado en ejecutar SQL."""
    
    def __init__(self, data_registry: DataRegistry):
        self.data_registry = data_registry
    
    def execute_sql(
        self,
        sql: str,
        source_id: str,
        read_only: bool = True,
    ) -> SQLExecutionResult:
        """Ejecuta SQL en una base de datos.
        
        Args:
            sql: SQL a ejecutar
            source_id: ID de la fuente de datos
            read_only: Si True, solo permite SELECT
        
        Returns:
            SQLExecutionResult con resultados o error
        """
        import time
        start_time = time.time()
        
        # Verificar que source existe
        if source_id not in self.data_registry.sources:
            return SQLExecutionResult(
                success=False,
                error=f"Fuente de datos no encontrada: {source_id}",
            )
        
        source = self.data_registry.sources[source_id]
        connection = source.connection
        
        # Validar que es SELECT si read_only
        if read_only and not sql.strip().upper().startswith("SELECT"):
            return SQLExecutionResult(
                success=False,
                error="Solo se permiten queries SELECT en modo read-only",
            )
        
        # Intentar ejecutar SQL
        try:
            # Obtener connection string desde env var
            import os
            connection_string = None
            if connection.connection_string_env:
                connection_string = os.getenv(connection.connection_string_env)
            
            if not connection_string:
                # Construir connection string desde componentes
                if connection.db_type == "postgresql":
                    connection_string = (
                        f"postgresql://{connection.username}@"
                        f"{connection.host}:{connection.port}/{connection.database}"
                    )
                elif connection.db_type == "mysql":
                    connection_string = (
                        f"mysql://{connection.username}@"
                        f"{connection.host}:{connection.port}/{connection.database}"
                    )
                elif connection.db_type == "sqlite":
                    connection_string = f"sqlite:///{connection.database}"
                else:
                    return SQLExecutionResult(
                        success=False,
                        error=f"Tipo de BD no soportado para ejecución: {connection.db_type}",
                    )
            
            # Ejecutar SQL real usando SQLAlchemy
            try:
                from sqlalchemy import create_engine, text
                from sqlalchemy.exc import SQLAlchemyError
                
                # Crear engine
                engine = create_engine(connection_string, echo=False)
                
                # Ejecutar query
                with engine.connect() as conn:
                    result = conn.execute(text(sql))
                    
                    # Si es SELECT, obtener filas
                    if sql.strip().upper().startswith("SELECT"):
                        rows = []
                        for row in result:
                            # Convertir row a dict
                            row_dict = {}
                            for key, value in row._mapping.items():
                                # Convertir tipos no serializables
                                if hasattr(value, 'isoformat'):  # datetime
                                    row_dict[key] = value.isoformat()
                                else:
                                    row_dict[key] = value
                            rows.append(row_dict)
                        
                        execution_time = (time.time() - start_time) * 1000
                        return SQLExecutionResult(
                            success=True,
                            rows=rows,
                            row_count=len(rows),
                            execution_time_ms=execution_time,
                            sql_executed=sql,
                        )
                    else:
                        # Para queries no-SELECT (INSERT, UPDATE, DELETE)
                        # En modo read_only no deberían llegar aquí, pero por seguridad
                        conn.commit()
                        execution_time = (time.time() - start_time) * 1000
                        return SQLExecutionResult(
                            success=True,
                            rows=[],
                            row_count=0,
                            execution_time_ms=execution_time,
                            sql_executed=sql,
                        )
            except ImportError:
                # SQLAlchemy no disponible, usar stub
                execution_time = (time.time() - start_time) * 1000
                return SQLExecutionResult(
                    success=True,
                    rows=[{"message": "SQL ejecutado exitosamente (stub mode - instala sqlalchemy para ejecución real)"}],
                    row_count=1,
                    execution_time_ms=execution_time,
                    sql_executed=sql,
                )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return SQLExecutionResult(
                success=False,
                error=str(e),
                execution_time_ms=execution_time,
                sql_executed=sql,
            )


class SQLEnhancer:
    """Agente especializado en mejorar SQL basado en feedback."""
    
    def __init__(self, sql_generator: SQLGenerator):
        self.sql_generator = sql_generator
    
    def enhance_sql(
        self,
        original_sql: str,
        original_query: str,
        execution_result: SQLExecutionResult,
        schema_context: str,
    ) -> SQLGenerationResult:
        """Mejora SQL basado en resultados de ejecución.
        
        Args:
            original_sql: SQL original que falló o necesita mejora
            original_query: Query en lenguaje natural original
            execution_result: Resultado de ejecución (puede tener errores)
            schema_context: Contexto de schema
        
        Returns:
            SQLGenerationResult mejorado
        """
        if execution_result.success:
            # Si el SQL funcionó, intentar optimizarlo
            enhancement_prompt = f"""
El siguiente SQL se ejecutó exitosamente, pero podría optimizarse:

SQL original: {original_sql}
Query original: {original_query}

Genera una versión optimizada del SQL que:
1. Sea más eficiente
2. Use índices cuando sea posible
3. Evite subqueries innecesarias
4. Mantenga la misma funcionalidad
"""
        else:
            # Si falló, corregir errores
            enhancement_prompt = f"""
El siguiente SQL falló al ejecutarse:

SQL original: {original_sql}
Query original: {original_query}
Error: {execution_result.error}

Corrige el SQL para que:
1. Solucione el error reportado
2. Sea sintácticamente correcto
3. Use las tablas y columnas correctas del schema
"""
        
        try:
            result = self.sql_generator._generate_sql_with_llm(
                enhancement_prompt,
                schema_context,
                previous_errors=[execution_result.error] if execution_result.error else None,
            )
            
            return SQLGenerationResult(
                sql=result["sql"],
                confidence=result.get("confidence", 0.7),
                tables_used=[],  # Se puede extraer del SQL si es necesario
                explanation=f"SQL mejorado: {result.get('explanation', '')}",
            )
        except Exception as e:
            # Si la mejora falla, retornar el original
            return SQLGenerationResult(
                sql=original_sql,
                confidence=0.5,
                tables_used=[],
                explanation=f"Error mejorando SQL: {str(e)}. Retornando SQL original.",
                errors=[str(e)],
            )


class MultiAgentSQLFramework:
    """Framework multi-agente para SQL generation con feedback loop."""
    
    def __init__(
        self,
        sql_generator: SQLGenerator,
        sql_runner: SQLRunner,
        sql_enhancer: SQLEnhancer,
        max_iterations: int = 3,
    ):
        self.sql_generator = sql_generator
        self.sql_runner = sql_runner
        self.sql_enhancer = sql_enhancer
        self.max_iterations = max_iterations
    
    def generate_and_execute(
        self,
        natural_language_query: str,
        source_id: str,
        tenant_id: Optional[str] = None,
        auto_fix: bool = True,
    ) -> Dict[str, Any]:
        """Genera SQL, lo ejecuta, y lo mejora iterativamente si es necesario.
        
        Args:
            natural_language_query: Query en lenguaje natural
            source_id: ID de fuente de datos
            tenant_id: ID de tenant
            auto_fix: Si True, intenta corregir errores automáticamente
        
        Returns:
            Dict con SQL final, resultados de ejecución, y metadata
        """
        # Paso 1: Generar SQL inicial
        sql_result = self.sql_generator.generate_sql(
            natural_language_query,
            source_id=source_id,
            tenant_id=tenant_id,
        )
        
        if not sql_result.sql:
            return {
                "success": False,
                "error": "No se pudo generar SQL",
                "sql_result": sql_result,
            }
        
        current_sql = sql_result.sql
        iterations = []
        
        # Paso 2: Loop de ejecución y mejora
        for iteration in range(self.max_iterations):
            # Ejecutar SQL
            execution_result = self.sql_runner.execute_sql(
                current_sql,
                source_id=source_id,
                read_only=True,
            )
            
            iterations.append({
                "iteration": iteration + 1,
                "sql": current_sql,
                "execution": execution_result,
            })
            
            # Si ejecutó exitosamente, retornar
            if execution_result.success:
                return {
                    "success": True,
                    "sql": current_sql,
                    "execution_result": execution_result,
                    "sql_result": sql_result,
                    "iterations": iterations,
                    "final_iteration": iteration + 1,
                }
            
            # Si falló y auto_fix está activado, intentar mejorar
            if auto_fix and execution_result.error:
                # Obtener schema context
                schema_context = self.sql_generator.data_registry.get_schema_context(
                    sql_result.tables_used,
                )
                
                # Mejorar SQL
                enhanced_result = self.sql_enhancer.enhance_sql(
                    current_sql,
                    natural_language_query,
                    execution_result,
                    schema_context,
                )
                
                if enhanced_result.sql and enhanced_result.sql != current_sql:
                    current_sql = enhanced_result.sql
                    sql_result = enhanced_result
                else:
                    # No se pudo mejorar, retornar error
                    break
            else:
                # No auto_fix, retornar error
                break
        
        # Si llegamos aquí, falló después de todas las iteraciones
        return {
            "success": False,
            "error": f"SQL falló después de {len(iterations)} iteraciones",
            "sql": current_sql,
            "execution_result": execution_result,
            "sql_result": sql_result,
            "iterations": iterations,
        }


