"""
Context Folding - Plegado de contexto
Gestiona eficientemente contextos largos para 500+ PDFs
Permite "plegar" sub-trajectorias y mantener solo resúmenes
"""

from __future__ import annotations

import json
import time
import uuid
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from .config import AppConfig


class BranchStatus(str, Enum):
    """Estado de una rama."""
    ACTIVE = "active"
    FOLDED = "folded"
    ARCHIVED = "archived"


@dataclass
class ContextBranch:
    """Una rama de contexto que puede ser plegada."""
    branch_id: str
    description: str  # Descripción breve de la subtarea
    prompt: str  # Instrucción detallada para la rama
    context_before: str  # Contexto antes de la rama
    context_during: List[str] = field(default_factory=list)  # Contexto durante la rama
    context_after: Optional[str] = None  # Resumen después de plegar
    status: BranchStatus = BranchStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    folded_at: Optional[float] = None
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FoldedContext:
    """Contexto plegado con resumen."""
    original_length: int  # Tokens originales
    folded_length: int  # Tokens después de plegar
    compression_ratio: float  # Ratio de compresión
    summary: str  # Resumen del contexto plegado
    branches_folded: int  # Número de ramas plegadas
    timestamp: float = field(default_factory=time.time)


class ContextFolder:
    """
    Sistema de plegado de contexto para gestionar eficientemente contextos largos.
    
    Características:
    - Crea ramas para subtareas que consumen muchos tokens
    - Plegar ramas completadas manteniendo solo resúmenes
    - Gestiona contextos de 500+ PDFs eficientemente
    - Reduce tokens manteniendo información relevante
    """
    
    def __init__(
        self,
        config: AppConfig,
        llm: Optional[BaseLanguageModel] = None,
        max_context_tokens: int = 32000,
        max_branches: int = 10
    ):
        self.config = config
        self.llm = llm
        self.max_context_tokens = max_context_tokens
        self.max_branches = max_branches
        
        # Ramas activas
        self.active_branches: Dict[str, ContextBranch] = {}
        
        # Historial de ramas plegadas
        self.folded_branches: List[ContextBranch] = []
        
        # Contexto principal (sin plegar)
        self.main_context: List[str] = []
        
        # Estadísticas
        self.total_tokens_saved: int = 0
        self.total_branches_created: int = 0
        self.total_branches_folded: int = 0
        
        # Directorio para persistencia
        self.storage_dir = Path(config.memory_dir) / "context_folding"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar historial
        self._load_history()
        
        # Prompt para generar resúmenes
        self.summary_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un experto en resumir información manteniendo solo lo esencial.

Tu tarea es crear un resumen conciso de un contexto largo, preservando:
1. Conclusiones clave
2. Información crítica para decisiones futuras
3. Resultados importantes
4. Dependencias con otras partes del contexto

Elimina:
- Detalles redundantes
- Información intermedia que ya no es relevante
- Pasos de proceso que ya se completaron

Responde SOLO con el resumen, sin explicaciones adicionales."""),
            ("human", """Contexto a resumir:

{context}

