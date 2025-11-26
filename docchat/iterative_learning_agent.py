"""
Iterative Learning Agent - Agentes que aprenden iterativamente.

Implementa el ciclo: Leer → Generar Hipótesis → Probar → Aprender → Actualizar Entendimiento
Basado en el concepto de ChemCrow y agentes científicos que Eric Schmidt menciona.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.documents import Document

from .config import AppConfig
from .utils.llm_factory import create_llm


@dataclass
class Hypothesis:
    """Hipótesis generada por el agente."""
    id: str
    description: str
    reasoning: str
    test_method: str
    expected_result: str
    status: str = "pending"  # pending, testing, passed, failed
    test_result: Optional[str] = None
    learned_insights: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class LearningCycle:
    """Ciclo completo de aprendizaje."""
    cycle_id: str
    topic: str
    documents_read: List[str]
    principles_discovered: List[str]
    hypotheses: List[Hypothesis]
    tests_performed: List[Dict[str, Any]]
    insights_learned: List[str]
    updated_understanding: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class IterativeLearningAgent:
    """
    Agente que aprende iterativamente siguiendo el ciclo científico:
    1. Leer y descubrir principios
    2. Generar hipótesis
    3. Probar hipótesis
    4. Aprender de resultados
    5. Actualizar entendimiento
    """
    
    def __init__(self, config: AppConfig, provider: str = "openai"):
        self.config = config
        self.provider = provider
        
        # LLM principal para razonamiento
        self.llm = create_llm(
            provider=provider,
            model=config.agentic_model or "gpt-4o",
            temperature=0.3,  # Balance entre creatividad y precisión
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=8000,
            request_timeout=180
        )
        
        # Directorio para almacenar ciclos de aprendizaje
        self.data_dir = Path(config.memory_dir) / "iterative_learning"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Historial de ciclos de aprendizaje
        self.learning_cycles: Dict[str, LearningCycle] = {}
        
        # Entendimiento acumulado por dominio
        self.domain_knowledge: Dict[str, str] = {}
    
    def start_learning_cycle(
        self,
        topic: str,
        documents: List[Document],
        domain: str = "general",
        max_hypotheses: int = 5,
        test_executor: Optional[Callable] = None
    ) -> LearningCycle:
        """
        Inicia un ciclo de aprendizaje iterativo.
        
        Args:
            topic: Tema o pregunta a investigar
            documents: Documentos para leer y analizar
            domain: Dominio del conocimiento (ej: "chemistry", "physics", "business")
            max_hypotheses: Máximo de hipótesis a generar
            test_executor: Función opcional para ejecutar tests personalizados
        
        Returns:
            LearningCycle con todo el proceso
        """
        cycle_id = f"cycle_{int(time.time())}"
        
        print(f"\n{'='*60}")
        print(f"🧠 INICIANDO CICLO DE APRENDIZAJE ITERATIVO")
        print(f"{'='*60}")
        print(f"📚 Tema: {topic}")
        print(f"📄 Documentos: {len(documents)}")
        print(f"🔬 Dominio: {domain}\n")
        
        # Paso 1: Leer y descubrir principios
        print("📖 Paso 1: Leyendo documentos y descubriendo principios...")
        principles = self._discover_principles(topic, documents, domain)
        print(f"   ✅ Principios descubiertos: {len(principles)}\n")
        
        # Paso 2: Generar hipótesis
        print("💡 Paso 2: Generando hipótesis basadas en principios...")
        hypotheses = self._generate_hypotheses(topic, principles, domain, max_hypotheses)
        print(f"   ✅ Hipótesis generadas: {len(hypotheses)}\n")
        
        # Paso 3: Probar hipótesis
        print("🧪 Paso 3: Probando hipótesis...")
        tested_hypotheses = []
        for i, hyp in enumerate(hypotheses, 1):
            print(f"   [{i}/{len(hypotheses)}] Probando: {hyp.description[:60]}...")
            tested_hyp = self._test_hypothesis(hyp, topic, domain, test_executor)
            tested_hypotheses.append(tested_hyp)
            if tested_hyp.status == "passed":
                print(f"      ✅ Hipótesis pasó la prueba")
            else:
                print(f"      ❌ Hipótesis falló: {tested_hyp.test_result[:80] if tested_hyp.test_result else 'Sin resultado'}")
        print()
        
        # Paso 4: Aprender de resultados
        print("📚 Paso 4: Aprendiendo de los resultados...")
        insights = self._extract_insights(tested_hypotheses, topic, domain)
        print(f"   ✅ Insights extraídos: {len(insights)}\n")
        
        # Paso 5: Actualizar entendimiento
        print("🔄 Paso 5: Actualizando entendimiento del dominio...")
        updated_understanding = self._update_understanding(domain, principles, insights, tested_hypotheses)
        print(f"   ✅ Entendimiento actualizado\n")
        
        # Crear ciclo completo
        cycle = LearningCycle(
            cycle_id=cycle_id,
            topic=topic,
            documents_read=[doc.metadata.get("source", "unknown") for doc in documents],
            principles_discovered=principles,
            hypotheses=tested_hypotheses,
            tests_performed=[self._hypothesis_to_dict(h) for h in tested_hypotheses],
            insights_learned=insights,
            updated_understanding=updated_understanding
        )
        
        # Guardar ciclo
        self.learning_cycles[cycle_id] = cycle
        self._save_cycle(cycle)
        
        # Actualizar conocimiento del dominio
        self.domain_knowledge[domain] = updated_understanding
        
        print(f"{'='*60}")
        print(f"✅ CICLO DE APRENDIZAJE COMPLETADO")
        print(f"{'='*60}\n")
        
        return cycle
    
    def _discover_principles(self, topic: str, documents: List[Document], domain: str) -> List[str]:
        """Descubre principios fundamentales de los documentos."""
        # Combinar contenido de documentos
        content = "\n\n".join([doc.page_content for doc in documents[:10]])  # Limitar a 10 docs
        
        # Obtener conocimiento previo del dominio si existe
        prior_knowledge = self.domain_knowledge.get(domain, "")
        
        prompt = f"""Eres un agente científico experto en descubrir principios fundamentales.

