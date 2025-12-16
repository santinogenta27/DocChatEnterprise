"""
Model Orchestrator - Orquestador de modelos
Selección automática de modelos según caso de uso
Basado en: Multi-model approach y model evaluation
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    MODEL_AVAILABLE = True
except ImportError:
    MODEL_AVAILABLE = False


class ModelProvider(str, Enum):
    """Proveedores de modelos"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    META = "meta"
    GOOGLE = "google"
    IBM = "ibm"


@dataclass
class ModelConfig:
    """Configuración de modelo"""
    provider: ModelProvider
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    cost_per_1k_tokens: float = 0.0
    latency_ms: float = 0.0
    capabilities: List[str] = None  # ["text", "image", "audio", "code"]


class ModelSelector:
    """
    Selector de modelos basado en caso de uso
    Evalúa modelos y selecciona el mejor para cada tarea
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.models: Dict[str, ModelConfig] = {}
        self.benchmarks: Dict[str, Dict[str, float]] = {}
        self._initialize_default_models()
    
    def _initialize_default_models(self):
        """Inicializa modelos por defecto"""
        openai_key = getattr(self.config, 'openai_api_key', None)
        anthropic_key = getattr(self.config, 'anthropic_api_key', None)
        
        # OpenAI models
        if openai_key:
            self.models["gpt-4o"] = ModelConfig(
                provider=ModelProvider.OPENAI,
                model_name="gpt-4o",
                api_key=openai_key,
                temperature=0.7,
                cost_per_1k_tokens=5.0,  # Ejemplo
                capabilities=["text", "image", "code"]
            )
            self.models["gpt-4-turbo"] = ModelConfig(
                provider=ModelProvider.OPENAI,
                model_name="gpt-4-turbo",
                api_key=openai_key,
                temperature=0.7,
                cost_per_1k_tokens=10.0,
                capabilities=["text", "image", "code"]
            )
            self.models["gpt-3.5-turbo"] = ModelConfig(
                provider=ModelProvider.OPENAI,
                model_name="gpt-3.5-turbo",
                api_key=openai_key,
                temperature=0.7,
                cost_per_1k_tokens=1.5,
                capabilities=["text", "code"]
            )
        
        # Anthropic models
        if anthropic_key:
            self.models["claude-3-5-sonnet"] = ModelConfig(
                provider=ModelProvider.ANTHROPIC,
                model_name="claude-3-5-sonnet",
                api_key=anthropic_key,
                temperature=0.7,
                cost_per_1k_tokens=3.0,
                capabilities=["text", "code"]
            )
            self.models["claude-3-opus"] = ModelConfig(
                provider=ModelProvider.ANTHROPIC,
                model_name="claude-3-opus",
                api_key=anthropic_key,
                temperature=0.7,
                cost_per_1k_tokens=15.0,
                capabilities=["text", "code"]
            )
    
    def select_model(
        self,
        use_case: str,
        requirements: Dict[str, Any],
        budget_constraint: Optional[float] = None
    ) -> str:
        """
        Selecciona el mejor modelo para un caso de uso
        
        Args:
            use_case: Descripción del caso de uso
            requirements: {
                "capabilities": ["text", "image"],
                "max_cost_per_1k": 5.0,
                "max_latency_ms": 1000,
                "accuracy_priority": True
            }
            budget_constraint: Presupuesto máximo por 1k tokens
            
        Returns:
            model_name: Nombre del modelo seleccionado
        """
        candidates = []
        
        # Filtrar modelos por capacidades
        required_caps = requirements.get("capabilities", ["text"])
        for model_name, model_config in self.models.items():
            if all(cap in (model_config.capabilities or []) for cap in required_caps):
                candidates.append((model_name, model_config))
        
        if not candidates:
            raise ValueError("No hay modelos disponibles que cumplan los requisitos")
        
        # Filtrar por presupuesto
        if budget_constraint:
            candidates = [
                (name, config) for name, config in candidates
                if config.cost_per_1k_tokens <= budget_constraint
            ]
        
        # Filtrar por latencia
        max_latency = requirements.get("max_latency_ms")
        if max_latency:
            candidates = [
                (name, config) for name, config in candidates
                if config.latency_ms <= max_latency
            ]
        
        if not candidates:
            raise ValueError("No hay modelos que cumplan todas las restricciones")
        
        # Seleccionar mejor modelo
        if requirements.get("accuracy_priority", False):
            # Priorizar modelos más grandes (generalmente más precisos)
            candidates.sort(key=lambda x: x[1].cost_per_1k_tokens, reverse=True)
        else:
            # Priorizar costo
            candidates.sort(key=lambda x: x[1].cost_per_1k_tokens)
        
        return candidates[0][0]
    
    def evaluate_model(
        self,
        model_name: str,
        test_prompts: List[str],
        expected_outputs: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        Evalúa un modelo con prompts de prueba
        
        Returns:
            Dict con métricas: {"accuracy": 0.95, "latency_ms": 500, "cost": 0.05}
        """
        if model_name not in self.models:
            raise ValueError(f"Modelo {model_name} no encontrado")
        
        model_config = self.models[model_name]
        
        # Crear LLM
        llm = self._create_llm(model_config)
        
        # Ejecutar prompts y medir
        results = []
        total_latency = 0.0
        total_tokens = 0
        
        for prompt in test_prompts:
            import time
            start = time.time()
            try:
                response = llm.invoke(prompt)
                latency = (time.time() - start) * 1000
                total_latency += latency
                results.append(response.content if hasattr(response, 'content') else str(response))
            except Exception as e:
                print(f"Error evaluando modelo: {e}")
                results.append("")
        
        avg_latency = total_latency / len(test_prompts) if test_prompts else 0
        
        # Calcular accuracy si hay expected outputs
        accuracy = 1.0
        if expected_outputs:
            matches = sum(1 for r, e in zip(results, expected_outputs) if r == e)
            accuracy = matches / len(expected_outputs) if expected_outputs else 1.0
        
        # Calcular costo estimado
        estimated_cost = (total_tokens / 1000) * model_config.cost_per_1k_tokens
        
        return {
            "accuracy": accuracy,
            "latency_ms": avg_latency,
            "cost_per_1k_requests": estimated_cost,
            "model": model_name
        }
    
    def _create_llm(self, model_config: ModelConfig) -> Any:
        """Crea instancia de LLM"""
        if not MODEL_AVAILABLE:
            raise ImportError("LangChain requerido")
        
        if model_config.provider == ModelProvider.OPENAI:
            return ChatOpenAI(
                model=model_config.model_name,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
                api_key=model_config.api_key
            )
        elif model_config.provider == ModelProvider.ANTHROPIC:
            return ChatAnthropic(
                model=model_config.model_name,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
                api_key=model_config.api_key
            )
        else:
            raise ValueError(f"Proveedor no soportado: {model_config.provider}")


