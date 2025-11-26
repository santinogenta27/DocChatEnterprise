"""
Sistema de Control de Acceso Basado en Roles (RBAC).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..config import AppConfig


class Permission(Enum):
    """Permisos disponibles."""
    READ_DOCUMENTS = "read_documents"
    WRITE_DOCUMENTS = "write_documents"
    DELETE_DOCUMENTS = "delete_documents"
    QUERY_RAG = "query_rag"
    MANAGE_USERS = "manage_users"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_SETTINGS = "manage_settings"
    EXPORT_DATA = "export_data"
    API_ACCESS = "api_access"


class Role(Enum):
    """Roles predefinidos."""
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    VIEWER = "viewer"
    API_USER = "api_user"


@dataclass
class User:
    """Usuario del sistema."""
    user_id: str
    username: str
    email: str
    role: Role
    permissions: Set[Permission] = field(default_factory=set)
    created_at: str = ""
    last_login: str = ""


class RBACManager:
    """
    Gestor de Control de Acceso Basado en Roles.
    """
    
    # Mapeo de roles a permisos
    ROLE_PERMISSIONS = {
        Role.ADMIN: {
            Permission.READ_DOCUMENTS,
            Permission.WRITE_DOCUMENTS,
            Permission.DELETE_DOCUMENTS,
            Permission.QUERY_RAG,
            Permission.MANAGE_USERS,
            Permission.VIEW_ANALYTICS,
            Permission.MANAGE_SETTINGS,
            Permission.EXPORT_DATA,
            Permission.API_ACCESS
        },
        Role.MANAGER: {
            Permission.READ_DOCUMENTS,
            Permission.WRITE_DOCUMENTS,
            Permission.QUERY_RAG,
            Permission.VIEW_ANALYTICS,
            Permission.EXPORT_DATA
        },
        Role.USER: {
            Permission.READ_DOCUMENTS,
            Permission.QUERY_RAG
        },
        Role.VIEWER: {
            Permission.READ_DOCUMENTS,
            Permission.QUERY_RAG
        },
        Role.API_USER: {
            Permission.API_ACCESS,
            Permission.QUERY_RAG
        }
    }
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.data_dir = Path(config.memory_dir) / "rbac"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.users_file = self.data_dir / "users.json"
        self.users: Dict[str, User] = self._load_users()
    
    def _load_users(self) -> Dict[str, User]:
        """Carga usuarios desde archivo."""
        try:
            if self.users_file.exists():
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {
                        user_id: User(
                            user_id=u["user_id"],
                            username=u["username"],
                            email=u["email"],
                            role=Role(u["role"]),
                            permissions={Permission(p) for p in u.get("permissions", [])},
                            created_at=u.get("created_at", ""),
                            last_login=u.get("last_login", "")
                        )
                        for user_id, u in data.items()
                    }
            return {}
        except Exception:
            return {}
    
    def _save_users(self):
        """Guarda usuarios."""
        try:
            data = {
                user_id: {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role.value,
                    "permissions": [p.value for p in user.permissions],
                    "created_at": user.created_at,
                    "last_login": user.last_login
                }
                for user_id, user in self.users.items()
            }
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando usuarios: {e}")
    
    def create_user(
        self,
        username: str,
        email: str,
        role: Role,
        custom_permissions: Optional[Set[Permission]] = None
    ) -> User:
        """Crea un nuevo usuario."""
        import uuid
        from datetime import datetime
        
        user_id = str(uuid.uuid4())
        
        # Obtener permisos del rol
        permissions = self.ROLE_PERMISSIONS.get(role, set()).copy()
        
        # Agregar permisos personalizados
        if custom_permissions:
            permissions.update(custom_permissions)
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            role=role,
            permissions=permissions,
            created_at=datetime.now().isoformat()
        )
        
        self.users[user_id] = user
        self._save_users()
        
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Obtiene usuario por ID."""
        return self.users.get(user_id)
    
    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """Verifica si usuario tiene permiso."""
        user = self.get_user(user_id)
        if not user:
            return False
        
        return permission in user.permissions
    
    def has_role(self, user_id: str, role: Role) -> bool:
        """Verifica si usuario tiene rol."""
        user = self.get_user(user_id)
        if not user:
            return False
        
        return user.role == role
    
    def grant_permission(self, user_id: str, permission: Permission):
        """Otorga permiso a usuario."""
        user = self.get_user(user_id)
        if user:
            user.permissions.add(permission)
            self._save_users()
    
    def revoke_permission(self, user_id: str, permission: Permission):
        """Revoca permiso de usuario."""
        user = self.get_user(user_id)
        if user:
            user.permissions.discard(permission)
            self._save_users()

