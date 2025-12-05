"""
Text-to-Action: Convierte lenguaje natural en código y acciones
Basado en las ideas de Eric Schmidt sobre "cada humano con su programador personal"
"""

from __future__ import annotations

import ast
import subprocess
import tempfile
import os
import json
import time
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import re

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from .config import AppConfig
from .tools.whatsapp_tool import WhatsAppTool
from .tools.advertising_tool import AdvertisingTool
from .tools.email_marketing_tool import EmailMarketingTool
from .tools.integration_tool import IntegrationTool


class ActionType(str, Enum):
    """Tipos de acciones que se pueden ejecutar."""
    CODE_EXECUTION = "code_execution"
    API_CALL = "api_call"
    EMAIL_SEND = "email_send"
    SLACK_MESSAGE = "slack_message"
    WHATSAPP_MESSAGE = "whatsapp_message"
    ADVERTISING_ACTION = "advertising_action"
    EMAIL_MARKETING_ACTION = "email_marketing_action"
    INTEGRATION_MESSAGE = "integration_message"
    SALESFORCE_ACTION = "salesforce_action"
    DATABASE_QUERY = "database_query"
    FILE_OPERATION = "file_operation"
    DASHBOARD_CREATE = "dashboard_create"
    REPORT_GENERATE = "report_generate"
    ADVICE = "advice"  # Para consultas que requieren consejo/respuesta
    CUSTOM = "custom"


@dataclass
class ActionPlan:
    """Plan de acción generado desde lenguaje natural."""
    action_id: str
    action_type: ActionType
    description: str
    code: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_result: Optional[str] = None
    safety_checks: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    created_at: float = field(default_factory=time.time)


@dataclass
class ActionResult:
    """Resultado de ejecutar una acción."""
    action_id: str
    success: bool
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    safety_violations: List[str] = field(default_factory=list)
    executed_at: float = field(default_factory=time.time)


