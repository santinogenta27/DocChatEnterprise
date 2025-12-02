"""
Sistema de Plantillas de Agentes Predefinidas
Permite a los usuarios activar agentes especializados (Ventas, Soporte, Análisis, etc.)
"""

from __future__ import annotations

import json
import time
import uuid
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import logging

from .config import AppConfig

logger = logging.getLogger(__name__)


class AgentTemplateType(str, Enum):
    """Tipos de plantillas de agentes disponibles."""
    SALES = "sales"  # Agente de Ventas
    SUPPORT = "support"  # Agente de Soporte
    ANALYSIS = "analysis"  # Agente de Análisis
    HR = "hr"  # Agente de Recursos Humanos
    FINANCE = "finance"  # Agente de Finanzas
    MARKETING = "marketing"  # Agente de Marketing
    OPERATIONS = "operations"  # Agente de Operaciones
    CUSTOM = "custom"  # Plantilla personalizada


@dataclass
class AgentTemplate:
    """Plantilla de agente predefinida."""
    template_id: str
    template_type: AgentTemplateType
    name: str
    description: str
    system_prompt: str  # Prompt del sistema para el agente
    tools: List[str] = field(default_factory=list)  # IDs de herramientas a usar
    tasks: List[str] = field(default_factory=list)  # IDs de tareas predefinidas
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    usage_count: int = 0
    last_used: Optional[float] = None


class AgentTemplateManager:
    """Gestiona plantillas de agentes predefinidas."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.templates: Dict[str, AgentTemplate] = {}
        self.active_templates: Dict[str, AgentTemplate] = {}  # Templates activados por usuario
        self.storage_file = Path(config.memory_dir) / "agent_templates.json"
        
        # Inicializar plantillas predefinidas
        self._initialize_default_templates()
        self._load_templates()
    
    def _initialize_default_templates(self):
        """Inicializa plantillas predefinidas."""
        
        # Agente de Ventas
        sales_template = AgentTemplate(
            template_id="sales_agent_v1",
            template_type=AgentTemplateType.SALES,
            name="Agente de Ventas",
            description="Agente especializado en análisis de ventas, seguimiento de clientes y generación de reportes comerciales",
            system_prompt="""Eres un Agente de Ventas especializado en:
- Analizar datos de ventas y tendencias
- Identificar oportunidades de negocio
- Generar reportes de rendimiento comercial
- Seguimiento de clientes y leads
- Análisis de competencia y mercado

Tu objetivo es ayudar a maximizar las ventas y mejorar la relación con los clientes.""",
            tools=["sql_tool", "rag_tool", "email_tool", "analytics_tool"],
            tasks=["analyze_sales_trends", "generate_sales_report", "track_customer_activity"],
            parameters={
                "focus_areas": ["ventas", "clientes", "oportunidades"],
                "report_frequency": "daily",
                "alert_thresholds": {
                    "low_sales": 0.8,
                    "high_opportunity": 0.9
                }
            }
        )
        self.templates[sales_template.template_id] = sales_template
        
        # Agente de Soporte
        support_template = AgentTemplate(
            template_id="support_agent_v1",
            template_type=AgentTemplateType.SUPPORT,
            name="Agente de Soporte",
            description="Agente especializado en atención al cliente, resolución de tickets y gestión de incidencias",
            system_prompt="""Eres un Agente de Soporte especializado en:
- Resolver consultas de clientes
- Gestionar tickets de soporte
- Analizar patrones de problemas comunes
- Generar respuestas automáticas
- Escalar casos complejos

Tu objetivo es proporcionar soporte rápido y efectivo a los clientes.""",
            tools=["rag_tool", "email_tool", "ticket_tool", "knowledge_base_tool"],
            tasks=["process_support_tickets", "generate_support_responses", "analyze_common_issues"],
            parameters={
                "response_time_target": 60,  # segundos
                "auto_resolve_threshold": 0.85,
                "escalation_keywords": ["urgente", "crítico", "fallo"]
            }
        )
        self.templates[support_template.template_id] = support_template
        
        # Agente de Análisis
        analysis_template = AgentTemplate(
            template_id="analysis_agent_v1",
            template_type=AgentTemplateType.ANALYSIS,
            name="Agente de Análisis",
            description="Agente especializado en análisis de datos, descubrimiento de insights y generación de reportes analíticos",
            system_prompt="""Eres un Agente de Análisis especializado en:
- Análisis profundo de datos
- Descubrimiento de patrones y tendencias
- Generación de insights accionables
- Creación de visualizaciones y reportes
- Análisis predictivo

