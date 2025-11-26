"""Tool for advanced table analysis."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import pandas as pd
import json

from .base_tool import BaseTool, ToolResult


class TableAnalysisTool(BaseTool):
    """Tool for analyzing tables extracted from documents."""
    
    def get_name(self) -> str:
        return "table_analyzer"
    
    def get_description(self) -> str:
        return "Analyze tables from documents: extract data, find trends, calculate statistics"
    
    def get_keywords(self) -> List[str]:
        return ["tabla", "table", "analizar tabla", "datos estructurados", "estadísticas", "tendencias"]
    
    def execute(
        self,
        table_data: List[List] | Dict | pd.DataFrame,
        analysis_type: str = "summary",
        **kwargs
    ) -> ToolResult:
        """Analyze table data."""
        try:
            # Convert to DataFrame
            if isinstance(table_data, pd.DataFrame):
                df = table_data
            elif isinstance(table_data, list):
                df = pd.DataFrame(table_data)
            elif isinstance(table_data, dict):
                df = pd.DataFrame([table_data])
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message="Invalid table data format",
                    metadata={}
                )
            
            if analysis_type == "summary":
                return self._analyze_summary(df)
            elif analysis_type == "trends":
                return self._analyze_trends(df)
            elif analysis_type == "statistics":
                return self._analyze_statistics(df)
            elif analysis_type == "comparison":
                return self._analyze_comparison(df, kwargs.get("compare_with"))
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Unsupported analysis type: {analysis_type}",
                    metadata={}
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Table analysis failed: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _analyze_summary(self, df: pd.DataFrame) -> ToolResult:
        """Generate summary of table."""
        summary = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": df.columns.tolist(),
            "data_types": df.dtypes.astype(str).to_dict(),
            "null_counts": df.isnull().sum().to_dict(),
            "sample_data": df.head(5).to_dict('records')
        }
        
        return ToolResult(
            success=True,
            data=summary,
            message=f"Table summary: {len(df)} rows, {len(df.columns)} columns",
            metadata={"analysis_type": "summary"}
        )
    
    def _analyze_trends(self, df: pd.DataFrame) -> ToolResult:
        """Analyze trends in numeric columns."""
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        trends = {}
        for col in numeric_cols:
            if len(df) > 1:
                trends[col] = {
                    "trend": "increasing" if df[col].iloc[-1] > df[col].iloc[0] else "decreasing",
                    "change": float(df[col].iloc[-1] - df[col].iloc[0]),
                    "change_percent": float((df[col].iloc[-1] - df[col].iloc[0]) / df[col].iloc[0] * 100) if df[col].iloc[0] != 0 else 0
                }
        
        return ToolResult(
            success=True,
            data={"trends": trends, "numeric_columns": numeric_cols.tolist()},
            message=f"Trend analysis completed for {len(numeric_cols)} numeric columns",
            metadata={"analysis_type": "trends"}
        )
    
    def _analyze_statistics(self, df: pd.DataFrame) -> ToolResult:
        """Calculate statistics for numeric columns."""
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        stats = {}
        for col in numeric_cols:
            stats[col] = {
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "count": int(df[col].count())
            }
        
        return ToolResult(
            success=True,
            data={"statistics": stats},
            message=f"Statistics calculated for {len(numeric_cols)} columns",
            metadata={"analysis_type": "statistics"}
        )
    
    def _analyze_comparison(self, df1: pd.DataFrame, df2: Optional[pd.DataFrame]) -> ToolResult:
        """Compare two tables."""
        if df2 is None:
            return ToolResult(
                success=False,
                data=None,
                message="Second table required for comparison",
                metadata={}
            )
        
        comparison = {
            "row_difference": len(df1) - len(df2),
            "column_difference": len(df1.columns) - len(df2.columns),
            "common_columns": list(set(df1.columns) & set(df2.columns))
        }
        
        return ToolResult(
            success=True,
            data=comparison,
            message="Table comparison completed",
            metadata={"analysis_type": "comparison"}
        )



