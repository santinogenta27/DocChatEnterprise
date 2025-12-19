"""
Simple queue system for asynchronous processing
Uses ThreadPoolExecutor for lightweight async processing
"""
import logging
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any, Optional, Dict
from queue import Queue
import threading

from .logging import setup_logger

logger = setup_logger("ads_worker.queue")


class SimpleTaskQueue:
    """Simple task queue for processing assets and campaigns asynchronously"""
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize task queue
        
        Args:
            max_workers: Maximum number of worker threads
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = Queue()
        self.results = {}
        self.result_lock = threading.Lock()
        logger.info(f"✅ Task queue inicializado con {max_workers} workers")
    
    def submit_task(
        self,
        task_id: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Future:
        """
        Submit a task to the queue
        
        Args:
            task_id: Unique task identifier
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Future object
        """
        logger.info(f"📤 Enviando tarea a cola: {task_id}")
        
        future = self.executor.submit(func, *args, **kwargs)
        
        # Store result mapping
        with self.result_lock:
            self.results[task_id] = {
                "future": future,
                "status": "pending"
            }
        
        return future
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get task status
        
        Args:
            task_id: Task identifier
            
        Returns:
            Status dictionary
        """
        with self.result_lock:
            if task_id not in self.results:
                return {"status": "not_found"}
            
            task_info = self.results[task_id]
            future = task_info["future"]
            
            if future.done():
                try:
                    result = future.result()
                    return {
                        "status": "completed",
                        "result": result
                    }
                except Exception as e:
                    return {
                        "status": "failed",
                        "error": str(e)
                    }
            else:
                return {
                    "status": "running"
                }
    
    def shutdown(self, wait: bool = True):
        """Shutdown the executor"""
        self.executor.shutdown(wait=wait)
        logger.info("Task queue cerrado")