Tu objetivo es transformar datos en conocimiento accionable.""",
            tools=["sql_tool", "python_tool", "visualization_tool", "statistics_tool"],
            tasks=["deep_data_analysis", "pattern_discovery", "generate_insights", "create_visualizations"],
            parameters={
                "analysis_depth": "deep",
                "visualization_preference": "interactive",
                "insight_confidence_threshold": 0.7
            }
        )
        self.templates[analysis_template.template_id] = analysis_template
        
        # Agente de Recursos Humanos
        hr_template = AgentTemplate(
            template_id="hr_agent_v1",
            template_type=AgentTemplateType.HR,
            name="Agente de Recursos Humanos",
            description="Agente especializado en gestión de empleados, análisis de rendimiento y procesos de RRHH",
            system_prompt="""Eres un Agente de Recursos Humanos especializado en:
- Gestión de información de empleados
- Análisis de rendimiento
- Procesos de contratación y onboarding
- Gestión de beneficios y políticas
- Análisis de satisfacción laboral

Tu objetivo es apoyar la gestión eficiente de recursos humanos.""",
            tools=["employee_db_tool", "performance_tool", "document_tool"],
            tasks=["analyze_employee_data", "generate_hr_reports", "process_hr_queries"],
            parameters={
                "privacy_mode": "strict",
                "compliance_checks": True
            }
        )
        self.templates[hr_template.template_id] = hr_template
        
        # Agente de Finanzas
        finance_template = AgentTemplate(
            template_id="finance_agent_v1",
            template_type=AgentTemplateType.FINANCE,
            name="Agente de Finanzas",
            description="Agente especializado en análisis financiero, reportes contables y gestión de presupuestos",
            system_prompt="""Eres un Agente de Finanzas especializado en:
- Análisis de estados financieros
- Generación de reportes contables
- Análisis de presupuestos y costos
- Detección de anomalías financieras
- Proyecciones y forecasting

Tu objetivo es proporcionar análisis financiero preciso y oportuno.""",
            tools=["financial_db_tool", "accounting_tool", "budget_tool", "reporting_tool"],
            tasks=["analyze_financial_data", "generate_financial_reports", "detect_anomalies"],
            parameters={
                "precision_level": "high",
                "audit_trail": True,
                "compliance_checks": True
            }
        )
        self.templates[finance_template.template_id] = finance_template
        
        # Agente de Marketing
        marketing_template = AgentTemplate(
            template_id="marketing_agent_v1",
            template_type=AgentTemplateType.MARKETING,
            name="Agente de Marketing",
            description="Agente especializado en análisis de campañas, métricas de marketing y optimización de estrategias",
            system_prompt="""Eres un Agente de Marketing especializado en:
- Análisis de campañas de marketing
- Métricas y KPIs de marketing
- Análisis de audiencia y segmentación
- Optimización de estrategias
- Análisis de competencia

Tu objetivo es maximizar el ROI de las campañas de marketing.""",
            tools=["campaign_tool", "analytics_tool", "social_media_tool", "seo_tool"],
            tasks=["analyze_campaigns", "track_marketing_metrics", "optimize_strategies"],
            parameters={
                "kpi_focus": ["roi", "conversion", "engagement"],
                "report_frequency": "weekly"
            }
        )
        self.templates[marketing_template.template_id] = marketing_template
        
        # Agente de Operaciones
        operations_template = AgentTemplate(
            template_id="operations_agent_v1",
            template_type=AgentTemplateType.OPERATIONS,
            name="Agente de Operaciones",
            description="Agente especializado en optimización de procesos, gestión de operaciones y mejora continua",
            system_prompt="""Eres un Agente de Operaciones especializado en:
- Optimización de procesos operativos
- Análisis de eficiencia
- Gestión de recursos y capacidad
- Detección de cuellos de botella
- Mejora continua

