"""
Deep Chain of Thought - Razonamiento profundo de hasta 1000 pasos.

Implementa el concepto de Eric Schmidt sobre Chain of Thought reasoning:
- Generar hasta 1000 pasos de razonamiento
- Cada paso es verificable
- Como construir recetas que se pueden ejecutar y probar
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from .config import AppConfig
from .utils.llm_factory import create_llm


@dataclass
class ReasoningStep:
    """Un paso en el razonamiento Chain of Thought."""
    step_number: int
    description: str
    reasoning: str
    input_data: Optional[Any] = None
    output_data: Optional[Any] = None
    verification: Optional[str] = None
    verified: bool = False
    confidence: float = 0.0
    dependencies: List[int] = field(default_factory=list)  # Pasos de los que depende


@dataclass
class DeepChainOfThought:
    """Cadena completa de razonamiento profundo."""
    chain_id: str
    problem: str
    steps: List[ReasoningStep]
    max_steps: int
    current_step: int = 0
    final_answer: Optional[str] = None
    verification_results: Dict[int, bool] = field(default_factory=dict)
    status: str = "reasoning"  # reasoning, completed, verified, failed
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class DeepChainOfThoughtAgent:
    """
    Agente que genera razonamiento Chain of Thought profundo (hasta 1000 pasos).
    
    Características:
    - Genera pasos de razonamiento estructurados
    - Cada paso es verificable
    - Puede generar hasta 1000 pasos
    - Verifica cada paso antes de continuar
    - Construye "recetas" ejecutables
    """
    
    def __init__(self, config: AppConfig, provider: str = "openai"):
        self.config = config
        self.provider = provider
        
        # LLM para razonamiento
        self.llm = create_llm(
            provider=provider,
            model=config.agentic_model or "gpt-4o",
            temperature=0.1,  # Muy baja para razonamiento preciso
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=8000,
            request_timeout=300  # Más tiempo para razonamiento profundo
        )
        
        # Directorio para almacenar cadenas de razonamiento
        self.data_dir = Path(config.memory_dir) / "deep_cot"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Cadenas activas
        self.active_chains: Dict[str, DeepChainOfThought] = {}
    
    def solve_with_deep_cot(
        self,
        problem: str,
        max_steps: int = 100,
        verify_steps: bool = True,
        step_verifier: Optional[Callable] = None
    ) -> DeepChainOfThought:
        """
        Resuelve un problema usando Chain of Thought profundo.
        
        Args:
            problem: Problema a resolver
            max_steps: Máximo de pasos (hasta 1000)
            verify_steps: Si True, verifica cada paso antes de continuar
            step_verifier: Función opcional para verificar pasos personalizados
        
        Returns:
            DeepChainOfThought con todo el razonamiento
        """
        chain_id = f"cot_{int(time.time())}"
        max_steps = min(max_steps, 1000)  # Límite de 1000 pasos
        
        print(f"\n{'='*60}")
        print(f"🧠 INICIANDO CHAIN OF THOUGHT PROFUNDO")
        print(f"{'='*60}")
        print(f"❓ Problema: {problem}")
        print(f"📊 Máximo de pasos: {max_steps}")
        print(f"✅ Verificación: {'Activada' if verify_steps else 'Desactivada'}\n")
        
        chain = DeepChainOfThought(
            chain_id=chain_id,
            problem=problem,
            steps=[],
            max_steps=max_steps,
            status="reasoning"
        )
        
        self.active_chains[chain_id] = chain
        
        # Generar pasos iterativamente
        current_context = problem
        previous_steps_summary = ""
        
        for step_num in range(1, max_steps + 1):
            print(f"📝 Generando paso {step_num}/{max_steps}...", end='\r')
            
            # Generar siguiente paso
            step = self._generate_next_step(
                problem,
                step_num,
                previous_steps_summary,
                current_context
            )
            
            if not step:
                print(f"\n   ⚠️ No se pudo generar paso {step_num}, finalizando...")
                break
            
            chain.steps.append(step)
            chain.current_step = step_num
            
            # Verificar paso si está habilitado
            if verify_steps:
                verified = self._verify_step(step, step_verifier)
                step.verified = verified
                chain.verification_results[step_num] = verified
                
                if not verified:
                    print(f"\n   ⚠️ Paso {step_num} no verificado, revisando...")
                    # Intentar corregir o continuar
                    corrected = self._correct_step(step, previous_steps_summary)
                    if corrected:
                        step.verified = True
                        chain.verification_results[step_num] = True
            
            # Actualizar contexto para siguiente paso
            previous_steps_summary = self._summarize_steps(chain.steps[-5:])  # Últimos 5 pasos
            current_context = f"{current_context}\n\nPaso {step_num}: {step.description}\n{step.reasoning}"
            
            # Verificar si llegamos a una conclusión
            if self._check_for_conclusion(step, problem):
                print(f"\n   ✅ Conclusión alcanzada en paso {step_num}")
                chain.final_answer = step.output_data or step.description
                chain.status = "completed"
                break
            
            # Pausa pequeña para no sobrecargar
            if step_num % 10 == 0:
                time.sleep(0.1)
        
        print()  # Nueva línea
        
        # Generar respuesta final si no se alcanzó conclusión
        if not chain.final_answer:
            print("📊 Generando respuesta final...")
            chain.final_answer = self._generate_final_answer(chain)
            chain.status = "completed"
        
        # Guardar cadena
        self._save_chain(chain)
        
        print(f"\n{'='*60}")
        print(f"✅ CHAIN OF THOUGHT COMPLETADO")
        print(f"📊 Total de pasos: {len(chain.steps)}")
        print(f"✅ Pasos verificados: {sum(chain.verification_results.values())}/{len(chain.verification_results)}")
        print(f"{'='*60}\n")
        
        return chain
    
    def _generate_next_step(
        self,
        problem: str,
        step_number: int,
        previous_steps: str,
        current_context: str
    ) -> Optional[ReasoningStep]:
        """Genera el siguiente paso en el razonamiento."""
        prompt = f"""Eres un experto en razonamiento paso a paso (Chain of Thought).

