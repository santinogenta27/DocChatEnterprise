"""
GraphRAG: RAG basado en grafos de conocimiento para relaciones complejas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from langchain_core.documents import Document


@dataclass
class Entity:
    """Entidad en el grafo de conocimiento."""
    name: str
    entity_type: str
    metadata: Dict = None


@dataclass
class Relationship:
    """Relación entre entidades."""
    source: str
    target: str
    relationship_type: str
    strength: float = 1.0
    metadata: Dict = None


class KnowledgeGraph:
    """
    Grafo de conocimiento para representar relaciones entre documentos y entidades.
    """
    
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
        self.entity_documents: Dict[str, List[str]] = {}  # entity_id -> document_ids
    
    def add_entity(self, entity: Entity):
        """Agrega entidad al grafo."""
        self.entities[entity.name] = entity
    
    def add_relationship(self, relationship: Relationship):
        """Agrega relación al grafo."""
        self.relationships.append(relationship)
    
    def link_entity_to_document(self, entity_name: str, document_id: str):
        """Vincula entidad a documento."""
        if entity_name not in self.entity_documents:
            self.entity_documents[entity_name] = []
        if document_id not in self.entity_documents[entity_name]:
            self.entity_documents[entity_name].append(document_id)
    
    def get_related_entities(self, entity_name: str, max_depth: int = 2) -> Set[str]:
        """Obtiene entidades relacionadas."""
        related = {entity_name}
        current_level = {entity_name}
        
        for depth in range(max_depth):
            next_level = set()
            for entity in current_level:
                # Buscar relaciones
                for rel in self.relationships:
                    if rel.source == entity:
                        next_level.add(rel.target)
                    elif rel.target == entity:
                        next_level.add(rel.source)
            
            related.update(next_level)
            current_level = next_level
        
        return related
    
    def get_documents_for_entities(self, entity_names: List[str]) -> List[str]:
        """Obtiene documentos relacionados con entidades."""
        document_ids = set()
        
        for entity_name in entity_names:
            related_entities = self.get_related_entities(entity_name)
            for related in related_entities:
                if related in self.entity_documents:
                    document_ids.update(self.entity_documents[related])
        
        return list(document_ids)


class GraphRAG:
    """
    RAG basado en grafos de conocimiento para relaciones complejas.
    """
    
    def __init__(self):
        self.knowledge_graph = KnowledgeGraph()
    
    def build_graph_from_documents(self, documents: List[Document]):
        """Construye grafo de conocimiento desde documentos."""
        # Extraer entidades y relaciones (simplificado)
        # En producción, usar NER y relation extraction más sofisticado
        
        for doc in documents:
            doc_id = doc.metadata.get("source", "unknown")
            
            # Extraer entidades básicas (nombres propios, organizaciones, etc.)
            entities = self._extract_entities(doc.page_content)
            
            for entity_name, entity_type in entities:
                entity = Entity(
                    name=entity_name,
                    entity_type=entity_type,
                    metadata={"source": doc_id}
                )
                self.knowledge_graph.add_entity(entity)
                self.knowledge_graph.link_entity_to_document(entity_name, doc_id)
            
            # Extraer relaciones básicas
            relationships = self._extract_relationships(doc.page_content, entities)
            for rel in relationships:
                self.knowledge_graph.add_relationship(rel)
    
    def _extract_entities(self, text: str) -> List[Tuple[str, str]]:
        """Extrae entidades del texto (simplificado)."""
        # En producción, usar spaCy, NLTK, o modelo de NER
        entities = []
        
        # Buscar patrones básicos (se puede mejorar mucho)
        import re
        
        # Nombres propios (capitalizados)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+\b', text)
        for noun in proper_nouns[:10]:  # Limitar
            if len(noun) > 2:
                entities.append((noun, "PERSON"))
        
        # Organizaciones (palabras con mayúsculas múltiples)
        orgs = re.findall(r'\b[A-Z][A-Za-z]+\s+[A-Z][A-Za-z]+\b', text)
        for org in orgs[:5]:
            entities.append((org, "ORGANIZATION"))
        
        return entities
    
    def _extract_relationships(self, text: str, entities: List[Tuple[str, str]]) -> List[Relationship]:
        """Extrae relaciones entre entidades (simplificado)."""
        relationships = []
        
        # Buscar patrones de relación básicos
        if len(entities) < 2:
            return relationships
        
        # Relaciones simples (entidades mencionadas juntas)
        for i, (ent1, _) in enumerate(entities):
            for ent2, _ in entities[i+1:]:
                if ent1.lower() in text.lower() and ent2.lower() in text.lower():
                    # Verificar proximidad
                    pos1 = text.lower().find(ent1.lower())
                    pos2 = text.lower().find(ent2.lower())
                    if abs(pos1 - pos2) < 100:  # Dentro de 100 caracteres
                        relationships.append(Relationship(
                            source=ent1,
                            target=ent2,
                            relationship_type="MENTIONED_TOGETHER",
                            strength=0.5
                        ))
        
        return relationships
    
    def query_with_graph(self, query: str, documents: List[Document]) -> List[Document]:
        """
        Consulta usando grafo de conocimiento.
        Encuentra documentos relacionados incluso si no coinciden directamente.
        """
        # Extraer entidades de la query
        query_entities = [ent[0] for ent in self._extract_entities(query)]
        
        if not query_entities:
            return documents  # Fallback a documentos originales
        
        # Obtener documentos relacionados
        related_doc_ids = self.knowledge_graph.get_documents_for_entities(query_entities)
        
        # Filtrar documentos
        doc_map = {doc.metadata.get("source", "unknown"): doc for doc in documents}
        related_docs = [doc_map[doc_id] for doc_id in related_doc_ids if doc_id in doc_map]
        
        # Combinar con documentos originales (priorizar relacionados)
        result = related_docs + [doc for doc in documents if doc not in related_docs]
        
        return result[:20]  # Limitar resultados