DOMINIO: {domain}
TEMA DE INVESTIGACIÓN: {topic}

CONOCIMIENTO PREVIO DEL DOMINIO:
{prior_knowledge[:2000] if prior_knowledge else "Ninguno (primera vez investigando este dominio)"}

DOCUMENTOS PARA ANALIZAR:
{content[:50000]}

INSTRUCCIONES:
1. Analiza los documentos cuidadosamente
2. Identifica los PRINCIPIOS FUNDAMENTALES que se pueden extraer
3. Los principios deben ser:
   - Generales y aplicables
   - Basados en evidencia de los documentos
   - Útiles para generar hipótesis
   - Relacionados con el tema de investigación

FORMATO DE RESPUESTA (JSON):
{{
    "principles": [
        "Principio 1: Descripción clara y concisa",
        "Principio 2: Descripción clara y concisa",
        ...
    ],
    "reasoning": "Explicación de cómo descubriste estos principios"
}}

Genera los principios ahora:"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            
            # Extraer JSON
            json_match = self._extract_json(response)
            if json_match:
                data = json.loads(json_match)
                return data.get("principles", [])
            else:
                # Fallback: extraer principios de texto
                lines = response.split('\n')
                principles = []
                for line in lines:
                    if 'principio' in line.lower() or 'principle' in line.lower() or line.strip().startswith('-'):
                        clean_line = line.strip().lstrip('- ').strip()
                        if len(clean_line) > 20:
                            principles.append(clean_line)
                return principles[:10]  # Máximo 10 principios
        except Exception as e:
            print(f"   ⚠️ Error descubriendo principios: {e}")
            return [f"Principio básico extraído de documentos sobre {topic}"]
    
    def _generate_hypotheses(
        self,
        topic: str,
        principles: List[str],
        domain: str,
        max_hypotheses: int
    ) -> List[Hypothesis]:
        """Genera hipótesis basadas en principios descubiertos."""
        principles_text = "\n".join([f"{i+1}. {p}" for i, p in enumerate(principles)])
        
        prompt = f"""Eres un científico generando hipótesis testables.

DOMINIO: {domain}
TEMA: {topic}

PRINCIPIOS DESCUBIERTOS:
{principles_text}

INSTRUCCIONES:
1. Genera {max_hypotheses} hipótesis testables basadas en estos principios
2. Cada hipótesis debe:
   - Ser específica y medible
   - Tener un método de prueba claro
   - Tener un resultado esperado definido
   - Estar basada en los principios descubiertos

FORMATO DE RESPUESTA (JSON):
{{
    "hypotheses": [
        {{
            "description": "Descripción clara de la hipótesis",
            "reasoning": "Por qué esta hipótesis es válida basada en los principios",
            "test_method": "Método específico para probar esta hipótesis",
            "expected_result": "Qué resultado esperamos si la hipótesis es correcta"
        }},
        ...
    ]
}}

Genera las hipótesis ahora:"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                hypotheses_data = data.get("hypotheses", [])
                
                hypotheses = []
                for i, hyp_data in enumerate(hypotheses_data[:max_hypotheses], 1):
                    hyp = Hypothesis(
                        id=f"hyp_{int(time.time())}_{i}",
                        description=hyp_data.get("description", ""),
                        reasoning=hyp_data.get("reasoning", ""),
                        test_method=hyp_data.get("test_method", ""),
                        expected_result=hyp_data.get("expected_result", ""),
                        status="pending"
                    )
                    hypotheses.append(hyp)
                
                return hypotheses
            else:
                # Fallback: generar hipótesis básicas
                return [
                    Hypothesis(
                        id=f"hyp_{int(time.time())}_1",
                        description=f"Hipótesis sobre {topic} basada en principios descubiertos",
                        reasoning="Basada en los principios analizados",
                        test_method="Análisis de datos y verificación",
                        expected_result="Confirmación de la hipótesis",
                        status="pending"
                    )
                ]
        except Exception as e:
            print(f"   ⚠️ Error generando hipótesis: {e}")
            return []
    
    def _test_hypothesis(
        self,
        hypothesis: Hypothesis,
        topic: str,
        domain: str,
        test_executor: Optional[Callable] = None
    ) -> Hypothesis:
        """Prueba una hipótesis."""
        hypothesis.status = "testing"
        
        # Si hay un test executor personalizado, usarlo
        if test_executor:
            try:
                result = test_executor(hypothesis)
                hypothesis.test_result = str(result)
                hypothesis.status = "passed" if result else "failed"
                return hypothesis
            except Exception as e:
                hypothesis.test_result = f"Error en test personalizado: {str(e)}"
                hypothesis.status = "failed"
                return hypothesis
        
        # Test automático usando LLM para simular/analizar
        prompt = f"""Eres un científico probando una hipótesis.

