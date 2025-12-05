"""Service-oriented scheduler and execution graph for Research & Action Agent.

Este módulo implementa una versión ligera de AaaS-AN:

- ServiceDescriptor: describe un rol/servicio (RGPS-style).
- ExecutionNode / ExecutionGraph: grafo dirigido de pasos.
- ServiceScheduler: orquesta servicios registrados.

No pretende reemplazar frameworks de orquestación complejos, pero
proporciona una capa clara y testeable para ejecutar flujos
multi-servicio dentro del modo Research & Action Agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ServiceDescriptor:
    """Describe un servicio / rol disponible para el scheduler."""

    name: str
    description: str
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionNode:
    """Nodo dentro de un ExecutionGraph."""

    node_id: str
    service_name: str
    params: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class ExecutionGraph:
    """Representa un grafo de ejecución de servicios."""

    nodes: Dict[str, ExecutionNode] = field(default_factory=dict)

    def add_node(self, node: ExecutionNode) -> None:
        if node.node_id in self.nodes:
            raise ValueError(f"Node {node.node_id} already exists in graph")
        self.nodes[node.node_id] = node

    def get_ready_nodes(self) -> List[ExecutionNode]:
        """Return nodes whose dependencies have completed and not yet executed."""
        ready: List[ExecutionNode] = []
        for node in self.nodes.values():
            if node.result is not None or node.error is not None:
                continue
            # All dependencies must have result and no error
            if all(
                dep_id in self.nodes
                and self.nodes[dep_id].result is not None
                and self.nodes[dep_id].error is None
                for dep_id in node.depends_on
            ):
                ready.append(node)
        return ready

    def is_completed(self) -> bool:
        return all(node.result is not None or node.error is not None for node in self.nodes.values())


class ServiceScheduler:
    """Orquesta servicios registrados usando un ExecutionGraph."""

    def __init__(self):
        self.services: Dict[str, ServiceDescriptor] = {}

    # Registro de servicios ---------------------------------------------

    def register_service(self, service: ServiceDescriptor) -> None:
        if service.name in self.services:
            raise ValueError(f"Service {service.name} already registered")
        self.services[service.name] = service

    def get_service(self, name: str) -> ServiceDescriptor:
        if name not in self.services:
            raise KeyError(f"Service {name} not found")
        return self.services[name]

    # Ejecución ---------------------------------------------------------

    def run_graph(self, graph: ExecutionGraph, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute an ExecutionGraph synchronously.

        - Ejecuta nodos en orden topológico (respetando depends_on).
        - Propaga resultados previos al contexto de cada nodo.
        - No soporta paralelismo real, pero el diseño lo permitiría.
        """
        context: Dict[str, Any] = dict(initial_context or {})
        execution_log: List[Dict[str, Any]] = []

        # Simple loop until graph is completed or no progress
        while not graph.is_completed():
            ready_nodes = graph.get_ready_nodes()
            if not ready_nodes:
                # Deadlock: remaining nodes cannot be executed
                break

            for node in ready_nodes:
                service = self.get_service(node.service_name)
                # Merge global context + node params
                payload = {**context, **node.params}
                try:
                    result = service.handler(payload)
                    node.result = result
                    # Update global context with node id and result
                    context[node.node_id] = result
                    execution_log.append(
                        {
                            "node_id": node.node_id,
                            "service": node.service_name,
                            "params": node.params,
                            "result": result,
                        }
                    )
                except Exception as e:  # pragma: no cover - unexpected runtime errors
                    node.error = str(e)
                    execution_log.append(
                        {
                            "node_id": node.node_id,
                            "service": node.service_name,
                            "params": node.params,
                            "error": str(e),
                        }
                    )

        return {
            "completed": graph.is_completed(),
            "context": context,
            "log": execution_log,
        }


__all__ = ["ServiceDescriptor", "ExecutionNode", "ExecutionGraph", "ServiceScheduler"]


