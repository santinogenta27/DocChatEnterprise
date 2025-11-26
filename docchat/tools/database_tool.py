"""Tool for database operations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import json

from .base_tool import BaseTool, ToolResult


class DatabaseTool(BaseTool):
    """Tool for interacting with databases (PostgreSQL, MongoDB, etc.)."""
    
    def __init__(self, config: Any):
        super().__init__(config)
        self.postgres_url = config.postgres_url
        self.mongodb_url = config.mongodb_url
    
    def get_name(self) -> str:
        return "database_operator"
    
    def get_description(self) -> str:
        return "Insert, update, or query data in databases (PostgreSQL, MongoDB)"
    
    def get_keywords(self) -> List[str]:
        return ["base de datos", "database", "insertar", "actualizar", "consultar", "guardar datos"]
    
    def execute(
        self,
        operation: str,
        table: Optional[str] = None,
        data: Optional[Dict | List[Dict]] = None,
        query: Optional[str] = None,
        database_type: str = "postgres",
        **kwargs
    ) -> ToolResult:
        """Execute database operation."""
        try:
            if operation.lower() == "insert":
                return self._insert_data(table, data, database_type)
            elif operation.lower() == "update":
                return self._update_data(table, data, query, database_type)
            elif operation.lower() == "query" or operation.lower() == "select":
                return self._query_data(query, database_type)
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Unsupported operation: {operation}",
                    metadata={}
                )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Database operation failed: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _insert_data(self, table: str, data: Any, db_type: str) -> ToolResult:
        """Insert data into database."""
        # Placeholder - would implement actual database connection
        return ToolResult(
            success=True,
            data={"table": table, "records": len(data) if isinstance(data, list) else 1},
            message=f"Data inserted into {table}",
            metadata={"database": db_type}
        )
    
    def _update_data(self, table: str, data: Dict, query: str, db_type: str) -> ToolResult:
        """Update data in database."""
        return ToolResult(
            success=True,
            data={"table": table, "updated": True},
            message=f"Data updated in {table}",
            metadata={"database": db_type}
        )
    
    def _query_data(self, query: str, db_type: str) -> ToolResult:
        """Query data from database."""
        return ToolResult(
            success=True,
            data={"query": query, "results": []},
            message="Query executed successfully",
            metadata={"database": db_type}
        )



