"""Research Agent optimizado para STAR AGENT.

Genera respuestas basadas en documentos recuperados usando Groq/OpenAI.
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage


class ResearchAgent:
    """Agente de investigaciÃ³n que genera respuestas basadas en documentos."""
    
    def __init__(self, llm: BaseLanguageModel):
        """Inicializa el Research Agent.
        
        Args:
            llm: Modelo de lenguaje (Groq/OpenAI)
        """
        self.llm = llm
    
    def generate_answer(self, question: str, documents: List[Document], max_context_length: int = 3000) -> dict:
        """Genera una respuesta basada en documentos recuperados.
        
        Args:
            question: Pregunta del usuario
            documents: Lista de documentos relevantes recuperados
            max_context_length: Longitud mÃ¡xima del contexto (caracteres)
            
        Returns:
            Dict con 'answer' y 'context_used'
        """
        if not documents:
            return {
                "answer": "No tengo informaciÃ³n suficiente en los documentos para responder esta pregunta.",
                "context_used": ""
            }
        
        # Construir contexto desde documentos
        context_parts = []
        current_length = 0
        
        for doc in documents:
            content = doc.page_content[:500]  # Limitar cada documento
            if current_length + len(content) > max_context_length:
                break
            context_parts.append(content)
            current_length += len(content)
        
        context = "\n\n".join(context_parts)
        
        # Crear prompt optimizado
        prompt = f"""Eres un asistente de IA diseÃ±ado para proporcionar respuestas precisas y basadas en hechos usando SOLO el contexto proporcionado.

**Instrucciones importantes:**
- Responde la siguiente pregunta usando ÃšNICAMENTE el contexto proporcionado abajo
- NO inventes informaciÃ³n que no estÃ© en el contexto
- Si la informaciÃ³n no estÃ¡ en el contexto, di claramente que no tienes esa informaciÃ³n
- SÃ© claro, conciso y factual
- Proporciona la mayor cantidad de informaciÃ³n posible del contexto
- Si hay mÃºltiples documentos, combina la informaciÃ³n de manera coherente

**Pregunta del usuario:** {question}

**Contexto de los documentos:**
{context}

**Proporciona tu respuesta basada SOLO en el contexto arriba:**"""
        
        try:
            # Invocar LLM
            response = self.llm.invoke([
                SystemMessage(content="Eres un asistente que responde preguntas usando SOLO la informaciÃ³n proporcionada en el contexto. No inventes informaciÃ³n."),
                HumanMessage(content=prompt),
            ])
            
            answer = getattr(response, "content", str(response)).strip()
            
            if not answer:
                return {
                    "answer": "No pude generar una respuesta basada en los documentos proporcionados.",
                    "context_used": context
                }
            
            return {
                "answer": answer,
                "context_used": context
            }
            
        except Exception as e:
            print(f"âš ï¸ Error generando respuesta con Research Agent: {e}")
            return {
                "answer": "Hubo un error al generar la respuesta. Por favor intenta de nuevo.",
                "context_used": ""
            }

