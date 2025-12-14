"""
Dynamic Memory Management para Co-Investigator AI.
Mantiene memoria persistente de narrativas históricas, guidelines regulatorios, y patrones tipológicos.
"""

from __future__ import annotations

import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from docchat.config import AppConfig

logger = logging.getLogger(__name__)


class DynamicMemoryManager:
    """
    Gestor de memoria dinámica para Co-Investigator AI.
    
    Capas de memoria:
    - Regulatory Memory: Guidelines y estándares AML
    - Historical Narrative Memory: Narrativas SAR previas
    - Typology-Specific Memory: Patrones y insights por tipología
    """
    
    def __init__(self, memory_dir: Path, config: AppConfig):
        self.memory_dir = memory_dir
        self.config = config
        
        # Directorios para cada tipo de memoria
        self.regulatory_dir = memory_dir / "regulatory"
        self.narratives_dir = memory_dir / "narratives"
        self.typology_dir = memory_dir / "typologies"
        
        # Crear directorios
        for dir_path in [self.regulatory_dir, self.narratives_dir, self.typology_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Cargar memoria existente
        self._load_memory()
        
        logger.info("✅ [Dynamic Memory] Inicializado")
    
    def _load_memory(self):
        """Carga memoria existente desde disco."""
        self.regulatory_memory = {}
        self.historical_narratives = []
        self.typology_memory = {}
        
        # Cargar regulatory memory
        regulatory_file = self.regulatory_dir / "guidelines.json"
        if regulatory_file.exists():
            try:
                with open(regulatory_file, 'r', encoding='utf-8') as f:
                    self.regulatory_memory = json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ [Dynamic Memory] Error cargando regulatory memory: {e}")
        
        # Cargar historical narratives
        narratives_file = self.narratives_dir / "narratives_index.json"
        if narratives_file.exists():
            try:
                with open(narratives_file, 'r', encoding='utf-8') as f:
                    self.historical_narratives = json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ [Dynamic Memory] Error cargando historical narratives: {e}")
        
        # Cargar typology memory
        typology_file = self.typology_dir / "typologies.json"
        if typology_file.exists():
            try:
                with open(typology_file, 'r', encoding='utf-8') as f:
                    self.typology_memory = json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ [Dynamic Memory] Error cargando typology memory: {e}")
    
    def get_regulatory_guidelines(self, jurisdiction: str) -> Dict[str, Any]:
        """Obtiene guidelines regulatorios para una jurisdicción."""
        return self.regulatory_memory.get(jurisdiction, {
            "jurisdiction": jurisdiction,
            "sar_requirements": {
                "filing_deadline_days": 30,
                "required_fields": [
                    "subject_details",
                    "suspicious_activity_description",
                    "date_range",
                    "institution_information",
                    "filer_contact",
                    "narrative_text"
                ]
            },
            "narrative_best_practices": [
                "Clear chronological account",
                "Specific transaction details",
                "Risk indicators clearly stated",
                "No tipping off language"
            ]
        })
    
    def get_regulatory_memory(self) -> Dict[str, Any]:
        """Obtiene toda la memoria regulatoria."""
        return self.regulatory_memory
    
    def get_historical_narratives(
        self,
        limit: int = 10,
        typology_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene narrativas históricas.
        
        Args:
            limit: Número máximo de narrativas a retornar
            typology_filter: Filtrar por tipología específica
        """
        narratives = self.historical_narratives.copy()
        
        if typology_filter:
            narratives = [
                n for n in narratives
                if typology_filter in n.get("crime_typologies", [])
            ]
        
        # Ordenar por fecha (más recientes primero)
        narratives.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
        
        return narratives[:limit]
    
    def get_narrative(self, narrative_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene una narrativa específica por ID."""
        narrative_file = self.narratives_dir / f"{narrative_id}.json"
        if narrative_file.exists():
            try:
                with open(narrative_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"❌ [Dynamic Memory] Error cargando narrativa {narrative_id}: {e}")
        return None
    
    def store_narrative(
        self,
        narrative: Any,  # SARNarrative
        crime_typologies: List[Any],  # List[CrimeTypology]
        jurisdiction: str
    ):
        """
        Almacena una narrativa en memoria histórica.
        """
        narrative_id = narrative.narrative_id if hasattr(narrative, 'narrative_id') else f"SAR_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Guardar narrativa completa
        narrative_data = {
            "narrative_id": narrative_id,
            "narrative_text": narrative.narrative_text if hasattr(narrative, 'narrative_text') else str(narrative),
            "crime_typologies": [
                {
                    "type": t.typology_type if hasattr(t, 'typology_type') else str(t),
                    "confidence": t.confidence_score if hasattr(t, 'confidence_score') else 0.0
                }
                for t in crime_typologies
            ],
            "jurisdiction": jurisdiction,
            "generated_at": datetime.now().isoformat(),
            "compliance_score": narrative.compliance_score if hasattr(narrative, 'compliance_score') else 0.0
        }
        
        narrative_file = self.narratives_dir / f"{narrative_id}.json"
        try:
            with open(narrative_file, 'w', encoding='utf-8') as f:
                json.dump(narrative_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ [Dynamic Memory] Error guardando narrativa: {e}")
            return
        
        # Actualizar índice
        self.historical_narratives.append({
            "narrative_id": narrative_id,
            "generated_at": narrative_data["generated_at"],
            "crime_typologies": [t.typology_type if hasattr(t, 'typology_type') else str(t) for t in crime_typologies],
            "jurisdiction": jurisdiction
        })
        
        # Guardar índice
        index_file = self.narratives_dir / "narratives_index.json"
        try:
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(self.historical_narratives, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ [Dynamic Memory] Error guardando índice: {e}")
        
        # Actualizar typology memory
        for typology in crime_typologies:
            typology_type = typology.typology_type if hasattr(typology, 'typology_type') else str(typology)
            if typology_type not in self.typology_memory:
                self.typology_memory[typology_type] = {
                    "patterns": [],
                    "risk_indicators": [],
                    "narrative_examples": []
                }
            
            # Agregar patrón
            self.typology_memory[typology_type]["narrative_examples"].append(narrative_id)
        
        # Guardar typology memory
        typology_file = self.typology_dir / "typologies.json"
        try:
            with open(typology_file, 'w', encoding='utf-8') as f:
                json.dump(self.typology_memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ [Dynamic Memory] Error guardando typology memory: {e}")
        
        logger.info(f"💾 [Dynamic Memory] Narrativa {narrative_id} almacenada")
    
    def update_narrative(self, narrative_id: str, narrative_data: Dict[str, Any]):
        """Actualiza una narrativa existente."""
        narrative_file = self.narratives_dir / f"{narrative_id}.json"
        if narrative_file.exists():
            try:
                with open(narrative_file, 'w', encoding='utf-8') as f:
                    json.dump(narrative_data, f, indent=2, ensure_ascii=False)
                logger.info(f"🔄 [Dynamic Memory] Narrativa {narrative_id} actualizada")
            except Exception as e:
                logger.error(f"❌ [Dynamic Memory] Error actualizando narrativa: {e}")













