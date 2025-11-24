"""
Sistema de Reglas Automáticas para Respuestas en Tiempo Real.
Permite programar respuestas específicas que se ejecutan automáticamente cuando llegan mensajes.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime


@dataclass
class AutoResponseRule:
    """Regla de respuesta automática."""
    rule_id: str
    name: str
    channel: str  # whatsapp, email, chat, all
    trigger_type: str  # keyword, pattern, always, ai_detection
    trigger_value: str  # palabra clave, regex, o "always"
    response_type: str  # fixed, ai_generated, template
    response_content: str  # respuesta fija o template
    enabled: bool = True
    priority: int = 0  # Mayor prioridad = se ejecuta primero
    conditions: Dict[str, Any] = field(default_factory=dict)  # Condiciones adicionales
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    usage_count: int = 0


class AutoResponseManager:
    """
    Gestor de reglas de respuesta automática.
    
    Permite:
    - Crear reglas de respuesta automática
    - Evaluar mensajes entrantes contra las reglas
    - Ejecutar respuestas automáticas
    - Gestionar múltiples canales (WhatsApp, Email, Chat, etc.)
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.rules_file = Path(config.memory_dir) / "auto_response_rules.json"
        self.rules: List[AutoResponseRule] = []
        self._load_rules()
    
    def _load_rules(self):
        """Carga reglas desde archivo."""
        try:
            if self.rules_file.exists():
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.rules = [AutoResponseRule(**rule) for rule in data]
            else:
                self.rules = []
                self._save_rules()
        except Exception as e:
            print(f"Error cargando reglas: {e}")
            self.rules = []
    
    def _save_rules(self):
        """Guarda reglas en archivo."""
        try:
            self.rules_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                data = [self._rule_to_dict(rule) for rule in self.rules]
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando reglas: {e}")
    
    def _rule_to_dict(self, rule: AutoResponseRule) -> Dict[str, Any]:
        """Convierte regla a diccionario."""
        return {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "channel": rule.channel,
            "trigger_type": rule.trigger_type,
            "trigger_value": rule.trigger_value,
            "response_type": rule.response_type,
            "response_content": rule.response_content,
            "enabled": rule.enabled,
            "priority": rule.priority,
            "conditions": rule.conditions,
            "created_at": rule.created_at,
            "updated_at": rule.updated_at,
            "usage_count": rule.usage_count
        }
    
    def add_rule(
        self,
        name: str,
        channel: str,
        trigger_type: str,
        trigger_value: str,
        response_type: str,
        response_content: str,
        priority: int = 0,
        conditions: Optional[Dict[str, Any]] = None
    ) -> AutoResponseRule:
        """Agrega una nueva regla."""
        rule_id = f"RULE-{int(datetime.now().timestamp())}-{len(self.rules)}"
        
        rule = AutoResponseRule(
            rule_id=rule_id,
            name=name,
            channel=channel,
            trigger_type=trigger_type,
            trigger_value=trigger_value,
            response_type=response_type,
            response_content=response_content,
            priority=priority,
            conditions=conditions or {}
        )
        
        self.rules.append(rule)
        self._save_rules()
        return rule
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Actualiza una regla existente."""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                for key, value in updates.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                rule.updated_at = datetime.now().isoformat()
                self._save_rules()
                return True
        return False
    
    def delete_rule(self, rule_id: str) -> bool:
        """Elimina una regla."""
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        self._save_rules()
        return True
    
    def get_rule(self, rule_id: str) -> Optional[AutoResponseRule]:
        """Obtiene una regla por ID."""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None
    
    def get_all_rules(self, channel: Optional[str] = None, enabled_only: bool = False) -> List[AutoResponseRule]:
        """Obtiene todas las reglas, opcionalmente filtradas."""
        rules = self.rules
        
        if channel:
            rules = [r for r in rules if r.channel == channel or r.channel == "all"]
        
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        
        # Ordenar por prioridad (mayor primero)
        rules.sort(key=lambda x: x.priority, reverse=True)
        
        return rules
    
    def evaluate_message(
        self,
        channel: str,
        message: str,
        customer_data: Optional[Dict[str, Any]] = None
    ) -> Optional[AutoResponseRule]:
        """
        Evalúa un mensaje entrante y retorna la regla que debe ejecutarse.
        
        Args:
            channel: Canal del mensaje (whatsapp, email, chat, etc.)
            message: Contenido del mensaje
            customer_data: Datos adicionales del cliente
        
        Returns:
            AutoResponseRule que debe ejecutarse, o None si no hay match
        """
        # Obtener reglas relevantes (habilitadas, del canal correcto, ordenadas por prioridad)
        relevant_rules = self.get_all_rules(channel=channel, enabled_only=True)
        
        message_lower = message.lower()
        
        for rule in relevant_rules:
            # Verificar condiciones adicionales
            if rule.conditions:
                if not self._check_conditions(rule.conditions, customer_data or {}):
                    continue
            
            # Evaluar trigger
            if rule.trigger_type == "always":
                # Siempre ejecutar
                rule.usage_count += 1
                self._save_rules()
                return rule
            
            elif rule.trigger_type == "keyword":
                # Buscar palabra clave
                keywords = [kw.strip().lower() for kw in rule.trigger_value.split(",")]
                if any(kw in message_lower for kw in keywords):
                    rule.usage_count += 1
                    self._save_rules()
                    return rule
            
            elif rule.trigger_type == "pattern":
                # Buscar patrón regex
                try:
                    pattern = re.compile(rule.trigger_value, re.IGNORECASE)
                    if pattern.search(message):
                        rule.usage_count += 1
                        self._save_rules()
                        return rule
                except re.error:
                    continue
            
            elif rule.trigger_type == "ai_detection":
                # Esto se manejaría con el LLM, por ahora skip
                continue
        
        return None
    
    def _check_conditions(self, conditions: Dict[str, Any], customer_data: Dict[str, Any]) -> bool:
        """Verifica condiciones adicionales."""
        # Ejemplo: verificar si el cliente es VIP, si es horario laboral, etc.
        for key, expected_value in conditions.items():
            actual_value = customer_data.get(key)
            if actual_value != expected_value:
                return False
        return True
    
    def generate_response(
        self,
        rule: AutoResponseRule,
        message: str,
        customer_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Genera la respuesta basada en la regla.
        
        Args:
            rule: Regla a ejecutar
            message: Mensaje original del cliente
            customer_data: Datos del cliente
        
        Returns:
            Texto de la respuesta
        """
        if rule.response_type == "fixed":
            # Respuesta fija
            return rule.response_content
        
        elif rule.response_type == "template":
            # Template con variables
            response = rule.response_content
            
            # Reemplazar variables comunes
            if customer_data:
                response = response.replace("{nombre}", customer_data.get("name", "cliente"))
                response = response.replace("{email}", customer_data.get("email", ""))
            
            response = response.replace("{fecha}", datetime.now().strftime("%d/%m/%Y"))
            response = response.replace("{hora}", datetime.now().strftime("%H:%M"))
            
            return response
        
        elif rule.response_type == "ai_generated":
            # Esto se manejaría con el LLM del CustomerServiceAgent
            # Por ahora retornamos el contenido como base
            return rule.response_content
        
        return rule.response_content
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de las reglas."""
        total_rules = len(self.rules)
        enabled_rules = len([r for r in self.rules if r.enabled])
        total_usage = sum(r.usage_count for r in self.rules)
        
        by_channel = {}
        for rule in self.rules:
            channel = rule.channel
            by_channel[channel] = by_channel.get(channel, 0) + 1
        
        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "disabled_rules": total_rules - enabled_rules,
            "total_usage": total_usage,
            "by_channel": by_channel,
            "top_rules": sorted(
                [{"name": r.name, "usage": r.usage_count} for r in self.rules],
                key=lambda x: x["usage"],
                reverse=True
            )[:5]
        }

