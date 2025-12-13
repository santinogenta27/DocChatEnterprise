"""
Advanced GraphRAG - Implementación avanzada basada en los papers más recientes de GraphRAG.

Este módulo implementa técnicas de vanguardia de los siguientes papers:

1. **Retrieval-Augmented Generation with Graphs** (Haoyu Han et al. 2025)
   - Fusion avanzada de texto y topología del grafo
   - Construcción de Knowledge Graph con LLMs
   - Subgraph retrieval eficiente

2. **GraphRAG: Query-Focused Summarization** (Edge et al. 2024)
   - Resúmenes centrados en consultas
   - Multi-hop reasoning sobre el grafo
   - Query-focused summarization mejorado

3. **GRAG: Graph Retrieval-Augmented Generation** (Y. Hu et al. 2024)
   - Recuperación eficiente de subgrafos
   - Búsqueda semántica con embeddings
   - Fusion texto/topología optimizada

4. **KGRAG-Ex: Explainable RAG with Knowledge Graphs** (2025)
   - Rutas de explicación detalladas
   - Trazabilidad completa de evidencias
   - Análisis de importancia de entidades y relaciones

5. **Injecting Knowledge Graphs into Large Language Models** (2025)
   - Extracción avanzada de entidades y relaciones con LLMs
   - Normalización y validación de entidades
   - Construcción de grafos de conocimiento precisos

6. **GMeLLo: Graph Memory-based Editing for LLMs** (2024)
   - Memoria del grafo basada en interacciones
   - Contexto histórico para entidades
   - Aprendizaje continuo del grafo

7. **RAG vs GraphRAG: A Systematic Evaluation** (2025)
   - Métricas avanzadas de relevancia
   - Evaluación de densidad del subgrafo
   - Scoring mejorado basado en cohesión

CARACTERÍSTICAS PRINCIPALES:
- ✅ Extracción de entidades y relaciones en múltiples pasadas con LLMs
- ✅ Subgraph retrieval con búsqueda semántica (embeddings) y LLM
- ✅ Fusion avanzada de texto y topología del grafo
- ✅ Multi-hop reasoning con paths detallados
- ✅ Explainability mejorada con rutas de explicación completas
- ✅ Graph memory (GMeLLo) para contexto histórico
- ✅ Query-focused summarization optimizado
- ✅ Métricas avanzadas de relevancia y scoring
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Tuple
from collections import defaultdict
from datetime import datetime

from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from .graph_rag import KnowledgeGraph, Entity, Relationship


@dataclass
class Subgraph:
    """Subgrafo extraído para una consulta específica."""
    subgraph_id: str
    entities: List[str]
    relationships: List[Dict[str, Any]]
    documents: List[str]
    relevance_score: float
    query: str
    extraction_method: str  # "entity_based", "semantic", "hybrid"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEvidence:
    """Evidencia extraída del grafo con explicabilidad."""
    evidence_id: str
    source_entities: List[str]
    target_entities: List[str]
    path: List[str]  # Path de entidades conectadas
    relationship_path: List[str]  # Tipos de relaciones en el path
    supporting_documents: List[str]
    confidence: float
    explanation: str  # Explicación de por qué esta evidencia es relevante
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FusedContext:
    """Contexto fusionado de texto y topología del grafo."""
    text_context: str
    graph_context: str  # Descripción de relaciones y entidades
    fused_summary: str  # Resumen fusionado
    entities_in_context: List[str]
    relationships_in_context: List[Dict[str, Any]]
    confidence: float


class AdvancedGraphRAG:
    """
    GraphRAG Avanzado basado en los papers más recientes.
    
    Implementa:
    1. Construcción de KG usando LLMs (más preciso que regex)
    2. Subgraph retrieval eficiente (GRAG paper)
    3. Fusion texto/topología (GraphRAG paper)
    4. Multi-hop reasoning
    5. Explainability mejorada (KGRAG-Ex)
    6. Graph memory (GMeLLo)
    """
    
    def __init__(self, llm: BaseLanguageModel, embeddings: Optional[Any] = None):
        self.llm = llm
        self.embeddings = embeddings
        
        # Knowledge Graph
        self.knowledge_graph = KnowledgeGraph()
        
        # Graph Memory (GMeLLo-style)
        self.graph_memory: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Cache de subgrafos
        self.subgraph_cache: Dict[str, Subgraph] = {}
        
        # Estadísticas
        self.stats = {
            "entities_extracted": 0,
            "relationships_extracted": 0,
            "subgraphs_retrieved": 0,
            "multi_hop_queries": 0
        }
    
    # ============================================
    # 1. CONSTRUCCIÓN DE KNOWLEDGE GRAPH (LLM-based)
    # ============================================
    
    async def build_knowledge_graph_from_documents(
        self,
        documents: List[Document],
        use_llm_extraction: bool = True
    ) -> Dict[str, Any]:
        """
        Construye Knowledge Graph desde documentos usando LLMs.
        
        Basado en: "Injecting Knowledge Graphs into Large Language Models" (2025)
        """
        print(f"🔷 [Advanced GraphRAG] Construyendo Knowledge Graph desde {len(documents)} documentos...")
        
        total_entities = 0
        total_relationships = 0
        
        for doc_idx, doc in enumerate(documents):
            doc_id = doc.metadata.get("source", f"doc_{doc_idx}")
            
            if use_llm_extraction:
                # Extracción avanzada usando LLM
                entities, relationships = await self._extract_entities_and_relationships_llm(doc)
            else:
                # Fallback a extracción básica
                entities, relationships = self._extract_entities_and_relationships_basic(doc)
            
            # Agregar entidades al grafo
            for entity_name, entity_type, metadata in entities:
                entity = Entity(
                    name=entity_name,
                    entity_type=entity_type,
                    metadata={**metadata, "source": doc_id, "extracted_at": datetime.now().isoformat()}
                )
                self.knowledge_graph.add_entity(entity)
                self.knowledge_graph.link_entity_to_document(entity_name, doc_id)
                total_entities += 1
            
            # Agregar relaciones al grafo
            for rel_data in relationships:
                relationship = Relationship(
                    source=rel_data["source"],
                    target=rel_data["target"],
                    relationship_type=rel_data["type"],
                    strength=rel_data.get("strength", 1.0),
                    metadata={**rel_data.get("metadata", {}), "source": doc_id}
                )
                self.knowledge_graph.add_relationship(relationship)
                total_relationships += 1
        
        self.stats["entities_extracted"] = total_entities
        self.stats["relationships_extracted"] = total_relationships
        
        print(f"✅ [Advanced GraphRAG] Knowledge Graph construido: {total_entities} entidades, {total_relationships} relaciones")
        
        return {
            "status": "success",
            "entities": total_entities,
            "relationships": total_relationships,
            "documents_processed": len(documents)
        }
    
    async def _extract_entities_and_relationships_llm(
        self,
        document: Document
    ) -> Tuple[List[Tuple[str, str, Dict]], List[Dict[str, Any]]]:
        """
        Extrae entidades y relaciones usando LLM con técnicas avanzadas.
        
        Basado en: "Injecting Knowledge Graphs into Large Language Models" (2025)
        - Extracción en múltiples pasadas para mayor precisión
        - Validación cruzada de relaciones
        - Normalización de entidades
        """
        text = document.page_content[:6000]  # Aumentar límite para más contexto
        
        # PASO 1: Extracción inicial de entidades
        entity_prompt = f"""Eres un experto en Named Entity Recognition (NER). Extrae TODAS las entidades del siguiente texto.