class CodeSafetyChecker:
    """Verifica seguridad del código antes de ejecutarlo."""
    
    DANGEROUS_PATTERNS = [
        r'__import__\s*\(',
        r'eval\s*\(',
        r'exec\s*\(',
        r'compile\s*\(',
        r'open\s*\([^)]*[\'"]w[\'"]',
        r'subprocess\s*\.',
        r'os\.system\s*\(',
        r'shutil\.',
        r'rm\s+-rf',
        r'del\s+\w+\s*\[',  # Delete operations
    ]
    
    ALLOWED_IMPORTS = [
        'json', 'datetime', 'time', 'math', 'random', 're',
        'requests', 'pandas', 'numpy', 'matplotlib', 'plotly',
        'sqlite3', 'csv', 'io', 'base64', 'hashlib'
    ]
    
    def check_code(self, code: str) -> tuple[bool, List[str]]:
        """
        Verifica seguridad del código.
        
        Returns:
            (is_safe, violations)
        """
        violations = []
        
        # 1. Check dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                violations.append(f"Patrón peligroso detectado: {pattern}")
        
        # 2. Parse AST and check imports
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name not in self.ALLOWED_IMPORTS:
                            violations.append(f"Import no permitido: {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module not in self.ALLOWED_IMPORTS:
                        violations.append(f"Import no permitido: {node.module}")
                
                # Check for dangerous function calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ['eval', 'exec', 'compile', '__import__']:
                            violations.append(f"Llamada peligrosa: {node.func.id}")
        except SyntaxError as e:
            violations.append(f"Error de sintaxis: {e}")
        
        # 3. Check for file system operations outside temp
        if 'open(' in code and 'tempfile' not in code:
            # Permitir solo lectura
            if 'w' in code or 'a' in code or 'x' in code:
                violations.append("Operaciones de escritura de archivos no permitidas fuera de tempfile")
        
        is_safe = len(violations) == 0
        return is_safe, violations


class TextToAction:
    """
    Convierte lenguaje natural en código ejecutable y acciones.
    
    Ejemplo: "Crea un dashboard con los datos de Salesforce"
    → Genera código Python que llama a la API de Salesforce
    → Ejecuta el código en un sandbox seguro
    → Crea el dashboard
    """
    
    def __init__(
        self,
        config: AppConfig,
        llm: Optional[BaseLanguageModel] = None,
        sandbox_enabled: bool = True
    ):
        self.config = config
        self.llm = llm or self._create_llm()
        self.sandbox_enabled = sandbox_enabled
        self.safety_checker = CodeSafetyChecker()

        # Herramientas enterprise para acciones en el mundo real
        self.whatsapp_tool = WhatsAppTool(config)
        self.advertising_tool = AdvertisingTool(config)
        self.email_marketing_tool = EmailMarketingTool(config)
        self.integration_tool = IntegrationTool(config)
        
        # Historial de acciones
        self.action_history: List[ActionPlan] = []
        self.result_history: List[ActionResult] = []
        
        # Prompts
        self.action_generation_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un asistente que convierte lenguaje natural en código ejecutable y acciones.
            
Dado un comando en lenguaje natural, genera un plan de acción que incluya:
1. Tipo de acción (code_execution, api_call, email_send, whatsapp_message, advertising_action, email_marketing_action, integration_message, etc.)
2. Código Python necesario (si aplica)
3. Parámetros necesarios
4. Resultado esperado
5. Verificaciones de seguridad
            
Casos especiales importantes para empresas:
- Usa \"whatsapp_message\" cuando el usuario quiera enviar mensajes por WhatsApp Business (campañas, mensajes a clientes, notificaciones).
- Usa \"advertising_action\" cuando el usuario quiera crear/optimizar campañas de anuncios en Meta, TikTok, Google Ads, LinkedIn.
- Usa \"email_marketing_action\" cuando el usuario hable de newsletters, campañas de email o automatizaciones (Mailchimp, HubSpot, ActiveCampaign).
- Usa \"integration_message\" cuando el usuario pida notificaciones o mensajes a Slack o Microsoft Teams (resúmenes diarios, alertas, reportes).
            
Responde en formato JSON:
{{
    "action_type": "code_execution|api_call|email_send|whatsapp_message|advertising_action|email_marketing_action|integration_message|...",
    "description": "Descripción de la acción",
    "code": "código Python si aplica",
    "parameters": {{"param1": "value1"}},
    "expected_result": "Qué se espera obtener",
    "safety_checks": ["check1", "check2"],
    "requires_confirmation": true/false
}}
            
IMPORTANTE:
- Solo genera código seguro
- No uses eval, exec, compile
- No accedas al sistema de archivos fuera de tempfile
- Usa solo imports permitidos
- Para APIs externas, usa requests de forma segura
- Para campañas de anuncios, usa \"advertising_action\" y parámetros como: platform (\"meta\"|\"tiktok\"|\"google_ads\"|\"linkedin\"), campaign_name, budget, objective, audience, creative_content.
- Para Email Marketing usa \"email_marketing_action\" y parámetros como: action (\"create_campaign\"|\"send_campaign\"|\"create_audience\"|\"add_subscriber\"|\"analyze_performance\"), platform (\"mailchimp\"|\"hubspot\"|\"activecampaign\"|\"local\"), campaign_data, audience_data.
- Para WhatsApp usa \"whatsapp_message\" y parámetros como: to, message, media_url (opcional).
- Para Slack/Teams usa \"integration_message\" y parámetros como: platform (\"slack\"|\"teams\"), message, title (opcional)."""),
            ("human", "{command}")
        ])
    
    def _create_llm(self) -> BaseLanguageModel:
        """Crea el LLM según la configuración."""
        provider = getattr(self.config, 'ai_provider', 'openai')
        
        if provider == 'anthropic':
            return ChatAnthropic(
                model="claude-sonnet-4-20250514",
                temperature=0.3,  # Más determinístico para código
                max_tokens=4000
            )
        else:
            return ChatOpenAI(
                model="gpt-4-turbo-preview",
                temperature=0.3,
                max_tokens=4000
            )
    
    async def generate_action_plan(self, command: str) -> ActionPlan:
        """
        Genera un plan de acción desde lenguaje natural.
        """
        try:
            chain = self.action_generation_prompt | self.llm
            response = await chain.ainvoke({"command": command})
            
            content = response.content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content
            
            # Extraer JSON
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', json_str, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise ValueError("No se pudo parsear JSON")
            
            # Manejar action_type de forma segura
            action_type_str = data.get("action_type", "code_execution")
            try:
                action_type = ActionType(action_type_str)
            except ValueError:
                # Si el tipo no es válido, usar CUSTOM como fallback
                print(f"⚠️ [Text-to-Action] Tipo de acción no válido: {action_type_str}, usando CUSTOM")
                action_type = ActionType.CUSTOM
            
            action_plan = ActionPlan(
                action_id=str(uuid.uuid4()),
                action_type=action_type,
                description=data.get("description", command),
                code=data.get("code"),
                parameters=data.get("parameters", {}),
                expected_result=data.get("expected_result"),
                safety_checks=data.get("safety_checks", []),
                requires_confirmation=data.get("requires_confirmation", False)
            )
            
            self.action_history.append(action_plan)
            return action_plan
            
        except Exception as e:
            print(f"❌ Error generando plan de acción: {e}")
            raise
    
    async def execute_action(self, action_plan: ActionPlan, confirm: bool = True) -> ActionResult:
        """
        Ejecuta un plan de acción.
        """
        if action_plan.requires_confirmation and not confirm:
            return ActionResult(
                action_id=action_plan.action_id,
                success=False,
                error="Acción requiere confirmación"
            )
        
        start_time = time.time()
        
        # Verificar seguridad si hay código
        if action_plan.code:
            is_safe, violations = self.safety_checker.check_code(action_plan.code)
            if not is_safe:
                return ActionResult(
                    action_id=action_plan.action_id,
                    success=False,
                    error="Código no seguro",
                    safety_violations=violations
                )
        
        try:
            # Ejecutar según tipo de acción
            if action_plan.action_type == ActionType.CODE_EXECUTION:
                result = await self._execute_code(action_plan.code, action_plan.parameters)
            elif action_plan.action_type == ActionType.API_CALL:
                result = await self._execute_api_call(action_plan.parameters)
            elif action_plan.action_type == ActionType.EMAIL_SEND:
                result = await self._execute_email_send(action_plan.parameters)
            elif action_plan.action_type == ActionType.SLACK_MESSAGE:
                result = await self._execute_slack_message(action_plan.parameters)
            elif action_plan.action_type == ActionType.WHATSAPP_MESSAGE:
                result = await self._execute_whatsapp_message(action_plan.parameters)
            elif action_plan.action_type == ActionType.ADVERTISING_ACTION:
                result = await self._execute_advertising_action(action_plan.parameters)
            elif action_plan.action_type == ActionType.EMAIL_MARKETING_ACTION:
                result = await self._execute_email_marketing_action(action_plan.parameters)
            elif action_plan.action_type == ActionType.INTEGRATION_MESSAGE:
                result = await self._execute_integration_message(action_plan.parameters)
            elif action_plan.action_type == ActionType.DASHBOARD_CREATE:
                result = await self._execute_dashboard_create(action_plan.parameters)
            elif action_plan.action_type == ActionType.ADVICE:
                # Para consultas que requieren consejo/respuesta, retornar la descripción como resultado
                result = {
                    "message": "Consulta de consejo procesada",
                    "advice": action_plan.description,
                    "expected_result": action_plan.expected_result
                }
            else:
                result = {"message": "Tipo de acción no implementado aún", "action_type": action_plan.action_type}
            
            execution_time = time.time() - start_time
            
            action_result = ActionResult(
                action_id=action_plan.action_id,
                success=True,
                output=result,
                execution_time=execution_time
            )
            
            self.result_history.append(action_result)
            return action_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            return ActionResult(
                action_id=action_plan.action_id,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _execute_code(self, code: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta código Python en un sandbox seguro."""
        if not self.sandbox_enabled:
            # Modo no-sandbox (solo para desarrollo)
            exec_globals = {
                "__builtins__": __builtins__,
                "json": __import__("json"),
                "time": __import__("time"),
                "math": __import__("math"),
                "re": __import__("re"),
                **parameters
            }
            exec_locals = {}
            exec(code, exec_globals, exec_locals)
            return {"output": exec_locals.get("result", "Código ejecutado"), "locals": str(exec_locals)}
        
        # Sandbox: ejecutar en proceso separado
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Ejecutar en subprocess con timeout
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, **{k: str(v) for k, v in parameters.items()}}
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "success": result.returncode == 0
            }
        finally:
            os.unlink(temp_file)
    
    async def _execute_api_call(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta una llamada a API."""
        import requests
        
        url = parameters.get("url")
        method = parameters.get("method", "GET")
        headers = parameters.get("headers", {})
        data = parameters.get("data")
        
        try:
            response = requests.request(method, url, headers=headers, json=data, timeout=10)
            return {
                "status_code": response.status_code,
                "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _execute_email_send(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Envía un email."""
        # Implementación básica - en producción usar servicio de email real
        return {
            "message": "Email enviado (simulado)",
            "to": parameters.get("to"),
            "subject": parameters.get("subject")
        }
    
    async def _execute_slack_message(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Envía mensaje a Slack."""
        # Implementación básica - en producción usar Slack API real
        return {
            "message": "Mensaje enviado a Slack (simulado)",
            "channel": parameters.get("channel"),
            "text": parameters.get("text")
        }
    
    async def _execute_dashboard_create(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Crea un dashboard."""
        # Implementación básica - en producción generar dashboard real
        return {
            "message": "Dashboard creado (simulado)",
            "dashboard_id": str(uuid.uuid4()),
            "data_source": parameters.get("data_source")
        }

    async def _execute_email_marketing_action(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta acciones de Email Marketing usando EmailMarketingTool.

        Espera parámetros como:
        - action: "create_campaign" | "send_campaign" | "create_audience" | "add_subscriber" | "analyze_performance" | ...
        - platform: "mailchimp" | "hubspot" | "activecampaign" | "local"
        - campaign_data, audience_data, automation_data, etc.
        """
        try:
            action = parameters.get("action", "create_campaign")

            tool_result = self.email_marketing_tool.execute(
                action=action,
                platform=parameters.get("platform"),
                campaign_data=parameters.get("campaign_data"),
                audience_data=parameters.get("audience_data"),
                automation_data=parameters.get("automation_data"),
                **{k: v for k, v in parameters.items() if k not in {
                    "action", "platform", "campaign_data", "audience_data", "automation_data"
                }}
            )

            return {
                "success": tool_result.success,
                "message": tool_result.message,
                "data": tool_result.data,
                "metadata": tool_result.metadata
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _execute_integration_message(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envía mensajes a Slack, Microsoft Teams o webhooks usando IntegrationTool.

        Espera parámetros como:
        - platform: "slack" | "teams" | "webhook"
        - message: texto principal
        - title: opcional (título del mensaje)
        - webhook_url: opcional (para overrides o webhooks custom)
        """
        try:
            platform = parameters.get("platform")
            message = parameters.get("message")
            title = parameters.get("title")
            webhook_url = parameters.get("webhook_url")

            if not platform or not message:
                return {
                    "success": False,
                    "error": "Parámetros insuficientes para integración (se requiere 'platform' y 'message')"
                }

            tool_result = self.integration_tool.execute(
                platform=platform,
                message=message,
                title=title,
                webhook_url=webhook_url
            )

            return {
                "success": tool_result.success,
                "message": tool_result.message,
                "data": tool_result.data,
                "metadata": tool_result.metadata
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _execute_whatsapp_message(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Envía un mensaje de WhatsApp usando la herramienta enterprise."""
        try:
            to = parameters.get("to") or parameters.get("phone") or parameters.get("phone_number")
            message = parameters.get("message") or parameters.get("text")
            media_url = parameters.get("media_url")

            if not to or not message:
                return {
                    "success": False,
                    "error": "Parámetros insuficientes para WhatsApp (se requiere 'to' y 'message')"
                }

            tool_result = self.whatsapp_tool.execute(
                to=to,
                message=message,
                media_url=media_url
            )

            return {
                "success": tool_result.success,
                "message": tool_result.message,
                "data": tool_result.data,
                "metadata": tool_result.metadata
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _execute_advertising_action(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta acciones avanzadas de publicidad/marketing usando AdvertisingTool.

        Espera parámetros como:
        - action: "create_campaign" | "optimize_campaign" | "generate_creative" | "analyze_performance"
        - platform: "meta" | "tiktok" | "google_ads" | "linkedin"
        - campaign_name, budget, objective, audience, creative_content, optimization_goal, etc.
        """
        try:
            action = parameters.get("action", "create_campaign")

            tool_result = self.advertising_tool.execute(
                action=action,
                campaign_name=parameters.get("campaign_name"),
                platform=parameters.get("platform"),
                budget=parameters.get("budget"),
                objective=parameters.get("objective"),
                audience=parameters.get("audience"),
                creative_content=parameters.get("creative_content") or parameters.get("creative"),
                optimization_goal=parameters.get("optimization_goal"),
                **{k: v for k, v in parameters.items() if k not in {
                    "action", "campaign_name", "platform", "budget", "objective",
                    "audience", "creative_content", "creative", "optimization_goal"
                }}
            )

            return {
                "success": tool_result.success,
                "message": tool_result.message,
                "data": tool_result.data,
                "metadata": tool_result.metadata
            }
        except Exception as e:
                return {
                "success": False,
                "error": str(e)
            }
    
    async def process_command(self, command: str, auto_execute: bool = False) -> Dict[str, Any]:
        """
        Procesa un comando completo: genera plan y opcionalmente ejecuta.
        """
        print(f"🎯 [Text-to-Action] Procesando comando: {command[:100]}...")
        
        # Generar plan
        action_plan = await self.generate_action_plan(command)
        
        result = {
            "action_plan": {
                "action_id": action_plan.action_id,
                "action_type": action_plan.action_type.value,
                "description": action_plan.description,
                "requires_confirmation": action_plan.requires_confirmation
            }
        }
        
        # Ejecutar si se solicita
        if auto_execute or not action_plan.requires_confirmation:
            action_result = await self.execute_action(action_plan, confirm=auto_execute)
            result["execution"] = {
                "success": action_result.success,
                "output": action_result.output,
                "error": action_result.error,
                "execution_time": action_result.execution_time
            }
        
        return result
    
    def get_history(self) -> Dict[str, Any]:
        """Obtiene historial de acciones."""
        return {
            "total_actions": len(self.action_history),
            "successful_executions": sum(1 for r in self.result_history if r.success),
            "failed_executions": sum(1 for r in self.result_history if not r.success),
            "recent_actions": [
                {
                    "action_id": a.action_id,
                    "type": a.action_type.value,
                    "description": a.description[:100]
                }
                for a in self.action_history[-10:]
            ]
        }
