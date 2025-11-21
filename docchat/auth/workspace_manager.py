"""Workspace management for multi-user collaboration."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict


@dataclass
class Workspace:
    """Workspace model."""
    workspace_id: str
    name: str
    owner_id: str
    members: List[str]  # user_ids
    documents: List[str]  # document hashes
    created_at: str = ""
    metadata: Dict = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Workspace":
        return cls(**data)


class WorkspaceManager:
    """Manages workspaces and document sharing."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.workspaces_file = self.data_dir / "workspaces.json"
        self._workspaces: Dict[str, Workspace] = {}
        self._load_workspaces()
    
    def _load_workspaces(self):
        """Load workspaces from disk."""
        if self.workspaces_file.exists():
            try:
                with open(self.workspaces_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._workspaces = {
                        wid: Workspace.from_dict(ws_data)
                        for wid, ws_data in data.items()
                    }
            except Exception:
                self._workspaces = {}
    
    def _save_workspaces(self):
        """Save workspaces to disk."""
        try:
            data = {
                wid: ws.to_dict()
                for wid, ws in self._workspaces.items()
            }
            with open(self.workspaces_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save workspaces: {e}")
    
    def create_workspace(self, name: str, owner_id: str) -> Workspace:
        """Create a new workspace."""
        import uuid
        workspace_id = f"ws_{uuid.uuid4().hex[:12]}"
        
        workspace = Workspace(
            workspace_id=workspace_id,
            name=name,
            owner_id=owner_id,
            members=[owner_id],
            documents=[]
        )
        
        self._workspaces[workspace_id] = workspace
        self._save_workspaces()
        return workspace
    
    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Get workspace by ID."""
        return self._workspaces.get(workspace_id)
    
    def get_user_workspaces(self, user_id: str) -> List[Workspace]:
        """Get all workspaces for a user."""
        return [
            ws for ws in self._workspaces.values()
            if user_id in ws.members or user_id == ws.owner_id
        ]
    
    def add_member(self, workspace_id: str, user_id: str):
        """Add member to workspace."""
        if workspace_id in self._workspaces:
            if user_id not in self._workspaces[workspace_id].members:
                self._workspaces[workspace_id].members.append(user_id)
                self._save_workspaces()
    
    def add_document(self, workspace_id: str, document_hash: str):
        """Add document to workspace."""
        if workspace_id in self._workspaces:
            if document_hash not in self._workspaces[workspace_id].documents:
                self._workspaces[workspace_id].documents.append(document_hash)
                self._save_workspaces()



