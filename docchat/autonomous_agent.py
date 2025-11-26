"""Autonomous agent system with tool usage."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from .config import AppConfig
from .tools import (
    EmailTool, ReportTool, DatabaseTool, PresentationTool,
    IntegrationTool, TableAnalysisTool, SchedulerTool
)


@dataclass
class AgentTask:
    """A task for an autonomous agent."""
    task_id: str
    description: str
    priority: int = 5
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    result: Optional[Any] = None


class AutonomousAgent:
    """Autonomous agent that can use tools to complete tasks."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        # Initialize LLM - Only OpenAI supported
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY required")
        self.llm = ChatOpenAI(
            model=config.agentic_model,
            temperature=0.3,
            api_key=config.openai_api_key
        )
        
        # Initialize tools
        self.tools = {
            "email": EmailTool(config),
            "report": ReportTool(config),
            "database": DatabaseTool(config),
            "presentation": PresentationTool(config),
            "integration": IntegrationTool(config),
            "table_analysis": TableAnalysisTool(config),
            "scheduler": SchedulerTool(config),
        }
        
        self.tool_descriptions = self._build_tool_descriptions()
    
    def _build_tool_descriptions(self) -> str:
        """Build descriptions of available tools."""
        descriptions = []
        for name, tool in self.tools.items():
            descriptions.append(
                f"- {name}: {tool.get_description()}\n"
                f"  Keywords: {', '.join(tool.get_keywords())}"
            )
        return "\n".join(descriptions)
    
    def execute_task(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        max_iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute an autonomous task."""
        if not self.config.enable_autonomous_agents:
            return {
                "success": False,
                "message": "Autonomous agents are disabled",
                "result": None
            }
        
        max_iterations = max_iterations or self.config.max_agent_iterations
        context = context or {}
        
        # Determine which tools to use
        selected_tools = self._select_tools(task_description)
        
        if not selected_tools:
            return {
                "success": False,
                "message": "No suitable tools found for this task",
                "result": None
            }
        
        # Execute task with selected tools
        results = []
        for tool_name in selected_tools:
            tool = self.tools[tool_name]
            
            # Use LLM to extract parameters from task description
            parameters = self._extract_parameters(task_description, tool, context)
            
            # Execute tool
            try:
                result = tool.execute(**parameters)
                results.append({
                    "tool": tool_name,
                    "result": result,
                    "success": result.success
                })
            except Exception as e:
                results.append({
                    "tool": tool_name,
                    "result": None,
                    "success": False,
                    "error": str(e)
                })
        
        # Generate summary
        summary = self._generate_summary(task_description, results)
        
        return {
            "success": any(r["success"] for r in results),
            "task_description": task_description,
            "tools_used": selected_tools,
            "results": results,
            "summary": summary
        }
    
    def _select_tools(self, task_description: str) -> List[str]:
        """Select appropriate tools for the task."""
        selected = []
        task_lower = task_description.lower()
        
        for tool_name, tool in self.tools.items():
            if tool.can_handle(task_description):
                selected.append(tool_name)
        
        return selected
    
    def _extract_parameters(
        self,
        task_description: str,
        tool: Any,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use LLM to extract parameters for tool execution."""
        prompt = f"""You are a parameter extraction assistant. Extract parameters from the task description for the tool: {tool.get_name()}

Task: {task_description}
Tool: {tool.get_description()}
Context: {context}

Extract relevant parameters as a JSON object. Only include parameters that are clearly mentioned in the task.
Return only valid JSON, no additional text."""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            # Parse JSON from response
            import json
            import re
            
            # Try to extract JSON from response
            text = response.content
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
            if json_match:
                params = json.loads(json_match.group(0))
                return {**params, **context}
            else:
                # Fallback: return context with task description
                return {"task_description": task_description, **context}
        except Exception:
            # Fallback: return basic parameters
            return {"task_description": task_description, **context}
    
    def _generate_summary(
        self,
        task_description: str,
        results: List[Dict[str, Any]]
    ) -> str:
        """Generate a summary of task execution."""
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        
        summary = f"Task: {task_description}\n\n"
        summary += f"Tools executed: {len(results)}\n"
        summary += f"Successful: {len(successful)}\n"
        summary += f"Failed: {len(failed)}\n\n"
        
        if successful:
            summary += "Successful operations:\n"
            for r in successful:
                tool_result = r.get("result")
                if tool_result:
                    summary += f"- {r['tool']}: {tool_result.message}\n"
        
        if failed:
            summary += "\nFailed operations:\n"
            for r in failed:
                error = r.get("error", "Unknown error")
                summary += f"- {r['tool']}: {error}\n"
        
        return summary