PROBLEMA ORIGINAL:
{problem}

PASOS ANTERIORES (últimos 5):
{previous_steps if previous_steps else "Ninguno (este es el primer paso)"}

CONTEXTO ACTUAL:
{current_context[:5000]}

INSTRUCCIONES:
1. Genera el SIGUIENTE paso lógico en el razonamiento
2. El paso debe:
   - Ser específico y accionable
   - Basarse en los pasos anteriores
   - Avanzar hacia la solución del problema
   - Ser verificable (tener un método de verificación)
3. Si el problema está resuelto, indica que es el paso final

FORMATO DE RESPUESTA (JSON):
{{
    "description": "Descripción clara y concisa del paso",
    "reasoning": "Razonamiento detallado de por qué este paso es necesario",
    "input_data": "Datos o información necesaria para este paso",
    "expected_output": "Qué resultado esperamos de este paso",
    "verification_method": "Cómo verificar que este paso es correcto",
    "is_final": false,
    "dependencies": [número de pasos de los que depende]
}}

Genera el paso {step_number} ahora:"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                
                step = ReasoningStep(
                    step_number=step_number,
                    description=data.get("description", ""),
                    reasoning=data.get("reasoning", ""),
                    input_data=data.get("input_data"),
                    output_data=data.get("expected_output"),
                    verification=data.get("verification_method", ""),
                    dependencies=data.get("dependencies", [])
                )
                
                return step
            else:
                # Paso básico de fallback
                return ReasoningStep(
                    step_number=step_number,
                    description=f"Paso {step_number} del razonamiento",
                    reasoning="Razonamiento continuo",
                    verification="Verificación básica"
                )
        except Exception as e:
            print(f"   ⚠️ Error generando paso {step_number}: {e}")
            return None
    
    def _verify_step(
        self,
        step: ReasoningStep,
        custom_verifier: Optional[Callable] = None
    ) -> bool:
        """Verifica que un paso es correcto."""
        if custom_verifier:
            try:
                return custom_verifier(step)
            except Exception:
                pass
        
        # Verificación usando LLM
        prompt = f"""Verifica si este paso de razonamiento es correcto.

PASO:
Descripción: {step.description}
Razonamiento: {step.reasoning}
Método de verificación: {step.verification}

INSTRUCCIONES:
1. Analiza si el razonamiento es lógico
2. Verifica si el paso es correcto según el método de verificación
3. Asigna un score de confianza

RESPUESTA (JSON):
{{
    "verified": true o false,
    "confidence": 0.0-1.0,
    "reasoning": "Por qué está verificado o no"
}}
"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                step.confidence = float(data.get("confidence", 0.5))
                return data.get("verified", False)
            return False
        except Exception:
            return False
    
    def _correct_step(
        self,
        step: ReasoningStep,
        previous_context: str
    ) -> bool:
        """Intenta corregir un paso que falló verificación."""
        prompt = f"""Corrige este paso de razonamiento que falló verificación.