Crea un resumen conciso que preserve solo la información esencial.""")
        ])
    
    def _load_history(self):
        """Carga historial de ramas plegadas."""
        history_file = self.storage_dir / "folded_branches.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for branch_data in data.get("branches", [])[-100:]:  # Últimas 100
                        branch = ContextBranch(**branch_data)
                        self.folded_branches.append(branch)
                print(f"✅ [Context Folding] {len(self.folded_branches)} ramas plegadas cargadas")
            except Exception as e:
                print(f"⚠️ [Context Folding] Error cargando historial: {e}")
    
    def _save_history(self):
        """Guarda historial de ramas plegadas."""
        history_file = self.storage_dir / "folded_branches.json"
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump({
                    "branches": [asdict(branch) for branch in self.folded_branches[-100:]]
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ [Context Folding] Error guardando historial: {e}")
    
    def create_branch(
        self,
        description: str,
        prompt: str,
        context_before: str
    ) -> str:
        """
        Crea una nueva rama de contexto.
        
        Returns:
            branch_id: ID de la rama creada
        """
        if len(self.active_branches) >= self.max_branches:
            # Plegar la rama más antigua
            oldest_branch_id = min(
                self.active_branches.keys(),
                key=lambda bid: self.active_branches[bid].created_at
            )
            self.fold_branch(oldest_branch_id)
        
        branch_id = str(uuid.uuid4())
        
        branch = ContextBranch(
            branch_id=branch_id,
            description=description,
            prompt=prompt,
            context_before=context_before,
            status=BranchStatus.ACTIVE
        )
        
        self.active_branches[branch_id] = branch
        self.total_branches_created += 1
        
        print(f"🌿 [Context Folding] Rama creada: {description[:50]}...")
        
        return branch_id
    
    def add_to_branch(self, branch_id: str, content: str):
        """Agrega contenido a una rama activa."""
        if branch_id not in self.active_branches:
            raise ValueError(f"Rama {branch_id} no encontrada")
        
        branch = self.active_branches[branch_id]
        branch.context_during.append(content)
        branch.token_count += self._estimate_tokens(content)
    
    def fold_branch(self, branch_id: str) -> Optional[FoldedContext]:
        """
        Plegar una rama, creando un resumen y liberando tokens.
        
        Returns:
            FoldedContext con información del plegado
        """
        if branch_id not in self.active_branches:
            return None
        
        branch = self.active_branches[branch_id]
        
        # Construir contexto completo de la rama
        full_context = f"{branch.context_before}\n\n"
        full_context += "\n\n".join(branch.context_during)
        
        # Generar resumen
        summary = self._generate_summary(full_context)
        
        branch.context_after = summary
        branch.status = BranchStatus.FOLDED
        branch.folded_at = time.time()
        
        # Calcular compresión
        original_tokens = branch.token_count
        folded_tokens = self._estimate_tokens(summary)
        compression_ratio = folded_tokens / original_tokens if original_tokens > 0 else 1.0
        
        # Mover a ramas plegadas
        self.folded_branches.append(branch)
        del self.active_branches[branch_id]
        self.total_branches_folded += 1
        self.total_tokens_saved += (original_tokens - folded_tokens)
        
        print(f"📦 [Context Folding] Rama plegada: {branch.description[:50]}... (compresión: {compression_ratio*100:.1f}%)")
        
        # Guardar periódicamente
        if self.total_branches_folded % 10 == 0:
            self._save_history()
        
        return FoldedContext(
            original_length=original_tokens,
            folded_length=folded_tokens,
            compression_ratio=compression_ratio,
            summary=summary,
            branches_folded=1
        )
    
    def _generate_summary(self, context: str) -> str:
        """Genera un resumen del contexto."""
        if not self.llm:
            # Fallback: resumen simple
            return context[:500] + "..." if len(context) > 500 else context
        
        try:
            prompt = self.summary_prompt.format_messages(context=context)
            response = self.llm.invoke(prompt)
            summary = response.content if hasattr(response, 'content') else str(response)
            return summary.strip()
        except Exception as e:
            print(f"⚠️ [Context Folding] Error generando resumen: {e}")
            # Fallback
            return context[:500] + "..." if len(context) > 500 else context
    
    def get_folded_context(self) -> str:
        """
        Obtiene el contexto plegado completo (main + resúmenes de ramas).
        
        Returns:
            Contexto completo con ramas plegadas como resúmenes
        """
        context_parts = []
        
        # Agregar contexto principal
        if self.main_context:
            context_parts.append("\n\n".join(self.main_context))
        
        # Agregar resúmenes de ramas plegadas
        for branch in self.folded_branches[-10:]:  # Últimas 10 ramas
            if branch.context_after:
                context_parts.append(f"[{branch.description}]\n{branch.context_after}")
        
        # Agregar ramas activas (completas)
        for branch in self.active_branches.values():
            branch_context = f"{branch.context_before}\n\n"
            branch_context += "\n\n".join(branch.context_during)
            context_parts.append(f"[{branch.description} - ACTIVA]\n{branch_context}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def get_current_token_count(self) -> int:
        """Obtiene el conteo actual de tokens."""
        total = 0
        
        # Tokens del contexto principal
        for part in self.main_context:
            total += self._estimate_tokens(part)
        
        # Tokens de ramas activas
        for branch in self.active_branches.values():
            total += branch.token_count
        
        # Tokens de resúmenes plegados
        for branch in self.folded_branches[-10:]:
            if branch.context_after:
                total += self._estimate_tokens(branch.context_after)
        
        return total
    
    def should_fold(self) -> bool:
        """Determina si debería plegar ramas para liberar tokens."""
        current_tokens = self.get_current_token_count()
        return current_tokens > (self.max_context_tokens * 0.8)  # 80% del límite
    
    def auto_fold_if_needed(self) -> List[FoldedContext]:
        """
        Plegar ramas automáticamente si se acerca al límite de tokens.
        
        Returns:
            Lista de contextos plegados
        """
        folded = []
        
        while self.should_fold() and self.active_branches:
            # Plegar la rama más antigua
            oldest_branch_id = min(
                self.active_branches.keys(),
                key=lambda bid: self.active_branches[bid].created_at
            )
            folded_ctx = self.fold_branch(oldest_branch_id)
            if folded_ctx:
                folded.append(folded_ctx)
        
        return folded
    
    def add_to_main_context(self, content: str):
        """Agrega contenido al contexto principal."""
        self.main_context.append(content)
        
        # Auto-plegar si es necesario
        if self.should_fold():
            self.auto_fold_if_needed()
    
    def _estimate_tokens(self, text: str) -> int:
        """Estima el número de tokens en un texto."""
        # Aproximación: 1 token ≈ 4 caracteres
        return len(text) // 4
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del plegado."""
        return {
            "active_branches": len(self.active_branches),
            "folded_branches": len(self.folded_branches),
            "total_branches_created": self.total_branches_created,
            "total_branches_folded": self.total_branches_folded,
            "total_tokens_saved": self.total_tokens_saved,
            "current_token_count": self.get_current_token_count(),
            "max_context_tokens": self.max_context_tokens,
            "compression_ratio": (
                self.total_tokens_saved / (self.total_tokens_saved + self.get_current_token_count())
                if (self.total_tokens_saved + self.get_current_token_count()) > 0
                else 0.0
            )
        }
    
    def clear_all(self):
        """Limpia todas las ramas y contexto."""
        # Plegar todas las ramas activas antes de limpiar
        for branch_id in list(self.active_branches.keys()):
            self.fold_branch(branch_id)
        
        self.active_branches.clear()
        self.main_context.clear()
        self._save_history()