class ModelOrchestrator:
    """
    Orquestador de modelos
    Gestiona múltiples modelos y selección automática
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.selector = ModelSelector(config)
        self.active_models: Dict[str, Any] = {}
    
    def get_model(
        self,
        model_name: Optional[str] = None,
        use_case: Optional[str] = None,
        requirements: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Obtiene un modelo (crea o selecciona automáticamente)
        
        Args:
            model_name: Nombre específico del modelo (opcional)
            use_case: Caso de uso para selección automática
            requirements: Requisitos para selección automática
        """
        # Si se especifica modelo, usarlo
        if model_name:
            if model_name not in self.selector.models:
                raise ValueError(f"Modelo {model_name} no encontrado")
            model_config = self.selector.models[model_name]
        else:
            # Selección automática
            if not use_case or not requirements:
                raise ValueError("Debe especificar model_name o (use_case + requirements)")
            model_name = self.selector.select_model(use_case, requirements)
            model_config = self.selector.models[model_name]
        
        # Crear o reutilizar instancia
        if model_name not in self.active_models:
            self.active_models[model_name] = self.selector._create_llm(model_config)
        
        return self.active_models[model_name]
    
    def benchmark_models(
        self,
        test_prompts: List[str],
        expected_outputs: Optional[List[str]] = None,
        model_names: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Evalúa múltiples modelos y retorna comparación
        """
        if model_names is None:
            model_names = list(self.selector.models.keys())
        
        results = {}
        for model_name in model_names:
            try:
                results[model_name] = self.selector.evaluate_model(
                    model_name,
                    test_prompts,
                    expected_outputs
                )
            except Exception as e:
                print(f"Error evaluando {model_name}: {e}")
                results[model_name] = {"error": str(e)}
        
        return results
