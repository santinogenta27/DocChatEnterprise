"""
Product Recommender - Sistema de Recomendaciones Inteligentes
Usa RAG + catálogo para recomendar productos complementarios, bundles, cross-sell
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum


class RecommendationType(Enum):
    """Tipos de recomendaciones."""
    COMPLEMENTARY = "complementary"  # Productos complementarios
    BUNDLE = "bundle"  # Bundles/paquetes
    CROSS_SELL = "cross_sell"  # Cross-selling
    UPSELL = "upsell"  # Up-selling (versión mejorada)
    SIMILAR = "similar"  # Productos similares
    POPULAR = "popular"  # Productos populares


@dataclass
class ProductRecommendation:
    """Recomendación de producto."""
    product_id: str
    product_name: str
    reason: str  # Por qué se recomienda
    recommendation_type: RecommendationType
    confidence: float  # 0.0 - 1.0
    price: Optional[float] = None
    discount: Optional[float] = None  # Descuento si es bundle


class ProductRecommender:
    """
    Sistema de recomendaciones inteligentes.
    
    Usa:
    - RAG para extraer información de productos desde PDFs
    - Catálogo de productos para relaciones complementarias
    - Contexto de conversación para personalización
    """
    
    def __init__(self, complementary_products_map: Optional[Dict[str, List[str]]] = None):
        """
        Inicializa el recomendador.
        
        Args:
            complementary_products_map: Mapa de product_id -> [complementary_product_ids]
        """
        # Mapa de productos complementarios (product_id -> [complementary_ids])
        self.complementary_map = complementary_products_map or {}
        
        # Bundles predefinidos (lista de product_ids que van juntos)
        self.bundles: List[List[str]] = []
    
    def recommend_based_on_rag(self,
                               current_product: str,
                               rag_context: str,
                               available_products: List[Dict]) -> List[ProductRecommendation]:
        """
        Recomienda productos basándose en información de RAG (PDFs).
        
        Args:
            current_product: Producto actual mencionado por el usuario
            rag_context: Contexto extraído de RAG sobre productos
            available_products: Lista de productos disponibles
            
        Returns:
            Lista de recomendaciones
        """
        recommendations = []
        
        # Buscar menciones de productos complementarios en RAG
        rag_lower = rag_context.lower()
        current_lower = current_product.lower()
        
        for product in available_products:
            product_name = product.get("name", product.get("title", ""))
            product_id = product.get("id", "")
            
            if not product_name or not product_id:
                continue
            
            product_lower = product_name.lower()
            
            # Si el producto actual y otro producto aparecen juntos en RAG, son complementarios
            if current_lower in rag_lower and product_lower in rag_lower:
                if product_lower != current_lower:
                    recommendations.append(ProductRecommendation(
                        product_id=product_id,
                        product_name=product_name,
                        reason=f"Mencionado junto con {current_product} en nuestra documentación",
                        recommendation_type=RecommendationType.COMPLEMENTARY,
                        confidence=0.7,
                        price=product.get("price", 0)
                    ))
        
        return recommendations
    
    def recommend_complementary(self,
                               product_id: str,
                               available_products: List[Dict]) -> List[ProductRecommendation]:
        """
        Recomienda productos complementarios usando mapa de relaciones.
        
        Args:
            product_id: ID del producto actual
            available_products: Lista de productos disponibles
            
        Returns:
            Lista de recomendaciones complementarias
        """
        recommendations = []
        
        # Obtener complementarios del mapa
        complementary_ids = self.complementary_map.get(product_id, [])
        
        # Crear dict de productos por ID para búsqueda rápida
        products_by_id = {p.get("id"): p for p in available_products if p.get("id")}
        
        for comp_id in complementary_ids:
            if comp_id in products_by_id:
                product = products_by_id[comp_id]
                recommendations.append(ProductRecommendation(
                    product_id=comp_id,
                    product_name=product.get("name", product.get("title", "")),
                    reason=f"Combinación perfecta con el producto que estás viendo",
                    recommendation_type=RecommendationType.COMPLEMENTARY,
                    confidence=0.8,
                    price=product.get("price", 0)
                ))
        
        return recommendations
    
    def recommend_bundles(self,
                         current_products: List[str],
                         available_products: List[Dict]) -> List[ProductRecommendation]:
        """
        Recomienda bundles/paquetes.
        
        Args:
            current_products: IDs de productos que el cliente está viendo/comprando
            available_products: Lista de productos disponibles
            
        Returns:
            Lista de recomendaciones de bundles
        """
        recommendations = []
        
        # Crear dict de productos por ID
        products_by_id = {p.get("id"): p for p in available_products if p.get("id")}
        
        # Buscar bundles que contengan productos actuales
        for bundle_product_ids in self.bundles:
            # Verificar si algún producto actual está en el bundle
            if any(pid in bundle_product_ids for pid in current_products):
                # Recomendar productos del bundle que no están en current_products
                for bundle_pid in bundle_product_ids:
                    if bundle_pid not in current_products and bundle_pid in products_by_id:
                        product = products_by_id[bundle_pid]
                        
                        # Calcular descuento del bundle (estimado 10-15%)
                        bundle_discount = 0.15
                        
                        recommendations.append(ProductRecommendation(
                            product_id=bundle_pid,
                            product_name=product.get("name", product.get("title", "")),
                            reason=f"Parte de un bundle especial - ¡ahorra {bundle_discount*100:.0f}% comprando juntos!",
                            recommendation_type=RecommendationType.BUNDLE,
                            confidence=0.85,
                            price=product.get("price", 0),
                            discount=bundle_discount
                        ))
        
        return recommendations
    
    def recommend_upsell(self,
                        current_product: Dict,
                        available_products: List[Dict]) -> List[ProductRecommendation]:
        """
        Recomienda versión superior (upsell).
        
        Args:
            current_product: Producto actual
            available_products: Lista de productos disponibles
            
        Returns:
            Lista de recomendaciones de upsell
        """
        recommendations = []
        
        current_name = current_product.get("name", current_product.get("title", "")).lower()
        current_price = current_product.get("price", 0)
        
        # Buscar productos con nombres similares pero "pro", "premium", "plus", etc.
        upsell_keywords = ["pro", "premium", "plus", "advanced", "deluxe", "ultimate"]
        
        for product in available_products:
            product_name = product.get("name", product.get("title", "")).lower()
            product_price = product.get("price", 0)
            
            # Si tiene keyword de upsell y precio mayor, puede ser upsell
            if any(keyword in product_name for keyword in upsell_keywords):
                # Verificar que sea de la misma categoría (nombres similares)
                if any(word in product_name for word in current_name.split()[:2]):  # Primeras 2 palabras
                    if product_price > current_price:
                        recommendations.append(ProductRecommendation(
                            product_id=product.get("id", ""),
                            product_name=product.get("name", product.get("title", "")),
                            reason=f"Versión mejorada del producto que estás viendo - más funciones y mayor durabilidad",
                            recommendation_type=RecommendationType.UPSELL,
                            confidence=0.75,
                            price=product_price
                        ))
        
        return recommendations
    
    def get_all_recommendations(self,
                               current_product_id: Optional[str],
                               current_product_name: Optional[str],
                               rag_context: Optional[str],
                               available_products: List[Dict],
                               limit: int = 5) -> List[ProductRecommendation]:
        """
        Obtiene todas las recomendaciones combinadas.
        
        Args:
            current_product_id: ID del producto actual
            current_product_name: Nombre del producto actual
            rag_context: Contexto de RAG
            available_products: Productos disponibles
            limit: Límite de recomendaciones
            
        Returns:
            Lista de recomendaciones ordenadas por confidence
        """
        all_recommendations = []
        
        # Recomendaciones complementarias (mapa)
        if current_product_id:
            all_recommendations.extend(self.recommend_complementary(current_product_id, available_products))
        
        # Recomendaciones basadas en RAG
        if current_product_name and rag_context:
            all_recommendations.extend(self.recommend_based_on_rag(current_product_name, rag_context, available_products))
        
        # Recomendaciones de bundles
        if current_product_id:
            all_recommendations.extend(self.recommend_bundles([current_product_id], available_products))
        
        # Recomendaciones de upsell
        if current_product_id:
            current_product = next((p for p in available_products if p.get("id") == current_product_id), None)
            if current_product:
                all_recommendations.extend(self.recommend_upsell(current_product, available_products))
        
        # Remover duplicados (mismo product_id)
        seen_ids = set()
        unique_recommendations = []
        for rec in all_recommendations:
            if rec.product_id not in seen_ids:
                seen_ids.add(rec.product_id)
                unique_recommendations.append(rec)
        
        # Ordenar por confidence
        unique_recommendations.sort(key=lambda x: x.confidence, reverse=True)
        
        return unique_recommendations[:limit]
    
    def format_recommendations_for_prompt(self, recommendations: List[ProductRecommendation]) -> str:
        """
        Formatea recomendaciones para incluir en prompt del LLM.
        
        Args:
            recommendations: Lista de recomendaciones
            
        Returns:
            Texto formateado
        """
        if not recommendations:
            return ""
        
        formatted = "**PRODUCTOS RECOMENDADOS (Cross-Sell/Up-Sell):**\n\n"
        
        for i, rec in enumerate(recommendations, 1):
            price_str = f"${rec.price:.2f}" if rec.price else "Precio disponible"
            discount_str = f" (Descuento: {rec.discount*100:.0f}%)" if rec.discount else ""
            
            formatted += f"{i}. **{rec.product_name}** - {price_str}{discount_str}\n"
            formatted += f"   - Razón: {rec.reason}\n"
            formatted += f"   - Tipo: {rec.recommendation_type.value}\n\n"
        
        formatted += "**INSTRUCCIÓN:** Menciona estos productos de forma natural en tu respuesta cuando sea apropiado. "
        formatted += "NO los listes todos de golpe - intégralos naturalmente en la conversación.\n\n"
        
        return formatted

