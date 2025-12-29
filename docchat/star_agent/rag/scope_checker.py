"""Scope Checker para detectar preguntas fuera del alcance.

Verifica si una pregunta puede ser respondida con los documentos disponibles.
"""

from __future__ import annotations

from typing import Optional
from langchain_core.retrievers import BaseRetriever
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage


class ScopeChecker:
    """Verifica si una pregunta estÃ¡ dentro del alcance de los documentos."""
    
    def __init__(self, llm: BaseLanguageModel, retriever: Optional[BaseRetriever] = None):
        """Inicializa el Scope Checker.
        
        Args:
            llm: Modelo de lenguaje para verificaciÃ³n (Groq/OpenAI)
            retriever: Retriever para buscar documentos relevantes (opcional)
        """
        self.llm = llm
        self.retriever = retriever
    
    def check(self, question: str, k: int = 3) -> str:
        """Verifica si la pregunta estÃ¡ en el alcance de los documentos.
        
        Args:
            question: Pregunta del usuario
            k: NÃºmero de documentos a recuperar para verificaciÃ³n
            
        Returns:
            "CAN_ANSWER" | "PARTIAL" | "NO_MATCH"
        """
        if not self.retriever:
            # Si no hay retriever, asumir que puede responder
            return "CAN_ANSWER"
        
        try:
            # Buscar documentos relevantes
            # BaseRetriever.get_relevant_documents acepta query como primer arg
            if hasattr(self.retriever, 'get_relevant_documents'):
                # Intentar con parÃ¡metro k si el retriever lo soporta
                try:
                    top_docs = self.retriever.get_relevant_documents(question, k=k)
                except TypeError:
                    # Si no acepta k, usar mÃ©todo estÃ¡ndar
                    top_docs = self.retriever.get_relevant_documents(question)[:k]
            else:
                # Fallback: invocar directamente
                top_docs = self.retriever.invoke(question) if hasattr(self.retriever, 'invoke') else []
                top_docs = top_docs[:k] if isinstance(top_docs, list) else []
            
            if not top_docs:
                return "NO_MATCH"
            
            # Construir contexto de documentos
            document_content = "\n\n".join(
                [doc.page_content[:500] for doc in top_docs[:k]]  # Limitar longitud
            )
            
            # Crear prompt para verificaciÃ³n
            prompt = f"""Eres un verificador de alcance entre una pregunta del usuario y contenido de documentos.

**Instrucciones:**
- Clasifica quÃ© tan bien el contenido del documento responde a la pregunta del usuario.
- Responde SOLO con una de estas etiquetas: CAN_ANSWER, PARTIAL, NO_MATCH
- CAN_ANSWER: Los documentos proporcionan suficiente informaciÃ³n para una respuesta completa
- PARTIAL: Los documentos mencionan el tema pero carecen de detalles completos
- NO_MATCH: Los documentos no discuten la pregunta en absoluto

**Pregunta del usuario:** {question}

**Contenido de documentos:**
{document_content}

**Responde SOLO con: CAN_ANSWER, PARTIAL, o NO_MATCH**"""
            
            # Invocar LLM
            response = self.llm.invoke([
                SystemMessage(content="Responde SOLO con CAN_ANSWER, PARTIAL, o NO_MATCH"),
                HumanMessage(content=prompt),
            ])
            
            # Extraer respuesta
            content = getattr(response, "content", str(response)).strip().upper()
            
            # Validar respuesta
            valid_labels = {"CAN_ANSWER", "PARTIAL", "NO_MATCH"}
            if any(label in content for label in valid_labels):
                for label in valid_labels:
                    if label in content:
                        return label
            
            # Default a NO_MATCH si no es vÃ¡lido
            return "NO_MATCH"
            
        except Exception as e:
            print(f"âš ï¸ Error en scope checking: {e}")
            # En caso de error, permitir que continÃºe (mejor tener respuesta que bloquear)
            return "CAN_ANSWER"

