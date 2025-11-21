"""Base class for agent tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    data: Any
    message: str
    metadata: Dict[str, Any]


class BaseTool(ABC):
    """Base class for all agent tools."""
    
    def __init__(self, config: Any):
        self.config = config
        self.name = self.get_name()
        self.description = self.get_description()
    
    @abstractmethod
    def get_name(self) -> str:
        """Return the tool name."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return the tool description."""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
    
    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate input parameters. Returns (is_valid, error_message)."""
        return True, None
    
    def can_handle(self, task_description: str) -> bool:
        """Check if this tool can handle the given task."""
        keywords = self.get_keywords()
        task_lower = task_description.lower()
        return any(keyword in task_lower for keyword in keywords)
    
    @abstractmethod
    def get_keywords(self) -> List[str]:
        """Return keywords that indicate this tool should be used."""
        pass



