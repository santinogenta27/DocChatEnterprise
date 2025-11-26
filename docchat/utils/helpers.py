"""Funciones de utilidad para DocChat Enterprise."""
from __future__ import annotations

import pickle
import hashlib
from pathlib import Path
from typing import Any


def sha256_bytes(data: bytes) -> str:
    """Calcula el hash SHA256 de bytes."""
    return hashlib.sha256(data).hexdigest()


def read_bytes(file_obj) -> bytes:
    """Lee bytes de un objeto de archivo."""
    if hasattr(file_obj, "read"):
        pos = file_obj.tell() if hasattr(file_obj, "tell") else None
        data = file_obj.read()
        if hasattr(file_obj, "seek") and pos is not None:
            file_obj.seek(pos)
        else:
            try:
                file_obj.seek(0)
            except Exception:
                pass
        return data
    file_path = Path(file_obj)
    with open(file_path, "rb") as f:
        return f.read()


def save_pickle(path: Path, obj: Any) -> None:
    """Guarda un objeto en un archivo pickle."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        pickle.dump(obj, fh)


def load_pickle(path: Path) -> Any:
    """Carga un objeto desde un archivo pickle."""
    with open(path, "rb") as fh:
        return pickle.load(fh)



import pickle
import hashlib
from pathlib import Path
from typing import Any


def sha256_bytes(data: bytes) -> str:
    """Calcula el hash SHA256 de bytes."""
    return hashlib.sha256(data).hexdigest()


def read_bytes(file_obj) -> bytes:
    """Lee bytes de un objeto de archivo."""
    if hasattr(file_obj, "read"):
        pos = file_obj.tell() if hasattr(file_obj, "tell") else None
        data = file_obj.read()
        if hasattr(file_obj, "seek") and pos is not None:
            file_obj.seek(pos)
        else:
            try:
                file_obj.seek(0)
            except Exception:
                pass
        return data
    file_path = Path(file_obj)
    with open(file_path, "rb") as f:
        return f.read()


def save_pickle(path: Path, obj: Any) -> None:
    """Guarda un objeto en un archivo pickle."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        pickle.dump(obj, fh)


def load_pickle(path: Path) -> Any:
    """Carga un objeto desde un archivo pickle."""
    with open(path, "rb") as fh:
        return pickle.load(fh)