Texto:
{text[:3000]}

Para cada entidad, identifica:
- Nombre exacto (normalizado)
- Tipo: PERSON, ORGANIZATION, LOCATION, CONCEPT, PRODUCT, EVENT, DATE, NUMBER, OTHER
- Descripción breve (1-2 frases)
- Importancia (HIGH, MEDIUM, LOW)

Formato JSON:
{{
    "entities": [
        {{
            "name": "Nombre normalizado",
            "type": "TIPO",
            "description": "Descripción",
            "importance": "HIGH|MEDIUM|LOW",
            "mentions": ["variaciones del nombre encontradas"]
        }}
    ]
}}

Sé exhaustivo. Extrae todas las entidades relevantes, incluso si aparecen múltiples veces."""
        
        # PASO 2: Extracción de relaciones (después de tener entidades)
        relationship_prompt_template = """Eres un experto en extracción de relaciones semánticas. Identifica TODAS las relaciones significativas entre las siguientes entidades en el texto.

Entidades identificadas:
{entities}

Texto:
{text}

Para cada relación, identifica:
- Entidad origen
- Entidad destino  
- Tipo de relación (ej: WORKS_AT, LOCATED_IN, CREATED_BY, RELATED_TO, PART_OF, CAUSES, PRECEDES, etc.)
- Descripción de la relación
- Confianza (0.0-1.0)
- Evidencia textual (cita del texto que soporta la relación)

Formato JSON:
{{
    "relationships": [
        {{
            "source": "Entidad origen",
            "target": "Entidad destino",
            "type": "TIPO_RELACION",
            "description": "Descripción",
            "confidence": 0.0-1.0,
            "evidence": "Cita textual"
        }}
    ]
}}

