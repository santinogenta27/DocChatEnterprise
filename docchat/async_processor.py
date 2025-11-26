"""
Procesamiento asíncrono con colas para grandes volúmenes de documentos.
"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from queue import Queue, Empty

from langchain_core.documents import Document

from .config import AppConfig
from .document_processor import DocumentProcessor


@dataclass
class ProcessingTask:
    """Tarea de procesamiento."""
    task_id: str
    files: List[Any]
    callback: Optional[Callable] = None
    metadata: Dict[str, Any] = None


@dataclass
class ProcessingResult:
    """Resultado de procesamiento."""
    task_id: str
    success: bool
    documents: List[Document]
    error: Optional[str] = None
    processing_time: float = 0.0


class AsyncDocumentProcessor:
    """
    Procesador asíncrono de documentos con cola de tareas.
    Permite procesar grandes volúmenes sin bloquear la aplicación.
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.document_processor = DocumentProcessor(config)
        
        # Cola de tareas
        self.task_queue: Queue = Queue()
        self.results: Dict[str, ProcessingResult] = {}
        
        # Thread pool para procesamiento
        self.executor = ThreadPoolExecutor(
            max_workers=config.max_workers or 8,
            thread_name_prefix="doc_processor"
        )
        
        # Estado
        self.is_processing = False
        self.active_tasks = 0
        self.max_concurrent_tasks = config.max_workers or 8
    
    def submit_task(
        self,
        files: List[Any],
        callback: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Envía una tarea de procesamiento a la cola.
        
        Returns:
            task_id: ID único de la tarea
        """
        import uuid
        task_id = str(uuid.uuid4())
        
        task = ProcessingTask(
            task_id=task_id,
            files=files,
            callback=callback,
            metadata=metadata or {}
        )
        
        self.task_queue.put(task)
        
        # Iniciar procesamiento si no está activo
        if not self.is_processing:
            self._start_processing()
        
        return task_id
    
    def _start_processing(self):
        """Inicia el procesamiento de tareas en background."""
        if self.is_processing:
            return
        
        self.is_processing = True
        
        # Ejecutar en thread separado
        import threading
        thread = threading.Thread(target=self._process_queue, daemon=True)
        thread.start()
    
    def _process_queue(self):
        """Procesa tareas de la cola."""
        while True:
            try:
                # Obtener tarea de la cola (con timeout para poder salir)
                try:
                    task = self.task_queue.get(timeout=1.0)
                except Empty:
                    if self.active_tasks == 0:
                        self.is_processing = False
                        break
                    continue
                
                # Procesar en thread pool
                self.active_tasks += 1
                future = self.executor.submit(self._process_task, task)
                
                # No esperar, continuar con siguiente tarea
                self.task_queue.task_done()
                
            except Exception as e:
                print(f"Error en procesamiento de cola: {e}")
                self.is_processing = False
                break
    
    def _process_task(self, task: ProcessingTask):
        """Procesa una tarea individual."""
        start_time = time.time()
        
        try:
            # Procesar documentos
            documents = self.document_processor.process(task.files)
            
            result = ProcessingResult(
                task_id=task.task_id,
                success=True,
                documents=documents,
                processing_time=time.time() - start_time
            )
            
            # Guardar resultado
            self.results[task.task_id] = result
            
            # Ejecutar callback si existe
            if task.callback:
                try:
                    task.callback(result)
                except Exception as e:
                    print(f"Error en callback: {e}")
        
        except Exception as e:
            result = ProcessingResult(
                task_id=task.task_id,
                success=False,
                documents=[],
                error=str(e),
                processing_time=time.time() - start_time
            )
            self.results[task.task_id] = result
        
        finally:
            self.active_tasks -= 1
    
    def get_result(self, task_id: str) -> Optional[ProcessingResult]:
        """Obtiene resultado de una tarea."""
        return self.results.get(task_id)
    
    def wait_for_result(self, task_id: str, timeout: float = 300.0) -> Optional[ProcessingResult]:
        """Espera por resultado de una tarea."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.results.get(task_id)
            if result:
                return result
            time.sleep(0.5)
        
        return None
    
    def get_queue_size(self) -> int:
        """Obtiene tamaño de la cola."""
        return self.task_queue.qsize()
    
    def get_active_tasks_count(self) -> int:
        """Obtiene número de tareas activas."""
        return self.active_tasks
    
    def shutdown(self):
        """Cierra el procesador."""
        self.executor.shutdown(wait=True)

