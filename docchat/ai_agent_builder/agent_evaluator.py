"""
Agent Evaluator - Sistema de evaluación y benchmarking
Evalúa agentes con métricas de performance, costo, y calidad
"""

from __future__ import annotations

import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EvaluationMetrics:
    """Métricas de evaluación"""
    accuracy: float = 0.0
    latency_ms: float = 0.0
    cost_per_1k_requests: float = 0.0
    token_usage: int = 0
    error_rate: float = 0.0
    user_satisfaction: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class BenchmarkTest:
    """Test de benchmark"""
    test_id: str
    name: str
    description: str
    test_prompts: List[str]
    expected_outputs: Optional[List[str]] = None
    evaluation_criteria: Dict[str, Any] = field(default_factory=dict)


class BenchmarkSuite:
    """
    Suite de benchmarks para evaluar agentes
    Incluye tests estándar y personalizados
    """
    
    def __init__(self):
        self.tests: Dict[str, BenchmarkTest] = {}
        self._initialize_standard_tests()
    
    def _initialize_standard_tests(self):
        """Inicializa tests estándar"""
        # Test de precisión básica
        self.tests["accuracy_basic"] = BenchmarkTest(
            test_id="accuracy_basic",
            name="Basic Accuracy Test",
            description="Evalúa precisión básica con preguntas simples",
            test_prompts=[
                "What is 2+2?",
                "What is the capital of France?",
                "Who wrote Romeo and Juliet?"
            ],
            expected_outputs=[
                "4",
                "Paris",
                "William Shakespeare"
            ],
            evaluation_criteria={"exact_match": True}
        )
        
        # Test de latencia
        self.tests["latency"] = BenchmarkTest(
            test_id="latency",
            name="Latency Test",
            description="Evalúa tiempo de respuesta",
            test_prompts=[
                "Hello",
                "How are you?",
                "What is AI?"
            ]
        )
        
        # Test de costo
        self.tests["cost"] = BenchmarkTest(
            test_id="cost",
            name="Cost Test",
            description="Evalúa costo por request",
            test_prompts=[
                "Generate a short summary",
                "Answer a question",
                "Complete a task"
            ]
        )
    
    def add_test(self, test: BenchmarkTest):
        """Agrega un test personalizado"""
        self.tests[test.test_id] = test
    
    def get_test(self, test_id: str) -> Optional[BenchmarkTest]:
        """Obtiene un test"""
        return self.tests.get(test_id)
    
    def list_tests(self) -> List[str]:
        """Lista todos los tests disponibles"""
        return list(self.tests.keys())


class AgentEvaluator:
    """
    Evaluador de agentes
    Ejecuta benchmarks y genera métricas
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.benchmark_suite = BenchmarkSuite()
        self.evaluation_history: Dict[str, List[EvaluationMetrics]] = {}
    
    def evaluate_agent(
        self,
        agent_id: str,
        agent_executor: Any,
        test_ids: Optional[List[str]] = None,
        custom_tests: Optional[List[BenchmarkTest]] = None
    ) -> Dict[str, EvaluationMetrics]:
        """
        Evalúa un agente con múltiples tests
        
        Args:
            agent_id: ID del agente
            agent_executor: Función que ejecuta el agente (agent_executor(input) -> output)
            test_ids: IDs de tests del benchmark suite
            custom_tests: Tests personalizados
            
        Returns:
            Dict con métricas por test
        """
        results = {}
        
        # Ejecutar tests estándar
        if test_ids:
            for test_id in test_ids:
                test = self.benchmark_suite.get_test(test_id)
                if test:
                    metrics = self._run_test(agent_executor, test)
                    results[test_id] = metrics
        
        # Ejecutar tests personalizados
        if custom_tests:
            for test in custom_tests:
                metrics = self._run_test(agent_executor, test)
                results[test.test_id] = metrics
        
        # Guardar en historial
        if agent_id not in self.evaluation_history:
            self.evaluation_history[agent_id] = []
        
        for metrics in results.values():
            self.evaluation_history[agent_id].append(metrics)
        
        return results
    
    def _run_test(
        self,
        agent_executor: Any,
        test: BenchmarkTest
    ) -> EvaluationMetrics:
        """Ejecuta un test individual"""
        latencies = []
        errors = 0
        total_tokens = 0
        correct = 0
        
        for i, prompt in enumerate(test.test_prompts):
            start = time.time()
            try:
                response = agent_executor(prompt)
                latency = (time.time() - start) * 1000
                latencies.append(latency)
                
                # Calcular tokens (estimación simple)
                total_tokens += len(prompt.split()) + len(str(response).split())
                
                # Verificar accuracy si hay expected outputs
                if test.expected_outputs and i < len(test.expected_outputs):
                    expected = test.expected_outputs[i]
                    if test.evaluation_criteria.get("exact_match"):
                        if str(response).strip().lower() == expected.strip().lower():
                            correct += 1
                    else:
                        # Fuzzy match
                        if expected.lower() in str(response).lower():
                            correct += 1
                
            except Exception as e:
                errors += 1
                latencies.append(0)  # Error no tiene latencia
        
        # Calcular métricas
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        error_rate = errors / len(test.test_prompts) if test.test_prompts else 0
        accuracy = correct / len(test.expected_outputs) if test.expected_outputs else 1.0
        
        # Estimar costo (simplificado)
        cost_per_1k = (total_tokens / 1000) * 0.002  # Ejemplo: $0.002 por 1k tokens
        
        return EvaluationMetrics(
            accuracy=accuracy,
            latency_ms=avg_latency,
            cost_per_1k_requests=cost_per_1k,
            token_usage=total_tokens,
            error_rate=error_rate
        )
    
    def compare_agents(
        self,
        agent_results: Dict[str, Dict[str, EvaluationMetrics]]
    ) -> Dict[str, Any]:
        """
        Compara resultados de múltiples agentes
        
        Args:
            agent_results: {agent_id: {test_id: EvaluationMetrics}}
            
        Returns:
            Dict con comparación
        """
        comparison = {
            "agents": list(agent_results.keys()),
            "tests": {},
            "summary": {}
        }
        
        # Agrupar por test
        all_test_ids = set()
        for agent_id, results in agent_results.items():
            all_test_ids.update(results.keys())
        
        for test_id in all_test_ids:
            test_comparison = {}
            for agent_id, results in agent_results.items():
                if test_id in results:
                    metrics = results[test_id]
                    test_comparison[agent_id] = {
                        "accuracy": metrics.accuracy,
                        "latency_ms": metrics.latency_ms,
                        "cost_per_1k": metrics.cost_per_1k_requests,
                        "error_rate": metrics.error_rate
                    }
            
            comparison["tests"][test_id] = test_comparison
        
        # Calcular resumen
        for agent_id in agent_results.keys():
            all_metrics = list(agent_results[agent_id].values())
            comparison["summary"][agent_id] = {
                "avg_accuracy": sum(m.accuracy for m in all_metrics) / len(all_metrics) if all_metrics else 0,
                "avg_latency_ms": sum(m.latency_ms for m in all_metrics) / len(all_metrics) if all_metrics else 0,
                "total_cost_per_1k": sum(m.cost_per_1k_requests for m in all_metrics),
                "avg_error_rate": sum(m.error_rate for m in all_metrics) / len(all_metrics) if all_metrics else 0
            }
        
        return comparison
    
    def get_evaluation_history(self, agent_id: str) -> List[EvaluationMetrics]:
        """Obtiene historial de evaluaciones de un agente"""
        return self.evaluation_history.get(agent_id, [])
