"""
Text-to-Action System - Convierte lenguaje natural en código Python ejecutable.
Sistema avanzado que permite a los usuarios crear y ejecutar código desde descripciones en lenguaje natural.
"""
from __future__ import annotations

import ast
import io
import sys
import traceback
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from docchat.config import AppConfig
from docchat.utils.llm_factory import create_llm


class CodeSandbox:
    """Sandbox seguro para ejecutar código Python."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.allowed_modules = {
            'os', 'sys', 'json', 'datetime', 'math', 'random', 're', 'collections',
            'itertools', 'functools', 'operator', 'string', 'pathlib', 'urllib',
            'requests', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'plotly',
            'sqlite3', 'csv', 'io', 'base64', 'hashlib', 'uuid', 'time', 'calendar'
        }
        self.blocked_keywords = [
            'eval', 'exec', '__import__', 'open', 'file', 'input', 'raw_input',
            'compile', 'reload', '__builtins__', 'globals', 'locals', 'vars',
            'dir', 'hasattr', 'getattr', 'setattr', 'delattr', 'callable'
        ]
    
    def _check_code_safety(self, code: str) -> Tuple[bool, Optional[str]]:
        """Verifica que el código sea seguro para ejecutar."""
        try:
            # Parsear el código para verificar sintaxis
            ast.parse(code)
            
            # Verificar keywords bloqueadas
            code_lower = code.lower()
            for keyword in self.blocked_keywords:
                if keyword in code_lower:
                    # Permitir comentarios y strings
                    lines = code.split('\n')
                    for line in lines:
                        stripped = line.strip()
                        if not stripped.startswith('#') and keyword in line.lower():
                            # Verificar que no esté en un string
                            if f'"{keyword}"' not in line and f"'{keyword}'" not in line:
                                return False, f"❌ Código bloqueado: uso de '{keyword}' no permitido por seguridad"
            
            return True, None
        except SyntaxError as e:
            return False, f"❌ Error de sintaxis: {str(e)}"
        except Exception as e:
            return False, f"❌ Error verificando código: {str(e)}"
    
    def execute(self, code: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Ejecuta código Python de forma segura en un sandbox.
        
        Args:
            code: Código Python a ejecutar
            context: Variables de contexto a inyectar en el entorno de ejecución
        
        Returns:
            Dict con 'success', 'output', 'error', 'result'
        """
        # Verificar seguridad
        is_safe, error_msg = self._check_code_safety(code)
        if not is_safe:
            return {
                'success': False,
                'output': '',
                'error': error_msg,
                'result': None
            }
        
        # Capturar stdout y stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = captured_output = io.StringIO()
        sys.stderr = captured_error = io.StringIO()
        
        try:
            # Crear namespace seguro con builtins limitados
            import builtins
            safe_builtins = {
                'print': print,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'min': min,
                'max': max,
                'sum': sum,
                'abs': abs,
                'round': round,
                'sorted': sorted,
                'reversed': reversed,
                'any': any,
                'all': all,
                'isinstance': isinstance,
                'type': type,
                'repr': repr,
                'format': format,
            }
            
            safe_globals = {
                '__builtins__': safe_builtins,
                'json': __import__('json'),
                'datetime': __import__('datetime'),
                'math': __import__('math'),
                'random': __import__('random'),
                're': __import__('re'),
                'collections': __import__('collections'),
                'itertools': __import__('itertools'),
                'functools': __import__('functools'),
                'operator': __import__('operator'),
                'string': __import__('string'),
                'Path': __import__('pathlib').Path,
            }
            
            # Inyectar contexto si está disponible
            if context:
                safe_globals.update(context)
            
            # Ejecutar código
            exec(code, safe_globals)
            
            # Capturar resultado si hay una variable 'result'
            result = safe_globals.get('result', None)
            
            output = captured_output.getvalue()
            error = captured_error.getvalue()
            
            return {
                'success': True,
                'output': output,
                'error': error if error else None,
                'result': result
            }
            
        except Exception as e:
            error_trace = traceback.format_exc()
            return {
                'success': False,
                'output': captured_output.getvalue(),
                'error': f"❌ Error ejecutando código:\n{str(e)}\n\nTraceback:\n{error_trace}",
                'result': None
            }
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


