"""
Sistema de Tareas Personalizadas para JARVIS
Permite a los usuarios definir tareas personalizadas que JARVIS ejecuta en su loop 24/7
"""

from __future__ import annotations

import json
import time
import uuid
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
from datetime import datetime, timedelta
import logging

from .config import AppConfig

logger = logging.getLogger(__name__)


class TaskSchedule(str, Enum):
    """Frecuencia de ejecución de tareas."""
    CONTINUOUS = "continuous"  # Cada ciclo del loop
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM_CRON = "custom_cron"  # Expresión cron personalizada


@dataclass
class CustomTask:
    """Tarea personalizada definida por el usuario."""
    task_id: str
    name: str
    description: str
    instructions: str  # Instrucciones en lenguaje natural para JARVIS
    schedule: TaskSchedule = TaskSchedule.DAILY
    cron_expression: Optional[str] = None  # Si schedule es CUSTOM_CRON
    enabled: bool = True
    priority: str = "medium"  # "low", "medium", "high", "critical"
    parameters: Dict[str, Any] = field(default_factory=dict)
    last_executed: Optional[float] = None
    next_execution: Optional[float] = None
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    created_at: float = field(default_factory=time.time)
    created_by: str = "user"
    tags: List[str] = field(default_factory=list)
    
    def should_execute(self, current_time: float) -> bool:
        """Determina si la tarea debe ejecutarse ahora."""
        if not self.enabled:
            return False
        
        if self.next_execution is None:
            # Primera ejecución
            return True
        
        return current_time >= self.next_execution
    
    def calculate_next_execution(self, current_time: float):
        """Calcula el próximo tiempo de ejecución."""
        if self.schedule == TaskSchedule.CONTINUOUS:
            self.next_execution = current_time + 60  # Cada minuto
        elif self.schedule == TaskSchedule.HOURLY:
            self.next_execution = current_time + 3600  # 1 hora
        elif self.schedule == TaskSchedule.DAILY:
            self.next_execution = current_time + 86400  # 24 horas
        elif self.schedule == TaskSchedule.WEEKLY:
            self.next_execution = current_time + 604800  # 7 días
        elif self.schedule == TaskSchedule.MONTHLY:
            self.next_execution = current_time + 2592000  # 30 días
        elif self.schedule == TaskSchedule.CUSTOM_CRON:
            # Parsear expresión cron básica (simplificado)
            # Formato: "minuto hora día mes día_semana"
            # Por ahora, solo soportamos horarios simples
            if self.cron_expression:
                # Ejemplo: "0 9 * * *" = cada día a las 9:00 AM
                parts = self.cron_expression.split()
                if len(parts) >= 2:
                    try:
                        hour = int(parts[1])
                        minute = int(parts[0])
                        # Calcular próximo tiempo
                        now = datetime.fromtimestamp(current_time)
                        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        if next_run <= now:
                            next_run += timedelta(days=1)
                        self.next_execution = next_run.timestamp()
                    except:
                        # Fallback a diario
                        self.next_execution = current_time + 86400
            else:
                self.next_execution = current_time + 86400
        else:
            self.next_execution = current_time + 86400  # Default diario


@dataclass
class TaskExecution:
    """Registro de ejecución de una tarea personalizada."""
    execution_id: str
    task_id: str
    started_at: float
    completed_at: Optional[float] = None
    status: str = "running"  # "running", "completed", "failed"
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0


