"""
Sistema de personalización y perfiles de usuario.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from ..config import AppConfig


class UserRole(Enum):
    """Roles de usuario para personalización."""
    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    CLIENT = "client"
    ANALYST = "analyst"
    MANAGER = "manager"


@dataclass
class UserProfile:
    """Perfil de usuario con preferencias."""
    user_id: str
    username: str
    role: UserRole
    language: str = "es"
    preferences: Dict = field(default_factory=dict)
    query_patterns: List[str] = field(default_factory=list)
    favorite_documents: List[str] = field(default_factory=list)
    created_at: str = ""
    last_active: str = ""


class PersonalizationEngine:
    """
    Motor de personalización para adaptar respuestas a usuarios.
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.data_dir = Path(config.memory_dir) / "personalization"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.profiles_file = self.data_dir / "profiles.json"
        self.profiles: Dict[str, UserProfile] = self._load_profiles()
    
    def _load_profiles(self) -> Dict[str, UserProfile]:
        """Carga perfiles desde archivo."""
        try:
            if self.profiles_file.exists():
                with open(self.profiles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        user_id: UserProfile(
                            user_id=p["user_id"],
                            username=p["username"],
                            role=UserRole(p["role"]),
                            language=p.get("language", "es"),
                            preferences=p.get("preferences", {}),
                            query_patterns=p.get("query_patterns", []),
                            favorite_documents=p.get("favorite_documents", []),
                            created_at=p.get("created_at", ""),
                            last_active=p.get("last_active", "")
                        )
                        for user_id, p in data.items()
                    }
            return {}
        except Exception:
            return {}
    
    def _save_profiles(self):
        """Guarda perfiles."""
        try:
            data = {
                user_id: {
                    "user_id": profile.user_id,
                    "username": profile.username,
                    "role": profile.role.value,
                    "language": profile.language,
                    "preferences": profile.preferences,
                    "query_patterns": profile.query_patterns,
                    "favorite_documents": profile.favorite_documents,
                    "created_at": profile.created_at,
                    "last_active": profile.last_active
                }
                for user_id, profile in self.profiles.items()
            }
            with open(self.profiles_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando perfiles: {e}")
    
    def create_profile(
        self,
        username: str,
        role: UserRole,
        language: str = "es"
    ) -> UserProfile:
        """Crea perfil de usuario."""
        import uuid
        
        user_id = str(uuid.uuid4())
        profile = UserProfile(
            user_id=user_id,
            username=username,
            role=role,
            language=language,
            created_at=datetime.now().isoformat(),
            last_active=datetime.now().isoformat()
        )
        
        self.profiles[user_id] = profile
        self._save_profiles()
        
        return profile
    
    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Obtiene perfil de usuario."""
        return self.profiles.get(user_id)
    
    def adapt_response_to_role(self, response: str, role: UserRole) -> str:
        """Adapta respuesta según rol del usuario."""
        if role == UserRole.EXECUTIVE:
            # Respuestas más concisas y orientadas a decisiones
            return self._make_executive_friendly(response)
        elif role == UserRole.TECHNICAL:
            # Respuestas más detalladas y técnicas
            return self._make_technical_friendly(response)
        elif role == UserRole.CLIENT:
            # Respuestas más simples y amigables
            return self._make_client_friendly(response)
        
        return response
    
    def _make_executive_friendly(self, text: str) -> str:
        """Hace texto más amigable para ejecutivos."""
        # Simplificar y resumir
        if len(text) > 500:
            return text[:500] + "...\n\n[Resumen ejecutivo - Para más detalles, consulta el documento completo]"
        return text
    
    def _make_technical_friendly(self, text: str) -> str:
        """Hace texto más técnico y detallado."""
        # Agregar más contexto técnico si es necesario
        return text
    
    def _make_client_friendly(self, text: str) -> str:
        """Hace texto más amigable para clientes."""
        # Simplificar lenguaje técnico
        return text
    
    def learn_from_query(self, user_id: str, query: str):
        """Aprende de patrones de consulta del usuario."""
        profile = self.get_profile(user_id)
        if profile:
            # Agregar patrón de consulta
            if query not in profile.query_patterns:
                profile.query_patterns.append(query)
                # Mantener solo últimos 50
                profile.query_patterns = profile.query_patterns[-50:]
                profile.last_active = datetime.now().isoformat()
                self._save_profiles()
    
    def get_recommendations(self, user_id: str) -> List[str]:
        """Obtiene recomendaciones personalizadas de documentos."""
        profile = self.get_profile(user_id)
        if not profile:
            return []
        
        # Basado en documentos favoritos y patrones de consulta
        return profile.favorite_documents[:10]