DOMINIO: {domain}
TEMA: {topic}

HIPÓTESIS A PROBAR:
Descripción: {hypothesis.description}
Razonamiento: {hypothesis.reasoning}
Método de prueba: {hypothesis.test_method}
Resultado esperado: {hypothesis.expected_result}

INSTRUCCIONES:
1. Analiza si la hipótesis es válida según el método de prueba
2. Simula o analiza el resultado del test
3. Determina si la hipótesis pasa o falla
4. Explica el resultado detalladamente

FORMATO DE RESPUESTA (JSON):
{{
    "status": "passed" o "failed",
    "test_result": "Resultado detallado de la prueba",
    "reasoning": "Por qué pasó o falló",
    "confidence": 0.0-1.0
}}

Prueba la hipótesis ahora:"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                hypothesis.status = data.get("status", "failed")
                hypothesis.test_result = data.get("test_result", "")
                hypothesis.learned_insights = data.get("reasoning", "")
            else:
                # Fallback: marcar como pendiente de prueba real
                hypothesis.status = "pending"
                hypothesis.test_result = "Requiere prueba experimental real"
            
            return hypothesis
        except Exception as e:
            hypothesis.status = "failed"
            hypothesis.test_result = f"Error probando hipótesis: {str(e)}"
            return hypothesis
    
    def _extract_insights(
        self,
        hypotheses: List[Hypothesis],
        topic: str,
        domain: str
    ) -> List[str]:
        """Extrae insights aprendidos de las hipótesis probadas."""
        passed_hypotheses = [h for h in hypotheses if h.status == "passed"]
        failed_hypotheses = [h for h in hypotheses if h.status == "failed"]
        
        hypotheses_summary = "\n".join([
            f"- {h.description} ({'✅ PASÓ' if h.status == 'passed' else '❌ FALLÓ'}): {h.test_result or 'Sin resultado'}"
            for h in hypotheses
        ])
        
        prompt = f"""Eres un científico extrayendo insights de experimentos.

DOMINIO: {domain}
TEMA: {topic}

HIPÓTESIS PROBADAS:
{hypotheses_summary}

INSTRUCCIONES:
1. Analiza todos los resultados de las pruebas
2. Extrae insights clave aprendidos
3. Identifica patrones y lecciones
4. Genera conocimiento nuevo basado en los resultados

FORMATO DE RESPUESTA (JSON):
{{
    "insights": [
        "Insight 1: Descripción clara del aprendizaje",
        "Insight 2: Descripción clara del aprendizaje",
        ...
    ],
    "patterns": "Patrones observados en los resultados",
    "lessons": "Lecciones aprendidas"
}}

Extrae los insights ahora:"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                insights = data.get("insights", [])
                if data.get("patterns"):
                    insights.append(f"Patrón observado: {data['patterns']}")
                if data.get("lessons"):
                    insights.append(f"Lección aprendida: {data['lessons']}")
                return insights
            else:
                return [f"Se aprendió sobre {topic} a través de {len(passed_hypotheses)} hipótesis exitosas"]
        except Exception as e:
            print(f"   ⚠️ Error extrayendo insights: {e}")
            return [f"Insights básicos sobre {topic}"]
    
    def _update_understanding(
        self,
        domain: str,
        principles: List[str],
        insights: List[str],
        hypotheses: List[Hypothesis]
    ) -> str:
        """Actualiza el entendimiento del dominio con nuevo conocimiento."""
        prior = self.domain_knowledge.get(domain, "")
        
        principles_text = "\n".join([f"- {p}" for p in principles])
        insights_text = "\n".join([f"- {i}" for i in insights])
        passed_count = len([h for h in hypotheses if h.status == "passed"])
        
        prompt = f"""Actualiza el conocimiento del dominio con nueva información aprendida.