class CustomTaskManager:
    """Gestiona todas las tareas personalizadas de JARVIS."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.tasks: Dict[str, CustomTask] = {}
        self.executions: List[TaskExecution] = []
        self.storage_file = Path(config.memory_dir) / "custom_tasks.json"
        self.executions_file = Path(config.memory_dir) / "task_executions.json"
        
        # Cargar tareas guardadas
        self._load_tasks()
        self._load_executions()
    
    def _load_tasks(self):
        """Carga tareas personalizadas desde almacenamiento."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for task_data in data.get("tasks", []):
                        task = CustomTask(**task_data)
                        self.tasks[task.task_id] = task
                logger.info(f"✅ [Custom Tasks] {len(self.tasks)} tareas cargadas")
            except Exception as e:
                logger.error(f"❌ [Custom Tasks] Error cargando tareas: {e}")
    
    def _save_tasks(self):
        """Guarda tareas personalizadas."""
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = {
                "tasks": [asdict(task) for task in self.tasks.values()]
            }
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ [Custom Tasks] Error guardando tareas: {e}")
    
    def _load_executions(self):
        """Carga historial de ejecuciones."""
        if self.executions_file.exists():
            try:
                with open(self.executions_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for exec_data in data.get("executions", []):
                        execution = TaskExecution(**exec_data)
                        self.executions.append(execution)
                # Mantener solo las últimas 1000 ejecuciones
                if len(self.executions) > 1000:
                    self.executions = self.executions[-1000:]
            except Exception as e:
                logger.error(f"❌ [Custom Tasks] Error cargando ejecuciones: {e}")
    
    def _save_executions(self):
        """Guarda historial de ejecuciones."""
        self.executions_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = {
                "executions": [asdict(exec) for exec in self.executions[-1000:]]
            }
            with open(self.executions_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ [Custom Tasks] Error guardando ejecuciones: {e}")
    
    def create_task(
        self,
        name: str,
        description: str,
        instructions: str,
        schedule: TaskSchedule = TaskSchedule.DAILY,
        cron_expression: Optional[str] = None,
        priority: str = "medium",
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Crea una nueva tarea personalizada.
        
        Returns:
            task_id: ID de la tarea creada
        """
        task_id = str(uuid.uuid4())
        
        task = CustomTask(
            task_id=task_id,
            name=name,
            description=description,
            instructions=instructions,
            schedule=schedule,
            cron_expression=cron_expression,
            priority=priority,
            parameters=parameters or {},
            tags=tags or []
        )
        
        # Calcular próxima ejecución
        task.calculate_next_execution(time.time())
        
        self.tasks[task_id] = task
        self._save_tasks()
        
        logger.info(f"✅ [Custom Tasks] Tarea creada: {name} ({task_id})")
        return task_id
    
    def update_task(
        self,
        task_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        schedule: Optional[TaskSchedule] = None,
        cron_expression: Optional[str] = None,
        enabled: Optional[bool] = None,
        priority: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Actualiza una tarea existente."""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        if name is not None:
            task.name = name
        if description is not None:
            task.description = description
        if instructions is not None:
            task.instructions = instructions
        if schedule is not None:
            task.schedule = schedule
        if cron_expression is not None:
            task.cron_expression = cron_expression
        if enabled is not None:
            task.enabled = enabled
        if priority is not None:
            task.priority = priority
        if parameters is not None:
            task.parameters.update(parameters)
        if tags is not None:
            task.tags = tags
        
        # Recalcular próxima ejecución si cambió el schedule
        if schedule is not None or cron_expression is not None:
            task.calculate_next_execution(time.time())
        
        self._save_tasks()
        logger.info(f"✅ [Custom Tasks] Tarea actualizada: {task_id}")
        return True
    
    def delete_task(self, task_id: str) -> bool:
        """Elimina una tarea."""
        if task_id not in self.tasks:
            return False
        
        del self.tasks[task_id]
        self._save_tasks()
        logger.info(f"✅ [Custom Tasks] Tarea eliminada: {task_id}")
        return True
    
    def get_task(self, task_id: str) -> Optional[CustomTask]:
        """Obtiene una tarea por ID."""
        return self.tasks.get(task_id)
    
    def list_tasks(
        self,
        enabled_only: bool = False,
        tag_filter: Optional[str] = None
    ) -> List[CustomTask]:
        """Lista todas las tareas."""
        tasks = list(self.tasks.values())
        
        if enabled_only:
            tasks = [t for t in tasks if t.enabled]
        
        if tag_filter:
            tasks = [t for t in tasks if tag_filter in t.tags]
        
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)
    
    def get_tasks_to_execute(self, current_time: float) -> List[CustomTask]:
        """Obtiene todas las tareas que deben ejecutarse ahora."""
        return [
            task for task in self.tasks.values()
            if task.should_execute(current_time)
        ]
    
    def record_execution(
        self,
        task_id: str,
        status: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        execution_time: float = 0.0
    ) -> str:
        """Registra una ejecución de tarea."""
        execution_id = str(uuid.uuid4())
        
        execution = TaskExecution(
            execution_id=execution_id,
            task_id=task_id,
            started_at=time.time() - execution_time,
            completed_at=time.time(),
            status=status,
            result=result,
            error=error,
            execution_time=execution_time
        )
        
        self.executions.append(execution)
        
        # Actualizar estadísticas de la tarea
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.execution_count += 1
            task.last_executed = time.time()
            
            if status == "completed":
                task.success_count += 1
            elif status == "failed":
                task.failure_count += 1
            
            # Calcular próxima ejecución
            task.calculate_next_execution(time.time())
            self._save_tasks()
        
        # Mantener solo últimas 1000 ejecuciones
        if len(self.executions) > 1000:
            self.executions = self.executions[-1000:]
        
        self._save_executions()
        
        return execution_id
    
    def get_execution_history(
        self,
        task_id: Optional[str] = None,
        limit: int = 100
    ) -> List[TaskExecution]:
        """Obtiene historial de ejecuciones."""
        executions = self.executions
        
        if task_id:
            executions = [e for e in executions if e.task_id == task_id]
        
        return sorted(executions, key=lambda e: e.started_at, reverse=True)[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de tareas personalizadas."""
        total_tasks = len(self.tasks)
        enabled_tasks = len([t for t in self.tasks.values() if t.enabled])
        
        total_executions = len(self.executions)
        successful_executions = len([e for e in self.executions if e.status == "completed"])
        failed_executions = len([e for e in self.executions if e.status == "failed"])
        
        return {
            "total_tasks": total_tasks,
            "enabled_tasks": enabled_tasks,
            "disabled_tasks": total_tasks - enabled_tasks,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": (successful_executions / total_executions * 100) if total_executions > 0 else 0,
            "tasks_by_schedule": {
                schedule.value: len([t for t in self.tasks.values() if t.schedule == schedule])
                for schedule in TaskSchedule
            }
        }


