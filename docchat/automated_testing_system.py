"""
Automated Testing System - Sistema de testing y verificación automática.

Implementa el concepto de Eric Schmidt sobre tests de eficacia:
- Tests automáticos para verificar que algo funcionó
- Verificación de resultados
- Tests adversariales
"""

from __future__ import annotations

import json
import time
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from .config import AppConfig
from .utils.llm_factory import create_llm


@dataclass
class TestCase:
    """Caso de prueba."""
    test_id: str
    name: str
    description: str
    test_type: str  # unit, integration, functional, adversarial
    test_code: Optional[str] = None
    expected_result: Any = None
    actual_result: Optional[Any] = None
    passed: bool = False
    error_message: Optional[str] = None
    execution_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TestSuite:
    """Suite de pruebas."""
    suite_id: str
    name: str
    description: str
    target: str  # Qué se está probando (código, aplicación, modelo, etc.)
    test_cases: List[TestCase]
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    execution_time: float = 0.0
    status: str = "pending"  # pending, running, completed, failed
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AutomatedTestingSystem:
    """
    Sistema de testing automático y verificación de resultados.
    
    Características:
    - Genera tests automáticamente
    - Ejecuta tests y verifica resultados
    - Tests de eficacia (efficacy tests)
    - Tests adversariales
    - Verificación de código, aplicaciones, modelos, etc.
    """
    
    def __init__(self, config: AppConfig, provider: str = "openai"):
        self.config = config
        self.provider = provider
        
        # LLM para generar tests
        self.test_generator_llm = create_llm(
            provider=provider,
            model=config.agentic_model or "gpt-4o",
            temperature=0.2,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=8000,
            request_timeout=180
        )
        
        # LLM para verificar resultados
        self.verifier_llm = create_llm(
            provider=provider,
            model=config.agentic_model or "gpt-4o",
            temperature=0.1,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=4000,
            request_timeout=120
        )
        
        # Directorio para tests
        self.tests_dir = Path(config.memory_dir) / "automated_tests"
        self.tests_dir.mkdir(parents=True, exist_ok=True)
        
        # Suites de pruebas
        self.test_suites: Dict[str, TestSuite] = {}
    
    def create_test_suite(
        self,
        target: str,
        target_type: str = "code",  # code, application, model, api, etc.
        test_types: Optional[List[str]] = None,
        custom_requirements: Optional[str] = None
    ) -> TestSuite:
        """
        Crea una suite de pruebas para un objetivo.
        
        Args:
            target: Código, aplicación, o sistema a probar
            target_type: Tipo de objetivo (code, application, model, api)
            test_types: Tipos de tests a generar (unit, integration, functional, adversarial)
            custom_requirements: Requisitos específicos de testing
        
        Returns:
            TestSuite con tests generados
        """
        suite_id = f"suite_{int(time.time())}"
        test_types = test_types or ["unit", "functional"]
        
        print(f"\n{'='*60}")
        print(f"🧪 CREANDO SUITE DE PRUEBAS")
        print(f"{'='*60}")
        print(f"🎯 Objetivo: {target_type}")
        print(f"📋 Tipos de tests: {', '.join(test_types)}\n")
        
        # Generar tests
        print("📝 Generando casos de prueba...")
        test_cases = []
        for test_type in test_types:
            print(f"   🔍 Generando tests {test_type}...")
            cases = self._generate_tests(target, target_type, test_type, custom_requirements)
            test_cases.extend(cases)
            print(f"      ✅ {len(cases)} tests generados")
        
        print()
        
        # Crear suite
        suite = TestSuite(
            suite_id=suite_id,
            name=f"Test Suite for {target_type}",
            description=f"Tests automáticos para {target}",
            target=target,
            test_cases=test_cases,
            total_tests=len(test_cases),
            status="pending"
        )
        
        self.test_suites[suite_id] = suite
        
        print(f"{'='*60}")
        print(f"✅ SUITE DE PRUEBAS CREADA")
        print(f"📊 Total de tests: {suite.total_tests}")
        print(f"{'='*60}\n")
        
        return suite
    
    def run_test_suite(self, suite_id: str) -> TestSuite:
        """Ejecuta una suite de pruebas completa."""
        if suite_id not in self.test_suites:
            raise ValueError(f"Suite {suite_id} no encontrada")
        
        suite = self.test_suites[suite_id]
        suite.status = "running"
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"🚀 EJECUTANDO SUITE DE PRUEBAS")
        print(f"{'='*60}")
        print(f"📋 Suite: {suite.name}")
        print(f"🧪 Tests: {suite.total_tests}\n")
        
        # Ejecutar cada test
        for i, test_case in enumerate(suite.test_cases, 1):
            print(f"[{i}/{suite.total_tests}] Ejecutando: {test_case.name}...", end=' ')
            
            test_start = time.time()
            result = self._execute_test(test_case, suite.target)
            test_case.execution_time = time.time() - test_start
            
            if result["passed"]:
                test_case.passed = True
                test_case.actual_result = result.get("result")
                suite.passed_tests += 1
                print("✅ PASÓ")
            else:
                test_case.passed = False
                test_case.error_message = result.get("error", "Test falló")
                suite.failed_tests += 1
                print(f"❌ FALLÓ: {test_case.error_message[:50]}")
        
        suite.execution_time = time.time() - start_time
        suite.status = "completed"
        
        # Guardar resultados
        self._save_test_suite(suite)
        
        print(f"\n{'='*60}")
        print(f"✅ EJECUCIÓN COMPLETADA")
        print(f"✅ Pasaron: {suite.passed_tests}/{suite.total_tests}")
        print(f"❌ Fallaron: {suite.failed_tests}/{suite.total_tests}")
        print(f"⏱️  Tiempo: {suite.execution_time:.2f}s")
        print(f"{'='*60}\n")
        
        return suite
    
    def _generate_tests(
        self,
        target: str,
        target_type: str,
        test_type: str,
        custom_requirements: Optional[str]
    ) -> List[TestCase]:
        """Genera casos de prueba."""
        prompt = f"""Eres un experto en testing generando casos de prueba automáticos.

OBJETIVO A PROBAR:
{target[:5000]}

TIPO DE OBJETIVO: {target_type}
TIPO DE TEST: {test_type}

REQUISITOS ESPECÍFICOS:
{custom_requirements or "Ninguno - generar tests comprehensivos"}

INSTRUCCIONES:
1. Genera 5-10 casos de prueba {test_type} relevantes
2. Cada test debe:
   - Ser específico y verificable
   - Tener un resultado esperado claro
   - Ser ejecutable automáticamente
   - Cubrir diferentes aspectos del objetivo
3. Para tests adversariales, enfócate en encontrar vulnerabilidades

FORMATO DE RESPUESTA (JSON):
{{
    "tests": [
        {{
            "name": "Nombre del test",
            "description": "Qué prueba este test",
            "test_code": "Código del test (si aplica)",
            "expected_result": "Resultado esperado",
            "test_method": "Método de verificación"
        }},
        ...
    ]
}}

Genera los tests ahora:"""
        
        try:
            response = self.test_generator_llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                test_cases = []
                
                for i, test_data in enumerate(data.get("tests", []), 1):
                    test_case = TestCase(
                        test_id=f"test_{int(time.time())}_{i}",
                        name=test_data.get("name", f"Test {i}"),
                        description=test_data.get("description", ""),
                        test_type=test_type,
                        test_code=test_data.get("test_code"),
                        expected_result=test_data.get("expected_result"),
                    )
                    test_cases.append(test_case)
                
                return test_cases
            else:
                # Test básico de fallback
                return [
                    TestCase(
                        test_id=f"test_{int(time.time())}_1",
                        name=f"Basic {test_type} test",
                        description=f"Test básico {test_type} para {target_type}",
                        test_type=test_type,
                        expected_result="Test passed"
                    )
                ]
        except Exception as e:
            print(f"      ⚠️ Error generando tests: {e}")
            return []
    
    def _execute_test(self, test_case: TestCase, target: str) -> Dict[str, Any]:
        """Ejecuta un caso de prueba."""
        # Si hay código de test, intentar ejecutarlo
        if test_case.test_code:
            try:
                # Ejecutar en sandbox seguro
                from .text_to_action import TextToAction
                # Usar TextToAction para ejecución segura
                text_to_action = TextToAction(self.config, sandbox_enabled=True)
                # Crear un ActionPlan temporal para ejecutar el código
                from .text_to_action import ActionPlan, ActionType
                action_plan = ActionPlan(
                    action_id="test_execution",
                    action_type=ActionType.CODE_EXECUTION,
                    description="Test code execution",
                    code=test_case.test_code,
                    parameters={"target": target}
                )
                import asyncio
                result_obj = asyncio.run(text_to_action.execute_action(action_plan, confirm=True))
                result = {
                    "success": result_obj.success,
                    "output": result_obj.output,
                    "error": result_obj.error
                }
                
                if result["success"]:
                    # Verificar resultado
                    verified = self._verify_result(
                        test_case.expected_result,
                        result.get("result"),
                        test_case.description
                    )
                    return {
                        "passed": verified,
                        "result": result.get("result"),
                        "output": result.get("output")
                    }
                else:
                    return {
                        "passed": False,
                        "error": result.get("error", "Error ejecutando test")
                    }
            except Exception as e:
                return {
                    "passed": False,
                    "error": f"Error ejecutando test: {str(e)}"
                }
        else:
            # Test sin código - verificación conceptual usando LLM
            verified = self._verify_result_conceptual(
                target,
                test_case.expected_result,
                test_case.description,
                test_case.test_type
            )
            return {
                "passed": verified,
                "result": "Verificación conceptual completada"
            }
    
    def _verify_result(
        self,
        expected: Any,
        actual: Any,
        description: str
    ) -> bool:
        """Verifica que el resultado actual coincida con el esperado."""
        # Comparación directa
        if expected == actual:
            return True
        
        # Verificación usando LLM para casos más complejos
        prompt = f"""Verifica si el resultado actual coincide con el esperado.

DESCRIPCIÓN DEL TEST:
{description}

RESULTADO ESPERADO:
{expected}

RESULTADO ACTUAL:
{actual}

¿El resultado actual cumple con lo esperado?

RESPUESTA (JSON):
{{
    "matches": true o false,
    "reasoning": "Por qué coincide o no"
}}
"""
        
        try:
            response = self.verifier_llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                return data.get("matches", False)
            return False
        except Exception:
            return str(expected) == str(actual)
    
    def _verify_result_conceptual(
        self,
        target: str,
        expected: str,
        description: str,
        test_type: str
    ) -> bool:
        """Verificación conceptual usando LLM."""
        prompt = f"""Verifica conceptualmente si el objetivo cumple con este test.

OBJETIVO:
{target[:3000]}

TEST:
Tipo: {test_type}
Descripción: {description}
Resultado esperado: {expected}

¿El objetivo cumple con este test?

RESPUESTA (JSON):
{{
    "passes": true o false,
    "confidence": 0.0-1.0,
    "reasoning": "Por qué pasa o falla"
}}
"""
        
        try:
            response = self.verifier_llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                return data.get("passes", False)
            return False
        except Exception:
            return False
    
    def create_adversarial_tests(
        self,
        target: str,
        target_type: str = "model"
    ) -> TestSuite:
        """Crea tests adversariales para encontrar vulnerabilidades."""
        print(f"\n🔴 Creando tests adversariales para {target_type}...")
        
        prompt = f"""Eres un experto en seguridad y testing adversarial.

OBJETIVO A ATACAR:
{target[:5000]}

TIPO: {target_type}

INSTRUCCIONES:
1. Genera tests adversariales diseñados para encontrar vulnerabilidades
2. Enfócate en:
   - Casos edge
   - Inputs maliciosos
   - Exploits potenciales
   - Comportamiento inesperado
   - Límites del sistema
3. Los tests deben intentar "romper" el sistema de forma controlada

FORMATO DE RESPUESTA (JSON):
{{
    "adversarial_tests": [
        {{
            "name": "Nombre del test adversarial",
            "description": "Qué vulnerabilidad busca",
            "attack_vector": "Cómo ataca",
            "expected_vulnerability": "Qué vulnerabilidad esperamos encontrar",
            "test_code": "Código del test (si aplica)"
        }},
        ...
    ]
}}
"""
        
        try:
            response = self.test_generator_llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                test_cases = []
                
                for i, test_data in enumerate(data.get("adversarial_tests", []), 1):
                    test_case = TestCase(
                        test_id=f"adv_test_{int(time.time())}_{i}",
                        name=test_data.get("name", f"Adversarial Test {i}"),
                        description=test_data.get("description", ""),
                        test_type="adversarial",
                        test_code=test_data.get("test_code"),
                        expected_result=f"Vulnerability: {test_data.get('expected_vulnerability', 'Unknown')}"
                    )
                    test_cases.append(test_case)
                
                suite = TestSuite(
                    suite_id=f"adv_suite_{int(time.time())}",
                    name="Adversarial Test Suite",
                    description=f"Tests adversariales para {target_type}",
                    target=target,
                    test_cases=test_cases,
                    total_tests=len(test_cases)
                )
                
                self.test_suites[suite.suite_id] = suite
                return suite
        except Exception as e:
            print(f"   ⚠️ Error creando tests adversariales: {e}")
        
        return TestSuite(
            suite_id=f"adv_suite_{int(time.time())}",
            name="Adversarial Test Suite",
            description="Tests adversariales",
            target=target,
            test_cases=[],
            total_tests=0
        )
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extrae JSON de un texto."""
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        return None
    
    def _save_test_suite(self, suite: TestSuite):
        """Guarda una suite de pruebas."""
        suite_file = self.tests_dir / f"{suite.suite_id}.json"
        suite_dict = {
            "suite_id": suite.suite_id,
            "name": suite.name,
            "description": suite.description,
            "target": suite.target,
            "test_cases": [
                {
                    "test_id": t.test_id,
                    "name": t.name,
                    "description": t.description,
                    "test_type": t.test_type,
                    "test_code": t.test_code,
                    "expected_result": str(t.expected_result) if t.expected_result else None,
                    "actual_result": str(t.actual_result) if t.actual_result else None,
                    "passed": t.passed,
                    "error_message": t.error_message,
                    "execution_time": t.execution_time,
                    "timestamp": t.timestamp
                }
                for t in suite.test_cases
            ],
            "total_tests": suite.total_tests,
            "passed_tests": suite.passed_tests,
            "failed_tests": suite.failed_tests,
            "execution_time": suite.execution_time,
            "status": suite.status,
            "timestamp": suite.timestamp
        }
        
        with open(suite_file, 'w', encoding='utf-8') as f:
            json.dump(suite_dict, f, indent=2, ensure_ascii=False)
    
    def get_test_suite(self, suite_id: str) -> Optional[TestSuite]:
        """Obtiene una suite por ID."""
        return self.test_suites.get(suite_id)
    
    def get_test_report(self, suite_id: str) -> Dict[str, Any]:
        """Genera un reporte detallado de una suite."""
        suite = self.get_test_suite(suite_id)
        if not suite:
            return {}
        
        return {
            "suite_id": suite.suite_id,
            "name": suite.name,
            "status": suite.status,
            "summary": {
                "total": suite.total_tests,
                "passed": suite.passed_tests,
                "failed": suite.failed_tests,
                "pass_rate": suite.passed_tests / suite.total_tests if suite.total_tests > 0 else 0
            },
            "execution_time": suite.execution_time,
            "test_details": [
                {
                    "name": t.name,
                    "type": t.test_type,
                    "passed": t.passed,
                    "execution_time": t.execution_time,
                    "error": t.error_message
                }
                for t in suite.test_cases
            ],
            "timestamp": suite.timestamp
        }