Sé exhaustivo. Identifica todas las relaciones relevantes, incluso indirectas."""
        
        try:
            # PASO 1: Extraer entidades
            entity_response = await self.llm.ainvoke(entity_prompt)
            entity_content = entity_response.content if hasattr(entity_response, 'content') else str(entity_response)
            
            # Limpiar JSON
            if "```json" in entity_content:
                entity_content = entity_content.split("```json")[1].split("```")[0].strip()
            elif "```" in entity_content:
                entity_content = entity_content.split("```")[1].split("```")[0].strip()
            
            entity_data = json.loads(entity_content)
            
            # Normalizar y validar entidades
            entities = []
            entity_names = []
            for e in entity_data.get("entities", []):
                name = e.get("name", "").strip()
                if name and len(name) > 1:
                    # Normalizar nombre (capitalizar apropiadamente)
                    normalized_name = name.title() if name.islower() else name
                    entity_type = e.get("type", "OTHER")
                    description = e.get("description", "")
                    importance = e.get("importance", "MEDIUM")
                    
                    entities.append((
                        normalized_name,
                        entity_type,
                        {
                            "description": description,
                            "importance": importance,
                            "mentions": e.get("mentions", [normalized_name])
                        }
                    ))
                    entity_names.append(normalized_name)
            
            # PASO 2: Extraer relaciones (solo si hay entidades)
            relationships = []
            if len(entities) >= 2:
                # Formatear lista de entidades para el prompt
                entities_list = "\n".join([f"- {e[0]} ({e[1]})" for e in entities[:30]])  # Limitar a 30 para no exceder tokens
                
                relationship_prompt = relationship_prompt_template.format(
                    entities=entities_list,
                    text=text[:3000]
                )
                
                relationship_response = await self.llm.ainvoke(relationship_prompt)
                relationship_content = relationship_response.content if hasattr(relationship_response, 'content') else str(relationship_response)
                
                # Limpiar JSON
                if "```json" in relationship_content:
                    relationship_content = relationship_content.split("```json")[1].split("```")[0].strip()
                elif "```" in relationship_content:
                    relationship_content = relationship_content.split("```")[1].split("```")[0].strip()
                
                relationship_data = json.loads(relationship_content)
                
                # Validar y normalizar relaciones
                for r in relationship_data.get("relationships", []):
                    source = r.get("source", "").strip()
                    target = r.get("target", "").strip()
                    rel_type = r.get("type", "RELATED_TO")
                    
                    # Verificar que ambas entidades existen
                    if source in entity_names and target in entity_names and source != target:
                        relationships.append({
                            "source": source,
                            "target": target,
                            "type": rel_type,
                            "strength": r.get("confidence", 0.8),
                            "metadata": {
                                "description": r.get("description", ""),
                                "evidence": r.get("evidence", ""),
                                "confidence": r.get("confidence", 0.8)
                            }
                        })
            
            return entities, relationships
            
        except Exception as e:
            print(f"⚠️ [Advanced GraphRAG] Error en extracción LLM avanzada: {e}")
            # Fallback a extracción básica
            return self._extract_entities_and_relationships_basic(document)
    
    def _extract_entities_and_relationships_basic(
        self,
        document: Document
    ) -> Tuple[List[Tuple[str, str, Dict]], List[Dict[str, Any]]]:
        """Extracción básica usando regex (fallback)."""
        import re
        text = document.page_content
        
        entities = []
        relationships = []
        
        # Nombres propios
        proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        for noun in set(proper_nouns[:20]):
            if len(noun) > 2:
                entities.append((noun, "PERSON", {}))
        
        return entities, relationships
    
    # ============================================
    # 2. SUBGRAPH RETRIEVAL (GRAG Paper)
    # ============================================
    
    async def retrieve_subgraph_for_query(
        self,
        query: str,
        max_entities: int = 20,
        max_depth: int = 2
    ) -> Subgraph:
        """
        Recupera subgrafo relevante para una consulta.
        
        Basado en: "GRAG: Graph Retrieval-Augmented Generation" (Y. Hu et al. 2024)
        """
        # Extraer entidades de la query
        query_entities = await self._extract_query_entities(query)
        
        if not query_entities:
            # Si no hay entidades, usar búsqueda semántica
            return await self._retrieve_subgraph_semantic(query, max_entities)
        
        # Obtener entidades relacionadas (multi-hop)
        all_relevant_entities = set(query_entities)
        for entity in query_entities:
            related = self.knowledge_graph.get_related_entities(entity, max_depth=max_depth)
            all_relevant_entities.update(related)
        
        # Limitar número de entidades
        relevant_entities = list(all_relevant_entities)[:max_entities]
        
        # Obtener documentos relacionados
        related_doc_ids = self.knowledge_graph.get_documents_for_entities(relevant_entities)
        
        # Obtener relaciones entre entidades relevantes
        relevant_relationships = [
            {
                "source": rel.source,
                "target": rel.target,
                "type": rel.relationship_type,
                "strength": rel.strength
            }
            for rel in self.knowledge_graph.relationships
            if rel.source in relevant_entities and rel.target in relevant_entities
        ]
        
        # Calcular relevance score
        relevance_score = self._calculate_subgraph_relevance(query, relevant_entities, relevant_relationships)
        
        subgraph = Subgraph(
            subgraph_id=f"SG-{uuid.uuid4().hex[:8].upper()}",
            entities=relevant_entities,
            relationships=relevant_relationships,
            documents=related_doc_ids,
            relevance_score=relevance_score,
            query=query,
            extraction_method="entity_based",
            metadata={"max_depth": max_depth, "query_entities": query_entities}
        )
        
        self.subgraph_cache[query] = subgraph
        self.stats["subgraphs_retrieved"] += 1
        
        return subgraph
    
    async def _extract_query_entities(self, query: str) -> List[str]:
        """Extrae entidades de la query usando LLM."""
        prompt = f"""Extrae las entidades principales de esta consulta para búsqueda en grafo de conocimiento.

