"""Tool for scheduling tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path

from .base_tool import BaseTool, ToolResult


class SchedulerTool(BaseTool):
    """Tool for scheduling automated tasks."""
    
    def __init__(self, config: Any):
        super().__init__(config)
        self.schedule_file = config.memory_dir / "scheduled_tasks.json"
        self.schedule_file.parent.mkdir(parents=True, exist_ok=True)
    
    def get_name(self) -> str:
        return "task_scheduler"
    
    def get_description(self) -> str:
        return "Schedule automated tasks to run at specific times or intervals"
    
    def get_keywords(self) -> List[str]:
        return ["programar", "schedule", "tarea programada", "automatizar", "cron", "recurrente"]
    
    def execute(
        self,
        task_name: str,
        task_type: str,
        schedule: str,
        task_data: Dict,
        **kwargs
    ) -> ToolResult:
        """Schedule a task."""
        try:
            # Load existing schedules
            schedules = self._load_schedules()
            
            # Create new schedule entry
            schedule_entry = {
                "task_name": task_name,
                "task_type": task_type,
                "schedule": schedule,
                "task_data": task_data,
                "created_at": datetime.now().isoformat(),
                "status": "scheduled"
            }
            
            schedules.append(schedule_entry)
            
            # Save schedules
            self._save_schedules(schedules)
            
            return ToolResult(
                success=True,
                data={"task_name": task_name, "schedule": schedule},
                message=f"Task '{task_name}' scheduled successfully",
                metadata={"total_scheduled": len(schedules)}
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                message=f"Failed to schedule task: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _load_schedules(self) -> List[Dict]:
        """Load scheduled tasks from file."""
        if self.schedule_file.exists():
            with open(self.schedule_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_schedules(self, schedules: List[Dict]):
        """Save scheduled tasks to file."""
        with open(self.schedule_file, 'w', encoding='utf-8') as f:
            json.dump(schedules, f, indent=2, ensure_ascii=False)



