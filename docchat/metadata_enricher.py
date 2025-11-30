"""
Enriquecimiento de Metadatos para Documentos

Implementa el pipeline de enriquecimiento según las especificaciones:
- KeyBERT: Extrae palabras clave y frases importantes
- YAKE: Genera frases representativas del contenido
- NER (spaCy): Detecta entidades (personas, organizaciones, lugares)
- LLM (opcional): Crea metadatos avanzados (temas, sinónimos, acrónimos, etiquetas)
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Any
from langchain_core.documents import Document

try:
    from keybert import KeyBERT
    KEYBERT_AVAILABLE = True
except ImportError:
    KEYBERT_AVAILABLE = False

try:
    import yake
    YAKE_AVAILABLE = True
except ImportError:
    YAKE_AVAILABLE = False

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


class MetadataEnricher:
    """
    Enriquece documentos con metadatos avanzados para mejorar RAG.
    
    Pipeline:
    1. KeyBERT → palabras clave y frases importantes
    2. YAKE → frases representativas
    3. NER (spaCy) → entidades (personas, organizaciones, lugares)
    4. LLM (opcional) → metadatos avanzados (temas, sinónimos, acrónimos)
    """
    
    def __init__(self, use_llm: bool = False, llm=None):
        """
        Inicializa el enriquecedor de metadatos.
        
        Args:
            use_llm: Si True, usa LLM para metadatos avanzados (solo para docs técnicos)
            llm: Instancia de LLM para enriquecimiento avanzado
        """
        self.use_llm = use_llm
        self.llm = llm
        
        # Inicializar KeyBERT
        if KEYBERT_AVAILABLE:
            try:
                self.keybert = KeyBERT()
            except Exception:
                self.keybert = None
        else:
            self.keybert = None
        
        # Inicializar YAKE
        if YAKE_AVAILABLE:
            try:
                self.yake = yake.KeywordExtractor(lan="es", n=3, dedupLim=0.7, top=10)
            except Exception:
                self.yake = None
        else:
            self.yake = None
        
        # Inicializar spaCy para NER
        if SPACY_AVAILABLE:
            try:
                # Intentar cargar modelo en español, fallback a inglés
                try:
                    self.nlp = spacy.load("es_core_news_sm")
                except OSError:
                    try:
                        self.nlp = spacy.load("en_core_web_sm")
                    except OSError:
                        self.nlp = None
            except Exception:
                self.nlp = None
        else:
            self.nlp = None
    
    def enrich_document(self, document: Document, use_advanced: bool = False) -> Document:
        """
        Enriquece un documento con metadatos.
        
        Args:
            document: Documento a enriquecer
            use_advanced: Si True, usa LLM para metadatos avanzados (solo docs técnicos)
        
        Returns:
            Documento enriquecido con metadatos adicionales
        """
        content = document.page_content
        metadata = document.metadata.copy()
        
        # 1. KeyBERT: Palabras clave y frases importantes
        keywords = self._extract_keywords_keybert(content)
        if keywords:
            metadata["keywords"] = keywords
        
        # 2. YAKE: Frases representativas
        yake_phrases = self._extract_phrases_yake(content)
        if yake_phrases:
            metadata["representative_phrases"] = yake_phrases
        
        # 3. NER: Entidades (personas, organizaciones, lugares)
        entities = self._extract_entities_ner(content)
        if entities:
            metadata["entities"] = entities
        
        # 4. LLM: Metadatos avanzados (solo si use_advanced=True y es documento técnico)
        if use_advanced and self.use_llm and self.llm:
            advanced_metadata = self._extract_advanced_metadata_llm(content)
            if advanced_metadata:
                metadata.update(advanced_metadata)
        
        # Crear nuevo documento con metadatos enriquecidos
        enriched_doc = Document(
            page_content=content,
            metadata=metadata
        )
        
        return enriched_doc
    
    def _extract_keywords_keybert(self, text: str, top_n: int = 10) -> List[str]:
        """Extrae palabras clave usando KeyBERT."""
        if not self.keybert or not text or len(text) < 50:
            return []
        
        try:
            # Extraer keywords (palabras y frases de 1-2 palabras)
            keywords = self.keybert.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),
                stop_words='spanish',
                top_n=top_n,
                use_mmr=True,
                diversity=0.5
            )
            return [kw[0] for kw in keywords]
        except Exception as e:
            print(f"⚠️ Error en KeyBERT: {e}")
            return []
    
    def _extract_phrases_yake(self, text: str) -> List[str]:
        """Extrae frases representativas usando YAKE."""
        if not self.yake or not text or len(text) < 50:
            return []
        
        try:
            keywords = self.yake.extract_keywords(text)
            return [kw[0] for kw in keywords[:10]]
        except Exception as e:
            print(f"⚠️ Error en YAKE: {e}")
            return []
    
    def _extract_entities_ner(self, text: str) -> Dict[str, List[str]]:
        """Extrae entidades usando NER (spaCy)."""
        if not self.nlp or not text or len(text) < 50:
            return {}
        
        try:
            doc = self.nlp(text[:10000])  # Limitar tamaño para performance
            
            entities = {
                "PERSON": [],
                "ORG": [],
                "LOC": [],
                "MISC": []
            }
            
            for ent in doc.ents:
                if ent.label_ in entities:
                    entities[ent.label_].append(ent.text)
            
            # Eliminar duplicados
            for key in entities:
                entities[key] = list(set(entities[key]))
            
            return {k: v for k, v in entities.items() if v}
        except Exception as e:
            print(f"⚠️ Error en NER: {e}")
            return {}
    
    def _extract_advanced_metadata_llm(self, text: str) -> Dict[str, Any]:
        """
        Extrae metadatos avanzados usando LLM.
        Solo para documentos técnicos o con terminología propia.
        """
        if not self.llm or not text:
            return {}
        
        try:
            prompt = f"""Analiza este documento y extrae metadatos avanzados en formato JSON.

Documento (primeros 2000 caracteres):
{text[:2000]}

Extrae y devuelve SOLO un JSON con esta estructura:
{{
    "temas_principales": ["tema1", "tema2", "tema3"],
    "sinonimos": {{"termino1": ["sinonimo1", "sinonimo2"]}},
    "acronimos": {{"ACRONIMO": "significado completo"}},
    "etiquetas": ["etiqueta1", "etiqueta2", "etiqueta3"],
    "resumen_corto": "resumen de 1-2 oraciones"
}}

Responde SOLO con el JSON, sin explicaciones adicionales."""

            response = self.llm.invoke(prompt).content.strip()
            
            # Limpiar respuesta (remover markdown code blocks si hay)
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            # Parsear JSON
            metadata = json.loads(response)
            return metadata
        
        except Exception as e:
            print(f"⚠️ Error en LLM metadata extraction: {e}")
            return {}
    
    def enrich_documents_batch(
        self,
        documents: List[Document],
        use_advanced: bool = False
    ) -> List[Document]:
        """
        Enriquece un lote de documentos.
        
        Args:
            documents: Lista de documentos a enriquecer
            use_advanced: Si True, usa LLM para metadatos avanzados
        
        Returns:
            Lista de documentos enriquecidos
        """
        enriched = []
        for doc in documents:
            enriched_doc = self.enrich_document(doc, use_advanced=use_advanced)
            enriched.append(enriched_doc)
        
        return enriched