class TextToActionAgent:
    """
    Agente que convierte lenguaje natural en código Python ejecutable.
    Utiliza LLM para generar código y sandbox para ejecutarlo de forma segura.
    """
    
    def __init__(self, config: AppConfig, provider: str = "openai"):
        self.config = config
        self.provider = provider
        self.sandbox = CodeSandbox(timeout=30)
        
        # LLM para generar código
        self.code_llm = create_llm(
            provider=provider,
            model=config.agentic_model or "gpt-4o",
            temperature=0.1,  # Baja temperatura para código más preciso
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=8000,  # Código puede ser largo
            request_timeout=180,
            max_retries=3
        )
        
        # LLM para mejorar código basado en errores
        self.fix_llm = create_llm(
            provider=provider,
            model=config.agentic_model or "gpt-4o",
            temperature=0.1,
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=4000,
            request_timeout=120,
            max_retries=2
        )
    
    def generate_code(
        self,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        previous_code: Optional[str] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Genera código Python desde una descripción en lenguaje natural.
        
        Args:
            description: Descripción en lenguaje natural de lo que se quiere hacer
            context: Contexto adicional (datos, variables, etc.)
            previous_code: Código anterior si hay que mejorarlo
            error: Error del código anterior si hay que corregirlo
        
        Returns:
            Dict con 'code', 'explanation', 'success'
        """
        if error and previous_code:
            # Modo: corregir código con error
            prompt = self._build_fix_prompt(description, previous_code, error, context)
            llm_to_use = self.fix_llm
        else:
            # Modo: generar código nuevo
            prompt = self._build_generation_prompt(description, context)
            llm_to_use = self.code_llm
        
        try:
            response = llm_to_use.invoke(prompt).content.strip()
            
            # Extraer código del response
            code, explanation = self._extract_code_from_response(response)
            
            return {
                'code': code,
                'explanation': explanation,
                'success': True,
                'raw_response': response
            }
        except Exception as e:
            return {
                'code': None,
                'explanation': f"Error generando código: {str(e)}",
                'success': False,
                'raw_response': None
            }
    
    def _build_generation_prompt(self, description: str, context: Optional[Dict[str, Any]]) -> str:
        """Construye el prompt para generar código."""
        context_str = ""
        if context:
            context_str = f"\n\nCONTEXTO DISPONIBLE:\n{json.dumps(context, indent=2, default=str)}\n"
        
        prompt = f"""Eres un experto programador Python. Tu tarea es convertir descripciones en lenguaje natural en código Python ejecutable y funcional.

DESCRIPCIÓN DEL USUARIO:
{description}
{context_str}

INSTRUCCIONES CRÍTICAS:
1. GENERA CÓDIGO PYTHON COMPLETO Y FUNCIONAL
2. El código debe ser autocontenido (no requiere imports externos complejos)
3. Si necesitas procesar datos, usa las variables del contexto si están disponibles
4. Si generas resultados, guárdalos en una variable llamada 'result'
5. Usa print() para mostrar información importante
6. El código debe ser claro, bien comentado y seguir buenas prácticas
7. Si es un análisis de datos, incluye visualizaciones si es apropiado
8. Si es una tarea de procesamiento, muestra el progreso

RESTRICCIONES DE SEGURIDAD:
- NO uses eval(), exec(), __import__(), open(), file(), input()
- NO accedas al sistema de archivos de forma peligrosa
- NO hagas llamadas de red peligrosas
- El código se ejecutará en un sandbox seguro

FORMATO DE RESPUESTA:
```python
# Tu código Python aquí
# Incluye comentarios explicativos
# Si hay resultados, guárdalos en 'result'
```

EXPLICACIÓN:
[Explica brevemente qué hace el código y cómo funciona]

Genera el código ahora:"""
        
        return prompt
    
    def _build_fix_prompt(self, description: str, code: str, error: str, context: Optional[Dict[str, Any]]) -> str:
        """Construye el prompt para corregir código con errores."""
        context_str = ""
        if context:
            context_str = f"\n\nCONTEXTO DISPONIBLE:\n{json.dumps(context, indent=2, default=str)}\n"
        
        prompt = f"""Eres un experto programador Python. El código generado tiene un error y necesitas corregirlo.

DESCRIPCIÓN ORIGINAL:
{description}
{context_str}

CÓDIGO CON ERROR:
```python
{code}
```

ERROR ENCONTRADO:
{error}

INSTRUCCIONES:
1. Analiza el error cuidadosamente
2. Corrige el código manteniendo la funcionalidad original
3. Asegúrate de que el código corregido sea funcional
4. Si hay resultados, guárdalos en 'result'
5. Usa print() para mostrar información importante

FORMATO DE RESPUESTA:
```python
# Código corregido aquí
```

EXPLICACIÓN:
[Explica qué error había y cómo lo corregiste]

Corrige el código ahora:"""
        
        return prompt
    
    def _extract_code_from_response(self, response: str) -> Tuple[str, str]:
        """Extrae código Python del response del LLM."""
        # Buscar código entre ```python y ```
        code_pattern = r'```python\s*(.*?)\s*```'
        match = re.search(code_pattern, response, re.DOTALL)
        
        if match:
            code = match.group(1).strip()
            # Extraer explicación (todo lo que no es código)
            explanation = response.replace(match.group(0), '').strip()
            # Limpiar explicación
            explanation = re.sub(r'^EXPLICACIÓN:?\s*', '', explanation, flags=re.IGNORECASE | re.MULTILINE)
            explanation = explanation.strip()
        else:
            # Si no hay bloques de código, buscar código sin bloques
            lines = response.split('\n')
            code_lines = []
            explanation_lines = []
            in_code = False
            
            for line in lines:
                if line.strip().startswith('#') or '=' in line or 'def ' in line or 'import ' in line or 'print(' in line:
                    code_lines.append(line)
                    in_code = True
                elif in_code and line.strip():
                    code_lines.append(line)
                else:
                    explanation_lines.append(line)
            
            code = '\n'.join(code_lines).strip()
            explanation = '\n'.join(explanation_lines).strip()
        
        if not code:
            code = response  # Si no se puede extraer, usar todo el response
        
        return code, explanation or "Código generado automáticamente"
    
    def execute_action(
        self,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Ejecuta una acción completa: genera código y lo ejecuta, corrigiendo errores si es necesario.
        
        Args:
            description: Descripción en lenguaje natural
            context: Contexto adicional
            max_iterations: Máximo de intentos para corregir errores
        
        Returns:
            Dict con 'success', 'code', 'output', 'result', 'explanation', 'iterations'
        """
        iterations = []
        current_code = None
        current_error = None
        
        for iteration in range(max_iterations):
            # Generar o corregir código
            if iteration == 0:
                # Primera iteración: generar código nuevo
                code_result = self.generate_code(description, context)
            else:
                # Iteraciones siguientes: corregir código con error
                code_result = self.generate_code(description, context, current_code, current_error)
            
            if not code_result['success']:
                return {
                    'success': False,
                    'code': None,
                    'output': '',
                    'result': None,
                    'explanation': code_result['explanation'],
                    'error': 'Error generando código',
                    'iterations': iterations
                }
            
            current_code = code_result['code']
            explanation = code_result['explanation']
            
            # Ejecutar código
            execution_result = self.sandbox.execute(current_code, context)
            
            iterations.append({
                'iteration': iteration + 1,
                'code': current_code,
                'explanation': explanation,
                'execution': execution_result
            })
            
            if execution_result['success']:
                # Éxito: código ejecutado correctamente
                return {
                    'success': True,
                    'code': current_code,
                    'output': execution_result['output'],
                    'result': execution_result['result'],
                    'explanation': explanation,
                    'error': execution_result.get('error'),
                    'iterations': iterations
                }
            else:
                # Error: guardar para próxima iteración
                current_error = execution_result['error']
        
        # Si llegamos aquí, se agotaron los intentos
        return {
            'success': False,
            'code': current_code,
            'output': execution_result.get('output', ''),
            'result': None,
            'explanation': explanation,
            'error': f"❌ No se pudo ejecutar el código después de {max_iterations} intentos. Último error: {current_error}",
            'iterations': iterations
        }
