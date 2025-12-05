"""Enterprise Autonomous Workflows

Nuevo modo que orquesta:
- EnterpriseAPIMode (ingesta masiva + análisis inicial de PDFs)
- ResearchActionAgent (planificación, análisis profundo, acciones)

Sin modificar los modos originales.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .enterprise_api import EnterpriseAPIMode
from .research_action_agent import ResearchActionAgent
from .data_ingestion_engine import DataIngestionEngine
from .audit import AuditLogger
from .enterprise_policy_engine import EnterprisePolicyEngine
from .research_action_agent.action_layer import (
    jira_create_ticket,
    servicenow_create_incident,
    send_email_smtp,
    slack_send_message,
    teams_send_message,
    http_request,
    file_writer,
    export_pdf_report,
    sql_executor,
    erp_get_order,
    erp_update_order,
    salesforce_create_record,
    s3_upload_file,
)


@dataclass
class WorkflowResult:
    workflow_type: str
    enterprise_summary: str
    research_result: Dict[str, Any]
    logs: List[Dict[str, Any]]


class EnterpriseAutonomousWorkflows:
    """Capa de orquestación entre Enterprise API y Research & Action Agent."""

    def __init__(
        self,
        config: Any,
        enterprise_api: EnterpriseAPIMode,
        research_agent: ResearchActionAgent,
        ingestion_engine: Optional[DataIngestionEngine],
        audit_logger: Optional[AuditLogger] = None,
        policy_engine: Optional[EnterprisePolicyEngine] = None,
    ):
        self.config = config
        self.enterprise_api = enterprise_api
        self.research_agent = research_agent
        self.ingestion_engine = ingestion_engine
        self.audit_logger = audit_logger or AuditLogger()
        self.policy_engine = policy_engine or EnterprisePolicyEngine()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run_workflow(
        self,
        files: List[Any],
        workflow_type: str,
        auto_detect: bool = True,
        auto_execute_actions: bool = False,
        tenant_id: Optional[str] = None,
        integration_prefs: Optional[Dict[str, Any]] = None,
        webhook_url: Optional[str] = None,
        simulation_mode: bool = False,
    ) -> WorkflowResult:
        """Ejecuta un flujo autónomo de extremo a extremo."""
        # 1) Ingesta masiva con Enterprise API (análisis inicial)
        enterprise_output = self.enterprise_api.process_enterprise_documents(
            files=files,
            auto_detect=auto_detect,
            rules=None,
            stream=False,
        )

        enterprise_summary = self._build_enterprise_summary(enterprise_output, workflow_type)
        
        # Verificar si Enterprise API falló (0 chunks)
        chunks_generated = enterprise_output.get("chunks_generated", 0)
        enterprise_failed = chunks_generated == 0 or enterprise_output.get("status") == "error"
        
        if enterprise_failed:
            # Si Enterprise API falló, proporcionar contexto alternativo
            enterprise_summary = (
                f"⚠️ Enterprise API no pudo procesar los documentos completamente "
                f"(chunks generados: {chunks_generated}). "
                f"Los documentos se están ingiriendo directamente en el motor semántico para que el R&A Agent pueda trabajar con ellos. "
                f"Tipo de workflow: {workflow_type}. "
                f"Archivos recibidos: {len(files)}."
            )

        # 2) Ingestar los archivos en el motor semántico global (para uso posterior del R&A)
        doc_ids: List[str] = []
        if self.ingestion_engine is not None:
            try:
                doc_ids = self.ingestion_engine.ingest_files_from_gradio(files)
                if doc_ids:
                    enterprise_summary += f"\n✅ {len(doc_ids)} documentos ingeridos en el motor semántico para análisis del R&A Agent."
            except Exception as e:
                enterprise_summary += f"\n⚠️ Error ingiriendo documentos: {str(e)[:200]}"

        # 3) Construir prompt + modo para el Research & Action Agent
        question = self._build_research_question(workflow_type, enterprise_summary)
        mode = self._select_agent_mode(workflow_type, auto_execute_actions)

        # Ejecutar R&A Agent con mejor manejo de errores
        try:
            research_result = self.research_agent.run_query(query=question, mode=mode)
            
            # Si no hay resumen, intentar generarlo desde el resultado
            if not research_result.get("summary") or research_result.get("summary") == "(Sin resumen)":
                # Extraer información útil del resultado
                answer = research_result.get("answer", "")
                if answer and len(answer) > 50:
                    research_result["summary"] = answer[:500] + ("..." if len(answer) > 500 else "")
                else:
                    research_result["summary"] = (
                        f"Análisis completado para workflow '{workflow_type}'. "
                        f"Modo: {mode}. "
                        f"El agente procesó la información disponible y generó recomendaciones."
                    )
        except Exception as e:
            # Si el R&A Agent falla, crear un resultado básico
            research_result = {
                "summary": f"⚠️ Error ejecutando R&A Agent: {str(e)[:300]}. "
                          f"Los documentos fueron procesados pero el agente no pudo generar un análisis completo.",
                "intent": workflow_type,
                "mode": mode,
                "actions_recommended": [],
                "actions_executed": [],
                "error": str(e)[:500],
            }

        # 4) Aplicar motor de políticas y modo simulación sobre acciones recomendadas
        actions_recommended = list(research_result.get("actions_recommended", []) or [])
        actions_executed = list(research_result.get("actions_executed", []) or [])

        policy_decisions: List[Dict[str, Any]] = []
        filtered_actions: List[Dict[str, Any]] = []
        if self.policy_engine and actions_recommended:
            filtered_actions, policy_decisions = self.policy_engine.evaluate_actions(
                tenant_id=tenant_id or "default",
                workflow_type=workflow_type,
                proposed_actions=actions_recommended,
                simulation_mode=simulation_mode,
                integration_prefs=integration_prefs,
            )

        # En modo simulación nunca devolvemos acciones ejecutadas "reales"
        if simulation_mode:
            research_result["actions_executed"] = []
            research_result["simulation"] = {
                "enabled": True,
                "would_execute": filtered_actions,
                "policy_decisions": policy_decisions,
            }
        elif auto_execute_actions:
            # En ejecución real con auto_execute: ejecutar acciones aprobadas por políticas
            executed: List[Dict[str, Any]] = []
            for idx, action in enumerate(filtered_actions):
                # Enriquecer acción con metadatos de familia/tipo para trazabilidad
                enriched_action = self._enrich_action_metadata(
                    action=action,
                    workflow_type=workflow_type,
                    index=idx,
                )
                print(f"🔧 Ejecutando acción [{idx}]: {enriched_action.get('type', 'unknown')} ({enriched_action.get('family', 'unknown_family')})")
                plugin_result = self._execute_action_plugin(
                    enriched_action,
                    tenant_id=tenant_id or "default",
                    integration_prefs=integration_prefs or {},
                )
                executed.append(
                    {
                        "action": enriched_action,
                        "result": plugin_result,
                    }
                )
                if plugin_result.get("status") == "ok":
                    print(f"✅ Acción ejecutada exitosamente: {enriched_action.get('type', 'unknown')}")
                else:
                    print(f"⚠️ Acción falló: {plugin_result.get('message', 'Unknown error')}")
            
            research_result["actions_executed"] = executed
            research_result["actions_recommended"] = filtered_actions
            research_result.setdefault("policy_decisions", policy_decisions)
        else:
            # Sin auto_execute: solo mostrar recomendaciones
            enriched_actions = [
                self._enrich_action_metadata(action=a, workflow_type=workflow_type, index=i)
                for i, a in enumerate(filtered_actions)
            ]
            research_result["actions_executed"] = []
            research_result["actions_recommended"] = enriched_actions
            research_result["note"] = "Acciones no ejecutadas automáticamente. Activa 'auto_execute_actions' para ejecutarlas."

        # 5) Calcular KPIs y métricas de negocio del workflow
        workflow_kpis = self._compute_workflow_kpis(
            workflow_type=workflow_type,
            research_result=research_result,
            actions_before_policy=actions_recommended,
            actions_after_policy=filtered_actions,
            executed_actions=research_result.get("actions_executed", []),
        )
        research_result["workflow_kpis"] = workflow_kpis

        # 6) Registrar en auditoría
        self.audit_logger.log(
            event_type="enterprise_autonomous_workflow",
            action="run_workflow",
            resource=workflow_type,
            user_id=tenant_id or "system",
            metadata={
                "workflow_type": workflow_type,
                "file_count": len(files),
                "doc_ids": doc_ids,
                "auto_execute_actions": auto_execute_actions,
                "tenant_id": tenant_id,
                "integration_prefs": integration_prefs or {},
                "webhook_url": webhook_url,
                "simulation_mode": simulation_mode,
                "workflow_kpis": workflow_kpis,
            },
        )

        return WorkflowResult(
            workflow_type=workflow_type,
            enterprise_summary=enterprise_summary,
            research_result=research_result,
            logs=[
                {
                    "step": "enterprise_api",
                    "summary_excerpt": enterprise_summary[:500],
                },
                {
                    "step": "research_action_agent",
                    "intent": research_result.get("intent"),
                    "mode": research_result.get("mode"),
                    "simulation_mode": simulation_mode,
                },
                {
                    "step": "policy_engine",
                    "decisions": policy_decisions,
                },
            ],
        )

    # ------------------------------------------------------------------
    # Action plugins (Jira, ServiceNow, Slack, Email, HTTP, SQL, ERP…)
    # ------------------------------------------------------------------

    def _execute_action_plugin(
        self,
        action: Dict[str, Any],
        tenant_id: str,
        integration_prefs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Mapea una acción aprobada a un plugin concreto de integración.

        IMPORTANTE: muchas implementaciones son stubs controlados por variables
        de entorno. En producción, basta con configurar las URLs/credenciales
        y estos plugins empezarán a hablar con sistemas reales.
        """
        a_type = (action.get("type") or action.get("action_type") or "").lower()
        integration_prefs = integration_prefs or {}

        try:
            # -------------------------------
            # Action Tools de negocio (riesgo, CRM, ERP, alertas, reportes)
            # -------------------------------

            # Tickets de riesgo / incidencias
            if a_type in {"crear_ticket_riesgo", "risk_ticket"}:
                # Decidir destino según preferencias del tenant
                destino = integration_prefs.get("tickets_destination", "jira").lower()
                summary = action.get("summary") or f"[RIESGO] {action.get('titulo', 'Incidente detectado por agente')}"
                description = action.get("description") or action.get("detalle", "")
                if destino == "servicenow":
                    return servicenow_create_incident(
                        short_description=summary,
                        description=description,
                        urgency=str(action.get("urgency", "3")),
                    )
                else:
                    # default Jira
                    return jira_create_ticket(
                        project=action.get("project", integration_prefs.get("jira_project", "RISK")),
                        summary=summary,
                        description=description,
                        priority=action.get("priority", "High"),
                    )

            if a_type in {"create_ticket_jira", "jira_ticket"}:
                return jira_create_ticket(
                    project=action.get("project", "PROJ"),
                    summary=action.get("summary", "Ticket creado por agente"),
                    description=action.get("description", ""),
                    priority=action.get("priority", "Medium"),
                )
            if a_type in {"create_incident_servicenow", "servicenow_incident"}:
                return servicenow_create_incident(
                    short_description=action.get("summary", "Incidente creado por agente"),
                    description=action.get("description", ""),
                    urgency=str(action.get("urgency", "3")),
                )
            # CRM / oportunidades
            if a_type in {"crear_oportunidad_crm", "crm_opportunity"}:
                fields = action.get("fields", {})
                # Campos mínimos típicos de Opportunity
                default_fields = {
                    "Name": action.get("name") or action.get("nombre") or "Oportunidad generada por agente",
                    "StageName": fields.get("StageName", "Qualification"),
                    "CloseDate": fields.get("CloseDate"),
                    "Amount": fields.get("Amount") or action.get("monto"),
                }
                merged_fields = {**fields, **{k: v for k, v in default_fields.items() if v is not None}}
                return salesforce_create_record(
                    object_type=action.get("object_type", "Opportunity"),
                    fields=merged_fields,
                )

            # Actualización de órdenes en ERP con semántica de negocio
            if a_type in {"actualizar_estado_orden_erp", "erp_update_business"}:
                updates = action.get("updates", {})
                # Enriquecer con estado y comentarios si vienen con nombres de negocio
                if "nuevo_estado" in action and "state" not in updates:
                    updates["state"] = action["nuevo_estado"]
                if "comentario" in action and "comment" not in updates:
                    updates["comment"] = action["comentario"]
                return erp_update_order(
                    order_id=str(action.get("order_id", "")),
                    updates=updates,
                )

            # Alertas de riesgo multicanal
            if a_type in {"enviar_alerta_riesgo", "risk_alert"}:
                message = action.get("text") or action.get("message") or action.get("detalle", "")
                canal = (integration_prefs.get("alerts_channel") or action.get("canal") or "slack").lower()
                if canal == "teams":
                    return teams_send_message(text=message)
                elif canal == "email":
                    to = action.get("to") or integration_prefs.get("alerts_email_to", [])
                    if isinstance(to, str):
                        to = [to]
                    return send_email_smtp(
                        to=to,
                        subject=action.get("subject", "[DocChat] Alerta de riesgo detectada"),
                        body=message,
                        from_email=action.get("from_email"),
                    )
                else:
                    # default Slack
                    return slack_send_message(
                        channel=action.get("channel", integration_prefs.get("slack_channel", "#risk-alerts")),
                        text=message,
                    )

            if a_type in {"send_slack", "slack_alert"}:
                return slack_send_message(
                    channel=action.get("channel", "#alerts"),
                    text=action.get("text", action.get("message", "")),
                )
            if a_type in {"send_teams", "teams_alert"}:
                return teams_send_message(
                    text=action.get("text", action.get("message", "")),
                )
            if a_type in {"send_email", "email_report"}:
                to = action.get("to") or []
                if isinstance(to, str):
                    to = [to]
                return send_email_smtp(
                    to=to,
                    subject=action.get("subject", "Reporte automático DocChat"),
                    body=action.get("body", ""),
                    from_email=action.get("from_email"),
                )
            if a_type in {"http_request", "webhook_call"}:
                return http_request(
                    method=action.get("method", "POST"),
                    url=action.get("url", ""),
                    headers=action.get("headers"),
                    body=action.get("body"),
                )
            if a_type in {"write_file", "export_report"}:
                return file_writer(
                    path=action.get("path", f"exports/{tenant_id}_report.txt"),
                    content=action.get("content", ""),
                )
            if a_type in {"export_pdf", "pdf_report"}:
                return export_pdf_report(
                    file_path=action.get("path", f"exports/{tenant_id}_report.pdf"),
                    html_content=action.get("html", action.get("content", "")),
                )
            if a_type in {"sql_read"}:
                return sql_executor(
                    query=action.get("query", ""),
                    mode="read",
                )
            if a_type in {"erp_update_order"}:
                return erp_update_order(
                    order_id=str(action.get("order_id", "")),
                    updates=action.get("updates", {}),
                )
            if a_type in {"erp_get_order"}:
                return erp_get_order(order_id=str(action.get("order_id", "")))
            
            if a_type in {"salesforce_create", "crm_create"}:
                return salesforce_create_record(
                    object_type=action.get("object_type", "Account"),
                    fields=action.get("fields", {}),
                )
            
            if a_type in {"s3_upload", "upload_to_s3"}:
                return s3_upload_file(
                    bucket=action.get("bucket", ""),
                    key=action.get("key", ""),
                    content=action.get("content", ""),
                    content_type=action.get("content_type", "text/plain"),
                )

            # Acción desconocida: no ejecutar, pero registrar
            return {
                "status": "ignored",
                "reason": f"Tipo de acción desconocido o no mapeado: {a_type}",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "action_type": a_type,
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _enrich_action_metadata(
        self,
        action: Dict[str, Any],
        workflow_type: str,
        index: int,
    ) -> Dict[str, Any]:
        """
        Enriquecimiento ligero de acciones con:
        - family: acción / datos / política / hitl / observabilidad / plantilla / negocio / auto_mejora
        - workflow_type: contexto del flujo
        - index: orden dentro del workflow
        """
        enriched = dict(action)
        a_type = (enriched.get("type") or enriched.get("action_type") or "").lower()

        # Heurística de familia por tipo
        if any(k in a_type for k in ["ticket", "incident", "alert", "email", "erp", "crm", "s3", "pdf"]):
            family = "action"
        elif any(k in a_type for k in ["sql", "compare", "reconcile", "anomaly", "buscar_contrato", "data_"]):
            family = "data_intel"
        elif any(k in a_type for k in ["policy", "evaluar_monto", "clasificar_riesgo", "jsonschema"]):
            family = "policy_guardrails"
        elif any(k in a_type for k in ["aprobacion_humana", "feedback_humano", "clarificacion", "outcome"]):
            family = "human_in_the_loop"
        elif any(k in a_type for k in ["log_", "kpi_", "metric", "workflow_trace"]):
            family = "observability"
        elif any(k in a_type for k in ["tool_", "mcp_", "a2a_", "optimizar_tool"]):
            family = "tooling_mcp_a2a"
        elif any(k in a_type for k in ["workflow_", "plantilla_workflow"]):
            family = "workflow_template"
        elif any(k in a_type for k in ["roi", "ahorro", "ingreso_incremental"]):
            family = "business_kpi"
        elif any(k in a_type for k in ["auto_mejora", "prompt_tuning", "sandbox"]):
            family = "auto_improvement"
        else:
            family = enriched.get("family", "unknown")

        enriched.setdefault("family", family)
        enriched.setdefault("workflow_type", workflow_type)
        enriched.setdefault("index", index)
        return enriched

    def _compute_workflow_kpis(
        self,
        workflow_type: str,
        research_result: Dict[str, Any],
        actions_before_policy: List[Dict[str, Any]],
        actions_after_policy: List[Dict[str, Any]],
        executed_actions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        KPIs básicos de Enterprise Autonomous Workflows:
        - total_actions_recommended
        - total_actions_approved_by_policy
        - total_actions_executed
        - by_family: conteos por tipo (action, data_intel, policy_guardrails, etc.)
        - estimated_savings/impact placeholders para ROI (calculados de forma simple)
        """
        kpis: Dict[str, Any] = {
            "workflow_type": workflow_type,
            "total_actions_recommended": len(actions_before_policy),
            "total_actions_approved_by_policy": len(actions_after_policy),
            "total_actions_executed": len(executed_actions),
        }

        # Conteos por familia
        def _family_counts(actions: List[Dict[str, Any]]) -> Dict[str, int]:
            counts: Dict[str, int] = {}
            for a in actions:
                family = (a.get("family") or "").lower() or "unknown"
                counts[family] = counts.get(family, 0) + 1
            return counts

        kpis["approved_by_family"] = _family_counts(actions_after_policy)
        kpis["executed_by_family"] = _family_counts(
            [ae.get("action", {}) for ae in executed_actions]
        )

        # Estimaciones de impacto muy simples (placeholders)
        # Estas fórmulas se pueden reemplazar por modelos/heurísticas más avanzadas.
        risk_actions = kpis["executed_by_family"].get("action", 0)
        data_actions = kpis["executed_by_family"].get("data_intel", 0)

        kpis["estimated_time_saved_minutes"] = int(
            5 * kpis["total_actions_executed"]  # asumimos 5 minutos manuales por acción
        )
        kpis["estimated_incidents_prevented"] = int(risk_actions * 0.3)
        kpis["estimated_data_issues_resolved"] = int(data_actions * 0.5)

        # ROI placeholder (en dinero ficticio) para storytelling empresarial
        kpis["estimated_savings_usd"] = int(
            kpis["estimated_incidents_prevented"] * 200
            + kpis["estimated_data_issues_resolved"] * 50
        )

        return kpis

    def _build_enterprise_summary(self, enterprise_output: Dict[str, Any], workflow_type: str) -> str:
        """Construye un resumen compacto del resultado de Enterprise API."""
        parts: List[str] = []
        status = enterprise_output.get("status", "unknown")
        docs = enterprise_output.get("documents_processed", enterprise_output.get("documents_processed", 0))
        chunks = enterprise_output.get("chunks_generated", 0)

        # Información básica
        if status == "error" or chunks == 0:
            parts.append(f"⚠️ Estado del análisis inicial: {status}")
            parts.append(f"Documentos recibidos: {docs}, chunks generados: {chunks}")
            parts.append("")
            parts.append("💡 Nota: El sistema intentará procesar los documentos directamente con el R&A Agent.")
            
            # Si hay mensaje de error, incluirlo
            error_msg = enterprise_output.get("error") or enterprise_output.get("message")
            if error_msg:
                parts.append(f"Detalle del error: {str(error_msg)[:300]}")
        else:
            parts.append(f"✅ Estado del análisis inicial: {status}")
            parts.append(f"Documentos procesados: {docs}, chunks generados: {chunks}")

        summaries = enterprise_output.get("summaries", {}) or {}
        if summaries:
            parts.append("")
            parts.append("📄 Resúmenes generados:")
            # Tomar algunos resúmenes
            for i, (name, summary) in enumerate(summaries.items()):
                if i >= 5:
                    break
                stext = summary.get("summary") or ""
                if stext:
                    parts.append(f"- {Path(name).name}: {stext[:300]}...")

        problems = enterprise_output.get("problems_detected") or []
        if problems:
            parts.append("")
            parts.append("⚠️ Problemas detectados:")
            for p in problems[:5]:
                parts.append(f"- {p.get('type', 'Issue')}: {p.get('description', '')[:200]}")

        opportunities = enterprise_output.get("opportunities_detected") or []
        if opportunities:
            parts.append("")
            parts.append("💡 Oportunidades detectadas:")
            for o in opportunities[:3]:
                parts.append(f"- {o.get('type', 'Opportunity')}: {o.get('description', '')[:200]}")

        return "\n".join(parts) if parts else "No hay información disponible del análisis inicial."

    def _select_agent_mode(self, workflow_type: str, auto_execute_actions: bool) -> str:
        """Elige el modo del R&A Agent según el caso de uso."""
        # Casos donde queremos búsqueda profunda en grafo + reasoning avanzado
        deep_search_workflows = {
            "auditoria_contratos",
            "contract_intelligence",
            "compliance_normativo",
            "compliance_reportes",
        }
        # Casos fuertemente operativos donde interesa acción agentic
        advanced_workflows = {
            "fraude_facturas",
            "ap_automation",
            "aprobacion_pagos",
            "conciliacion_sistemas",
            "alertas_riesgo",
            "workflow_multisistema",
        }

        if workflow_type in deep_search_workflows:
            # Profundizar en grafos y evidencia (GraphRAG / Deep Search)
            return "deep_search"
        if workflow_type in advanced_workflows:
            # Orquestación y acciones cross-sistema
            return "advanced"
        # Fallback: respetar preferencia de auto-acciones
        return "advanced" if auto_execute_actions else "manual"

    def _build_research_question(self, workflow_type: str, enterprise_summary: str) -> str:
        """Crea el prompt para el Research & Action Agent según el caso de uso."""
        base = (
            "Eres el Research & Action Agent de DocChat Enterprise. "
            "Ya se ejecutó el modo Enterprise API y a continuación tienes un resumen "
            "del análisis inicial (resúmenes, problemas detectados, patrones):\n\n"
            f"{enterprise_summary}\n\n"
            "Tu misión ahora es ejecutar un workflow AGENTIC completo: investigar profundo, "
            "conectar evidencia, tomar decisiones y disparar acciones usando las herramientas "
            "enterprise disponibles (tickets, email, Slack, ERP, SQL, reportes PDF, webhooks, etc.).\n\n"
        )

        # FINANZAS: fraude, AP, pagos, conciliación
        if workflow_type in {"fraude_facturas", "facturas", "ap_automation"}:
            extra = (
                "FOCO: Toma de decisiones financieras sobre facturas y pagos.\n"
                "- Detecta fraude en facturas, duplicados, importes anómalos, cambios en cuentas bancarias y patrones sospechosos.\n"
                "- Señala excepciones de pago y propone si se deben aprobar, frenar o escalar.\n"
                "- Sugiere aprobaciones automáticas basadas en reglas claras (montos, proveedores confiables, límites de riesgo).\n"
                "- Si tu análisis lo justifica, crea tickets en sistemas de incidencias, envía alertas por email/Slack "
                "y genera un reporte PDF ejecutivo con los casos críticos.\n"
                "Devuelve un JSON estructurado con: summary, riesgos_detectados, facturas_sospechosas, "
                "pagos_recomendados, acciones_recomendadas y acciones_ejecutadas."
            )
        elif workflow_type in {"aprobacion_pagos"}:
            extra = (
                "FOCO: Aprobación automática de pagos bajo reglas de negocio.\n"
                "- Clasifica los pagos en: aprobar_auto, revisar_manual, rechazar.\n"
                "- Usa evidencia de contratos, órdenes de compra y facturas para justificar cada decisión.\n"
                "- Aplica reglas de límites por monto, proveedor, país, riesgo y tipo de gasto.\n"
                "- Donde sea seguro, prepara acciones para actualizar ERP/finanzas y notificar por email/Slack "
                "a los responsables.\n"
                "Devuelve un JSON con: summary, pagos_auto_aprobados, pagos_en_revision, pagos_rechazados, "
                "reglas_aplicadas y acciones_recomendadas."
            )
        elif workflow_type in {"conciliacion_sistemas"}:
            extra = (
                "FOCO: Conciliación de datos entre sistemas (ERP, CRM, billing, etc.).\n"
                "- Identifica desajustes entre lo que indican los documentos (facturas, contratos, reportes) "
                "y lo que normalmente debería existir en los sistemas.\n"
                "- Clasifica diferencias en: menores, relevantes, críticas.\n"
                "- Propone qué actualizaciones harías en ERP/CRM (sin ejecutarlas a menos que se confirme) "
                "y qué tickets/alertas deberías levantar.\n"
                "Devuelve un JSON con: summary, diferencias_detectadas, impacto_estimado, "
                "acciones_sugeridas_sobre_sistemas y acciones_ejecutadas."
            )

        # COMPLIANCE REAL: legal + normativo
        elif workflow_type in {"compliance", "compliance_normativo", "compliance_reportes"}:
            extra = (
                "FOCO: Cumplimiento normativo real (leyes locales, regulaciones sectoriales, políticas internas).\n"
                "- Verifica si los contratos y documentos cumplen con normas clave (laborales, financieras, "
                "protección de datos, consumidor, sectoriales, etc.).\n"
                "- Detecta cláusulas ilegales, abusivas o con riesgo elevado.\n"
                "- Mapea cada hallazgo a un checklist normativo (por ejemplo: GDPR, SOX, HIPAA, regulaciones locales, etc.).\n"
                "- Genera un pre-informe formal para auditoría/regulador con: marco normativo, evidencias, riesgos y recomendaciones.\n"
                "Devuelve un JSON con: summary, marco_normativo, clausulas_riesgosas, brechas_cumplimiento, "
                "checklist_evidencia y acciones_recomendadas (incluyendo tickets, alertas y reportes)."
            )

        # RIESGO Y ALERTAS CRÍTICAS
        elif workflow_type in {"risk_scan", "alertas_riesgo"}:
            extra = (
                "FOCO: Evaluación de riesgo integral (legal, financiero, operativo, reputacional).\n"
                "- Usa lógica de risk scoring: asigna un score 0-100 y una categoría (bajo, medio, alto, crítico).\n"
                "- Identifica los principales drivers de riesgo (cláusulas, importes, plazos, jurisdicciones, contrapartes).\n"
                "- Si el riesgo es alto o crítico, genera plan de acción: tickets, alertas y tareas de seguimiento.\n"
                "Devuelve un JSON con: summary, risk_score, risk_category, drivers, alertas_criticas, "
                "acciones_recomendadas y acciones_ejecutadas."
            )

        # AUDITORÍA DE CONTRATOS (Contract Intelligence)
        elif workflow_type in {"auditoria_contratos", "contract_intelligence"}:
            extra = (
                "FOCO: Auditoría automática de contratos (Contract Intelligence).\n"
                "- Extrae cláusulas clave: precio, plazos, renovaciones, terminación, penalidades, SLAs, jurisdicción, data, confidencialidad.\n"
                "- Compara contra una 'plantilla ideal' implícita y marca desviaciones importantes.\n"
                "- Señala oportunidades de renegociación (precio, plazos, volumen mínimo, exclusividades, etc.).\n"
                "- Prepara un resumen ejecutivo por contrato y un dashboard agregado para dirección.\n"
                "Devuelve un JSON con: summary_global, contratos_resumidos, clausulas_clave, "
                "desviaciones_relevantes, oportunidades_renegociacion y acciones_recomendadas."
            )

        # WORKFLOW INTER-SISTEMAS / MULTIPLATAFORMA
        elif workflow_type in {"workflow_multisistema"}:
            extra = (
                "FOCO: Workflow inter-sistemas (multiplataforma).\n"
                "- A partir de los documentos y del análisis inicial, detecta problemas u oportunidades.\n"
                "- Diseña un flujo de acciones entre sistemas: crear tickets (Jira/ServiceNow), actualizar CRM, "
                "modificar ERP, enviar correos, mandar mensajes a Slack/Teams, mover archivos a S3, "
                "generar reportes PDF y programar tareas futuras.\n"
                "- Clasifica acciones en: seguras_auto, requieren_aprobacion, solo_recomendadas.\n"
                "Devuelve un JSON con: summary, problemas_oportunidades, plan_workflow, "
                "acciones_seguras, acciones_requieren_aprobacion y acciones_ejecutadas."
            )

        # GENERAL / FALLBACK
        else:
            extra = (
                "FOCO: Análisis ejecutivo general.\n"
                "- Identifica riesgos, oportunidades y próximos pasos recomendados.\n"
                "- Propón tickets, alertas, cambios en sistemas y reportes que aportarían más valor al negocio.\n"
                "Devuelve un JSON con: summary, riesgos, oportunidades, acciones_recomendadas y acciones_ejecutadas."
            )

        return base + "\n\n" + extra


__all__ = ["EnterpriseAutonomousWorkflows", "WorkflowResult"]


