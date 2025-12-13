"""
KafkaBridge - integración opcional con Kafka/Confluent.

Se inicializa solo si:
- Existe librería `confluent_kafka`
- Se proveen parámetros mínimos en config (bootstrap servers)

Uso:
    bridge = KafkaBridge(bootstrap_servers="localhost:9092")
    bridge.produce("docchat-events", {"type": "document_uploaded"})
"""

from __future__ import annotations

import json
from typing import Optional, Dict, Any

try:
    from confluent_kafka import Producer

    KAFKA_AVAILABLE = True
except Exception:
    Producer = None  # type: ignore
    KAFKA_AVAILABLE = False


class KafkaBridge:
    """Capa mínima para publicar eventos en Kafka."""

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        security_config: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
    ):
        self.enabled = bool(enabled and bootstrap_servers and KAFKA_AVAILABLE)
        self.bootstrap_servers = bootstrap_servers or ""
        self.security_config = security_config or {}
        self._producer: Optional[Producer] = None

        if self.enabled:
            config = {"bootstrap.servers": self.bootstrap_servers}
            config.update(self.security_config)
            try:
                self._producer = Producer(config)
            except Exception as e:
                print(f"⚠️ [KafkaBridge] No se pudo inicializar Producer: {e}")
                self.enabled = False

    def produce(self, topic: str, data: Dict[str, Any]) -> None:
        """Publica un evento en Kafka (best effort)."""
        if not self.enabled or not self._producer:
            return
        try:
            payload = json.dumps(data, ensure_ascii=False)
            self._producer.produce(topic, payload.encode("utf-8"))
            self._producer.poll(0)
        except Exception as e:
            print(f"⚠️ [KafkaBridge] Error enviando a Kafka: {e}")

    def flush(self, timeout: float = 2.0) -> None:
        if self.enabled and self._producer:
            try:
                self._producer.flush(timeout)
            except Exception:
                pass


__all__ = ["KafkaBridge", "KAFKA_AVAILABLE"]

