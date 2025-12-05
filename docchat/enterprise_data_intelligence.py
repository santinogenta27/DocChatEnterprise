"""Enterprise Data Intelligence Mode.

Nuevo modo que permite:
- Registrar bases de datos y tablas (Data Registry)
- Generar SQL desde lenguaje natural (SQL Generation)
- Ejecutar queries y obtener resultados
- Integrar con el resto del sistema (RAG, agentes, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .data_registry import DataRegistry, DatabaseConnection, TableMetadata
from .sql_generation import SQLGenerator, SQLGenerationResult
from .sql_agents import MultiAgentSQLFramework, SQLRunner, SQLEnhancer
from .agent_registry import AgentRegistry


@dataclass
class QueryResult:
    """Resultado de una query de data intelligence."""
    success: bool
    sql: str
    natural_language_query: str
    execution_result: Optional[Any] = None
    sql_generation_result: Optional[SQLGenerationResult] = None
    explanation: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


class EnterpriseDataIntelligence:
    """Modo Enterprise Data Intelligence: SQL Generation + Data Registry."""
    
    def __init__(
        self,
        config: Any,
        data_registry: Optional[DataRegistry] = None,
        agent_registry: Optional[AgentRegistry] = None,
    ):
        self.config = config
        
        # Inicializar Data Registry
        self.data_registry = data_registry or DataRegistry(config)
        
        # Inicializar Agent Registry
        self.agent_registry = agent_registry or AgentRegistry(config)
        
        # Inicializar SQL Generator
        try:
            self.sql_generator = SQLGenerator(
                config=config,
                data_registry=self.data_registry,
            )
            print("✅ SQL Generator inicializado correctamente")
        except ImportError as e:
            print(f"⚠️ Error de importación en SQL Generator: {e}")
            print("   💡 Asegúrate de tener instalado: pip install langchain-openai")
            self.sql_generator = None
        except Exception as e:
            print(f"⚠️ Error inicializando SQL Generator: {e}")
            import traceback
            traceback.print_exc()
            self.sql_generator = None
        
        # Inicializar SQL Runner y Enhancer
        self.sql_runner = SQLRunner(self.data_registry)
        self.sql_enhancer = None
        if self.sql_generator:
            self.sql_enhancer = SQLEnhancer(self.sql_generator)
        
        # Inicializar Multi-Agent Framework
        if self.sql_generator and self.sql_enhancer:
            self.multi_agent_framework = MultiAgentSQLFramework(
                sql_generator=self.sql_generator,
                sql_runner=self.sql_runner,
                sql_enhancer=self.sql_enhancer,
                max_iterations=3,
            )
        else:
            self.multi_agent_framework = None
    
    # ------------------------------------------------------------------
    # Data Registry Operations
    # ------------------------------------------------------------------
    
    def register_database(
        self,
        name: str,
        db_type: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        connection_string_env: Optional[str] = None,
        description: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registra una nueva base de datos."""
        try:
            source_id = self.data_registry.register_database(
                name=name,
                db_type=db_type,
                host=host,
                port=port,
                database=database,
                username=username,
                connection_string_env=connection_string_env,
                description=description,
                tenant_id=tenant_id,
            )
            return {
                "success": True,
                "source_id": source_id,
                "message": f"Base de datos '{name}' registrada exitosamente",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def register_table(
        self,
        source_id: str,
        table_name: str,
        description: Optional[str] = None,
        business_domain: Optional[str] = None,
        columns: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Registra una tabla en una base de datos."""
        try:
            success = self.data_registry.register_table(
                source_id=source_id,
                table_name=table_name,
                description=description,
                business_domain=business_domain,
                columns=columns,
            )
            if success:
                return {
                    "success": True,
                    "message": f"Tabla '{table_name}' registrada en '{source_id}'",
                }
            else:
                return {
                    "success": False,
                    "error": f"No se pudo registrar la tabla '{table_name}'",
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def list_databases(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista todas las bases de datos registradas."""
        return self.data_registry.list_sources(tenant_id=tenant_id)
    
    def search_tables(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Busca tablas relevantes."""
        tables = self.data_registry.search_tables(
            query=query,
            limit=limit,
            tenant_id=tenant_id,
        )
        return [
            {
                "name": t.name,
                "database": t.database_name,
                "description": t.description,
                "business_domain": t.business_domain,
                "columns_count": len(t.columns),
            }
            for t in tables
        ]
    
    # ------------------------------------------------------------------
    # SQL Generation Operations
    # ------------------------------------------------------------------
    
    def query_with_natural_language(
        self,
        natural_language_query: str,
        source_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        use_multi_agent: bool = True,
        auto_fix: bool = True,
    ) -> QueryResult:
        """Convierte una query en lenguaje natural a SQL y la ejecuta.
        
        Args:
            natural_language_query: Query del usuario (ej: "¿Cuántas ventas hubo en diciembre?")
            source_id: ID de fuente de datos específica (opcional)
            tenant_id: ID de tenant
            use_multi_agent: Si True, usa el framework multi-agente
            auto_fix: Si True, intenta corregir errores automáticamente
        
        Returns:
            QueryResult con SQL, resultados, y metadata
        """
        if not self.sql_generator:
            error_msg = (
                "SQL Generator no está inicializado. "
                "Posibles causas:\n"
                "1. OPENAI_API_KEY no está configurada en variables de entorno\n"
                "2. langchain-openai no está instalado (pip install langchain-openai)\n"
                "3. Error al inicializar el modelo LLM\n\n"
                "💡 Revisa los logs de inicialización para más detalles."
            )
            return QueryResult(
                success=False,
                sql="",
                natural_language_query=natural_language_query,
                error=error_msg,
            )
        
        try:
            # Si use_multi_agent y tenemos framework, usarlo
            if use_multi_agent and self.multi_agent_framework and source_id:
                result = self.multi_agent_framework.generate_and_execute(
                    natural_language_query=natural_language_query,
                    source_id=source_id,
                    tenant_id=tenant_id,
                    auto_fix=auto_fix,
                )
                
                return QueryResult(
                    success=result.get("success", False),
                    sql=result.get("sql", ""),
                    natural_language_query=natural_language_query,
                    execution_result=result.get("execution_result"),
                    sql_generation_result=result.get("sql_result"),
                    explanation=result.get("sql_result", {}).get("explanation"),
                    error=result.get("error"),
                    metadata={
                        "iterations": result.get("iterations", []),
                        "final_iteration": result.get("final_iteration", 0),
                    },
                )
            else:
                # Solo generar SQL sin ejecutar
                sql_result = self.sql_generator.generate_sql(
                    natural_language_query=natural_language_query,
                    source_id=source_id,
                    tenant_id=tenant_id,
                )
                
                return QueryResult(
                    success=bool(sql_result.sql),
                    sql=sql_result.sql,
                    natural_language_query=natural_language_query,
                    sql_generation_result=sql_result,
                    explanation=sql_result.explanation,
                    error="; ".join(sql_result.errors) if sql_result.errors else None,
                )
        except Exception as e:
            return QueryResult(
                success=False,
                sql="",
                natural_language_query=natural_language_query,
                error=f"Error procesando query: {str(e)}",
            )
    
    def explain_sql(self, sql: str) -> str:
        """Genera explicación en lenguaje natural de un SQL."""
        if not self.sql_generator:
            return "SQL Generator no está inicializado"
        return self.sql_generator.explain_sql(sql)
    
    def generate_sql_only(
        self,
        natural_language_query: str,
        source_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> SQLGenerationResult:
        """Solo genera SQL sin ejecutarlo."""
        if not self.sql_generator:
            return SQLGenerationResult(
                sql="",
                confidence=0.0,
                tables_used=[],
                explanation="SQL Generator no está inicializado",
                errors=["SQL Generator not initialized"],
            )
        return self.sql_generator.generate_sql(
            natural_language_query=natural_language_query,
            source_id=source_id,
            tenant_id=tenant_id,
        )
    
    # ------------------------------------------------------------------
    # Agent Registry Operations
    # ------------------------------------------------------------------
    
    def register_agent(
        self,
        agent_id: str,
        name: str,
        description: str,
        category: str,
        input_parameters: Optional[List[Dict[str, Any]]] = None,
        output_parameters: Optional[List[Dict[str, Any]]] = None,
        deployment_info: Optional[Dict[str, Any]] = None,
        stream_tags: Optional[List[str]] = None,
        cost_per_call: Optional[float] = None,
        latency_ms: Optional[float] = None,
        requires_approval: bool = False,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registra un nuevo agente/API en el registry."""
        try:
            success = self.agent_registry.register_agent(
                agent_id=agent_id,
                name=name,
                description=description,
                category=category,
                input_parameters=input_parameters,
                output_parameters=output_parameters,
                deployment_info=deployment_info,
                stream_tags=stream_tags,
                cost_per_call=cost_per_call,
                latency_ms=latency_ms,
                requires_approval=requires_approval,
                tenant_id=tenant_id,
            )
            if success:
                return {
                    "success": True,
                    "message": f"Agente '{agent_id}' registrado exitosamente",
                }
            else:
                return {
                    "success": False,
                    "error": "No se pudo registrar el agente",
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def search_agents(
        self,
        query: str,
        category: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Busca agentes relevantes."""
        agents = self.agent_registry.search_agents(
            query=query,
            category=category,
            tenant_id=tenant_id,
            limit=limit,
        )
        return [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "description": a.description,
                "category": a.category,
                "input_params_count": len(a.input_parameters),
                "output_params_count": len(a.output_parameters),
                "requires_approval": a.requires_approval,
            }
            for a in agents
        ]
    
    def list_agents(
        self,
        category: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lista todos los agentes registrados."""
        return self.agent_registry.list_agents(
            category=category,
            tenant_id=tenant_id,
        )
    
    # ------------------------------------------------------------------
    # Integration with other modes
    # ------------------------------------------------------------------
    
    def enrich_with_database_context(
        self,
        query: str,
        tenant_id: Optional[str] = None,
    ) -> str:
        """Enriquece una query con contexto de bases de datos disponibles.
        
        Útil para integrar con otros modos (RAG, Research Agent, etc.)
        """
        # Buscar tablas relevantes
        relevant_tables = self.data_registry.search_tables(
            query=query,
            limit=3,
            tenant_id=tenant_id,
        )
        
        if not relevant_tables:
            return query  # Sin cambios si no hay tablas relevantes
        
        # Construir contexto
        context_parts = [
            "Bases de datos disponibles:",
        ]
        for table in relevant_tables:
            context_parts.append(f"- {table.name} ({table.database_name})")
            if table.description:
                context_parts.append(f"  Descripción: {table.description}")
        
        context = "\n".join(context_parts)
        return f"{query}\n\n{context}"


