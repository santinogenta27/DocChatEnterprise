"""
Cross-Selling Engine - Motor de cross-selling automático
Sugiere productos complementarios y relacionados
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage
import json

from .product_catalog import Product


@dataclass
class ProductRecommendation:
    """Recomendación de producto."""
    product: Product
    reason: str
    confidence: float  # 0.0 a 1.0
    recommendation_type: str  # "complementary", "similar", "popular", "trending"


class CrossSellingEngine:
    """
    Motor de cross-selling automático.
    
    Características:
    - Sugiere productos complementarios
    - Recomienda productos similares
    - Sugiere productos populares
    - Usa LLM para razonamiento contextual
    """
    
    def __init__(self, llm: BaseLanguageModel, product_catalog: Any):
        """
        Inicializa el motor de cross-selling.
        
        Args:
            llm: Modelo de lenguaje para razonamiento
            product_catalog: Catálogo de productos
        """
        self.llm = llm
        self.product_catalog = product_catalog
    
    def get_recommendations(
        self,
        current_product: Product,
        cart_items: Optional[List[Product]] = None,
        limit: int = 5
    ) -> List[ProductRecommendation]:
        """
        Obtiene recomendaciones de productos.
        
        Args:
            current_product: Producto actual que está viendo el usuario
            cart_items: Productos en el carrito
            limit: Número máximo de recomendaciones
        
        Returns:
            Lista de recomendaciones
        """
        recommendations = []
        
        # 1. Productos complementarios (usando LLM)
        complementary = self._get_complementary_products(current_product, limit=limit)
        recommendations.extend(complementary)
        
        # 2. Productos similares
        similar = self._get_similar_products(current_product, limit=limit)
        recommendations.extend(similar)
        
        # 3. Productos populares del mismo tipo
        popular = self._get_popular_products(current_product, limit=limit)
        recommendations.extend(popular)
        
        # 4. Recomendaciones basadas en carrito
        if cart_items:
            cart_based = self._get_cart_based_recommendations(cart_items, limit=limit)
            recommendations.extend(cart_based)
        
        # Eliminar duplicados y ordenar por confianza
        seen_ids = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec.product.id not in seen_ids:
                seen_ids.add(rec.product.id)
                unique_recommendations.append(rec)
        
        # Ordenar por confianza
        unique_recommendations.sort(key=lambda x: x.confidence, reverse=True)
        
        return unique_recommendations[:limit]
    
    def _get_complementary_products(
        self,
        product: Product,
        limit: int = 5
    ) -> List[ProductRecommendation]:
        """Obtiene productos complementarios usando LLM."""
        prompt = f"""Analiza este producto y sugiere productos complementarios que los clientes suelen comprar junto con él:

Producto: {product.title}
Descripción: {product.description[:200]}
Tipo: {product.product_type}
Precio: ${product.price}

Sugiere productos que:
1. Complementen este producto (accesorios, consumibles, etc.)
2. Sean relevantes y útiles juntos
3. Tengan sentido comercialmente

Responde en formato JSON con array de sugerencias:
[
    {{
        "product_type": "tipo de producto complementario",
        "reason": "por qué es complementario",
        "confidence": 0.8
    }}
]"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="Eres un experto en cross-selling y recomendaciones de productos."),
                HumanMessage(content=prompt)
            ])
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parsear JSON
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                suggestions = json.loads(json_match.group())
                
                recommendations = []
                for suggestion in suggestions[:limit]:
                    # Buscar productos del tipo sugerido
                    product_type = suggestion.get("product_type", "")
                    if product_type:
                        search_result = self.product_catalog.search_products(
                            query="",
                            product_type=product_type,
                            limit=1
                        )
                        
                        if search_result.products:
                            rec_product = search_result.products[0]
                            recommendations.append(ProductRecommendation(
                                product=rec_product,
                                reason=suggestion.get("reason", "Producto complementario"),
                                confidence=float(suggestion.get("confidence", 0.7)),
                                recommendation_type="complementary"
                            ))
                
                return recommendations
        except Exception as e:
            print(f"⚠️ Error obteniendo productos complementarios: {e}")
        
        return []
    
    def _get_similar_products(
        self,
        product: Product,
        limit: int = 5
    ) -> List[ProductRecommendation]:
        """Obtiene productos similares."""
        similar = self.product_catalog.get_related_products(product.id, limit=limit)
        
        recommendations = []
        for similar_product in similar:
            recommendations.append(ProductRecommendation(
                product=similar_product,
                reason=f"Similar a {product.title}",
                confidence=0.8,
                recommendation_type="similar"
            ))
        
        return recommendations
    
    def _get_popular_products(
        self,
        product: Product,
        limit: int = 5
    ) -> List[ProductRecommendation]:
        """Obtiene productos populares del mismo tipo."""
        if not product.product_type:
            return []
        
        search_result = self.product_catalog.search_products(
            query="",
            product_type=product.product_type,
            limit=limit + 1
        )
        
        recommendations = []
        for popular_product in search_result.products:
            if popular_product.id != product.id:
                recommendations.append(ProductRecommendation(
                    product=popular_product,
                    reason=f"Popular en {product.product_type}",
                    confidence=0.7,
                    recommendation_type="popular"
                ))
        
        return recommendations[:limit]
    
    def _get_cart_based_recommendations(
        self,
        cart_items: List[Product],
        limit: int = 5
    ) -> List[ProductRecommendation]:
        """Obtiene recomendaciones basadas en productos del carrito."""
        # Analizar tipos de productos en el carrito
        product_types = {}
        for item in cart_items:
            if item.product_type:
                product_types[item.product_type] = product_types.get(item.product_type, 0) + 1
        
        # Buscar productos complementarios para los tipos más comunes
        recommendations = []
        for product_type, count in sorted(product_types.items(), key=lambda x: x[1], reverse=True)[:2]:
            search_result = self.product_catalog.search_products(
                query="",
                product_type=product_type,
                limit=limit
            )
            
            for rec_product in search_result.products:
                # Evitar productos ya en el carrito
                if not any(item.id == rec_product.id for item in cart_items):
                    recommendations.append(ProductRecommendation(
                        product=rec_product,
                        reason=f"Completa tu compra de {product_type}",
                        confidence=0.75,
                        recommendation_type="cart_based"
                    ))
        
        return recommendations[:limit]
    
    def generate_cross_sell_message(
        self,
        recommendations: List[ProductRecommendation]
    ) -> str:
        """
        Genera un mensaje de cross-selling para mostrar al usuario.
        
        Args:
            recommendations: Lista de recomendaciones
        
        Returns:
            Mensaje formateado
        """
        if not recommendations:
            return ""
        
        top_rec = recommendations[0]
        
        message = f"💡 **¿Te interesa también?**\n\n"
        message += f"**{top_rec.product.title}** - ${top_rec.product.price:.2f}\n"
        message += f"_{top_rec.reason}_\n\n"
        
        if len(recommendations) > 1:
            message += "Otros productos que podrían interesarte:\n"
            for rec in recommendations[1:4]:  # Mostrar hasta 3 más
                message += f"• {rec.product.title} - ${rec.product.price:.2f}\n"
        
        return message




