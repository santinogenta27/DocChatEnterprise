"""
Sistema de Autenticación y RBAC
OAuth2/JWT, Role-based Access Control
"""

from __future__ import annotations

import os
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path


class Role(Enum):
    """Roles de usuario"""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    BILLING = "billing"


class Permission(Enum):
    """Permisos"""
    CREATE_CAMPAIGN = "create_campaign"
    EDIT_CAMPAIGN = "edit_campaign"
    DELETE_CAMPAIGN = "delete_campaign"
    VIEW_CAMPAIGN = "view_campaign"
    UPLOAD_ASSET = "upload_asset"
    GENERATE_VARIATIONS = "generate_variations"
    LAUNCH_CAMPAIGN = "launch_campaign"
    VIEW_BILLING = "view_billing"
    MANAGE_TENANT = "manage_tenant"


# Mapeo de roles a permisos
ROLE_PERMISSIONS = {
    Role.ADMIN: set(Permission),  # Todos los permisos
    Role.USER: {
        Permission.CREATE_CAMPAIGN,
        Permission.EDIT_CAMPAIGN,
        Permission.VIEW_CAMPAIGN,
        Permission.UPLOAD_ASSET,
        Permission.GENERATE_VARIATIONS,
        Permission.LAUNCH_CAMPAIGN,
        Permission.VIEW_BILLING
    },
    Role.VIEWER: {
        Permission.VIEW_CAMPAIGN,
        Permission.VIEW_BILLING
    },
    Role.BILLING: {
        Permission.VIEW_BILLING,
        Permission.VIEW_CAMPAIGN
    }
}


@dataclass
class User:
    """Usuario del sistema"""
    user_id: str
    tenant_id: str
    email: str
    role: Role
    api_key: Optional[str] = None
    api_key_hash: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_login: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class APIKey:
    """API Key para acceso programático"""
    key_id: str
    tenant_id: str
    user_id: str
    key_hash: str
    name: str
    permissions: Set[Permission] = field(default_factory=set)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = None
    last_used: Optional[str] = None
    revoked: bool = False


class AuthManager:
    """Gestor de autenticación"""
    
    def __init__(self, data_dir: Path, secret_key: Optional[str] = None):
        self.data_dir = data_dir / "auth"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
        self.algorithm = "HS256"
        
        self.users_file = self.data_dir / "users.json"
        self.api_keys_file = self.data_dir / "api_keys.json"
        
        self.users: Dict[str, User] = {}
        self.api_keys: Dict[str, APIKey] = {}
        
        self._load_data()
    
    def _load_data(self):
        """Carga usuarios y API keys"""
        # Cargar usuarios
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for uid, user_data in data.items():
                        user_data['role'] = Role(user_data['role'])
                        self.users[uid] = User(**user_data)
            except Exception as e:
                print(f"Error cargando usuarios: {e}")
        
        # Cargar API keys
        if self.api_keys_file.exists():
            try:
                with open(self.api_keys_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for kid, key_data in data.items():
                        key_data['permissions'] = {Permission(p) for p in key_data.get('permissions', [])}
                        self.api_keys[kid] = APIKey(**key_data)
            except Exception as e:
                print(f"Error cargando API keys: {e}")
    
    def _save_data(self):
        """Guarda usuarios y API keys"""
        # Guardar usuarios
        try:
            data = {
                uid: {
                    "user_id": u.user_id,
                    "tenant_id": u.tenant_id,
                    "email": u.email,
                    "role": u.role.value,
                    "api_key_hash": u.api_key_hash,
                    "created_at": u.created_at,
                    "last_login": u.last_login,
                    "metadata": u.metadata
                }
                for uid, u in self.users.items()
            }
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando usuarios: {e}")
        
        # Guardar API keys
        try:
            data = {
                kid: {
                    "key_id": k.key_id,
                    "tenant_id": k.tenant_id,
                    "user_id": k.user_id,
                    "key_hash": k.key_hash,
                    "name": k.name,
                    "permissions": [p.value for p in k.permissions],
                    "created_at": k.created_at,
                    "expires_at": k.expires_at,
                    "last_used": k.last_used,
                    "revoked": k.revoked
                }
                for kid, k in self.api_keys.items()
            }
            with open(self.api_keys_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando API keys: {e}")
    
    def create_user(
        self,
        tenant_id: str,
        email: str,
        role: Role = Role.USER
    ) -> User:
        """Crea un nuevo usuario"""
        user_id = hashlib.md5(f"{email}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        user = User(
            user_id=user_id,
            tenant_id=tenant_id,
            email=email,
            role=role
        )
        
        self.users[user_id] = user
        self._save_data()
        
        return user
    
    def generate_api_key(
        self,
        user_id: str,
        name: str,
        permissions: Optional[Set[Permission]] = None,
        expires_days: Optional[int] = None
    ) -> str:
        """Genera una nueva API key"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError(f"Usuario {user_id} no encontrado")
        
        # Generar key
        api_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        key_id = hashlib.md5(f"{user_id}{name}{datetime.now()}".encode()).hexdigest()[:16]
        
        expires_at = None
        if expires_days:
            expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
        
        # Permisos basados en rol si no se especifican
        if permissions is None:
            permissions = ROLE_PERMISSIONS.get(user.role, set())
        
        api_key_obj = APIKey(
            key_id=key_id,
            tenant_id=user.tenant_id,
            user_id=user_id,
            key_hash=key_hash,
            name=name,
            permissions=permissions,
            expires_at=expires_at
        )
        
        self.api_keys[key_id] = api_key_obj
        self._save_data()
        
        return api_key
    
    def verify_api_key(self, api_key: str) -> Optional[User]:
        """Verifica una API key y retorna el usuario"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        for key_obj in self.api_keys.values():
            if key_obj.key_hash == key_hash and not key_obj.revoked:
                # Verificar expiración
                if key_obj.expires_at:
                    if datetime.now() > datetime.fromisoformat(key_obj.expires_at):
                        continue
                
                # Actualizar último uso
                key_obj.last_used = datetime.now().isoformat()
                self._save_data()
                
                return self.users.get(key_obj.user_id)
        
        return None
    
    def generate_jwt_token(self, user: User, expires_hours: int = 24) -> str:
        """Genera JWT token"""
        payload = {
            "user_id": user.user_id,
            "tenant_id": user.tenant_id,
            "email": user.email,
            "role": user.role.value,
            "exp": datetime.utcnow() + timedelta(hours=expires_hours),
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_jwt_token(self, token: str) -> Optional[User]:
        """Verifica JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("user_id")
            return self.users.get(user_id)
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def has_permission(self, user: User, permission: Permission) -> bool:
        """Verifica si usuario tiene permiso"""
        user_permissions = ROLE_PERMISSIONS.get(user.role, set())
        return permission in user_permissions
    
    def check_permission(self, user: User, permission: Permission):
        """Verifica permiso y lanza excepción si no tiene"""
        if not self.has_permission(user, permission):
            raise PermissionError(f"Usuario no tiene permiso: {permission.value}")


def require_permission(permission: Permission):
    """Decorator para requerir permiso"""
    def decorator(func):
        def wrapper(self, user: User, *args, **kwargs):
            if not hasattr(self, 'auth_manager'):
                raise ValueError("AuthManager no disponible")
            self.auth_manager.check_permission(user, permission)
            return func(self, user, *args, **kwargs)
        return wrapper
    return decorator

