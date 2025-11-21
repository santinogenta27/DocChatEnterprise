"""User management and authentication."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class User:
    """User model."""
    user_id: str
    email: str
    name: str
    plan: str = "free"  # free, pro, team, enterprise
    created_at: str = ""
    last_login: str = ""
    metadata: Dict = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "User":
        return cls(**data)


class UserManager:
    """Manages users and authentication."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.users_file = self.data_dir / "users.json"
        self._users: Dict[str, User] = {}
        self._load_users()
    
    def _load_users(self):
        """Load users from disk."""
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._users = {
                        uid: User.from_dict(user_data)
                        for uid, user_data in data.items()
                    }
            except Exception:
                self._users = {}
    
    def _save_users(self):
        """Save users to disk."""
        try:
            data = {
                uid: user.to_dict()
                for uid, user in self._users.items()
            }
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save users: {e}")
    
    def create_user(self, email: str, name: str, plan: str = "free") -> User:
        """Create a new user."""
        user_id = hashlib.md5(email.encode()).hexdigest()
        
        if user_id in self._users:
            return self._users[user_id]
        
        user = User(
            user_id=user_id,
            email=email,
            name=name,
            plan=plan
        )
        
        self._users[user_id] = user
        self._save_users()
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        user_id = hashlib.md5(email.encode()).hexdigest()
        return self._users.get(user_id)
    
    def update_user_plan(self, user_id: str, plan: str):
        """Update user plan."""
        if user_id in self._users:
            self._users[user_id].plan = plan
            self._save_users()
    
    def update_last_login(self, user_id: str):
        """Update last login timestamp."""
        if user_id in self._users:
            self._users[user_id].last_login = datetime.now().isoformat()
            self._save_users()



