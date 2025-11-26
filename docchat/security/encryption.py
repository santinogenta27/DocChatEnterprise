"""
Sistema de encriptación end-to-end para documentos y datos sensibles.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class DocumentEncryption:
    """
    Sistema de encriptación para documentos y datos sensibles.
    """
    
    def __init__(self, config):
        self.config = config
        self.key_file = Path(config.memory_dir) / ".encryption_key"
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self) -> bytes:
        """Obtiene o crea clave de encriptación."""
        if self.key_file.exists():
            try:
                return self.key_file.read_bytes()
            except Exception:
                pass
        
        # Crear nueva clave
        key = Fernet.generate_key()
        try:
            self.key_file.write_bytes(key)
            # Proteger archivo de clave
            os.chmod(self.key_file, 0o600)
        except Exception as e:
            print(f"Warning: No se pudo guardar clave de encriptación: {e}")
        
        return key
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Encripta datos."""
        return self.cipher.encrypt(data)
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Desencripta datos."""
        return self.cipher.decrypt(encrypted_data)
    
    def encrypt_file(self, file_path: Path) -> Path:
        """Encripta un archivo."""
        encrypted_path = file_path.with_suffix(file_path.suffix + ".encrypted")
        
        data = file_path.read_bytes()
        encrypted_data = self.encrypt_data(data)
        encrypted_path.write_bytes(encrypted_data)
        
        return encrypted_path
    
    def decrypt_file(self, encrypted_path: Path) -> Path:
        """Desencripta un archivo."""
        decrypted_path = encrypted_path.with_suffix("").with_suffix(
            encrypted_path.suffix.replace(".encrypted", "")
        )
        
        encrypted_data = encrypted_path.read_bytes()
        decrypted_data = self.decrypt_data(encrypted_data)
        decrypted_path.write_bytes(decrypted_data)
        
        return decrypted_path


class Watermarking:
    """
    Sistema de watermarking para trazabilidad de respuestas.
    """
    
    def __init__(self, config):
        self.config = config
    
    def add_watermark(self, text: str, metadata: dict) -> str:
        """
        Agrega watermark invisible a texto.
        """
        # Watermark básico (se puede mejorar con steganography)
        watermark_data = {
            "timestamp": metadata.get("timestamp", ""),
            "user_id": metadata.get("user_id", ""),
            "session_id": metadata.get("session_id", "")
        }
        
        # Codificar en base64 y agregar al final (invisible)
        watermark_str = base64.b64encode(
            str(watermark_data).encode()
        ).decode()
        
        # Agregar como comentario invisible (zero-width characters)
        zero_width_space = "\u200B"
        watermark_encoded = "".join(
            zero_width_space + char for char in watermark_str
        )
        
        return text + watermark_encoded
    
    def extract_watermark(self, text: str) -> Optional[dict]:
        """Extrae watermark de texto."""
        # Buscar zero-width characters
        zero_width_space = "\u200B"
        if zero_width_space not in text:
            return None
        
        # Extraer watermark
        watermark_parts = text.split(zero_width_space)
        if len(watermark_parts) < 2:
            return None
        
        try:
            watermark_str = "".join(watermark_parts[1:])
            watermark_data = base64.b64decode(watermark_str).decode()
            # Parsear (básico, se puede mejorar)
            return {"watermark": watermark_data}
        except Exception:
            return None