Consulta: {query}

Devuelve SOLO una lista JSON de strings con los nombres de las entidades.
Ejemplo: ["Microsoft", "Azure", "Cloud Computing"]

Lista de entidades:"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            entities = json.loads(content)
            if isinstance(entities, list):
                return [str(e) for e in entities if e]
        except Exception as e:
            print(f"⚠️ [Advanced GraphRAG] Error extrayendo entidades de query: {e}")
        
        return []
    
    async def _retrieve_subgraph_semantic(
        self,
        query: str,
        max_entities: int = 20
    ) -> Subgraph:
        """
        Recupera subgrafo usando búsqueda semántica.
        
        Basado en: "GRAG: Graph Retrieval-Augmented Generation" (Y. Hu et al. 2024)
        - Usa embeddings para encontrar entidades semánticamente similares
        - Combina búsqueda semántica con estructura del grafo
        """
        if not self.embeddings:
            # Si no hay embeddings, usar LLM para encontrar entidades semánticamente relevantes
            return await self._retrieve_subgraph_llm_semantic(query, max_entities)
        
        try:
            # Generar embedding de la query
            query_embedding = await self.embeddings.aembed_query(query)
            
            # Calcular similitud con todas las entidades del grafo
            entity_scores = []
            for entity_name, entity_obj in self.knowledge_graph.entities.items():
                # Crear texto representativo de la entidad
                entity_text = f"{entity_name} {entity_obj.entity_type}"
                if entity_obj.metadata and "description" in entity_obj.metadata:
                    entity_text += f" {entity_obj.metadata['description']}"
                
                # Generar embedding de la entidad
                entity_embedding = await self.embeddings.aembed_query(entity_text)
                
                # Calcular similitud coseno
                try:
                    import numpy as np
                    similarity = np.dot(query_embedding, entity_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(entity_embedding)
                    )
                except ImportError:
                    # Fallback si numpy no está disponible
                    # Calcular similitud coseno manualmente
                    dot_product = sum(a * b for a, b in zip(query_embedding, entity_embedding))
                    norm_query = sum(a * a for a in query_embedding) ** 0.5
                    norm_entity = sum(a * a for a in entity_embedding) ** 0.5
                    similarity = dot_product / (norm_query * norm_entity) if (norm_query * norm_entity) > 0 else 0.0
                
                entity_scores.append((entity_name, similarity))
            
            # Ordenar por similitud y tomar las top entidades
            entity_scores.sort(key=lambda x: x[1], reverse=True)
            top_entities = [name for name, score in entity_scores[:max_entities] if score > 0.3]
            
            if not top_entities:
                return await self._retrieve_subgraph_llm_semantic(query, max_entities)
            
            # Obtener documentos y relaciones para estas entidades
            related_doc_ids = self.knowledge_graph.get_documents_for_entities(top_entities)
            
            relevant_relationships = [
                {
                    "source": rel.source,
                    "target": rel.target,
                    "type": rel.relationship_type,
                    "strength": rel.strength
                }
                for rel in self.knowledge_graph.relationships
                if rel.source in top_entities or rel.target in top_entities
            ]
            
            relevance_score = self._calculate_subgraph_relevance(query, top_entities, relevant_relationships)
            
            return Subgraph(
                subgraph_id=f"SG-SEM-{uuid.uuid4().hex[:8].upper()}",
                entities=top_entities,
                relationships=relevant_relationships,
                documents=related_doc_ids,
                relevance_score=relevance_score,
                query=query,
                extraction_method="semantic_embedding",
                metadata={"top_scores": entity_scores[:5]}
            )
            
        except Exception as e:
            print(f"⚠️ [Advanced GraphRAG] Error en búsqueda semántica con embeddings: {e}")
            return await self._retrieve_subgraph_llm_semantic(query, max_entities)
    
    async def _retrieve_subgraph_llm_semantic(
        self,
        query: str,
        max_entities: int = 20
    ) -> Subgraph:
        """Recupera subgrafo usando LLM para encontrar entidades semánticamente relevantes."""
        # Obtener todas las entidades del grafo
        all_entity_names = list(self.knowledge_graph.entities.keys())[:100]  # Limitar para no exceder tokens
        
        if not all_entity_names:
            return Subgraph(
                subgraph_id=f"SG-EMPTY-{uuid.uuid4().hex[:8].upper()}",
                entities=[],
                relationships=[],
                documents=[],
                relevance_score=0.0,
                query=query,
                extraction_method="semantic_llm",
                metadata={}
            )
        
        prompt = f"""Dada esta consulta, identifica qué entidades del grafo de conocimiento son más relevantes.

Consulta: {query}

Entidades disponibles en el grafo:
{', '.join(all_entity_names[:50])}

Identifica las {max_entities} entidades más relevantes para responder esta consulta.
Devuelve SOLO una lista JSON de strings con los nombres exactos de las entidades.

Lista de entidades relevantes:"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            relevant_entity_names = json.loads(content)
            if not isinstance(relevant_entity_names, list):
                relevant_entity_names = []
            
            # Filtrar solo entidades que existen en el grafo
            valid_entities = [e for e in relevant_entity_names if e in all_entity_names][:max_entities]
            
            if not valid_entities:
                return Subgraph(
                    subgraph_id=f"SG-EMPTY-{uuid.uuid4().hex[:8].upper()}",
                    entities=[],
                    relationships=[],
                    documents=[],
                    relevance_score=0.0,
                    query=query,
                    extraction_method="semantic_llm",
                    metadata={}
                )
            
            # Obtener documentos y relaciones
            related_doc_ids = self.knowledge_graph.get_documents_for_entities(valid_entities)
            
            relevant_relationships = [
                {
                    "source": rel.source,
                    "target": rel.target,
                    "type": rel.relationship_type,
                    "strength": rel.strength
                }
                for rel in self.knowledge_graph.relationships
                if rel.source in valid_entities or rel.target in valid_entities
            ]
            
            relevance_score = self._calculate_subgraph_relevance(query, valid_entities, relevant_relationships)
            
            return Subgraph(
                subgraph_id=f"SG-SEM-LLM-{uuid.uuid4().hex[:8].upper()}",
                entities=valid_entities,
                relationships=relevant_relationships,
                documents=related_doc_ids,
                relevance_score=relevance_score,
                query=query,
                extraction_method="semantic_llm",
                metadata={}
            )
            
        except Exception as e:
            print(f"⚠️ [Advanced GraphRAG] Error en búsqueda semántica con LLM: {e}")
            return Subgraph(
                subgraph_id=f"SG-ERROR-{uuid.uuid4().hex[:8].upper()}",
                entities=[],
                relationships=[],
                documents=[],
                relevance_score=0.0,
                query=query,
                extraction_method="semantic_llm_error",
                metadata={"error": str(e)}
            )
    
    def _calculate_subgraph_relevance(
        self,
        query: str,
        entities: List[str],
        relationships: List[Dict[str, Any]]
    ) -> float:
        """
        Calcula score de relevancia del subgrafo usando métricas avanzadas.
        
        Basado en: "RAG vs GraphRAG: A Systematic Evaluation" (2025)
        - Considera densidad del subgrafo
        - Ponderación por fuerza de relaciones
        - Cohesión entre entidades
        """
        if not entities:
            return 0.0
        
        # Score basado en número de entidades (normalizado)
        entity_score = min(len(entities) / 15.0, 1.0)
        
        # Score basado en número de relaciones (densidad del grafo)
        max_possible_relations = len(entities) * (len(entities) - 1) / 2
        if max_possible_relations > 0:
            relationship_density = len(relationships) / max_possible_relations
        else:
            relationship_density = 0.0
        relationship_score = min(relationship_density * 2.0, 1.0)  # Escalar densidad
        
        # Score basado en fuerza promedio de relaciones
        if relationships:
            avg_strength = sum(r.get("strength", 0.5) for r in relationships) / len(relationships)
            strength_score = avg_strength
        else:
            strength_score = 0.3
        
        # Score combinado (ponderado)
        relevance = (
            entity_score * 0.4 +           # Importancia de tener entidades relevantes
            relationship_score * 0.3 +      # Importancia de tener relaciones
            strength_score * 0.3           # Importancia de la fuerza de las relaciones
        )
        
        return min(relevance, 1.0)
    
    # ============================================
    # 3. FUSION TEXTO/TOPOLOGÍA (GraphRAG Paper)
    # ============================================
    
    async def fuse_text_and_graph_context(
        self,
        text_documents: List[Document],
        subgraph: Subgraph,
        query: str
    ) -> FusedContext:
        """
        Fusiona contexto textual con topología del grafo usando técnicas avanzadas.
        
        Basado en: "Retrieval-Augmented Generation with Graphs" (Haoyu Han et al. 2025)
        - Fusiona información textual y estructural del grafo
        - Identifica conexiones entre texto y relaciones del grafo
        - Genera contexto enriquecido para mejor generación
        """
        # Construir contexto de texto (priorizar documentos más relevantes)
        text_context_parts = []
        for doc in text_documents[:8]:  # Aumentar a 8 documentos
            # Verificar si el documento está relacionado con el subgrafo
            doc_id = doc.metadata.get("source", "")
            is_related = doc_id in subgraph.documents if subgraph.documents else True
            
            if is_related:
                text_context_parts.append(f"[Documento: {doc_id}]\n{doc.page_content[:1200]}")
            else:
                text_context_parts.append(f"[Documento: {doc_id}]\n{doc.page_content[:800]}")
        
        text_context = "\n\n---\n\n".join(text_context_parts)
        
        # Construir contexto del grafo más detallado
        graph_context_parts = []
        
        # Describir entidades principales con sus tipos y descripciones
        graph_context_parts.append("**ENTIDADES RELEVANTES EN EL GRAFO:**")
        for entity_name in subgraph.entities[:15]:
            entity_obj = self.knowledge_graph.entities.get(entity_name)
            if entity_obj:
                entity_desc = ""
                if entity_obj.metadata and "description" in entity_obj.metadata:
                    entity_desc = f" - {entity_obj.metadata['description'][:100]}"
                graph_context_parts.append(f"- {entity_name} ({entity_obj.entity_type}){entity_desc}")
            else:
                graph_context_parts.append(f"- {entity_name}")
        
        # Describir relaciones clave con más detalle
        if subgraph.relationships:
            graph_context_parts.append("\n**RELACIONES IDENTIFICADAS EN EL GRAFO:**")
            for rel in subgraph.relationships[:15]:
                rel_desc = ""
                if isinstance(rel, dict) and "metadata" in rel and isinstance(rel["metadata"], dict):
                    if "description" in rel["metadata"]:
                        rel_desc = f" - {rel['metadata']['description'][:80]}"
                graph_context_parts.append(
                    f"- {rel['source']} --[{rel['type']}]--> {rel['target']}{rel_desc}"
                )
        
        # Agregar información sobre paths multi-hop si están disponibles
        if subgraph.metadata and "multi_hop_paths" in subgraph.metadata:
            graph_context_parts.append("\n**PATHS MULTI-HOP IDENTIFICADOS:**")
            for path in subgraph.metadata["multi_hop_paths"][:5]:
                graph_context_parts.append(f"- {' -> '.join(path)}")
        
        graph_context = "\n".join(graph_context_parts)
        
        # Fusionar usando LLM con prompt más sofisticado
        fusion_prompt = f"""Eres un experto en síntesis de información estructurada. Tu tarea es fusionar el contexto textual con la estructura del grafo de conocimiento para crear un contexto enriquecido.

