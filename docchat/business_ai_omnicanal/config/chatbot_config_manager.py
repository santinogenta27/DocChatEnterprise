"""Gestor de configuración del chatbot Business AI.

Permite cargar y guardar configuraciones del chatbot desde JSON (preferido) o .env (fallback).
JSON es más fácil de usar para usuarios no técnicos.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field


@dataclass
class ChatbotConfig:
    """Configuración completa del chatbot."""
    # Personalización básica
    tone: str = "friendly"
    personality: str = ""
    custom_instructions: str = ""
    
    # RAG
    rag_enabled: bool = False
    documents_dir: str = ""
    retriever_path: str = ""  # Ruta al archivo pickle del Hybrid Retriever guardado
    
    # Lead Scoring
    lead_scoring_enabled: bool = False
    lead_questions: List[Dict[str, Any]] = field(default_factory=list)
    lead_hot_threshold: int = 7
    
    # Handoff
    handoff_keywords: List[str] = field(default_factory=lambda: ["queja", "fraude", "hablar con humano", "supervisor"])
    handoff_sentiment_threshold: float = 0.7
    
    # Idioma
    default_language: str = "es"
    multilingual_enabled: bool = False
    
    # Objeciones
    objection_responses: Dict[str, str] = field(default_factory=dict)
    
    # Agendamiento de Citas (Booking/CTA) - PRIORIDAD ALTA 🚨
    booking_enabled: bool = False
    calendly_url: str = ""
    google_calendar_url: str = ""
    crm_webhook_url: str = ""
    crm_type: str = ""  # hubspot, salesforce, pipedrive, ""
    booking_message: str = "Veo que estás listo para empezar. ¿Te parece bien agendar una demo? Puedes elegir el horario que mejor te convenga."
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la configuración a diccionario."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatbotConfig":
        """Crea configuración desde diccionario."""
        return cls(**data)


class ChatbotConfigManager:
    """Gestor de configuración del chatbot.
    
    Usa JSON como fuente principal (más fácil para usuarios no técnicos).
    .env se usa como fallback para compatibilidad.
    """
    
    def __init__(self, config_json_path: Optional[Path] = None, env_path: Optional[Path] = None):
        # JSON es la fuente principal (más fácil para usuarios)
        self.config_json_path = config_json_path or Path("docchat/business_ai_omnicanal/config/chatbot_config.json")
        # .env como fallback
        self.env_path = env_path or Path(".env")
        self.config: Optional[ChatbotConfig] = None
    
    def load(self) -> ChatbotConfig:
        """Carga configuración desde JSON (preferido) o .env (fallback)."""
        # Intentar cargar desde JSON primero
        if self.config_json_path.exists():
            try:
                return self.load_from_json()
            except Exception as e:
                print(f"⚠️ Error cargando config desde JSON: {e}. Intentando .env...")
        
        # Fallback a .env
        return self.load_from_env()
    
    def load_from_json(self) -> ChatbotConfig:
        """Carga configuración desde archivo JSON."""
        try:
            with open(self.config_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            chatbot_config = ChatbotConfig.from_dict(data)
            self.config = chatbot_config
            return chatbot_config
        except Exception as e:
            print(f"⚠️ Error leyendo JSON: {e}")
            # Retornar config por defecto
            return ChatbotConfig()
    
    def save_to_json(self, chatbot_config: ChatbotConfig) -> bool:
        """Guarda configuración en archivo JSON."""
        try:
            # Crear directorio si no existe
            self.config_json_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convertir a diccionario y guardar
            with open(self.config_json_path, "w", encoding="utf-8") as f:
                json.dump(chatbot_config.to_dict(), f, indent=2, ensure_ascii=False)
            
            self.config = chatbot_config
            print(f"✅ Configuración guardada en: {self.config_json_path}")
            return True
        except Exception as e:
            print(f"❌ Error guardando JSON: {e}")
            return False
    
    def load_from_env(self) -> ChatbotConfig:
        """Carga configuración desde variables de entorno (.env) - Fallback."""
        chatbot_config = ChatbotConfig()
        
        # Personalización básica
        chatbot_config.tone = os.getenv("DOCCHAT_CHATBOT_TONE", "friendly")
        chatbot_config.personality = os.getenv("DOCCHAT_CHATBOT_PERSONALITY", "")
        chatbot_config.custom_instructions = os.getenv("DOCCHAT_CHATBOT_CUSTOM_INSTRUCTIONS", "")
        
        # RAG
        chatbot_config.rag_enabled = os.getenv("DOCCHAT_CHATBOT_RAG_ENABLED", "false").lower() == "true"
        chatbot_config.documents_dir = os.getenv("DOCCHAT_CHATBOT_DOCUMENTS_DIR", "")
        chatbot_config.retriever_path = os.getenv("DOCCHAT_CHATBOT_RETRIEVER_PATH", "")
        
        # Lead Scoring
        chatbot_config.lead_scoring_enabled = os.getenv("DOCCHAT_CHATBOT_LEAD_SCORING_ENABLED", "false").lower() == "true"
        lead_questions_json = os.getenv("DOCCHAT_CHATBOT_LEAD_QUESTIONS", "[]")
        try:
            chatbot_config.lead_questions = json.loads(lead_questions_json)
        except:
            chatbot_config.lead_questions = []
        chatbot_config.lead_hot_threshold = int(os.getenv("DOCCHAT_CHATBOT_LEAD_HOT_THRESHOLD", "7"))
        
        # Handoff
        handoff_keywords_str = os.getenv("DOCCHAT_CHATBOT_HANDOFF_KEYWORDS", "queja,fraude,hablar con humano,supervisor")
        chatbot_config.handoff_keywords = [k.strip() for k in handoff_keywords_str.split(",") if k.strip()]
        chatbot_config.handoff_sentiment_threshold = float(os.getenv("DOCCHAT_CHATBOT_HANDOFF_SENTIMENT", "0.7"))
        
        # Idioma
        chatbot_config.default_language = os.getenv("DOCCHAT_CHATBOT_DEFAULT_LANGUAGE", "es")
        chatbot_config.multilingual_enabled = os.getenv("DOCCHAT_CHATBOT_MULTILINGUAL", "false").lower() == "true"
        
        # Objeciones
        objection_responses_json = os.getenv("DOCCHAT_CHATBOT_OBJECTION_RESPONSES", "{}")
        try:
            chatbot_config.objection_responses = json.loads(objection_responses_json)
        except:
            chatbot_config.objection_responses = {}
        
        # Agendamiento de Citas (Booking/CTA)
        chatbot_config.booking_enabled = os.getenv("DOCCHAT_CHATBOT_BOOKING_ENABLED", "false").lower() == "true"
        chatbot_config.calendly_url = os.getenv("DOCCHAT_CHATBOT_CALENDLY_URL", "")
        chatbot_config.google_calendar_url = os.getenv("DOCCHAT_CHATBOT_GOOGLE_CALENDAR_URL", "")
        chatbot_config.crm_type = os.getenv("DOCCHAT_CHATBOT_CRM_TYPE", "")
        chatbot_config.crm_webhook_url = os.getenv("DOCCHAT_CHATBOT_CRM_WEBHOOK_URL", "")
        chatbot_config.booking_message = os.getenv("DOCCHAT_CHATBOT_BOOKING_MESSAGE", "Veo que estás listo para empezar. ¿Te parece bien agendar una demo? Puedes elegir el horario que mejor te convenga.")
        
        self.config = chatbot_config
        return chatbot_config
    
    def save_to_env(self, chatbot_config: ChatbotConfig) -> bool:
        """Guarda configuración en .env - Solo para compatibilidad."""
        try:
            # Leer .env actual
            env_vars = {}
            if self.env_path.exists():
                with open(self.env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "=" in line and not line.strip().startswith("#"):
                            key, value = line.strip().split("=", 1)
                            env_vars[key] = value
            
            # Actualizar variables
            env_vars["DOCCHAT_CHATBOT_TONE"] = chatbot_config.tone
            env_vars["DOCCHAT_CHATBOT_PERSONALITY"] = chatbot_config.personality
            env_vars["DOCCHAT_CHATBOT_CUSTOM_INSTRUCTIONS"] = chatbot_config.custom_instructions
            
            env_vars["DOCCHAT_CHATBOT_RAG_ENABLED"] = "true" if chatbot_config.rag_enabled else "false"
            env_vars["DOCCHAT_CHATBOT_DOCUMENTS_DIR"] = chatbot_config.documents_dir or ""
            
            env_vars["DOCCHAT_CHATBOT_LEAD_SCORING_ENABLED"] = "true" if chatbot_config.lead_scoring_enabled else "false"
            env_vars["DOCCHAT_CHATBOT_LEAD_QUESTIONS"] = json.dumps(chatbot_config.lead_questions)
            env_vars["DOCCHAT_CHATBOT_LEAD_HOT_THRESHOLD"] = str(chatbot_config.lead_hot_threshold)
            
            env_vars["DOCCHAT_CHATBOT_HANDOFF_KEYWORDS"] = ",".join(chatbot_config.handoff_keywords)
            env_vars["DOCCHAT_CHATBOT_HANDOFF_SENTIMENT"] = str(chatbot_config.handoff_sentiment_threshold)
            
            env_vars["DOCCHAT_CHATBOT_DEFAULT_LANGUAGE"] = chatbot_config.default_language
            env_vars["DOCCHAT_CHATBOT_MULTILINGUAL"] = "true" if chatbot_config.multilingual_enabled else "false"
            
            env_vars["DOCCHAT_CHATBOT_OBJECTION_RESPONSES"] = json.dumps(chatbot_config.objection_responses)
            
            # Agendamiento de Citas (Booking/CTA)
            env_vars["DOCCHAT_CHATBOT_BOOKING_ENABLED"] = "true" if chatbot_config.booking_enabled else "false"
            env_vars["DOCCHAT_CHATBOT_CALENDLY_URL"] = chatbot_config.calendly_url or ""
            env_vars["DOCCHAT_CHATBOT_GOOGLE_CALENDAR_URL"] = chatbot_config.google_calendar_url or ""
            env_vars["DOCCHAT_CHATBOT_CRM_TYPE"] = chatbot_config.crm_type or ""
            env_vars["DOCCHAT_CHATBOT_CRM_WEBHOOK_URL"] = chatbot_config.crm_webhook_url or ""
            env_vars["DOCCHAT_CHATBOT_BOOKING_MESSAGE"] = chatbot_config.booking_message or ""
            
            # Escribir .env
            with open(self.env_path, "w", encoding="utf-8") as f:
                for key, value in env_vars.items():
                    f.write(f"{key}={value}\n")
            
            return True
        except Exception as e:
            print(f"⚠️ Error guardando .env (no crítico): {e}")
            return False
    
    def get_config(self) -> ChatbotConfig:
        """Obtiene la configuración actual (carga si no está cargada)."""
        if self.config is None:
            return self.load()
        return self.config
    
    def save(self, chatbot_config: ChatbotConfig, also_update_env: bool = True) -> bool:
        """Guarda configuración en JSON (y opcionalmente en .env para compatibilidad)."""
        # Guardar en JSON (principal)
        success = self.save_to_json(chatbot_config)
        
        # Opcionalmente también actualizar .env para compatibilidad
        if also_update_env and success:
            try:
                self.save_to_env(chatbot_config)
            except Exception as e:
                print(f"⚠️ No se pudo actualizar .env (no crítico): {e}")
        
        return success