Tu objetivo es optimizar las operaciones para máxima eficiencia.""",
            tools=["process_tool", "efficiency_tool", "resource_tool", "monitoring_tool"],
            tasks=["analyze_operations", "optimize_processes", "monitor_efficiency"],
            parameters={
                "efficiency_target": 0.9,
                "monitoring_frequency": "real-time"
            }
        )
        self.templates[operations_template.template_id] = operations_template
    
    def _load_templates(self):
        """Carga plantillas personalizadas desde almacenamiento."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for template_data in data.get("custom_templates", []):
                        template = AgentTemplate(**template_data)
                        # No sobrescribir plantillas predefinidas
                        if template.template_id not in self.templates:
                            self.templates[template.template_id] = template
                    for active_data in data.get("active_templates", []):
                        template_id = active_data["template_id"]
                        if template_id in self.templates:
                            self.active_templates[template_id] = self.templates[template_id]
                logger.info(f"✅ [Agent Templates] {len(self.templates)} plantillas cargadas")
            except Exception as e:
                logger.error(f"❌ [Agent Templates] Error cargando plantillas: {e}")
    
    def _save_templates(self):
        """Guarda plantillas personalizadas."""
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Solo guardar plantillas personalizadas (no predefinidas)
            custom_templates = [
                asdict(t) for t in self.templates.values()
                if t.template_type == AgentTemplateType.CUSTOM
            ]
            active_templates = [
                {"template_id": tid} for tid in self.active_templates.keys()
            ]
            data = {
                "custom_templates": custom_templates,
                "active_templates": active_templates
            }
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ [Agent Templates] Error guardando plantillas: {e}")
    
    def get_template(self, template_id: str) -> Optional[AgentTemplate]:
        """Obtiene una plantilla por ID."""
        return self.templates.get(template_id)
    
    def list_templates(
        self,
        template_type: Optional[AgentTemplateType] = None,
        active_only: bool = False
    ) -> List[AgentTemplate]:
        """Lista todas las plantillas."""
        templates = list(self.templates.values())
        
        if template_type:
            templates = [t for t in templates if t.template_type == template_type]
        
        if active_only:
            templates = [t for t in templates if t.template_id in self.active_templates]
        
        return sorted(templates, key=lambda t: t.name)
    
    def activate_template(self, template_id: str) -> bool:
        """Activa una plantilla para uso."""
        if template_id not in self.templates:
            return False
        
        template = self.templates[template_id]
        template.enabled = True
        template.usage_count += 1
        template.last_used = time.time()
        
        self.active_templates[template_id] = template
        self._save_templates()
        
        logger.info(f"✅ [Agent Templates] Plantilla activada: {template.name}")
        return True
    
    def deactivate_template(self, template_id: str) -> bool:
        """Desactiva una plantilla."""
        if template_id not in self.active_templates:
            return False
        
        template = self.templates[template_id]
        template.enabled = False
        
        del self.active_templates[template_id]
        self._save_templates()
        
        logger.info(f"✅ [Agent Templates] Plantilla desactivada: {template.name}")
        return True
    
    def create_custom_template(
        self,
        name: str,
        description: str,
        system_prompt: str,
        tools: Optional[List[str]] = None,
        tasks: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Crea una plantilla personalizada."""
        template_id = f"custom_{uuid.uuid4().hex[:8]}"
        
        template = AgentTemplate(
            template_id=template_id,
            template_type=AgentTemplateType.CUSTOM,
            name=name,
            description=description,
            system_prompt=system_prompt,
            tools=tools or [],
            tasks=tasks or [],
            parameters=parameters or {}
        )
        
        self.templates[template_id] = template
        self._save_templates()
        
        logger.info(f"✅ [Agent Templates] Plantilla personalizada creada: {name}")
        return template_id
    
    def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Actualiza una plantilla (solo personalizadas)."""
        if template_id not in self.templates:
            return False
        
        template = self.templates[template_id]
        
        # Solo permitir actualizar plantillas personalizadas
        if template.template_type != AgentTemplateType.CUSTOM:
            return False
        
        if name is not None:
            template.name = name
        if description is not None:
            template.description = description
        if system_prompt is not None:
            template.system_prompt = system_prompt
        if tools is not None:
            template.tools = tools
        if parameters is not None:
            template.parameters.update(parameters)
        
        self._save_templates()
        logger.info(f"✅ [Agent Templates] Plantilla actualizada: {template_id}")
        return True
    
    def delete_template(self, template_id: str) -> bool:
        """Elimina una plantilla (solo personalizadas)."""
        if template_id not in self.templates:
            return False
        
        template = self.templates[template_id]
        
        # No permitir eliminar plantillas predefinidas
        if template.template_type != AgentTemplateType.CUSTOM:
            return False
        
        # Desactivar si está activa
        if template_id in self.active_templates:
            del self.active_templates[template_id]
        
        del self.templates[template_id]
        self._save_templates()
        
        logger.info(f"✅ [Agent Templates] Plantilla eliminada: {template_id}")
        return True
    
    def get_active_templates(self) -> List[AgentTemplate]:
        """Obtiene todas las plantillas activas."""
        return list(self.active_templates.values())
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de plantillas."""
        total_templates = len(self.templates)
        active_templates = len(self.active_templates)
        custom_templates = len([t for t in self.templates.values() if t.template_type == AgentTemplateType.CUSTOM])
        
        templates_by_type = {}
        for template_type in AgentTemplateType:
            templates_by_type[template_type.value] = len([
                t for t in self.templates.values() if t.template_type == template_type
            ])
        
        return {
            "total_templates": total_templates,
            "active_templates": active_templates,
            "custom_templates": custom_templates,
            "predefined_templates": total_templates - custom_templates,
            "templates_by_type": templates_by_type,
            "most_used": sorted(
                self.templates.values(),
                key=lambda t: t.usage_count,
                reverse=True
            )[:5]
        }