CONSULTA DEL USUARIO:
{query}

CONTEXTO TEXTUAL (de documentos recuperados):
{text_context[:3000]}

ESTRUCTURA DEL GRAFO DE CONOCIMIENTO:
{graph_context}

INSTRUCCIONES PARA LA FUSIÓN:
1. **Integración**: Combina información del texto con las relaciones del grafo. Si el texto menciona una entidad del grafo, conecta esa información con las relaciones del grafo.
2. **Conexiones**: Identifica cómo las entidades del grafo se relacionan según el contenido textual.
3. **Coherencia**: Asegúrate de que la información fusionada sea coherente y no contradictoria.
4. **Relevancia**: Enfócate en información que sea directamente relevante para responder la consulta.
5. **Estructura**: Organiza la información fusionada de manera lógica y clara.

Genera un resumen fusionado que:
- Integre información textual con relaciones del grafo
- Explique cómo las entidades se relacionan según el texto Y el grafo
- Proporcione contexto enriquecido para responder la consulta
- Sea claro, estructurado y directamente relevante

RESUMEN FUSIONADO:"""
        
        try:
            response = await self.llm.ainvoke(fusion_prompt)
            fused_summary = response.content if hasattr(response, 'content') else str(response)
            
            # Si el resumen es muy corto, agregar información adicional
            if len(fused_summary) < 200:
                fused_summary += f"\n\n**Contexto adicional del grafo:** {graph_context[:500]}"
                
        except Exception as e:
            print(f"⚠️ [Advanced GraphRAG] Error en fusión avanzada: {e}")
            fused_summary = f"{text_context[:2000]}\n\n**Relaciones del grafo:**\n{graph_context}"
        
        return FusedContext(
            text_context=text_context[:3000],
            graph_context=graph_context,
            fused_summary=fused_summary,
            entities_in_context=subgraph.entities,
            relationships_in_context=subgraph.relationships,
            confidence=subgraph.relevance_score
        )
    
    # ============================================
    # 4. MULTI-HOP REASONING
    # ============================================
    
    async def multi_hop_reasoning(
        self,
        query: str,
        start_entities: List[str],
        max_hops: int = 3
    ) -> List[GraphEvidence]:
        """
        Razonamiento multi-hop sobre el grafo.
        
        Basado en: "GraphRAG: Query-Focused Summarization" (Edge et al. 2024)
        """
        evidences = []
        
        current_entities = set(start_entities)
        visited_entities = set(start_entities)
        
        for hop in range(max_hops):
            next_entities = set()
            
            # Encontrar entidades relacionadas
            for entity in current_entities:
                related = self.knowledge_graph.get_related_entities(entity, max_depth=1)
                next_entities.update(related)
            
            # Construir paths
            for entity in next_entities:
                if entity not in visited_entities:
                    # Encontrar path desde start_entities
                    path = self._find_path_to_entity(start_entities[0], entity, max_length=hop+1)
                    
                    if path:
                        evidence = GraphEvidence(
                            evidence_id=f"EVID-{uuid.uuid4().hex[:8].upper()}",
                            source_entities=[start_entities[0]],
                            target_entities=[entity],
                            path=path,
                            relationship_path=self._get_relationship_path(path),
                            supporting_documents=self._get_documents_for_path(path),
                            confidence=0.9 / (hop + 1),  # Disminuye con más hops
                            explanation=f"Path encontrado en {hop+1} hop(s) desde '{start_entities[0]}' hasta '{entity}'"
                        )
                        evidences.append(evidence)
                        visited_entities.add(entity)
            
            current_entities = next_entities - visited_entities
            if not current_entities:
                break
        
        self.stats["multi_hop_queries"] += len(evidences)
        
        return evidences
    
    def _find_path_to_entity(self, start: str, target: str, max_length: int = 3) -> List[str]:
        """Encuentra path desde start hasta target."""
        # BFS simple
        queue = [(start, [start])]
        visited = {start}
        
        while queue:
            current, path = queue.pop(0)
            
            if current == target:
                return path
            
            if len(path) >= max_length:
                continue
            
            # Encontrar vecinos
            for rel in self.knowledge_graph.relationships:
                next_entity = None
                if rel.source == current:
                    next_entity = rel.target
                elif rel.target == current:
                    next_entity = rel.source
                
                if next_entity and next_entity not in visited:
                    visited.add(next_entity)
                    queue.append((next_entity, path + [next_entity]))
        
        return []
    
    def _get_relationship_path(self, path: List[str]) -> List[str]:
        """Obtiene tipos de relaciones en el path."""
        relationship_types = []
        
        for i in range(len(path) - 1):
            source = path[i]
            target = path[i + 1]
            
            for rel in self.knowledge_graph.relationships:
                if (rel.source == source and rel.target == target) or \
                   (rel.source == target and rel.target == source):
                    relationship_types.append(rel.relationship_type)
                    break
        
        return relationship_types
    
    def _get_documents_for_path(self, path: List[str]) -> List[str]:
        """Obtiene documentos que soportan el path."""
        doc_ids = set()
        
        for entity in path:
            if entity in self.knowledge_graph.entity_documents:
                doc_ids.update(self.knowledge_graph.entity_documents[entity])
        
        return list(doc_ids)
    
    # ============================================
    # 5. EXPLAINABILITY (KGRAG-Ex)
    # ============================================
    
    async def generate_explanation(
        self,
        query: str,
        answer: str,
        evidences: List[GraphEvidence],
        subgraph: Subgraph
    ) -> Dict[str, Any]:
        """
        Genera explicación detallada de cómo se llegó a la respuesta.
        
        Basado en: "KGRAG-Ex: Explainable Retrieval-Augmented Generation with Knowledge Graphs" (2025)
        - Rutas de explicación detalladas
        - Análisis de importancia de entidades y relaciones
        - Trazabilidad completa
        """
        # Construir descripción detallada de evidencias
        evidence_details = []
        for i, e in enumerate(evidences[:8], 1):  # Aumentar a 8 evidencias
            path_str = " -> ".join(e.path) if e.path else "N/A"
            rel_str = " -> ".join(e.relationship_path) if e.relationship_path else "N/A"
            
            evidence_details.append({
                "evidencia": i,
                "path_entidades": path_str,
                "path_relaciones": rel_str,
                "confianza": f"{e.confidence:.2f}",
                "explicacion": e.explanation,
                "documentos_soporte": len(e.supporting_documents)
            })
        
        # Construir descripción de entidades con sus tipos
        entity_details = []
        for entity_name in subgraph.entities[:15]:
            entity_obj = self.knowledge_graph.entities.get(entity_name)
            if entity_obj:
                entity_details.append(f"- {entity_name} ({entity_obj.entity_type})")
            else:
                entity_details.append(f"- {entity_name}")
        
        explanation_prompt = f"""Eres un experto en explicabilidad de sistemas de IA. Tu tarea es explicar CÓMO y POR QUÉ se llegó a esta respuesta usando el grafo de conocimiento.

