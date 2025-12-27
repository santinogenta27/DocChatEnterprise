"""
Natural Language Enhancer - Mejora la comprensión de lenguaje natural
Inspirado en Sierra.ai - Maneja typos, variaciones y lenguaje coloquial
"""

from __future__ import annotations

import re
from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher


class NaturalLanguageEnhancer:
    """
    Mejora la comprensión de lenguaje natural.
    
    Características:
    - Corrección de typos comunes
    - Normalización de variaciones
    - Detección de intenciones con errores tipográficos
    - Mejora de búsquedas de productos
    """
    
    def __init__(self):
        """Inicializa el enhancer."""
        # Typos comunes y sus correcciones
        self.common_typos = {
            "delivr": "deliver",
            "delivr tomorrow": "deliver tomorrow",
            "thse": "these",
            "recs": "recommendations",
            "rec": "recommendation",
            "bouqet": "bouquet",
            "bouqets": "bouquets",
            "flwers": "flowers",
            "flwers": "flowers",
            "tomorow": "tomorrow",
            "tomorow": "tomorrow",
            "availble": "available",
            "availble": "available",
            "shippng": "shipping",
            "shippng": "shipping",
            "adres": "address",
            "adres": "address",
        }
        
        # Variaciones comunes de palabras
        self.word_variations = {
            "delivery": ["deliver", "delivering", "delivered", "ship", "shipping", "shipped"],
            "tomorrow": ["tomorow", "tomorrow", "next day", "next-day"],
            "available": ["availble", "in stock", "in-stock", "have"],
            "recommendation": ["rec", "recs", "suggestion", "suggest"],
            "bouquet": ["bouqet", "bouqets", "arrangement", "flowers"],
        }
    
    def correct_typos(self, text: str) -> str:
        """
        Corrige typos comunes en el texto.
        
        Args:
            text: Texto con posibles typos
            
        Returns:
            Texto corregido
        """
        corrected = text.lower()
        
        # Aplicar correcciones de typos comunes
        for typo, correction in self.common_typos.items():
            corrected = corrected.replace(typo, correction)
        
        return corrected
    
    def normalize_text(self, text: str) -> str:
        """
        Normaliza el texto para mejor matching.
        
        Args:
            text: Texto a normalizar
            
        Returns:
            Texto normalizado
        """
        # Convertir a minúsculas
        normalized = text.lower()
        
        # Remover caracteres especiales excepto espacios y guiones
        normalized = re.sub(r'[^\w\s-]', '', normalized)
        
        # Normalizar espacios múltiples
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Trim
        normalized = normalized.strip()
        
        return normalized
    
    def find_similar_words(self, word: str, word_list: List[str], threshold: float = 0.7) -> List[str]:
        """
        Encuentra palabras similares usando SequenceMatcher.
        
        Args:
            word: Palabra a buscar
            word_list: Lista de palabras candidatas
            threshold: Umbral de similitud (0.0 - 1.0)
            
        Returns:
            Lista de palabras similares ordenadas por similitud
        """
        word_lower = word.lower()
        similarities = []
        
        for candidate in word_list:
            candidate_lower = candidate.lower()
            similarity = SequenceMatcher(None, word_lower, candidate_lower).ratio()
            
            if similarity >= threshold:
                similarities.append((candidate, similarity))
        
        # Ordenar por similitud (mayor primero)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return [word for word, _ in similarities]
    
    def enhance_product_search_query(self, query: str) -> Dict[str, Any]:
        """
        Mejora una consulta de búsqueda de productos.
        
        Args:
            query: Consulta original del usuario
            
        Returns:
            Dict con query mejorada y metadata
        """
        original_query = query
        corrected_query = self.correct_typos(query)
        normalized_query = self.normalize_text(corrected_query)
        
        # Detectar intenciones comunes
        intentions = []
        query_lower = normalized_query.lower()
        
        if any(word in query_lower for word in ["deliver", "shipping", "ship", "tomorrow", "next day"]):
            intentions.append("delivery_time")
        
        if any(word in query_lower for word in ["available", "stock", "have", "in stock"]):
            intentions.append("availability_check")
        
        if any(word in query_lower for word in ["recommend", "suggest", "rec", "show"]):
            intentions.append("product_recommendation")
        
        if any(word in query_lower for word in ["price", "cost", "how much"]):
            intentions.append("price_inquiry")
        
        return {
            "original_query": original_query,
            "corrected_query": corrected_query,
            "normalized_query": normalized_query,
            "intentions": intentions,
            "has_typos": original_query != corrected_query,
        }
    
    def extract_delivery_info(self, text: str) -> Dict[str, Any]:
        """
        Extrae información sobre entrega del texto.
        
        Args:
            text: Texto del usuario
            
        Returns:
            Dict con información extraída
        """
        text_lower = text.lower()
        info = {
            "wants_delivery": False,
            "delivery_date": None,
            "delivery_type": None,
        }
        
        # Detectar si quiere entrega
        if any(word in text_lower for word in ["deliver", "ship", "send", "delivery"]):
            info["wants_delivery"] = True
        
        # Detectar fecha
        if "tomorrow" in text_lower or "tomorow" in text_lower:
            info["delivery_date"] = "tomorrow"
            info["delivery_type"] = "next_day"
        elif "next day" in text_lower:
            info["delivery_date"] = "next_day"
            info["delivery_type"] = "next_day"
        elif "today" in text_lower:
            info["delivery_date"] = "today"
            info["delivery_type"] = "same_day"
        
        return info
    
    def extract_address_info(self, text: str) -> Dict[str, Any]:
        """
        Extrae información de dirección del texto.
        
        Args:
            text: Texto con información de dirección
            
        Returns:
            Dict con componentes de dirección
        """
        # Patrón simple para extraer dirección
        # En producción, usar librería especializada como usaddress
        address_info = {
            "name": None,
            "street": None,
            "city": None,
            "state": None,
            "zip": None,
            "country": None,
        }
        
        # Buscar nombre (palabras antes de números)
        name_match = re.search(r'^([A-Za-z\s]+?)(?=\d)', text)
        if name_match:
            address_info["name"] = name_match.group(1).strip()
        
        # Buscar código postal (5 dígitos o 5-4)
        zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', text)
        if zip_match:
            address_info["zip"] = zip_match.group(1)
        
        # Buscar estado (2 letras mayúsculas o nombre completo)
        state_match = re.search(r'\b([A-Z]{2})\b', text)
        if state_match:
            address_info["state"] = state_match.group(1)
        
        return address_info

