"""
Agent 2: Extractor - Extrae entidades estructuradas de documentos.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
import re

try:
    from langchain_anthropic import ChatAnthropic
    from langchain_openai import ChatOpenAI
    ANTHROPIC_AVAILABLE = True
    OPENAI_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    OPENAI_AVAILABLE = False

from .base_agent import BaseBanksAgent
from ..schemas import EntityExtraction
from ....config import AppConfig

logger = logging.getLogger(__name__)


class ExtractorAgent(BaseBanksAgent):
    """Agente que extrae entidades estructuradas usando LLM + Pydantic."""
    
    def __init__(self, config: AppConfig):
        super().__init__(config, "extractor")
        
        # Preferir Claude 3.5 Sonnet para mejor reasoning
        if ANTHROPIC_AVAILABLE and config.anthropic_api_key:
            self.llm = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                temperature=0.1,
                api_key=config.anthropic_api_key
            )
        elif OPENAI_AVAILABLE and config.openai_api_key:
            self.llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0.1,
                api_key=config.openai_api_key
            )
        else:
            raise ValueError("Se requiere ANTHROPIC_API_KEY o OPENAI_API_KEY")
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrae entidades de documentos procesados.
        
        Input state:
            - processed_documents: List[Dict]
        
        Output state:
            - extracted_entities: List[EntityExtraction]
        """
        processed_docs = state.get("processed_documents", [])
        extracted_entities = []
        
        for doc in processed_docs:
            try:
                # Combinar todos los chunks del documento
                full_text = "\n\n".join([chunk.get("text", "") for chunk in doc.get("chunks", [])])
                
                if not full_text.strip():
                    continue
                
                # Extraer entidades usando LLM
                entity = self._extract_entities(full_text, doc.get("path", ""))
                if entity:
                    extracted_entities.append(entity)
            
            except Exception as e:
                logger.error(f"Error extrayendo entidades de {doc.get('path')}: {e}")
                continue
        
        # Log de auditoría
        self.log_audit(
            action="entity_extraction",
            input_data={"documents_count": len(processed_docs)},
            output_data={"entities_extracted": len(extracted_entities)}
        )
        
        state["extracted_entities"] = extracted_entities
        return state
    
    def _extract_entities(self, text: str, doc_path: str) -> Optional[EntityExtraction]:
        """Extrae entidades usando LLM con schema Pydantic."""
        
        prompt = f"""Eres un experto en KYC/AML. Extrae las siguientes entidades del siguiente documento:

DOCUMENTO:
{text[:10000]}  # Limitar a 10k chars para evitar tokens excesivos

Extrae:
- Nombre completo (persona o empresa)
- Número de identificación (DNI, pasaporte, NIF, etc.) y tipo
- Dirección física completa
- Fecha de nacimiento (si es persona)
- Nacionalidad
- Beneficiarios finales (UBO) - lista de personas/empresas con porcentajes
- Status PEP (Politically Exposed Person) - nivel 1, 2, 3, o None
- Transacciones relevantes (importes >€10k, transferencias a países de alto riesgo)

Responde SOLO con un JSON válido siguiendo este schema:
{{
    "name": "string o null",
    "id_number": "string o null",
    "id_type": "DNI/Passport/NIF/etc o null",
    "address": "string o null",
    "date_of_birth": "YYYY-MM-DD o null",
    "nationality": "string o null",
    "ubo": [{{"name": "string", "percentage": float, "country": "string"}}],
    "pep_status": "1/2/3/null",
    "transactions": [{{"amount": float, "currency": "string", "date": "YYYY-MM-DD", "destination": "string", "type": "wire/deposit/etc"}}]
}}

Si no encuentras una entidad, usa null. Sé preciso y conservador."""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parsear JSON de la respuesta
            import json
            # Limpiar markdown code blocks si existen
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            content = content.strip()
            
            data = json.loads(content)
            
            # Crear EntityExtraction
            return EntityExtraction(
                name=data.get("name"),
                id_number=data.get("id_number"),
                id_type=data.get("id_type"),
                address=data.get("address"),
                date_of_birth=data.get("date_of_birth"),
                nationality=data.get("nationality"),
                ubo=data.get("ubo", []),
                pep_status=data.get("pep_status"),
                transactions=data.get("transactions", [])
            )
        
        except Exception as e:
            logger.error(f"Error en extracción LLM: {e}")
            # Fallback: extracción básica con regex
            return self._extract_basic_entities(text)
    
    def _extract_basic_entities(self, text: str) -> Optional[EntityExtraction]:
        """Extracción básica con regex como fallback."""
        # Patrones básicos
        dni_pattern = r'\b\d{8}[A-Z]\b|\b[A-Z]\d{7,8}\b'  # DNI español
        passport_pattern = r'[A-Z]{1,2}\d{6,9}'
        
        dni_match = re.search(dni_pattern, text)
        passport_match = re.search(passport_pattern, text)
        
        id_number = None
        id_type = None
        if dni_match:
            id_number = dni_match.group()
            id_type = "DNI"
        elif passport_match:
            id_number = passport_match.group()
            id_type = "Passport"
        
        return EntityExtraction(
            id_number=id_number,
            id_type=id_type
        )