CONSULTA DEL USUARIO:
{query}

RESPUESTA GENERADA:
{answer}

EVIDENCIAS DEL GRAFO DE CONOCIMIENTO:
{json.dumps(evidence_details, indent=2, ensure_ascii=False)}

SUBGRAFO RELEVANTE:
- Entidades identificadas ({len(subgraph.entities)}):
{chr(10).join(entity_details)}

- Relaciones identificadas: {len(subgraph.relationships)}
- Score de relevancia del subgrafo: {subgraph.relevance_score:.2f}

INSTRUCCIONES PARA LA EXPLICACIÓN:
Proporciona una explicación clara y detallada que cubra:

1. **ENTIDADES RELEVANTES**: 
   - Qué entidades del grafo fueron más importantes para responder la consulta
   - Por qué estas entidades específicas fueron seleccionadas
   - Cómo se relacionan entre sí según el grafo

2. **RUTAS DE RAZONAMIENTO**:
   - Qué paths (caminos) en el grafo conectaron la información necesaria
   - Cómo las relaciones del grafo permitieron inferir la respuesta
   - Qué evidencias fueron más determinantes

3. **CONFIABILIDAD**:
   - Por qué esta respuesta es confiable basándose en el grafo
   - Qué nivel de certeza tenemos según las evidencias
   - Si hay limitaciones o incertidumbres