DOMINIO: {domain}

CONOCIMIENTO PREVIO:
{prior[:3000] if prior else "Ninguno"}

NUEVOS PRINCIPIOS DESCUBIERTOS:
{principles_text}

NUEVOS INSIGHTS APRENDIDOS:
{insights_text}

HIPÓTESIS EXITOSAS: {passed_count}/{len(hypotheses)}

INSTRUCCIONES:
1. Integra el nuevo conocimiento con el conocimiento previo
2. Actualiza o refina principios existentes si es necesario
3. Agrega nuevos insights de forma estructurada
4. Crea un resumen comprensivo del entendimiento actualizado del dominio

FORMATO: Texto estructurado y claro que represente el entendimiento completo del dominio.

Actualiza el entendimiento ahora:"""
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            return response
        except Exception as e:
            print(f"   ⚠️ Error actualizando entendimiento: {e}")
            return f"Entendimiento básico de {domain} con {len(principles)} principios y {len(insights)} insights"
    
    def _hypothesis_to_dict(self, hyp: Hypothesis) -> Dict[str, Any]:
        """Convierte Hypothesis a dict para serialización."""
        return {
            "id": hyp.id,
            "description": hyp.description,
            "reasoning": hyp.reasoning,
            "test_method": hyp.test_method,
            "expected_result": hyp.expected_result,
            "status": hyp.status,
            "test_result": hyp.test_result,
            "learned_insights": hyp.learned_insights,
            "timestamp": hyp.timestamp
        }
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extrae JSON de un texto."""
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        return None
    
    def _save_cycle(self, cycle: LearningCycle):
        """Guarda un ciclo de aprendizaje."""
        cycle_file = self.data_dir / f"{cycle.cycle_id}.json"
        cycle_dict = {
            "cycle_id": cycle.cycle_id,
            "topic": cycle.topic,
            "documents_read": cycle.documents_read,
            "principles_discovered": cycle.principles_discovered,
            "hypotheses": [self._hypothesis_to_dict(h) for h in cycle.hypotheses],
            "tests_performed": cycle.tests_performed,
            "insights_learned": cycle.insights_learned,
            "updated_understanding": cycle.updated_understanding,
            "timestamp": cycle.timestamp
        }
        
        with open(cycle_file, 'w', encoding='utf-8') as f:
            json.dump(cycle_dict, f, indent=2, ensure_ascii=False)
    
    def get_domain_knowledge(self, domain: str) -> str:
        """Obtiene el conocimiento acumulado de un dominio."""
        return self.domain_knowledge.get(domain, "No hay conocimiento previo de este dominio")
    
    def get_learning_history(self, domain: Optional[str] = None) -> List[LearningCycle]:
        """Obtiene historial de ciclos de aprendizaje."""
        if domain:
            # Filtrar por dominio si se especifica
            return [c for c in self.learning_cycles.values() if domain in c.topic.lower()]
        return list(self.learning_cycles.values())

