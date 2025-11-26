"""Tool for generating reports in various formats."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import pandas as pd

from .base_tool import BaseTool, ToolResult


class ReportTool(BaseTool):
    """Tool for generating reports in Excel, PDF, JSON, and Markdown formats."""
    
    def get_name(self) -> str:
        return "report_generator"
    
    def get_description(self) -> str:
        return "Generate reports in Excel, JSON, Markdown, or CSV format from analysis results"
    
    def get_keywords(self) -> List[str]:
        return ["reporte", "generar reporte", "crear reporte", "exportar", "excel", "csv", "json"]
    
    def execute(
        self,
        data: Dict | List[Dict],
        format: str = "excel",
        output_path: Optional[str] = None,
        title: str = "Report",
        **kwargs
    ) -> ToolResult:
        """Generate a report in the specified format."""
        try:
            if output_path is None:
                output_path = self.config.memory_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == "excel":
                return self._generate_excel(data, output_path, title)
            elif format.lower() == "json":
                return self._generate_json(data, output_path)
            elif format.lower() == "csv":
                return self._generate_csv(data, output_path)
            elif format.lower() == "markdown" or format.lower() == "md":
                return self._generate_markdown(data, output_path, title)
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    message=f"Unsupported format: {format}",
                    metadata={}
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to generate report: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _generate_excel(self, data: Any, output_path: Path, title: str) -> ToolResult:
        """Generate Excel report."""
        try:
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # Try to convert dict to DataFrame
                if all(isinstance(v, (list, dict)) for v in data.values()):
                    df = pd.DataFrame(data)
                else:
                    df = pd.DataFrame([data])
            else:
                df = pd.DataFrame([{"data": str(data)}])
            
            excel_path = output_path.with_suffix('.xlsx')
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Report', index=False)
            
            return ToolResult(
                success=True,
                data={"path": str(excel_path), "rows": len(df)},
                message=f"Excel report generated: {excel_path}",
                metadata={"format": "excel", "rows": len(df)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Excel generation failed: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _generate_json(self, data: Any, output_path: Path) -> ToolResult:
        """Generate JSON report."""
        json_path = output_path.with_suffix('.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return ToolResult(
            success=True,
            data={"path": str(json_path)},
            message=f"JSON report generated: {json_path}",
            metadata={"format": "json"}
        )
    
    def _generate_csv(self, data: Any, output_path: Path) -> ToolResult:
        """Generate CSV report."""
        try:
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                df = pd.DataFrame([{"data": str(data)}])
            
            csv_path = output_path.with_suffix('.csv')
            df.to_csv(csv_path, index=False, encoding='utf-8')
            
            return ToolResult(
                success=True,
                data={"path": str(csv_path), "rows": len(df)},
                message=f"CSV report generated: {csv_path}",
                metadata={"format": "csv", "rows": len(df)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"CSV generation failed: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _generate_markdown(self, data: Any, output_path: Path, title: str) -> ToolResult:
        """Generate Markdown report."""
        md_path = output_path.with_suffix('.md')
        
        content = f"# {title}\n\n"
        content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        if isinstance(data, dict):
            content += self._dict_to_markdown(data)
        elif isinstance(data, list):
            content += self._list_to_markdown(data)
        else:
            content += f"```\n{str(data)}\n```\n"
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return ToolResult(
            success=True,
            data={"path": str(md_path)},
            message=f"Markdown report generated: {md_path}",
            metadata={"format": "markdown"}
        )
    
    def _dict_to_markdown(self, data: Dict, level: int = 0) -> str:
        """Convert dict to markdown."""
        content = ""
        indent = "  " * level
        for key, value in data.items():
            if isinstance(value, dict):
                content += f"{indent}- **{key}**:\n"
                content += self._dict_to_markdown(value, level + 1)
            elif isinstance(value, list):
                content += f"{indent}- **{key}**:\n"
                for item in value:
                    if isinstance(item, dict):
                        content += self._dict_to_markdown(item, level + 1)
                    else:
                        content += f"{indent}  - {item}\n"
            else:
                content += f"{indent}- **{key}**: {value}\n"
        return content
    
    def _list_to_markdown(self, data: List) -> str:
        """Convert list to markdown."""
        content = ""
        for i, item in enumerate(data, 1):
            if isinstance(item, dict):
                content += f"\n## Item {i}\n\n"
                content += self._dict_to_markdown(item)
            else:
                content += f"{i}. {item}\n"
        return content



