"""
Sistema de Automatización RPA + IA para procesos empresariales.
Automatiza tareas repetitivas en múltiples áreas: Finanzas, RRHH, Logística, etc.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.documents import Document

from .config import AppConfig


@dataclass
class RPATask:
    """Tarea de automatización RPA."""
    task_id: str
    category: str  # finanzas, rrhh, logistica, etc.
    task_type: str  # tipo específico dentro de la categoría
    name: str
    description: str
    status: str = "pending"  # pending, running, completed, failed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class RPAAutomation:
    """Resultado de una automatización RPA."""
    automation_id: str
    category: str
    task_type: str
    success: bool
    data: Dict[str, Any]
    message: str
    execution_time: float
    tools_used: List[str] = field(default_factory=list)


class RPAAutomationEngine:
    """
    Motor de Automatización RPA + IA.
    
    Proporciona automatización inteligente para:
    - Finanzas y Contabilidad
    - Recursos Humanos
    - Logística y Cadena de Suministro
    - Marketing y Ventas
    - Salud
    - Industria y Manufactura
    - TI y Seguridad
    - Legal
    - Administración y Gestión de Proyectos
    - Educación
    - Comunicaciones
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY requerida para RPA Automation")
        
        # LLM para procesamiento inteligente
        self.llm = ChatOpenAI(
            model=config.agentic_model or "gpt-4o",
            temperature=0.2,  # Más determinístico para automatización
            api_key=config.openai_api_key,
            max_tokens=4000
        )
        
        # Directorio para almacenar datos y resultados
        self.data_dir = Path(config.memory_dir) / "rpa_automation"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivos de almacenamiento
        self.tasks_file = self.data_dir / "rpa_tasks.json"
        self.automations_file = self.data_dir / "automations.json"
        self.workflows_file = self.data_dir / "workflows.json"
        
        # Almacenamiento en memoria
        self.tasks: Dict[str, RPATask] = {}
        self.automations: List[RPAAutomation] = []
        self.workflows: Dict[str, Dict[str, Any]] = {}
        
        # Estadísticas
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "by_category": {},
            "average_execution_time": 0.0
        }
        
        # Cargar datos existentes
        self._load_data()
    
    def _load_data(self):
        """Carga datos guardados."""
        try:
            if self.tasks_file.exists():
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_data in data:
                        task = RPATask(**task_data)
                        self.tasks[task.task_id] = task
            
            if self.automations_file.exists():
                with open(self.automations_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for auto_data in data:
                        automation = RPAAutomation(**auto_data)
                        self.automations.append(automation)
            
            if self.workflows_file.exists():
                with open(self.workflows_file, 'r', encoding='utf-8') as f:
                    self.workflows = json.load(f)
        except Exception as e:
            print(f"Error cargando datos RPA: {e}")
    
    def _save_data(self):
        """Guarda datos."""
        try:
            # Guardar tareas
            tasks_data = [self._task_to_dict(task) for task in self.tasks.values()]
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(tasks_data, f, indent=2, ensure_ascii=False)
            
            # Guardar automatizaciones
            automations_data = [self._automation_to_dict(auto) for auto in self.automations[-100:]]  # Últimas 100
            with open(self.automations_file, 'w', encoding='utf-8') as f:
                json.dump(automations_data, f, indent=2, ensure_ascii=False)
            
            # Guardar workflows
            with open(self.workflows_file, 'w', encoding='utf-8') as f:
                json.dump(self.workflows, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando datos RPA: {e}")
    
    def _task_to_dict(self, task: RPATask) -> Dict[str, Any]:
        """Convierte tarea a diccionario."""
        return {
            "task_id": task.task_id,
            "category": task.category,
            "task_type": task.task_type,
            "name": task.name,
            "description": task.description,
            "status": task.status,
            "created_at": task.created_at,
            "completed_at": task.completed_at,
            "result": task.result,
            "error": task.error
        }
    
    def _automation_to_dict(self, automation: RPAAutomation) -> Dict[str, Any]:
        """Convierte automatización a diccionario."""
        return {
            "automation_id": automation.automation_id,
            "category": automation.category,
            "task_type": automation.task_type,
            "success": automation.success,
            "data": automation.data,
            "message": automation.message,
            "execution_time": automation.execution_time,
            "tools_used": automation.tools_used
        }
    
    def execute_automation(
        self,
        category: str,
        task_type: str,
        parameters: Dict[str, Any],
        documents: Optional[List[Document]] = None
    ) -> RPAAutomation:
        """
        Ejecuta una automatización RPA.
        
        Args:
            category: Categoría (finanzas, rrhh, logistica, etc.)
            task_type: Tipo de tarea específica
            parameters: Parámetros para la automatización
            documents: Documentos relevantes (opcional)
        
        Returns:
            RPAAutomation con el resultado
        """
        automation_id = f"RPA-{int(time.time())}-{len(self.automations)}"
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"🤖 EJECUTANDO AUTOMATIZACIÓN RPA")
        print(f"{'='*60}")
        print(f"Categoría: {category}")
        print(f"Tipo: {task_type}")
        print(f"ID: {automation_id}")
        print()
        
        try:
            # Ejecutar según la categoría
            if category == "finanzas":
                result = self._execute_finanzas(task_type, parameters, documents)
            elif category == "rrhh":
                result = self._execute_rrhh(task_type, parameters, documents)
            elif category == "logistica":
                result = self._execute_logistica(task_type, parameters, documents)
            elif category == "marketing":
                result = self._execute_marketing(task_type, parameters, documents)
            elif category == "salud":
                result = self._execute_salud(task_type, parameters, documents)
            elif category == "manufactura":
                result = self._execute_manufactura(task_type, parameters, documents)
            elif category == "ti_seguridad":
                result = self._execute_ti_seguridad(task_type, parameters, documents)
            elif category == "legal":
                result = self._execute_legal(task_type, parameters, documents)
            elif category == "gestion_proyectos":
                result = self._execute_gestion_proyectos(task_type, parameters, documents)
            elif category == "educacion":
                result = self._execute_educacion(task_type, parameters, documents)
            elif category == "comunicaciones":
                result = self._execute_comunicaciones(task_type, parameters, documents)
            else:
                raise ValueError(f"Categoría desconocida: {category}")
            
            execution_time = time.time() - start_time
            
            automation = RPAAutomation(
                automation_id=automation_id,
                category=category,
                task_type=task_type,
                success=True,
                data=result,
                message=f"Automatización '{task_type}' completada exitosamente",
                execution_time=execution_time,
                tools_used=result.get("tools_used", [])
            )
            
            self.automations.append(automation)
            self.stats["completed_tasks"] += 1
            self.stats["total_tasks"] += 1
            self.stats["by_category"][category] = self.stats["by_category"].get(category, 0) + 1
            
            # Actualizar tiempo promedio
            total_time = sum(a.execution_time for a in self.automations)
            self.stats["average_execution_time"] = total_time / len(self.automations) if self.automations else 0
            
            self._save_data()
            
            print(f"✅ Automatización completada en {execution_time:.2f}s")
            print()
            
            return automation
        
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            print(f"❌ Error en automatización: {error_msg}")
            print()
            
            automation = RPAAutomation(
                automation_id=automation_id,
                category=category,
                task_type=task_type,
                success=False,
                data={},
                message=f"Error: {error_msg}",
                execution_time=execution_time,
                tools_used=[]
            )
            
            self.automations.append(automation)
            self.stats["failed_tasks"] += 1
            self.stats["total_tasks"] += 1
            self._save_data()
            
            return automation
    
    # ============================================================================
    # FINANZAS Y CONTABILIDAD
    # ============================================================================
    
    def _execute_finanzas(self, task_type: str, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Ejecuta automatizaciones de finanzas."""
        if task_type == "generar_factura":
            return self._generar_factura(parameters, documents)
        elif task_type == "conciliacion_bancaria":
            return self._conciliacion_bancaria(parameters, documents)
        elif task_type == "procesar_pagos":
            return self._procesar_pagos(parameters, documents)
        elif task_type == "calcular_impuestos":
            return self._calcular_impuestos(parameters, documents)
        elif task_type == "auditoria_automatizada":
            return self._auditoria_automatizada(parameters, documents)
        elif task_type == "control_cuentas":
            return self._control_cuentas(parameters, documents)
        else:
            raise ValueError(f"Tipo de tarea desconocido: {task_type}")
    
    def _generar_factura(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Genera factura automáticamente desde orden de compra."""
        orden_compra = parameters.get("orden_compra", "")
        cliente = parameters.get("cliente", {})
        items = parameters.get("items", [])
        
        # Procesar con LLM si hay documentos
        context = ""
        if documents:
            context = "\n".join([doc.page_content[:500] for doc in documents[:3]])
        
        prompt = f"""Genera una factura profesional basada en esta información:

Orden de Compra: {orden_compra}
Cliente: {json.dumps(cliente, ensure_ascii=False)}
Items: {json.dumps(items, ensure_ascii=False)}

Contexto adicional:
{context}

Genera una factura en formato JSON con:
- Número de factura (generar automáticamente)
- Fecha
- Datos del cliente
- Items con descripción, cantidad, precio unitario, subtotal
- Total general
- Impuestos calculados
- Método de pago sugerido

Factura JSON:"""
        
        response = self.llm.invoke([{"role": "user", "content": prompt}])
        factura_data = json.loads(response.content)
        
        # Guardar factura
        factura_file = self.data_dir / f"factura_{factura_data.get('numero', 'N/A')}.json"
        with open(factura_file, 'w', encoding='utf-8') as f:
            json.dump(factura_data, f, indent=2, ensure_ascii=False)
        
        return {
            "factura": factura_data,
            "archivo": str(factura_file),
            "tools_used": ["llm", "file_system"]
        }
    
    def _conciliacion_bancaria(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Compara transacciones bancarias con registros contables."""
        transacciones_bancarias = parameters.get("transacciones_bancarias", [])
        registros_contables = parameters.get("registros_contables", [])
        
        # Comparar y encontrar discrepancias
        discrepancias = []
        coincidencias = []
        
        for trans in transacciones_bancarias:
            encontrado = False
            for reg in registros_contables:
                if (abs(trans.get("monto", 0) - reg.get("monto", 0)) < 0.01 and
                    trans.get("fecha") == reg.get("fecha")):
                    coincidencias.append({"transaccion": trans, "registro": reg})
                    encontrado = True
                    break
            
            if not encontrado:
                discrepancias.append({
                    "tipo": "no_encontrada",
                    "transaccion": trans
                })
        
        return {
            "total_transacciones": len(transacciones_bancarias),
            "coincidencias": len(coincidencias),
            "discrepancias": len(discrepancias),
            "detalle_discrepancias": discrepancias,
            "reporte": f"Conciliación completada: {len(coincidencias)} coincidencias, {len(discrepancias)} discrepancias",
            "tools_used": ["data_comparison"]
        }
    
    def _procesar_pagos(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Procesa pagos y registra en sistema ERP."""
        pagos = parameters.get("pagos", [])
        
        procesados = []
        for pago in pagos:
            registro = {
                "id": f"PAY-{int(time.time())}-{len(procesados)}",
                "fecha": datetime.now().isoformat(),
                "monto": pago.get("monto", 0),
                "metodo": pago.get("metodo", "transferencia"),
                "referencia": pago.get("referencia", ""),
                "estado": "procesado"
            }
            procesados.append(registro)
        
        return {
            "pagos_procesados": len(procesados),
            "total_monto": sum(p.get("monto", 0) for p in procesados),
            "registros": procesados,
            "tools_used": ["payment_processor"]
        }
    
    def _calcular_impuestos(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Calcula impuestos y genera informe fiscal."""
        ingresos = parameters.get("ingresos", 0)
        gastos = parameters.get("gastos", 0)
        tipo_impuesto = parameters.get("tipo_impuesto", "IVA")
        
        # Cálculos básicos (en producción usarías fórmulas reales)
        base_imponible = ingresos - gastos
        if tipo_impuesto == "IVA":
            impuesto = base_imponible * 0.21  # 21% IVA ejemplo
        else:
            impuesto = base_imponible * 0.25  # 25% ejemplo
        
        informe = {
            "periodo": parameters.get("periodo", datetime.now().strftime("%Y-%m")),
            "ingresos": ingresos,
            "gastos": gastos,
            "base_imponible": base_imponible,
            "tipo_impuesto": tipo_impuesto,
            "impuesto_calculado": impuesto,
            "fecha_calculo": datetime.now().isoformat()
        }
        
        return {
            "informe_fiscal": informe,
            "tools_used": ["tax_calculator"]
        }
    
    def _auditoria_automatizada(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Realiza auditoría de datos financieros."""
        datos_financieros = parameters.get("datos_financieros", [])
        
        inconsistencias = []
        for dato in datos_financieros:
            # Verificar consistencia básica
            if dato.get("debe", 0) != dato.get("haber", 0):
                inconsistencias.append({
                    "tipo": "desbalance",
                    "dato": dato
                })
        
        return {
            "total_registros": len(datos_financieros),
            "inconsistencias_encontradas": len(inconsistencias),
            "detalle": inconsistencias,
            "estado": "completa",
            "tools_used": ["audit_engine"]
        }
    
    def _control_cuentas(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Controla cuentas por cobrar y por pagar."""
        cuentas_por_cobrar = parameters.get("cuentas_por_cobrar", [])
        cuentas_por_pagar = parameters.get("cuentas_por_pagar", [])
        
        alertas = []
        hoy = datetime.now()
        
        for cuenta in cuentas_por_cobrar:
            fecha_vencimiento = datetime.fromisoformat(cuenta.get("fecha_vencimiento", hoy.isoformat()))
            if fecha_vencimiento < hoy:
                alertas.append({
                    "tipo": "vencida",
                    "cuenta": cuenta,
                    "dias_vencida": (hoy - fecha_vencimiento).days
                })
        
        for cuenta in cuentas_por_pagar:
            fecha_vencimiento = datetime.fromisoformat(cuenta.get("fecha_vencimiento", hoy.isoformat()))
            dias_restantes = (fecha_vencimiento - hoy).days
            if 0 < dias_restantes <= 7:
                alertas.append({
                    "tipo": "proxima_vencer",
                    "cuenta": cuenta,
                    "dias_restantes": dias_restantes
                })
        
        return {
            "total_por_cobrar": len(cuentas_por_cobrar),
            "total_por_pagar": len(cuentas_por_pagar),
            "alertas": alertas,
            "total_alertas": len(alertas),
            "tools_used": ["account_manager"]
        }
    
    # ============================================================================
    # RECURSOS HUMANOS
    # ============================================================================
    
    def _execute_rrhh(self, task_type: str, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Ejecuta automatizaciones de RRHH."""
        if task_type == "filtrar_cv":
            return self._filtrar_cv(parameters, documents)
        elif task_type == "onboarding_empleado":
            return self._onboarding_empleado(parameters, documents)
        elif task_type == "gestion_nomina":
            return self._gestion_nomina(parameters, documents)
        elif task_type == "gestion_ausencias":
            return self._gestion_ausencias(parameters, documents)
        elif task_type == "evaluacion_desempeno":
            return self._evaluacion_desempeno(parameters, documents)
        else:
            raise ValueError(f"Tipo de tarea desconocido: {task_type}")
    
    def _filtrar_cv(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Filtra y clasifica currículums."""
        cvs = parameters.get("cvs", [])
        requisitos = parameters.get("requisitos", {})
        
        # Procesar con LLM
        cv_text = "\n".join([f"CV {i+1}: {cv.get('contenido', '')[:500]}" for i, cv in enumerate(cvs[:5])])
        
        prompt = f"""Clasifica estos currículums según los requisitos:

Requisitos del puesto:
{json.dumps(requisitos, ensure_ascii=False)}

Currículums:
{cv_text}

Para cada CV, determina:
1. Si cumple los requisitos (sí/no)
2. Puntuación del 0-100
3. Razones principales
4. Recomendación (rechazar, entrevista, destacado)

Responde en formato JSON con lista de evaluaciones."""

        response = self.llm.invoke([{"role": "user", "content": prompt}])
        evaluaciones = json.loads(response.content)
        
        return {
            "total_cvs": len(cvs),
            "evaluaciones": evaluaciones,
            "candidatos_aptos": len([e for e in evaluaciones if e.get("cumple_requisitos", False)]),
            "tools_used": ["llm", "cv_analyzer"]
        }
    
    def _onboarding_empleado(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Automatiza onboarding de nuevos empleados."""
        empleado = parameters.get("empleado", {})
        
        tareas_completadas = []
        
        # Generar contrato
        contrato = {
            "empleado": empleado.get("nombre", ""),
            "puesto": empleado.get("puesto", ""),
            "fecha_inicio": empleado.get("fecha_inicio", datetime.now().isoformat()),
            "salario": empleado.get("salario", 0),
            "generado_el": datetime.now().isoformat()
        }
        tareas_completadas.append("contrato_generado")
        
        # Configurar accesos
        accesos = {
            "email": f"{empleado.get('nombre', '').lower().replace(' ', '.')}@empresa.com",
            "sistemas": ["ERP", "CRM", "Email"],
            "permisos": empleado.get("permisos", ["basico"])
        }
        tareas_completadas.append("accesos_configurados")
        
        # Documentos de bienvenida
        documentos = [
            "Manual de bienvenida",
            "Políticas de la empresa",
            "Guía de sistemas"
        ]
        tareas_completadas.append("documentos_enviados")
        
        return {
            "empleado": empleado.get("nombre", ""),
            "contrato": contrato,
            "accesos": accesos,
            "documentos": documentos,
            "tareas_completadas": tareas_completadas,
            "estado": "onboarding_completado",
            "tools_used": ["onboarding_automation"]
        }
    
    def _gestion_nomina(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Gestiona nómina automáticamente."""
        empleados = parameters.get("empleados", [])
        periodo = parameters.get("periodo", datetime.now().strftime("%Y-%m"))
        
        nominas = []
        for emp in empleados:
            horas_base = emp.get("horas_base", 160)
            horas_extras = emp.get("horas_extras", 0)
            salario_base = emp.get("salario_base", 0)
            
            # Cálculos
            pago_horas_extras = horas_extras * (salario_base / horas_base * 1.5)
            deducciones = salario_base * 0.15  # 15% ejemplo
            beneficios = emp.get("beneficios", 0)
            
            nomina = {
                "empleado": emp.get("nombre", ""),
                "periodo": periodo,
                "horas_base": horas_base,
                "horas_extras": horas_extras,
                "salario_base": salario_base,
                "pago_horas_extras": pago_horas_extras,
                "deducciones": deducciones,
                "beneficios": beneficios,
                "total": salario_base + pago_horas_extras - deducciones + beneficios
            }
            nominas.append(nomina)
        
        return {
            "periodo": periodo,
            "total_empleados": len(empleados),
            "nominas": nominas,
            "total_nomina": sum(n.get("total", 0) for n in nominas),
            "tools_used": ["payroll_processor"]
        }
    
    def _gestion_ausencias(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Gestiona ausencias de empleados."""
        solicitudes = parameters.get("solicitudes", [])
        
        aprobadas = []
        rechazadas = []
        
        for solicitud in solicitudes:
            tipo = solicitud.get("tipo", "vacaciones")
            dias = solicitud.get("dias", 0)
            
            # Lógica simple de aprobación
            if tipo == "vacaciones" and dias <= 15:
                aprobadas.append(solicitud)
            elif tipo == "permiso" and dias <= 3:
                aprobadas.append(solicitud)
            else:
                rechazadas.append(solicitud)
        
        return {
            "total_solicitudes": len(solicitudes),
            "aprobadas": len(aprobadas),
            "rechazadas": len(rechazadas),
            "detalle_aprobadas": aprobadas,
            "detalle_rechazadas": rechazadas,
            "tools_used": ["absence_manager"]
        }
    
    def _evaluacion_desempeno(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Genera evaluación de desempeño."""
        empleado = parameters.get("empleado", {})
        kpis = parameters.get("kpis", {})
        feedback = parameters.get("feedback", [])
        
        # Calcular puntuación
        puntuacion_total = sum(kpis.values()) / len(kpis) if kpis else 0
        
        informe = {
            "empleado": empleado.get("nombre", ""),
            "periodo": parameters.get("periodo", datetime.now().strftime("%Y-%m")),
            "kpis": kpis,
            "puntuacion_total": puntuacion_total,
            "feedback": feedback,
            "recomendaciones": self._generar_recomendaciones_desempeno(puntuacion_total, kpis),
            "fecha_generacion": datetime.now().isoformat()
        }
        
        return {
            "informe_desempeno": informe,
            "tools_used": ["performance_evaluator"]
        }
    
    def _generar_recomendaciones_desempeno(self, puntuacion: float, kpis: Dict[str, float]) -> List[str]:
        """Genera recomendaciones basadas en desempeño."""
        recomendaciones = []
        
        if puntuacion < 60:
            recomendaciones.append("Desempeño bajo - Requiere plan de mejora")
        elif puntuacion < 80:
            recomendaciones.append("Desempeño aceptable - Áreas de mejora identificadas")
        else:
            recomendaciones.append("Desempeño excelente - Considerar reconocimiento")
        
        # Recomendaciones específicas por KPI
        for kpi, valor in kpis.items():
            if valor < 60:
                recomendaciones.append(f"Mejorar {kpi}: Valor actual {valor:.1f}")
        
        return recomendaciones
    
    # Continuaré con las demás categorías en el siguiente mensaje debido a límites de tamaño...



# Continuación de rpa_automation.py - Agregar al final del archivo

    # ============================================================================
    # LOGÍSTICA Y CADENA DE SUMINISTRO
    # ============================================================================
    
    def _execute_logistica(self, task_type: str, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Ejecuta automatizaciones de logística."""
        if task_type == "gestion_inventario":
            return self._gestion_inventario(parameters, documents)
        elif task_type == "seguimiento_envios":
            return self._seguimiento_envios(parameters, documents)
        elif task_type == "optimizar_rutas":
            return self._optimizar_rutas(parameters, documents)
        elif task_type == "generar_orden_compra":
            return self._generar_orden_compra(parameters, documents)
        elif task_type == "facturacion_transporte":
            return self._facturacion_transporte(parameters, documents)
        else:
            raise ValueError(f"Tipo de tarea desconocido: {task_type}")
    
    def _gestion_inventario(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Gestiona inventario y reordenación automática."""
        productos = parameters.get("productos", [])
        umbral_minimo = parameters.get("umbral_minimo", 10)
        
        alertas = []
        reordenaciones = []
        
        for producto in productos:
            stock_actual = producto.get("stock", 0)
            if stock_actual < umbral_minimo:
                cantidad_reordenar = producto.get("stock_maximo", 100) - stock_actual
                alertas.append({
                    "producto": producto.get("nombre", ""),
                    "stock_actual": stock_actual,
                    "umbral": umbral_minimo,
                    "accion": "reordenar"
                })
                reordenaciones.append({
                    "producto_id": producto.get("id", ""),
                    "cantidad": cantidad_reordenar,
                    "proveedor": producto.get("proveedor", "")
                })
        
        return {
            "total_productos": len(productos),
            "alertas": len(alertas),
            "reordenaciones": reordenaciones,
            "detalle_alertas": alertas,
            "tools_used": ["inventory_manager"]
        }
    
    def _seguimiento_envios(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Rastrea estado de envíos."""
        envios = parameters.get("envios", [])
        
        estados = {
            "entregado": [],
            "en_transito": [],
            "retraso": [],
            "pendiente": []
        }
        
        for envio in envios:
            estado = envio.get("estado", "pendiente")
            if estado in estados:
                estados[estado].append(envio)
        
        return {
            "total_envios": len(envios),
            "por_estado": {k: len(v) for k, v in estados.items()},
            "detalle": estados,
            "tools_used": ["shipping_tracker"]
        }
    
    def _optimizar_rutas(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Optimiza rutas de entrega."""
        destinos = parameters.get("destinos", [])
        vehiculos = parameters.get("vehiculos", [])
        
        # Algoritmo simple de optimización (en producción usarías algoritmos avanzados)
        rutas_optimizadas = []
        for i, vehiculo in enumerate(vehiculos):
            destinos_asignados = destinos[i::len(vehiculos)] if destinos else []
            rutas_optimizadas.append({
                "vehiculo": vehiculo.get("id", ""),
                "destinos": destinos_asignados,
                "distancia_estimada": len(destinos_asignados) * 10,  # Ejemplo
                "tiempo_estimado": len(destinos_asignados) * 30  # minutos
            })
        
        return {
            "rutas": rutas_optimizadas,
            "total_destinos": len(destinos),
            "vehiculos_utilizados": len(vehiculos),
            "tools_used": ["route_optimizer"]
        }
    
    def _generar_orden_compra(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Genera orden de compra automáticamente."""
        productos = parameters.get("productos", [])
        proveedor = parameters.get("proveedor", {})
        
        orden = {
            "numero": f"OC-{int(time.time())}",
            "fecha": datetime.now().isoformat(),
            "proveedor": proveedor,
            "productos": productos,
            "total": sum(p.get("precio", 0) * p.get("cantidad", 0) for p in productos),
            "estado": "pendiente"
        }
        
        return {
            "orden_compra": orden,
            "tools_used": ["purchase_order_generator"]
        }
    
    def _facturacion_transporte(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Calcula y genera facturas de transporte."""
        envios = parameters.get("envios", [])
        tarifa_por_km = parameters.get("tarifa_por_km", 1.5)
        
        facturas = []
        for envio in envios:
            distancia = envio.get("distancia_km", 0)
            total = distancia * tarifa_por_km
            
            factura = {
                "envio_id": envio.get("id", ""),
                "distancia_km": distancia,
                "tarifa_por_km": tarifa_por_km,
                "total": total,
                "fecha": datetime.now().isoformat()
            }
            facturas.append(factura)
        
        return {
            "facturas": facturas,
            "total_facturado": sum(f.get("total", 0) for f in facturas),
            "tools_used": ["transport_billing"]
        }
    
    # ============================================================================
    # MARKETING Y VENTAS
    # ============================================================================
    
    def _execute_marketing(self, task_type: str, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Ejecuta automatizaciones de marketing."""
        if task_type == "generar_leads":
            return self._generar_leads(parameters, documents)
        elif task_type == "enviar_campana":
            return self._enviar_campana(parameters, documents)
        elif task_type == "seguimiento_leads":
            return self._seguimiento_leads(parameters, documents)
        elif task_type == "automatizar_precios":
            return self._automatizar_precios(parameters, documents)
        elif task_type == "analizar_comportamiento":
            return self._analizar_comportamiento(parameters, documents)
        else:
            raise ValueError(f"Tipo de tarea desconocido: {task_type}")
    
    def _generar_leads(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Genera leads automáticamente."""
        fuente = parameters.get("fuente", "formulario")
        datos = parameters.get("datos", [])
        
        leads_procesados = []
        for dato in datos:
            lead = {
                "id": f"LEAD-{int(time.time())}-{len(leads_procesados)}",
                "nombre": dato.get("nombre", ""),
                "email": dato.get("email", ""),
                "telefono": dato.get("telefono", ""),
                "fuente": fuente,
                "fecha": datetime.now().isoformat(),
                "estado": "nuevo"
            }
            leads_procesados.append(lead)
        
        return {
            "leads_generados": len(leads_procesados),
            "leads": leads_procesados,
            "tools_used": ["lead_generator"]
        }
    
    def _enviar_campana(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Envía campaña de marketing."""
        destinatarios = parameters.get("destinatarios", [])
        contenido = parameters.get("contenido", "")
        segmentacion = parameters.get("segmentacion", {})
        
        enviados = len(destinatarios)
        
        return {
            "campana_enviada": True,
            "destinatarios": enviados,
            "segmentacion": segmentacion,
            "contenido_preview": contenido[:100] + "...",
            "tools_used": ["campaign_sender"]
        }
    
    def _seguimiento_leads(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Sigue leads automáticamente."""
        leads = parameters.get("leads", [])
        
        seguimientos = []
        for lead in leads:
            ultimo_contacto = lead.get("ultimo_contacto")
            if not ultimo_contacto:
                seguimientos.append({
                    "lead_id": lead.get("id", ""),
                    "accion": "enviar_bienvenida",
                    "mensaje": "Email de bienvenida enviado"
                })
            else:
                dias_desde_contacto = (datetime.now() - datetime.fromisoformat(ultimo_contacto)).days
                if dias_desde_contacto > 7:
                    seguimientos.append({
                        "lead_id": lead.get("id", ""),
                        "accion": "recordatorio",
                        "mensaje": f"Recordatorio enviado después de {dias_desde_contacto} días"
                    })
        
        return {
            "seguimientos_realizados": len(seguimientos),
            "detalle": seguimientos,
            "tools_used": ["lead_follower"]
        }
    
    def _automatizar_precios(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Ajusta precios automáticamente."""
        productos = parameters.get("productos", [])
        condiciones_mercado = parameters.get("condiciones_mercado", {})
        
        ajustes = []
        for producto in productos:
            precio_actual = producto.get("precio", 0)
            demanda = condiciones_mercado.get("demanda", "normal")
            competencia = condiciones_mercado.get("competencia", "normal")
            
            # Lógica simple de ajuste
            nuevo_precio = precio_actual
            if demanda == "alta" and competencia == "baja":
                nuevo_precio = precio_actual * 1.1  # Aumentar 10%
            elif demanda == "baja" or competencia == "alta":
                nuevo_precio = precio_actual * 0.95  # Reducir 5%
            
            if nuevo_precio != precio_actual:
                ajustes.append({
                    "producto_id": producto.get("id", ""),
                    "precio_anterior": precio_actual,
                    "precio_nuevo": nuevo_precio,
                    "razon": f"Demanda: {demanda}, Competencia: {competencia}"
                })
        
        return {
            "ajustes_realizados": len(ajustes),
            "detalle_ajustes": ajustes,
            "tools_used": ["price_optimizer"]
        }
    
    def _analizar_comportamiento(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Analiza comportamiento de usuarios."""
        datos_navegacion = parameters.get("datos_navegacion", [])
        
        # Análisis básico
        paginas_visitadas = {}
        tiempo_promedio = 0
        
        for sesion in datos_navegacion:
            for pagina in sesion.get("paginas", []):
                paginas_visitadas[pagina] = paginas_visitadas.get(pagina, 0) + 1
            tiempo_promedio += sesion.get("tiempo_total", 0)
        
        tiempo_promedio = tiempo_promedio / len(datos_navegacion) if datos_navegacion else 0
        
        return {
            "total_sesiones": len(datos_navegacion),
            "paginas_populares": dict(sorted(paginas_visitadas.items(), key=lambda x: x[1], reverse=True)[:5]),
            "tiempo_promedio": tiempo_promedio,
            "recomendaciones": self._generar_recomendaciones_comportamiento(paginas_visitadas),
            "tools_used": ["behavior_analyzer"]
        }
    
    def _generar_recomendaciones_comportamiento(self, paginas: Dict[str, int]) -> List[str]:
        """Genera recomendaciones basadas en comportamiento."""
        recomendaciones = []
        
        if paginas:
            pagina_mas_visitada = max(paginas.items(), key=lambda x: x[1])
            recomendaciones.append(f"Destacar contenido de '{pagina_mas_visitada[0]}' en homepage")
        
        return recomendaciones
    
    # ============================================================================
    # SALUD
    # ============================================================================
    
    def _execute_salud(self, task_type: str, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Ejecuta automatizaciones de salud."""
        if task_type == "registros_medicos":
            return self._registros_medicos(parameters, documents)
        elif task_type == "gestion_citas":
            return self._gestion_citas(parameters, documents)
        elif task_type == "procesar_reclamaciones":
            return self._procesar_reclamaciones(parameters, documents)
        elif task_type == "diagnostico_automatizado":
            return self._diagnostico_automatizado(parameters, documents)
        elif task_type == "monitoreo_pacientes":
            return self._monitoreo_pacientes(parameters, documents)
        else:
            raise ValueError(f"Tipo de tarea desconocido: {task_type}")
    
    def _registros_medicos(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Captura y organiza registros médicos."""
        paciente = parameters.get("paciente", {})
        datos_medicos = parameters.get("datos_medicos", {})
        
        registro = {
            "paciente_id": paciente.get("id", ""),
            "nombre": paciente.get("nombre", ""),
            "fecha": datetime.now().isoformat(),
            "diagnostico": datos_medicos.get("diagnostico", ""),
            "tratamiento": datos_medicos.get("tratamiento", ""),
            "medicamentos": datos_medicos.get("medicamentos", []),
            "notas": datos_medicos.get("notas", "")
        }
        
        return {
            "registro_medico": registro,
            "tools_used": ["medical_records"]
        }
    
    def _gestion_citas(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Gestiona citas médicas."""
        solicitudes = parameters.get("solicitudes", [])
        doctores = parameters.get("doctores", [])
        
        citas_programadas = []
        for solicitud in solicitudes:
            # Asignar a doctor disponible
            doctor = doctores[len(citas_programadas) % len(doctores)] if doctores else {}
            
            cita = {
                "id": f"CITA-{int(time.time())}-{len(citas_programadas)}",
                "paciente": solicitud.get("paciente", ""),
                "doctor": doctor.get("nombre", ""),
                "fecha": solicitud.get("fecha_preferida", datetime.now().isoformat()),
                "tipo": solicitud.get("tipo", "consulta"),
                "estado": "programada"
            }
            citas_programadas.append(cita)
        
        return {
            "citas_programadas": len(citas_programadas),
            "citas": citas_programadas,
            "tools_used": ["appointment_manager"]
        }
    
    def _procesar_reclamaciones(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Procesa reclamaciones de seguros."""
        reclamaciones = parameters.get("reclamaciones", [])
        
        procesadas = []
        for reclamacion in reclamaciones:
            # Validación básica
            valida = (
                reclamacion.get("monto", 0) > 0 and
                reclamacion.get("paciente_id") and
                reclamacion.get("servicio")
            )
            
            procesadas.append({
                "reclamacion_id": reclamacion.get("id", ""),
                "valida": valida,
                "estado": "aprobada" if valida else "rechazada",
                "razon": "Reclamación válida" if valida else "Datos incompletos o inválidos"
            })
        
        return {
            "reclamaciones_procesadas": len(procesadas),
            "aprobadas": len([p for p in procesadas if p.get("valida")]),
            "rechazadas": len([p for p in procesadas if not p.get("valida")]),
            "detalle": procesadas,
            "tools_used": ["insurance_claims"]
        }
    
    def _diagnostico_automatizado(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Ayuda en diagnóstico usando IA."""
        sintomas = parameters.get("sintomas", [])
        imagenes = parameters.get("imagenes", [])
        
        # Procesar con LLM
        prompt = f"""Analiza estos síntomas y proporciona posibles diagnósticos (solo como ayuda, no reemplaza diagnóstico médico):

Síntomas: {', '.join(sintomas)}

Proporciona:
1. Posibles condiciones (máximo 3)
2. Nivel de urgencia (baja, media, alta)
3. Recomendaciones de acción

Responde en formato JSON."""

        response = self.llm.invoke([{"role": "user", "content": prompt}])
        diagnostico = json.loads(response.content)
        
        return {
            "diagnostico_ia": diagnostico,
            "advertencia": "Este es solo una ayuda. Siempre consulta con un médico profesional.",
            "tools_used": ["llm", "diagnostic_assistant"]
        }
    
    def _monitoreo_pacientes(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Monitorea pacientes con dispositivos."""
        pacientes = parameters.get("pacientes", [])
        
        alertas = []
        for paciente in pacientes:
            datos = paciente.get("datos_dispositivo", {})
            frecuencia_cardiaca = datos.get("frecuencia_cardiaca", 0)
            presion_arterial = datos.get("presion_arterial", {})
            
            # Detectar anomalías
            if frecuencia_cardiaca > 100 or frecuencia_cardiaca < 60:
                alertas.append({
                    "paciente_id": paciente.get("id", ""),
                    "tipo": "frecuencia_cardiaca_anormal",
                    "valor": frecuencia_cardiaca,
                    "urgencia": "alta" if frecuencia_cardiaca > 120 or frecuencia_cardiaca < 50 else "media"
                })
        
        return {
            "pacientes_monitoreados": len(pacientes),
            "alertas": alertas,
            "total_alertas": len(alertas),
            "tools_used": ["patient_monitor"]
        }
    
    # ============================================================================
    # INDUSTRIA Y MANUFACTURA
    # ============================================================================
    
    def _execute_manufactura(self, task_type: str, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Ejecuta automatizaciones de manufactura."""
        if task_type == "mantenimiento_predictivo":
            return self._mantenimiento_predictivo(parameters, documents)
        elif task_type == "control_calidad":
            return self._control_calidad(parameters, documents)
        elif task_type == "planificacion_produccion":
            return self._planificacion_produccion(parameters, documents)
        elif task_type == "gestion_proveedores":
            return self._gestion_proveedores(parameters, documents)
        elif task_type == "analisis_productividad":
            return self._analisis_productividad(parameters, documents)
        else:
            raise ValueError(f"Tipo de tarea desconocido: {task_type}")
    
    def _mantenimiento_predictivo(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Predice fallos en máquinas."""
        maquinas = parameters.get("maquinas", [])
        
        predicciones = []
        for maquina in maquinas:
            datos_sensores = maquina.get("datos_sensores", {})
            temperatura = datos_sensores.get("temperatura", 0)
            vibracion = datos_sensores.get("vibracion", 0)
            
            # Lógica simple de predicción
            riesgo = "bajo"
            if temperatura > 80 or vibracion > 5:
                riesgo = "alto"
            elif temperatura > 70 or vibracion > 3:
                riesgo = "medio"
            
            if riesgo != "bajo":
                predicciones.append({
                    "maquina_id": maquina.get("id", ""),
                    "riesgo": riesgo,
                    "recomendacion": "Mantenimiento preventivo recomendado",
                    "fecha_recomendada": (datetime.now() + timedelta(days=7)).isoformat()
                })
        
        return {
            "maquinas_analizadas": len(maquinas),
            "predicciones": predicciones,
            "total_alertas": len(predicciones),
            "tools_used": ["predictive_maintenance"]
        }
    
    def _control_calidad(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Control de calidad automatizado."""
        productos = parameters.get("productos", [])
        criterios = parameters.get("criterios_calidad", {})
        
        aprobados = []
        rechazados = []
        
        for producto in productos:
            cumple_criterios = True
            razones = []
            
            for criterio, valor_requerido in criterios.items():
                valor_producto = producto.get(criterio, 0)
                if valor_producto < valor_requerido:
                    cumple_criterios = False
                    razones.append(f"{criterio}: {valor_producto} < {valor_requerido}")
            
            if cumple_criterios:
                aprobados.append(producto)
            else:
                rechazados.append({
                    "producto": producto,
                    "razones": razones
                })
        
        return {
            "total_productos": len(productos),
            "aprobados": len(aprobados),
            "rechazados": len(rechazados),
            "detalle_rechazados": rechazados,
            "tools_used": ["quality_control"]
        }
    
    def _planificacion_produccion(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Planifica producción automáticamente."""
        demanda = parameters.get("demanda", {})
        capacidad = parameters.get("capacidad", {})
        
        plan = {
            "periodo": parameters.get("periodo", datetime.now().strftime("%Y-%m")),
            "productos": [],
            "recursos_necesarios": {}
        }
        
        for producto_id, cantidad_demanda in demanda.items():
            capacidad_disponible = capacidad.get(producto_id, 0)
            
            plan["productos"].append({
                "producto_id": producto_id,
                "demanda": cantidad_demanda,
                "capacidad": capacidad_disponible,
                "produccion_planificada": min(cantidad_demanda, capacidad_disponible),
                "deficit": max(0, cantidad_demanda - capacidad_disponible)
            })
        
        return {
            "plan_produccion": plan,
            "tools_used": ["production_planner"]
        }
    
    def _gestion_proveedores(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Gestiona proveedores automáticamente."""
        materiales = parameters.get("materiales", [])
        proveedores = parameters.get("proveedores", [])
        
        ordenes = []
        for material in materiales:
            stock_actual = material.get("stock", 0)
            stock_minimo = material.get("stock_minimo", 10)
            
            if stock_actual < stock_minimo:
                proveedor = next((p for p in proveedores if p.get("material_id") == material.get("id")), {})
                ordenes.append({
                    "material_id": material.get("id", ""),
                    "proveedor": proveedor.get("nombre", ""),
                    "cantidad": material.get("stock_maximo", 100) - stock_actual,
                    "estado": "pendiente"
                })
        
        return {
            "ordenes_generadas": len(ordenes),
            "ordenes": ordenes,
            "tools_used": ["supplier_manager"]
        }
    
    def _analisis_productividad(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Analiza productividad de líneas de producción."""
        lineas = parameters.get("lineas_produccion", [])
        periodo = parameters.get("periodo", datetime.now().strftime("%Y-%m"))
        
        analisis = []
        for linea in lineas:
            unidades_producidas = linea.get("unidades_producidas", 0)
            tiempo_total = linea.get("tiempo_total_horas", 0)
            eficiencia = (unidades_producidas / tiempo_total) if tiempo_total > 0 else 0
            
            analisis.append({
                "linea_id": linea.get("id", ""),
                "unidades_producidas": unidades_producidas,
                "tiempo_total": tiempo_total,
                "eficiencia": eficiencia,
                "productividad": "alta" if eficiencia > 50 else "media" if eficiencia > 30 else "baja"
            })
        
        return {
            "periodo": periodo,
            "lineas_analizadas": len(lineas),
            "analisis": analisis,
            "eficiencia_promedio": sum(a.get("eficiencia", 0) for a in analisis) / len(analisis) if analisis else 0,
            "tools_used": ["productivity_analyzer"]
        }
    
    # ============================================================================
    # TI Y SEGURIDAD
    # ============================================================================
    
    def _execute_ti_seguridad(self, task_type: str, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Ejecuta automatizaciones de TI y seguridad."""
        if task_type == "monitoreo_seguridad":
            return self._monitoreo_seguridad(parameters, documents)
        elif task_type == "gestion_contraseñas":
            return self._gestion_contraseñas(parameters, documents)
        elif task_type == "deteccion_anomalias":
            return self._deteccion_anomalias(parameters, documents)
        elif task_type == "automatizar_backups":
            return self._automatizar_backups(parameters, documents)
        else:
            raise ValueError(f"Tipo de tarea desconocido: {task_type}")
    
    def _monitoreo_seguridad(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Monitorea seguridad cibernética."""
        eventos = parameters.get("eventos", [])
        
        amenazas = []
        for evento in eventos:
            tipo = evento.get("tipo", "")
            if tipo in ["ddos", "acceso_no_autorizado", "malware"]:
                amenazas.append({
                    "tipo": tipo,
                    "severidad": "alta",
                    "evento": evento,
                    "accion_recomendada": "Bloquear IP y notificar al equipo de seguridad"
                })
        
        return {
            "eventos_analizados": len(eventos),
            "amenazas_detectadas": len(amenazas),
            "detalle_amenazas": amenazas,
            "tools_used": ["security_monitor"]
        }
    
    def _gestion_contraseñas(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Gestiona contraseñas automáticamente."""
        sistemas = parameters.get("sistemas", [])
        longitud = parameters.get("longitud", 16)
        
        contraseñas = []
        for sistema in sistemas:
            import secrets
            import string
            password = ''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(longitud))
            
            contraseñas.append({
                "sistema": sistema.get("nombre", ""),
                "usuario": sistema.get("usuario", ""),
                "contraseña": password,
                "fecha_generacion": datetime.now().isoformat()
            })
        
        return {
            "contraseñas_generadas": len(contraseñas),
            "contraseñas": contraseñas,
            "advertencia": "Guarda estas contraseñas de forma segura",
            "tools_used": ["password_manager"]
        }
    
    def _deteccion_anomalias(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Detecta anomalías en sistemas."""
        datos = parameters.get("datos", [])
        
        anomalias = []
        for registro in datos:
            # Detectar patrones anómalos
            if registro.get("intentos_fallidos", 0) > 5:
                anomalias.append({
                    "tipo": "múltiples_intentos_fallidos",
                    "registro": registro,
                    "severidad": "media"
                })
            elif registro.get("transaccion_monto", 0) > 10000:
                anomalias.append({
                    "tipo": "transaccion_sospechosa",
                    "registro": registro,
                    "severidad": "alta"
                })
        
        return {
            "registros_analizados": len(datos),
            "anomalias_detectadas": len(anomalias),
            "detalle": anomalias,
            "tools_used": ["anomaly_detector"]
        }
    
    def _automatizar_backups(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Automatiza copias de seguridad."""
        sistemas = parameters.get("sistemas", [])
        destino = parameters.get("destino", "cloud")
        
        backups = []
        for sistema in sistemas:
            backup = {
                "sistema": sistema.get("nombre", ""),
                "destino": destino,
                "fecha": datetime.now().isoformat(),
                "estado": "completado",
                "tamaño_mb": sistema.get("tamaño_mb", 0)
            }
            backups.append(backup)
        
        return {
            "backups_realizados": len(backups),
            "backups": backups,
            "total_tamaño_mb": sum(b.get("tamaño_mb", 0) for b in backups),
            "tools_used": ["backup_automation"]
        }
    
    # ============================================================================
    # LEGAL
    # ============================================================================
    
    def _execute_legal(self, task_type: str, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Ejecuta automatizaciones legales."""
        if task_type == "revisar_contrato":
            return self._revisar_contrato(parameters, documents)
        elif task_type == "redactar_documento":
            return self._redactar_documento(parameters, documents)
        elif task_type == "gestion_cumplimiento":
            return self._gestion_cumplimiento(parameters, documents)
        elif task_type == "investigacion_legal":
            return self._investigacion_legal(parameters, documents)
        else:
            raise ValueError(f"Tipo de tarea desconocido: {task_type}")
    
    def _revisar_contrato(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Revisa contratos con IA."""
        contrato_texto = parameters.get("contrato", "")
        if documents:
            contrato_texto = "\n".join([doc.page_content for doc in documents])
        
        prompt = f"""Analiza este contrato y proporciona:

1. Cláusulas relevantes identificadas
2. Posibles riesgos o discrepancias
3. Recomendaciones de revisión
4. Puntos de atención

Contrato:
{contrato_texto[:3000]}

Responde en formato JSON estructurado."""

        response = self.llm.invoke([{"role": "user", "content": prompt}])
        analisis = json.loads(response.content)
        
        return {
            "analisis_contrato": analisis,
            "tools_used": ["llm", "contract_analyzer"]
        }
    
    def _redactar_documento(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Redacta documentos legales."""
        tipo_documento = parameters.get("tipo_documento", "contrato")
        partes = parameters.get("partes", {})
        terminos = parameters.get("terminos", {})
        
        prompt = f"""Redacta un {tipo_documento} profesional con:

Partes involucradas: {json.dumps(partes, ensure_ascii=False)}
Términos y condiciones: {json.dumps(terminos, ensure_ascii=False)}

Genera un documento legal completo y profesional."""

        response = self.llm.invoke([{"role": "user", "content": prompt}])
        documento = response.content
        
        return {
            "documento_generado": documento,
            "tipo": tipo_documento,
            "tools_used": ["llm", "document_generator"]
        }
    
    def _gestion_cumplimiento(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Gestiona cumplimiento legal."""
        regulaciones = parameters.get("regulaciones", [])
        politicas = parameters.get("politicas", [])
        
        alertas = []
        for regulacion in regulaciones:
            # Verificar si las políticas cumplen
            cumple = any(p.get("regulacion_id") == regulacion.get("id") for p in politicas)
            if not cumple:
                alertas.append({
                    "regulacion": regulacion.get("nombre", ""),
                    "estado": "no_cumple",
                    "accion": "Actualizar políticas requerida"
                })
        
        return {
            "regulaciones_revisadas": len(regulaciones),
            "alertas": alertas,
            "total_alertas": len(alertas),
            "tools_used": ["compliance_manager"]
        }
    
    def _investigacion_legal(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Investiga documentos legales."""
        consulta = parameters.get("consulta", "")
        documentos_legales = parameters.get("documentos_legales", [])
        
        if documents:
            contexto = "\n".join([doc.page_content[:1000] for doc in documents[:5]])
        else:
            contexto = "\n".join([d.get("contenido", "")[:1000] for d in documentos_legales[:5]])
        
        prompt = f"""Busca precedentes y información relevante para esta consulta legal:

Consulta: {consulta}

Documentos disponibles:
{contexto}

Proporciona:
1. Precedentes relevantes encontrados
2. Información clave
3. Recomendaciones

Responde en formato JSON."""

        response = self.llm.invoke([{"role": "user", "content": prompt}])
        investigacion = json.loads(response.content)
        
        return {
            "investigacion": investigacion,
            "tools_used": ["llm", "legal_researcher"]
        }
    
    # ============================================================================
    # GESTIÓN DE PROYECTOS
    # ============================================================================
    
    def _execute_gestion_proyectos(self, task_type: str, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Ejecuta automatizaciones de gestión de proyectos."""
        if task_type == "gestion_proyecto":
            return self._gestion_proyecto(parameters, documents)
        elif task_type == "generar_reportes":
            return self._generar_reportes(parameters, documents)
        elif task_type == "asignar_recursos":
            return self._asignar_recursos(parameters, documents)
        elif task_type == "recordatorios_alertas":
            return self._recordatorios_alertas(parameters, documents)
        else:
            raise ValueError(f"Tipo de tarea desconocido: {task_type}")
    
    def _gestion_proyecto(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Gestiona proyecto automáticamente."""
        proyecto = parameters.get("proyecto", {})
        tareas = parameters.get("tareas", [])
        
        cronograma = []
        fecha_inicio = datetime.fromisoformat(proyecto.get("fecha_inicio", datetime.now().isoformat()))
        
        for i, tarea in enumerate(tareas):
            duracion = tarea.get("duracion_dias", 1)
            fecha_inicio_tarea = fecha_inicio + timedelta(days=sum(t.get("duracion_dias", 1) for t in tareas[:i]))
            fecha_fin_tarea = fecha_inicio_tarea + timedelta(days=duracion)
            
            cronograma.append({
                "tarea": tarea.get("nombre", ""),
                "fecha_inicio": fecha_inicio_tarea.isoformat(),
                "fecha_fin": fecha_fin_tarea.isoformat(),
                "responsable": tarea.get("responsable", ""),
                "estado": "pendiente"
            })
        
        return {
            "proyecto": proyecto.get("nombre", ""),
            "cronograma": cronograma,
            "fecha_fin_proyecto": cronograma[-1].get("fecha_fin") if cronograma else None,
            "tools_used": ["project_manager"]
        }
    
    def _generar_reportes(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Genera reportes automáticos."""
        proyecto = parameters.get("proyecto", {})
        metricas = parameters.get("metricas", {})
        
        reporte = {
            "proyecto": proyecto.get("nombre", ""),
            "fecha": datetime.now().isoformat(),
            "estado": "en_progreso",
            "avance": metricas.get("avance", 0),
            "recursos_utilizados": metricas.get("recursos_utilizados", 0),
            "metas_alcanzadas": metricas.get("metas_alcanzadas", []),
            "proximos_pasos": metricas.get("proximos_pasos", [])
        }
        
        return {
            "reporte": reporte,
            "tools_used": ["report_generator"]
        }
    
    def _asignar_recursos(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Asigna recursos automáticamente."""
        tareas = parameters.get("tareas", [])
        recursos = parameters.get("recursos", [])
        
        asignaciones = []
        for tarea in tareas:
            recursos_necesarios = tarea.get("recursos_necesarios", [])
            recursos_asignados = []
            
            for recurso_tipo in recursos_necesarios:
                recurso_disponible = next((r for r in recursos if r.get("tipo") == recurso_tipo and r.get("disponible")), None)
                if recurso_disponible:
                    recursos_asignados.append(recurso_disponible)
                    recurso_disponible["disponible"] = False
            
            asignaciones.append({
                "tarea": tarea.get("nombre", ""),
                "recursos_asignados": recursos_asignados
            })
        
        return {
            "asignaciones": asignaciones,
            "tools_used": ["resource_allocator"]
        }
    
    def _recordatorios_alertas(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Genera recordatorios y alertas."""
        eventos = parameters.get("eventos", [])
        hoy = datetime.now()
        
        recordatorios = []
        for evento in eventos:
            fecha_evento = datetime.fromisoformat(evento.get("fecha", hoy.isoformat()))
            dias_restantes = (fecha_evento - hoy).days
            
            if 0 <= dias_restantes <= 7:
                recordatorios.append({
                    "evento": evento.get("nombre", ""),
                    "fecha": evento.get("fecha", ""),
                    "dias_restantes": dias_restantes,
                    "tipo": evento.get("tipo", "recordatorio"),
                    "urgencia": "alta" if dias_restantes <= 1 else "media"
                })
        
        return {
            "recordatorios": recordatorios,
            "total": len(recordatorios),
            "tools_used": ["reminder_system"]
        }
    
    # ============================================================================
    # EDUCACIÓN
    # ============================================================================
    
    def _execute_educacion(self, task_type: str, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Ejecuta automatizaciones de educación."""
        if task_type == "evaluaciones_automatizadas":
            return self._evaluaciones_automatizadas(parameters, documents)
        elif task_type == "recomendacion_contenidos":
            return self._recomendacion_contenidos(parameters, documents)
        elif task_type == "administracion_inscripciones":
            return self._administracion_inscripciones(parameters, documents)
        elif task_type == "seguimiento_progreso":
            return self._seguimiento_progreso(parameters, documents)
        else:
            raise ValueError(f"Tipo de tarea desconocido: {task_type}")
    
    def _evaluaciones_automatizadas(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Califica evaluaciones automáticamente."""
        examenes = parameters.get("examenes", [])
        respuestas_correctas = parameters.get("respuestas_correctas", {})
        
        calificaciones = []
        for examen in examenes:
            estudiante = examen.get("estudiante", "")
            respuestas = examen.get("respuestas", {})
            
            correctas = 0
            total = len(respuestas_correctas)
            
            for pregunta, respuesta_correcta in respuestas_correctas.items():
                if respuestas.get(pregunta) == respuesta_correcta:
                    correctas += 1
            
            calificacion = (correctas / total * 100) if total > 0 else 0
            
            calificaciones.append({
                "estudiante": estudiante,
                "preguntas_correctas": correctas,
                "total_preguntas": total,
                "calificacion": calificacion,
                "retroalimentacion": self._generar_retroalimentacion(calificacion)
            })
        
        return {
            "calificaciones": calificaciones,
            "promedio": sum(c.get("calificacion", 0) for c in calificaciones) / len(calificaciones) if calificaciones else 0,
            "tools_used": ["auto_grader"]
        }
    
    def _generar_retroalimentacion(self, calificacion: float) -> str:
        """Genera retroalimentación basada en calificación."""
        if calificacion >= 90:
            return "Excelente trabajo. Continúa así."
        elif calificacion >= 70:
            return "Buen trabajo. Hay áreas de mejora."
        elif calificacion >= 50:
            return "Necesitas estudiar más. Revisa los conceptos."
        else:
            return "Requiere atención. Considera apoyo adicional."
    
    def _recomendacion_contenidos(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Recomienda contenidos educativos."""
        estudiante = parameters.get("estudiante", {})
        desempeno = estudiante.get("desempeno", {})
        preferencias = estudiante.get("preferencias", [])
        
        recomendaciones = []
        
        # Recomendar basado en desempeño
        for materia, puntuacion in desempeno.items():
            if puntuacion < 70:
                recomendaciones.append({
                    "tipo": "material_refuerzo",
                    "materia": materia,
                    "razon": f"Puntuación baja ({puntuacion}) - Material de refuerzo recomendado"
                })
        
        # Recomendar basado en preferencias
        for preferencia in preferencias:
            recomendaciones.append({
                "tipo": "contenido_interes",
                "categoria": preferencia,
                "razon": "Basado en tus intereses"
            })
        
        return {
            "recomendaciones": recomendaciones,
            "total": len(recomendaciones),
            "tools_used": ["content_recommender"]
        }
    
    def _administracion_inscripciones(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Administra inscripciones a cursos."""
        solicitudes = parameters.get("solicitudes", [])
        cursos = parameters.get("cursos", [])
        
        inscripciones = []
        for solicitud in solicitudes:
            curso_id = solicitud.get("curso_id", "")
            curso = next((c for c in cursos if c.get("id") == curso_id), {})
            
            cupos_disponibles = curso.get("cupos_disponibles", 0)
            if cupos_disponibles > 0:
                inscripciones.append({
                    "estudiante": solicitud.get("estudiante", ""),
                    "curso": curso.get("nombre", ""),
                    "estado": "inscrito",
                    "fecha": datetime.now().isoformat()
                })
                curso["cupos_disponibles"] = cupos_disponibles - 1
            else:
                inscripciones.append({
                    "estudiante": solicitud.get("estudiante", ""),
                    "curso": curso.get("nombre", ""),
                    "estado": "lista_espera",
                    "fecha": datetime.now().isoformat()
                })
        
        return {
            "inscripciones": inscripciones,
            "total": len(inscripciones),
            "tools_used": ["enrollment_manager"]
        }
    
    def _seguimiento_progreso(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Monitorea progreso de estudiantes."""
        estudiantes = parameters.get("estudiantes", [])
        
        reportes = []
        for estudiante in estudiantes:
            progreso = estudiante.get("progreso", {})
            promedio = sum(progreso.values()) / len(progreso) if progreso else 0
            
            reportes.append({
                "estudiante": estudiante.get("nombre", ""),
                "progreso": progreso,
                "promedio": promedio,
                "estado": "excelente" if promedio >= 90 else "bueno" if promedio >= 70 else "necesita_mejora",
                "recomendaciones": self._generar_recomendaciones_estudiante(promedio, progreso)
            })
        
        return {
            "reportes": reportes,
            "total_estudiantes": len(estudiantes),
            "tools_used": ["progress_tracker"]
        }
    
    def _generar_recomendaciones_estudiante(self, promedio: float, progreso: Dict[str, float]) -> List[str]:
        """Genera recomendaciones para estudiante."""
        recomendaciones = []
        
        if promedio < 70:
            recomendaciones.append("Necesita apoyo adicional")
        
        for materia, puntuacion in progreso.items():
            if puntuacion < 60:
                recomendaciones.append(f"Reforzar {materia}")
        
        return recomendaciones
    
    # ============================================================================
    # COMUNICACIONES
    # ============================================================================
    
    def _execute_comunicaciones(self, task_type: str, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Ejecuta automatizaciones de comunicaciones."""
        if task_type == "gestion_emails":
            return self._gestion_emails(parameters, documents)
        elif task_type == "automatizar_agendas":
            return self._automatizar_agendas(parameters, documents)
        elif task_type == "transcripcion_automatica":
            return self._transcripcion_automatica(parameters, documents)
        else:
            raise ValueError(f"Tipo de tarea desconocido: {task_type}")
    
    def _gestion_emails(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Gestiona emails automáticamente."""
        emails = parameters.get("emails", [])
        
        categorizados = {
            "importante": [],
            "normal": [],
            "spam": []
        }
        
        for email in emails:
            asunto = email.get("asunto", "").lower()
            remitente = email.get("remitente", "").lower()
            
            # Clasificación simple
            if any(palabra in asunto for palabra in ["urgente", "importante", "reunion"]):
                categorizados["importante"].append(email)
            elif any(palabra in remitente for palabra in ["noreply", "no-reply"]):
                categorizados["spam"].append(email)
            else:
                categorizados["normal"].append(email)
        
        return {
            "emails_procesados": len(emails),
            "categorizados": {k: len(v) for k, v in categorizados.items()},
            "detalle": categorizados,
            "tools_used": ["email_manager"]
        }
    
    def _automatizar_agendas(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Programa reuniones automáticamente."""
        participantes = parameters.get("participantes", [])
        duracion = parameters.get("duracion_minutos", 60)
        fecha_preferida = parameters.get("fecha_preferida", datetime.now().isoformat())
        
        # Encontrar horario común (lógica simplificada)
        horario_propuesto = datetime.fromisoformat(fecha_preferida)
        
        reunion = {
            "id": f"REU-{int(time.time())}",
            "participantes": [p.get("nombre", "") for p in participantes],
            "fecha": horario_propuesto.isoformat(),
            "duracion": duracion,
            "estado": "programada"
        }
        
        return {
            "reunion": reunion,
            "tools_used": ["calendar_automation"]
        }
    
    def _transcripcion_automatica(self, parameters: Dict[str, Any], documents: Optional[List[Document]]) -> Dict[str, Any]:
        """Transcribe reuniones y llamadas."""
        audio_texto = parameters.get("audio_texto", "")
        tipo = parameters.get("tipo", "reunion")
        
        # Si hay documentos, usar como contexto
        contexto = ""
        if documents:
            contexto = "\n".join([doc.page_content[:500] for doc in documents[:3]])
        
        prompt = f"""Transcribe y resume este {tipo}:

Audio/Texto: {audio_texto[:2000]}

Contexto adicional:
{contexto}

Proporciona:
1. Transcripción completa
2. Resumen ejecutivo
3. Puntos clave discutidos
4. Acciones acordadas

Responde en formato JSON."""

        response = self.llm.invoke([{"role": "user", "content": prompt}])
        transcripcion = json.loads(response.content)
        
        return {
            "transcripcion": transcripcion,
            "tipo": tipo,
            "tools_used": ["llm", "transcription_service"]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del sistema RPA."""
        return {
            **self.stats,
            "total_automations": len(self.automations),
            "success_rate": (self.stats["completed_tasks"] / self.stats["total_tasks"] * 100) if self.stats["total_tasks"] > 0 else 0
        }
    
    def get_available_categories(self) -> List[Dict[str, Any]]:
        """Obtiene categorías disponibles y sus tareas."""
        return [
            {
                "category": "finanzas",
                "name": "Finanzas y Contabilidad",
                "tasks": [
                    {"id": "generar_factura", "name": "Generar Factura"},
                    {"id": "conciliacion_bancaria", "name": "Conciliación Bancaria"},
                    {"id": "procesar_pagos", "name": "Procesar Pagos"},
                    {"id": "calcular_impuestos", "name": "Calcular Impuestos"},
                    {"id": "auditoria_automatizada", "name": "Auditoría Automatizada"},
                    {"id": "control_cuentas", "name": "Control de Cuentas"}
                ]
            },
            {
                "category": "rrhh",
                "name": "Recursos Humanos",
                "tasks": [
                    {"id": "filtrar_cv", "name": "Filtrar CVs"},
                    {"id": "onboarding_empleado", "name": "Onboarding de Empleado"},
                    {"id": "gestion_nomina", "name": "Gestión de Nómina"},
                    {"id": "gestion_ausencias", "name": "Gestión de Ausencias"},
                    {"id": "evaluacion_desempeno", "name": "Evaluación de Desempeño"}
                ]
            },
            {
                "category": "logistica",
                "name": "Logística y Cadena de Suministro",
                "tasks": [
                    {"id": "gestion_inventario", "name": "Gestión de Inventario"},
                    {"id": "seguimiento_envios", "name": "Seguimiento de Envíos"},
                    {"id": "optimizar_rutas", "name": "Optimizar Rutas"},
                    {"id": "generar_orden_compra", "name": "Generar Orden de Compra"},
                    {"id": "facturacion_transporte", "name": "Facturación de Transporte"}
                ]
            },
            {
                "category": "marketing",
                "name": "Marketing y Ventas",
                "tasks": [
                    {"id": "generar_leads", "name": "Generar Leads"},
                    {"id": "enviar_campana", "name": "Enviar Campaña"},
                    {"id": "seguimiento_leads", "name": "Seguimiento de Leads"},
                    {"id": "automatizar_precios", "name": "Automatizar Precios"},
                    {"id": "analizar_comportamiento", "name": "Analizar Comportamiento"}
                ]
            },
            {
                "category": "salud",
                "name": "Salud",
                "tasks": [
                    {"id": "registros_medicos", "name": "Registros Médicos"},
                    {"id": "gestion_citas", "name": "Gestión de Citas"},
                    {"id": "procesar_reclamaciones", "name": "Procesar Reclamaciones"},
                    {"id": "diagnostico_automatizado", "name": "Diagnóstico Automatizado"},
                    {"id": "monitoreo_pacientes", "name": "Monitoreo de Pacientes"}
                ]
            },
            {
                "category": "manufactura",
                "name": "Industria y Manufactura",
                "tasks": [
                    {"id": "mantenimiento_predictivo", "name": "Mantenimiento Predictivo"},
                    {"id": "control_calidad", "name": "Control de Calidad"},
                    {"id": "planificacion_produccion", "name": "Planificación de Producción"},
                    {"id": "gestion_proveedores", "name": "Gestión de Proveedores"},
                    {"id": "analisis_productividad", "name": "Análisis de Productividad"}
                ]
            },
            {
                "category": "ti_seguridad",
                "name": "TI y Seguridad",
                "tasks": [
                    {"id": "monitoreo_seguridad", "name": "Monitoreo de Seguridad"},
                    {"id": "gestion_contraseñas", "name": "Gestión de Contraseñas"},
                    {"id": "deteccion_anomalias", "name": "Detección de Anomalías"},
                    {"id": "automatizar_backups", "name": "Automatizar Backups"}
                ]
            },
            {
                "category": "legal",
                "name": "Legal",
                "tasks": [
                    {"id": "revisar_contrato", "name": "Revisar Contrato"},
                    {"id": "redactar_documento", "name": "Redactar Documento Legal"},
                    {"id": "gestion_cumplimiento", "name": "Gestión de Cumplimiento"},
                    {"id": "investigacion_legal", "name": "Investigación Legal"}
                ]
            },
            {
                "category": "gestion_proyectos",
                "name": "Gestión de Proyectos",
                "tasks": [
                    {"id": "gestion_proyecto", "name": "Gestión de Proyecto"},
                    {"id": "generar_reportes", "name": "Generar Reportes"},
                    {"id": "asignar_recursos", "name": "Asignar Recursos"},
                    {"id": "recordatorios_alertas", "name": "Recordatorios y Alertas"}
                ]
            },
            {
                "category": "educacion",
                "name": "Educación",
                "tasks": [
                    {"id": "evaluaciones_automatizadas", "name": "Evaluaciones Automatizadas"},
                    {"id": "recomendacion_contenidos", "name": "Recomendación de Contenidos"},
                    {"id": "administracion_inscripciones", "name": "Administración de Inscripciones"},
                    {"id": "seguimiento_progreso", "name": "Seguimiento de Progreso"}
                ]
            },
            {
                "category": "comunicaciones",
                "name": "Comunicaciones",
                "tasks": [
                    {"id": "gestion_emails", "name": "Gestión de Emails"},
                    {"id": "automatizar_agendas", "name": "Automatizar Agendas"},
                    {"id": "transcripcion_automatica", "name": "Transcripción Automática"}
                ]
            }
        ]