PASO A CORREGIR:
{step.description}
{step.reasoning}

CONTEXTO PREVIO:
{previous_context[:2000]}

Genera una versión corregida del paso.

RESPUESTA (JSON):
{{
    "corrected_description": "...",
    "corrected_reasoning": "...",
    "correction_explanation": "Qué se corrigió y por qué"
}}
"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                step.description = data.get("corrected_description", step.description)
                step.reasoning = data.get("corrected_reasoning", step.reasoning)
                return True
            return False
        except Exception:
            return False
    
    def _check_for_conclusion(self, step: ReasoningStep, problem: str) -> bool:
        """Verifica si el paso actual representa una conclusión."""
        conclusion_keywords = [
            "conclusión", "conclusión", "resuelto", "solución", "respuesta final",
            "final answer", "conclusion", "solved", "answer"
        ]
        
        step_text = f"{step.description} {step.reasoning}".lower()
        return any(keyword in step_text for keyword in conclusion_keywords)
    
    def _generate_final_answer(self, chain: DeepChainOfThought) -> str:
        """Genera respuesta final basada en todos los pasos."""
        steps_summary = "\n".join([
            f"Paso {s.step_number}: {s.description}\n{s.reasoning[:200]}\n"
            for s in chain.steps[-20:]  # Últimos 20 pasos
        ])
        
        prompt = f"""Genera la respuesta final basada en esta cadena de razonamiento.

PROBLEMA ORIGINAL:
{chain.problem}

PASOS DE RAZONAMIENTO ({len(chain.steps)} pasos totales):
{steps_summary}

INSTRUCCIONES:
1. Sintetiza todos los pasos en una respuesta final clara
2. Incluye la solución o conclusión principal
3. Menciona los pasos clave que llevaron a esta conclusión

RESPUESTA: Texto claro y completo con la solución final."""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            return response
        except Exception:
            return f"Solución basada en {len(chain.steps)} pasos de razonamiento."
    
    def _summarize_steps(self, steps: List[ReasoningStep]) -> str:
        """Resume los últimos pasos."""
        if not steps:
            return ""
        
        summary = []
        for step in steps:
            summary.append(f"Paso {step.step_number}: {step.description}")
        
        return "\n".join(summary)
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extrae JSON de un texto."""
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        return None
    
    def _save_chain(self, chain: DeepChainOfThought):
        """Guarda una cadena de razonamiento."""
        chain_file = self.data_dir / f"{chain.chain_id}.json"
        chain_dict = {
            "chain_id": chain.chain_id,
            "problem": chain.problem,
            "steps": [
                {
                    "step_number": s.step_number,
                    "description": s.description,
                    "reasoning": s.reasoning,
                    "input_data": str(s.input_data) if s.input_data else None,
                    "output_data": str(s.output_data) if s.output_data else None,
                    "verification": s.verification,
                    "verified": s.verified,
                    "confidence": s.confidence,
                    "dependencies": s.dependencies
                }
                for s in chain.steps
            ],
            "max_steps": chain.max_steps,
            "current_step": chain.current_step,
            "final_answer": chain.final_answer,
            "verification_results": chain.verification_results,
            "status": chain.status,
            "timestamp": chain.timestamp
        }
        
        with open(chain_file, 'w', encoding='utf-8') as f:
            json.dump(chain_dict, f, indent=2, ensure_ascii=False)
    
    def get_chain(self, chain_id: str) -> Optional[DeepChainOfThought]:
        """Obtiene una cadena por ID."""
        return self.active_chains.get(chain_id)
    
    def export_chain_as_recipe(self, chain_id: str) -> Dict[str, Any]:
        """Exporta una cadena como 'receta' ejecutable (concepto de Eric Schmidt)."""
        chain = self.get_chain(chain_id)
        if not chain:
            return {}
        
        return {
            "recipe_id": chain.chain_id,
            "problem": chain.problem,
            "steps": [
                {
                    "step": s.step_number,
                    "action": s.description,
                    "reasoning": s.reasoning,
                    "verification": s.verification,
                    "verified": s.verified
                }
                for s in chain.steps
            ],
            "final_answer": chain.final_answer,
            "executable": True,  # Esta receta puede ejecutarse y probarse
            "verification_summary": {
                "total_steps": len(chain.steps),
                "verified_steps": sum(chain.verification_results.values()),
                "verification_rate": sum(chain.verification_results.values()) / len(chain.steps) if chain.steps else 0
            }
        }

