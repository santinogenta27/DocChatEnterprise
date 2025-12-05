"""Base tool class with standard contract and utilities."""

from __future__ import annotations

import json
import uuid
import time
from typing import Dict, Any, Optional, Callable
from abc import ABC, abstractmethod
from datetime import datetime


class ToolResponse:
    """Standard tool response contract."""
    
    def __init__(
        self,
        status: str,  # "ok" | "error" | "requires_confirmation"
        data: Optional[Dict[str, Any]] = None,
        tool_name: str = "",
        duration_ms: int = 0,
        request_id: str = "",
        source: str = "",
        error: Optional[Dict[str, Any]] = None
    ):
        self.status = status
        self.data = data or {}
        self.meta = {
            "tool_name": tool_name,
            "duration_ms": duration_ms,
            "request_id": request_id,
            "source": source
        }
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to standard JSON contract."""
        result = {
            "status": self.status,
            "data": self.data,
            "meta": self.meta
        }
        if self.error:
            result["error"] = self.error
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


def tool_wrapper(
    tool_name: str,
    source: str = "internal",
    requires_confirmation: bool = False
):
    """
    Decorator to wrap tool functions with standard contract.
    
    Usage:
        @tool_wrapper("search_web", source="tavily")
        def search_web(query: str, top_k: int = 5) -> str:
            ...
            return ToolResponse(...).to_json()
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> str:
            start_time = time.time()
            request_id = str(uuid.uuid4())
            
            try:
                # Call the actual tool function
                result = func(*args, **kwargs)
                
                # If result is already a ToolResponse, use it
                if isinstance(result, ToolResponse):
                    result.meta["tool_name"] = tool_name
                    result.meta["request_id"] = request_id
                    result.meta["source"] = source
                    result.meta["duration_ms"] = int((time.time() - start_time) * 1000)
                    return result.to_json()
                
                # If result is a dict, wrap it
                if isinstance(result, dict):
                    response = ToolResponse(
                        status="ok",
                        data=result,
                        tool_name=tool_name,
                        duration_ms=int((time.time() - start_time) * 1000),
                        request_id=request_id,
                        source=source
                    )
                    return response.to_json()
                
                # If result is a string (JSON), try to parse and wrap
                if isinstance(result, str):
                    try:
                        parsed = json.loads(result)
                        if isinstance(parsed, dict) and "status" in parsed:
                            # Already in contract format
                            return result
                        # Wrap it
                        response = ToolResponse(
                            status="ok",
                            data=parsed if isinstance(parsed, dict) else {"result": parsed},
                            tool_name=tool_name,
                            duration_ms=int((time.time() - start_time) * 1000),
                            request_id=request_id,
                            source=source
                        )
                        return response.to_json()
                    except:
                        # Plain string, wrap it
                        response = ToolResponse(
                            status="ok",
                            data={"result": result},
                            tool_name=tool_name,
                            duration_ms=int((time.time() - start_time) * 1000),
                            request_id=request_id,
                            source=source
                        )
                        return response.to_json()
                
                # Fallback
                response = ToolResponse(
                    status="ok",
                    data={"result": str(result)},
                    tool_name=tool_name,
                    duration_ms=int((time.time() - start_time) * 1000),
                    request_id=request_id,
                    source=source
                )
                return response.to_json()
                
            except Exception as e:
                # Error response
                error_response = ToolResponse(
                    status="error",
                    data={},
                    tool_name=tool_name,
                    duration_ms=int((time.time() - start_time) * 1000),
                    request_id=request_id,
                    source=source,
                    error={
                        "code": type(e).__name__,
                        "message": str(e),
                        "details": {}
                    }
                )
                return error_response.to_json()
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator

