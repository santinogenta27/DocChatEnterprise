"""
Agent Builder Mode - Modo para construir agentes con drag-and-drop
Basado en principios de OpenAI, Notion, Google y mejores prácticas
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
import gradio as gr

from .config import AppConfig
from .agent_builder.orchestrator import AgentOrchestrator, AgentIdentity, AgentStatus
from .agent_builder.workflow_builder import WorkflowBuilder


class AgentBuilderMode:
    """Modo Agent Builder con UI drag-and-drop"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.orchestrator = AgentOrchestrator(config)
        self.workflow_builder = WorkflowBuilder(self.orchestrator)
    
    def create_ui(self) -> gr.Blocks:
        """Crea la UI del Agent Builder"""
        with gr.Blocks(title="🤖 Agent Builder", theme=gr.themes.Soft()) as ui:
            gr.Markdown("""
            # 🤖 Agent Builder - Construye Agentes con Drag-and-Drop
            
            **Principios aplicados:**
            - ✅ Stateful Intelligence (preserva contexto)
            - ✅ Bounded Uncertainty (determinismo)
            - ✅ Fail Fast Design (detección inteligente)
            - ✅ Capability-based Routing (enrutar por complejidad)
            - ✅ Continuous Validation (validar en cada paso)
            - ✅ Full Auditability (trazabilidad completa)
            
            **Mejores prácticas:**
            - Usa agentes "tontos" con contexto claro
            - Múltiples agentes pequeños > un agente súper inteligente
            - Diseña para el resultado primero
            - Prompts sin ambigüedad
            """)
            
            with gr.Tabs():
                # Tab 1: Registrar Agentes
                with gr.Tab("👤 Registrar Agentes"):
                    gr.Markdown("### Registra agentes como identidades de primera clase")
                    
                    agent_name = gr.Textbox(label="Nombre del Agente")
                    agent_role = gr.Textbox(label="Rol (ej: 'Document Analyzer', 'Data Extractor')")
                    agent_persona = gr.Textbox(label="Persona", lines=3, placeholder="Descripción de cómo debe comportarse")
                    agent_budget = gr.Number(1000.0, label="Presupuesto (tokens/costos)")
                    agent_policies = gr.Textbox(label="Políticas (una por línea)", lines=3)
                    register_btn = gr.Button("✅ Registrar Agente", variant="primary")
                    agent_output = gr.JSON(label="Agente Registrado")
                    
                    def register_agent(name, role, persona, budget, policies):
                        policies_list = [p.strip() for p in policies.split("\n") if p.strip()]
                        agent = self.orchestrator.register_agent(
                            name=name,
                            role=role,
                            persona=persona,
                            budget=float(budget),
                            policies=policies_list
                        )
                        return {
                            "agent_id": agent.agent_id,
                            "name": agent.name,
                            "role": agent.role,
                            "status": "registered"
                        }
                    
                    register_btn.click(
                        register_agent,
                        [agent_name, agent_role, agent_persona, agent_budget, agent_policies],
                        agent_output
                    )
                
                # Tab 2: Construir Workflow
                with gr.Tab("🔧 Construir Workflow"):
                    gr.Markdown("### Crea workflows con múltiples agentes")
                    
                    workflow_name = gr.Textbox(label="Nombre del Workflow")
                    workflow_desc = gr.Textbox(label="Descripción", lines=2)
                    
                    # Configuración de nodos (simplificado para UI)
                    nodes_json = gr.Textbox(
                        label="Nodos (JSON)",
                        lines=10,
                        placeholder='''[
  {
    "node_id": "node_1",
    "agent_id": "agent_123",
    "task": "Extraer información de documento",
    "input_sources": [],
    "output_targets": ["node_2"],
    "tools": ["mcp_document_reader"],
    "temperature": 0.0,
    "max_tokens": 2000
  },
  {
    "node_id": "node_2",
    "agent_id": "agent_456",
    "task": "Procesar información extraída",
    "input_sources": ["node_1"],
    "output_targets": [],
    "tools": [],
    "temperature": 0.0,
    "max_tokens": 2000
  }
]'''
                    )
                    
                    create_workflow_btn = gr.Button("🚀 Crear Workflow", variant="primary")
                    workflow_output = gr.JSON(label="Workflow Creado")
                    
                    def create_workflow(name, desc, nodes_str):
                        try:
                            nodes = json.loads(nodes_str)
                            workflow = self.workflow_builder.create_workflow_from_ui(
                                name=name,
                                description=desc,
                                nodes=nodes
                            )
                            return {
                                "workflow_id": workflow.workflow_id,
                                "name": workflow.name,
                                "nodes_count": len(workflow.nodes),
                                "status": "created"
                            }
                        except Exception as e:
                            return {"error": str(e)}
                    
                    create_workflow_btn.click(
                        create_workflow,
                        [workflow_name, workflow_desc, nodes_json],
                        workflow_output
                    )
                
                # Tab 3: Ejecutar Workflow
                with gr.Tab("▶️ Ejecutar Workflow"):
                    gr.Markdown("### Ejecuta workflows con validación continua")
                    
                    workflow_id_exec = gr.Textbox(label="Workflow ID")
                    initial_input = gr.Textbox(
                        label="Input Inicial (JSON)",
                        lines=5,
                        placeholder='{"document_path": "/path/to/doc.pdf", "task": "extract data"}'
                    )
                    validate_continuous = gr.Checkbox(True, label="Validación Continua")
                    execute_btn = gr.Button("▶️ Ejecutar", variant="primary")
                    execution_output = gr.JSON(label="Resultado de Ejecución")
                    
                    def execute_workflow(wf_id, input_str, validate):
                        try:
                            initial_data = json.loads(input_str) if input_str else {}
                            import asyncio
                            trace = asyncio.run(self.orchestrator.execute_workflow(
                                workflow_id=wf_id,
                                initial_input=initial_data,
                                validate_continuously=validate
                            ))
                            return {
                                "trace_id": trace.trace_id,
                                "nodes_executed": trace.nodes_executed,
                                "quality_score": trace.quality_score,
                                "errors": len(trace.errors),
                                "warnings": len(trace.warnings),
                                "duration": trace.end_time - trace.start_time if trace.end_time else None
                            }
                        except Exception as e:
                            return {"error": str(e)}
                    
                    execute_btn.click(
                        execute_workflow,
                        [workflow_id_exec, initial_input, validate_continuous],
                        execution_output
                    )
                
                # Tab 4: Monitoring y Auditabilidad
                with gr.Tab("📊 Monitoring"):
                    gr.Markdown("### Estado de salud y auditabilidad")
                    
                    workflow_id_monitor = gr.Textbox(label="Workflow ID")
                    monitor_btn = gr.Button("📊 Obtener Estado", variant="primary")
                    health_output = gr.JSON(label="Estado de Salud")
                    
                    trace_id = gr.Textbox(label="Trace ID (para auditoría)")
                    audit_btn = gr.Button("🔍 Ver Traza Completa", variant="secondary")
                    audit_output = gr.JSON(label="Traza de Auditoría")
                    
                    def get_health(wf_id):
                        health = self.orchestrator.get_workflow_health(wf_id)
                        return health
                    
                    def get_audit(t_id):
                        trace = self.orchestrator.get_audit_trace(t_id)
                        if trace:
                            return {
                                "trace_id": trace.trace_id,
                                "workflow_id": trace.workflow_id,
                                "nodes_executed": trace.nodes_executed,
                                "errors": trace.errors,
                                "warnings": trace.warnings,
                                "quality_score": trace.quality_score,
                                "duration": trace.end_time - trace.start_time if trace.end_time else None
                            }
                        return {"error": "Trace no encontrado"}
                    
                    monitor_btn.click(get_health, workflow_id_monitor, health_output)
                    audit_btn.click(get_audit, trace_id, audit_output)
            
            return ui

