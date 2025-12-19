"""
CUSTOMER SUPPORT MANAGER - Autonomous Resolution Agent
=====================================================

Sistema completo de agente autónomo de atención al cliente que:
- Resuelve 70-85% de problemas rutinarios de forma autónoma
- Usa RAG para búsqueda contextual precisa en bases de conocimiento
- Orquesta herramientas para acciones reales (reembolsos, tickets, rastreo)
- Se integra con herramientas/APIs externas
- Escala casos complejos a humanos
- Listo para SaaS, embeddable vía iframe o API

Versión: 1.0.0
"""

from .customer_support_mode import CustomerSupportMode

__version__ = "1.0.0"
__all__ = ['CustomerSupportMode']




