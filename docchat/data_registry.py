"""Data Registry: Registro centralizado de fuentes de datos empresariales.

Este módulo mantiene metadata de bases de datos, tablas, columnas,
y relaciones para habilitar SQL generation desde lenguaje natural.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from langchain_openai import OpenAIEmbeddings
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


@dataclass
class ColumnMetadata:
    """Metadata de una columna de base de datos."""
    name: str
    data_type: str
    description: Optional[str] = None  # Descripción en lenguaje natural
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_table: Optional[str] = None
    foreign_key_column: Optional[str] = None
    sample_values: List[str] = field(default_factory=list)  # Valores de ejemplo
    nullable: bool = True
    unique: bool = False


@dataclass
class TableMetadata:
    """Metadata de una tabla de base de datos."""
    name: str
    database_name: str
    description: Optional[str] = None  # Descripción en lenguaje natural
    columns: List[ColumnMetadata] = field(default_factory=list)
    row_count: Optional[int] = None
    last_updated: Optional[str] = None
    business_domain: Optional[str] = None  # Ej: "sales", "finance", "hr"


@dataclass
class DatabaseConnection:
    """Información de conexión a una base de datos."""
    name: str
    db_type: str  # "postgresql", "mysql", "sqlite", "mssql", etc.
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    # Password NO se guarda aquí por seguridad, se obtiene de env vars
    connection_string_env: Optional[str] = None  # Nombre de env var con connection string
    description: Optional[str] = None


@dataclass
class DataSource:
    """Fuente de datos completa (database + tablas)."""
    connection: DatabaseConnection
    tables: List[TableMetadata] = field(default_factory=list)
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tenant_id: Optional[str] = None  # Para multi-tenant


class DataRegistry:
    """Registro centralizado de fuentes de datos empresariales."""
    
    def __init__(self, config: Any, registry_path: Optional[Path] = None):
        self.config = config
        self.registry_path = registry_path or (config.cache_dir / "data_registry.json")
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Almacenamiento en memoria
        self.sources: Dict[str, DataSource] = {}  # source_id -> DataSource
        self.table_index: Dict[str, TableMetadata] = {}  # "db.table" -> TableMetadata
        self.column_index: Dict[str, ColumnMetadata] = {}  # "db.table.column" -> ColumnMetadata
        
        # Embeddings para búsqueda semántica (opcional)
        self.embeddings = None
        if EMBEDDINGS_AVAILABLE:
            try:
                self.embeddings = OpenAIEmbeddings(model=self.config.embedding_model)
            except Exception as e:
                print(f"⚠️ No se pudo inicializar embeddings para Data Registry: {e}")
        
        # Cargar registry existente
        self._load_registry()
    
    def _load_registry(self):
        """Carga el registry desde disco."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for source_id, source_data in data.get("sources", {}).items():
                        # Reconstruir objetos desde dict
                        source = self._dict_to_source(source_data)
                        self.sources[source_id] = source
                        # Indexar tablas y columnas
                        for table in source.tables:
                            key = f"{source.connection.database}.{table.name}"
                            self.table_index[key] = table
                            for col in table.columns:
                                col_key = f"{key}.{col.name}"
                                self.column_index[col_key] = col
                print(f"✅ Data Registry cargado: {len(self.sources)} fuentes, {len(self.table_index)} tablas")
            except Exception as e:
                print(f"⚠️ Error cargando Data Registry: {e}")
    
    def _save_registry(self):
        """Guarda el registry en disco."""
        try:
            data = {
                "sources": {
                    source_id: self._source_to_dict(source)
                    for source_id, source in self.sources.items()
                }
            }
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error guardando Data Registry: {e}")
    
    def _source_to_dict(self, source: DataSource) -> Dict[str, Any]:
        """Convierte DataSource a dict para serialización."""
        return {
            "connection": asdict(source.connection),
            "tables": [asdict(table) for table in source.tables],
            "registered_at": source.registered_at,
            "tenant_id": source.tenant_id,
        }
    
    def _dict_to_source(self, data: Dict[str, Any]) -> DataSource:
        """Reconstruye DataSource desde dict."""
        connection = DatabaseConnection(**data["connection"])
        tables = [TableMetadata(**t) for t in data["tables"]]
        return DataSource(
            connection=connection,
            tables=tables,
            registered_at=data.get("registered_at", datetime.now().isoformat()),
            tenant_id=data.get("tenant_id"),
        )
    
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
    ) -> str:
        """Registra una nueva base de datos en el registry.
        
        Returns:
            source_id: ID único de la fuente registrada
        """
        connection = DatabaseConnection(
            name=name,
            db_type=db_type,
            host=host,
            port=port,
            database=database,
            username=username,
            connection_string_env=connection_string_env,
            description=description,
        )
        
        source_id = f"{name}_{db_type}_{database or 'default'}"
        source = DataSource(
            connection=connection,
            tenant_id=tenant_id,
        )
        
        self.sources[source_id] = source
        self._save_registry()
        print(f"✅ Base de datos registrada: {source_id}")
        return source_id
    
    def register_table(
        self,
        source_id: str,
        table_name: str,
        description: Optional[str] = None,
        business_domain: Optional[str] = None,
        columns: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Registra una tabla en una fuente de datos existente.
        
        Args:
            source_id: ID de la fuente de datos
            table_name: Nombre de la tabla
            description: Descripción en lenguaje natural
            business_domain: Dominio de negocio (ej: "sales", "finance")
            columns: Lista de dicts con metadata de columnas
        
        Returns:
            True si se registró exitosamente
        """
        if source_id not in self.sources:
            print(f"❌ Fuente de datos no encontrada: {source_id}")
            return False
        
        source = self.sources[source_id]
        db_name = source.connection.database or source.connection.name
        
        # Verificar si la tabla ya existe
        existing_table = None
        for table in source.tables:
            if table.name == table_name:
                existing_table = table
                break
        
        if existing_table:
            # Actualizar tabla existente
            if description:
                existing_table.description = description
            if business_domain:
                existing_table.business_domain = business_domain
            if columns:
                existing_table.columns = [
                    ColumnMetadata(**col) if isinstance(col, dict) else col
                    for col in columns
                ]
        else:
            # Crear nueva tabla
            table = TableMetadata(
                name=table_name,
                database_name=db_name,
                description=description,
                business_domain=business_domain,
                columns=[
                    ColumnMetadata(**col) if isinstance(col, dict) else col
                    for col in (columns or [])
                ],
            )
            source.tables.append(table)
        
        # Re-indexar
        for table in source.tables:
            if table.name == table_name:
                key = f"{db_name}.{table.name}"
                self.table_index[key] = table
                for col in table.columns:
                    col_key = f"{key}.{col.name}"
                    self.column_index[col_key] = col
                break
        
        self._save_registry()
        print(f"✅ Tabla registrada: {source_id}.{table_name}")
        return True
    
    def search_tables(
        self,
        query: str,
        limit: int = 10,
        tenant_id: Optional[str] = None,
    ) -> List[TableMetadata]:
        """Busca tablas relevantes usando búsqueda semántica/keyword.
        
        Args:
            query: Query en lenguaje natural
            limit: Número máximo de resultados
            tenant_id: Filtrar por tenant
        
        Returns:
            Lista de tablas ordenadas por relevancia
        """
        results = []
        
        # Búsqueda keyword simple (si no hay embeddings)
        query_lower = query.lower()
        
        for table_key, table in self.table_index.items():
            # Filtrar por tenant si se especifica
            if tenant_id:
                # Buscar en sources para obtener tenant_id
                found = False
                for source in self.sources.values():
                    if table in source.tables:
                        if source.tenant_id == tenant_id:
                            found = True
                        break
                if not found:
                    continue
            
            score = 0.0
            
            # Match en nombre de tabla
            if query_lower in table.name.lower():
                score += 2.0
            
            # Match en descripción
            if table.description and query_lower in table.description.lower():
                score += 1.5
            
            # Match en business_domain
            if table.business_domain and query_lower in table.business_domain.lower():
                score += 1.0
            
            # Match en nombres de columnas
            for col in table.columns:
                if query_lower in col.name.lower():
                    score += 0.5
                if col.description and query_lower in col.description.lower():
                    score += 0.3
            
            if score > 0:
                results.append((score, table))
        
        # Ordenar por score y retornar top N
        results.sort(key=lambda x: x[0], reverse=True)
        return [table for _, table in results[:limit]]
    
    def search_columns(
        self,
        query: str,
        table_name: Optional[str] = None,
        limit: int = 20,
    ) -> List[ColumnMetadata]:
        """Busca columnas relevantes.
        
        Args:
            query: Query en lenguaje natural
            table_name: Filtrar por tabla específica (opcional)
            limit: Número máximo de resultados
        
        Returns:
            Lista de columnas ordenadas por relevancia
        """
        results = []
        query_lower = query.lower()
        
        for col_key, col in self.column_index.items():
            # Filtrar por tabla si se especifica
            if table_name and table_name not in col_key:
                continue
            
            score = 0.0
            
            # Match en nombre
            if query_lower in col.name.lower():
                score += 2.0
            
            # Match en descripción
            if col.description and query_lower in col.description.lower():
                score += 1.5
            
            # Match en data_type
            if query_lower in col.data_type.lower():
                score += 0.5
            
            if score > 0:
                results.append((score, col))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [col for _, col in results[:limit]]
    
    def get_schema_context(
        self,
        table_names: List[str],
        include_samples: bool = False,
    ) -> str:
        """Genera contexto de schema para SQL generation.
        
        Args:
            table_names: Lista de nombres de tablas (formato "db.table" o solo "table")
            include_samples: Incluir valores de ejemplo en columnas
        
        Returns:
            String con contexto de schema formateado
        """
        context_parts = []
        
        for table_key in table_names:
            # Buscar tabla en índice
            table = None
            for key, t in self.table_index.items():
                if table_key in key or t.name == table_key:
                    table = t
                    break
            
            if not table:
                continue
            
            # Formatear metadata de tabla
            table_info = f"Table: {table.name}"
            if table.description:
                table_info += f" ({table.description})"
            if table.business_domain:
                table_info += f" [Domain: {table.business_domain}]"
            context_parts.append(table_info)
            
            # Formatear columnas
            for col in table.columns:
                col_info = f"  - {col.name} ({col.data_type})"
                if col.description:
                    col_info += f": {col.description}"
                if col.is_primary_key:
                    col_info += " [PRIMARY KEY]"
                if col.is_foreign_key:
                    col_info += f" [FOREIGN KEY -> {col.foreign_key_table}.{col.foreign_key_column}]"
                if include_samples and col.sample_values:
                    samples = ", ".join(col.sample_values[:3])
                    col_info += f" [Examples: {samples}]"
                context_parts.append(col_info)
            
            context_parts.append("")  # Separador
        
        return "\n".join(context_parts)
    
    def list_sources(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista todas las fuentes de datos registradas."""
        sources = []
        for source_id, source in self.sources.items():
            if tenant_id and source.tenant_id != tenant_id:
                continue
            sources.append({
                "source_id": source_id,
                "name": source.connection.name,
                "db_type": source.connection.db_type,
                "database": source.connection.database,
                "tables_count": len(source.tables),
                "description": source.connection.description,
            })
        return sources