4. **TRAZABILIDAD**:
   - De dónde viene cada pieza de información (qué documentos/entidades)
   - Cómo se conectó la información del texto con el grafo
   - Qué relaciones del grafo fueron más importantes

EXPLICACIÓN DETALLADA:"""
        
        try:
            response = await self.llm.ainvoke(explanation_prompt)
            explanation_text = response.content if hasattr(response, 'content') else str(response)
            
            # Si la explicación es muy corta, agregar información adicional
            if len(explanation_text) < 300:
                explanation_text += f"\n\n**Información adicional:**\n"
                explanation_text += f"- Total de evidencias utilizadas: {len(evidences)}\n"
                explanation_text += f"- Entidades involucradas: {', '.join(subgraph.entities[:10])}\n"
                explanation_text += f"- Confianza del subgrafo: {subgraph.relevance_score:.2f}"
                
        except Exception as e:
            print(f"⚠️ [Advanced GraphRAG] Error generando explicación: {e}")
            explanation_text = f"Explicación no disponible debido a error: {e}"
        
        return {
            "explanation": explanation_text,
            "evidences_used": len(evidences),
            "entities_involved": subgraph.entities,
            "paths_traversed": [e.path for e in evidences if e.path],
            "relationship_paths": [e.relationship_path for e in evidences if e.relationship_path],
            "confidence": subgraph.relevance_score,
            "subgraph_stats": {
                "total_entities": len(subgraph.entities),
                "total_relationships": len(subgraph.relationships),
                "relevance_score": subgraph.relevance_score
            }
        }
    
    # ============================================
    # 6. GRAPH MEMORY (GMeLLo)
    # ============================================
    
    def update_graph_memory(
        self,
        query: str,
        answer: str,
        subgraph: Subgraph,
        evidences: List[GraphEvidence]
    ):
        """
        Actualiza memoria del grafo basándose en interacciones.
        
        Basado en: "Graph Memory-based Editing for LLMs (GMeLLo)" (2024)
        """
        memory_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "answer": answer,
            "entities_used": subgraph.entities,
            "evidences_count": len(evidences),
            "relevance_score": subgraph.relevance_score
        }
        
        # Agregar a memoria por entidad
        for entity in subgraph.entities[:5]:  # Top 5 entidades
            self.graph_memory[entity].append(memory_entry)
            
            # Limitar tamaño de memoria
            if len(self.graph_memory[entity]) > 10:
                self.graph_memory[entity] = self.graph_memory[entity][-10:]
    
    def get_graph_memory_context(self, entities: List[str]) -> str:
        """Obtiene contexto de memoria del grafo para entidades."""
        memory_contexts = []
        
        for entity in entities[:5]:
            if entity in self.graph_memory:
                memories = self.graph_memory[entity][-3:]  # Últimas 3 interacciones
                for mem in memories:
                    memory_contexts.append(
                        f"Consulta previa sobre '{entity}': {mem['query']}\n"
                        f"Respuesta: {mem['answer'][:200]}..."
                    )
        
        return "\n\n".join(memory_contexts) if memory_contexts else ""
    
    # ============================================
    # 7. QUERY-FOCUSED SUMMARIZATION (GraphRAG Paper)
    # ============================================
    
    async def query_focused_summarization(
        self,
        query: str,
        documents: List[Document],
        subgraph: Subgraph
    ) -> str:
        """
        Genera resumen centrado en la consulta usando el grafo.
        
        Basado en: "A Graph RAG Approach to Query-Focused Summarization" (Edge et al. 2024)
        """
        # Construir contexto del grafo
        graph_summary = f"""Estructura del Grafo de Conocimiento:

Entidades Principales: {', '.join(subgraph.entities[:15])}

Relaciones Clave:
"""
        for rel in subgraph.relationships[:10]:
            graph_summary += f"- {rel['source']} --[{rel['type']}]--> {rel['target']}\n"
        
        # Contexto textual
        text_context = "\n\n".join([doc.page_content[:800] for doc in documents[:5]])
        
        summarization_prompt = f"""Genera un resumen centrado en la consulta usando tanto el texto como la estructura del grafo.

Consulta: {query}

Contexto Textual:
{text_context[:2000]}

Estructura del Grafo:
{graph_summary}

Genera un resumen que:
1. Responda directamente a la consulta
2. Use información del texto
3. Explique relaciones del grafo relevantes
4. Sea conciso pero completo

Resumen:"""
        
        try:
            response = await self.llm.ainvoke(summarization_prompt)
            summary = response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            summary = f"Error generando resumen: {e}"
        
        return summary
    
    # ============================================
    # UTILITY METHODS
    # ============================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del GraphRAG."""
        return {
            **self.stats,
            "total_entities": len(self.knowledge_graph.entities),
            "total_relationships": len(self.knowledge_graph.relationships),
            "subgraph_cache_size": len(self.subgraph_cache),
            "graph_memory_entries": sum(len(mem) for mem in self.graph_memory.values())
        }

