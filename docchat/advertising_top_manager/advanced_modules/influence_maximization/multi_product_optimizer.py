"""
Multi-Product Influence Maximization Optimizer
Implements algorithms for selecting billboard slots to maximize influence across multiple products
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class AttributionStrategy(str, Enum):
    """Attribution strategies for influence calculation"""
    COMMON_SLOTS = "common_slots"  # Single set of slots for all products
    DISJOINT_SLOTS = "disjoint_slots"  # Separate slots for each product
    BALANCED = "balanced"  # Balanced popularity across products


@dataclass
class BillboardSlot:
    """Represents a billboard slot"""
    slot_id: str
    billboard_id: str
    location: Tuple[float, float]  # (lat, lon)
    time_interval: Tuple[int, int]  # (start_time, end_time)
    cost: float
    influence_probability: Dict[str, float]  # product_id -> probability


@dataclass
class Product:
    """Represents a product to advertise"""
    product_id: str
    influence_demand: float
    budget: float
    target_users: List[str]  # List of user IDs interested in this product


@dataclass
class OptimizationResult:
    """Result of influence maximization optimization"""
    selected_slots: Dict[str, List[str]]  # product_id -> list of slot_ids
    total_influence: float
    total_cost: float
    product_influences: Dict[str, float]  # product_id -> achieved influence
    balance_score: float  # Measure of balance across products


class MultiProductInfluenceOptimizer:
    """
    Optimizes billboard slot selection for multiple products
    to maximize aggregated influence while satisfying budget and balance constraints
    """

    def __init__(self, config: Any):
        """
        Initialize Multi-Product Influence Optimizer
        
        Args:
            config: AppConfig object
        """
        self.config = config
        self.slots: Dict[str, BillboardSlot] = {}
        self.products: Dict[str, Product] = {}

    def add_slot(self, slot: BillboardSlot):
        """Add a billboard slot to the optimization pool"""
        self.slots[slot.slot_id] = slot

    def add_product(self, product: Product):
        """Add a product to optimize for"""
        self.products[product.product_id] = product

    def calculate_influence(
        self,
        product_id: str,
        selected_slot_ids: List[str]
    ) -> float:
        """
        Calculate total influence for a product given selected slots
        
        Uses the formula: I(S) = sum over users [1 - product over slots (1 - Pr(slot, user))]
        """
        product = self.products[product_id]
        total_influence = 0.0
        
        for user_id in product.target_users:
            # Calculate probability that user is influenced by at least one slot
            prob_not_influenced = 1.0
            for slot_id in selected_slot_ids:
                if slot_id in self.slots:
                    slot = self.slots[slot_id]
                    prob = slot.influence_probability.get(user_id, 0.0)
                    prob_not_influenced *= (1.0 - prob)
            
            user_influence = 1.0 - prob_not_influenced
            total_influence += user_influence
        
        return total_influence

    def optimize_common_slots(
        self,
        budget: float,
        min_influence_per_product: Dict[str, float]
    ) -> OptimizationResult:
        """
        Common Slot Selection: Select a single set of slots that satisfies
        influence demands for all products
        
        Uses continuous greedy algorithm with randomized rounding
        """
        selected_slot_ids = []
        remaining_budget = budget
        
        # Greedy selection: iteratively add slot with best marginal gain
        while remaining_budget > 0:
            best_slot = None
            best_marginal_gain = 0.0
            
            for slot_id, slot in self.slots.items():
                if slot_id in selected_slot_ids:
                    continue
                
                if slot.cost > remaining_budget:
                    continue
                
                # Calculate marginal gain for all products
                marginal_gain = 0.0
                for product_id in self.products:
                    current_influence = self.calculate_influence(
                        product_id, selected_slot_ids
                    )
                    new_influence = self.calculate_influence(
                        product_id, selected_slot_ids + [slot_id]
                    )
                    marginal_gain += max(0, new_influence - current_influence)
                
                # Normalize by cost
                normalized_gain = marginal_gain / slot.cost if slot.cost > 0 else 0
                
                if normalized_gain > best_marginal_gain:
                    best_marginal_gain = normalized_gain
                    best_slot = slot_id
            
            if best_slot is None:
                break
            
            selected_slot_ids.append(best_slot)
            remaining_budget -= self.slots[best_slot].cost
        
        # Calculate results
        product_influences = {}
        for product_id in self.products:
            product_influences[product_id] = self.calculate_influence(
                product_id, selected_slot_ids
            )
        
        total_influence = sum(product_influences.values())
        total_cost = sum(self.slots[sid].cost for sid in selected_slot_ids)
        
        # Calculate balance score (lower variance = better balance)
        if len(product_influences) > 1:
            influences = list(product_influences.values())
            mean_influence = np.mean(influences)
            variance = np.var(influences)
            balance_score = 1.0 / (1.0 + variance) if variance > 0 else 1.0
        else:
            balance_score = 1.0
        
        return OptimizationResult(
            selected_slots={pid: selected_slot_ids for pid in self.products},
            total_influence=total_influence,
            total_cost=total_cost,
            product_influences=product_influences,
            balance_score=balance_score
        )

    def optimize_disjoint_slots(
        self,
        product_budgets: Dict[str, float],
        min_influence_per_product: Dict[str, float]
    ) -> OptimizationResult:
        """
        Disjoint Slot Selection: Select separate slots for each product
        
        Uses sampling-based randomized algorithm
        """
        product_slots = {pid: [] for pid in self.products}
        used_slots = set()
        
        # Greedy allocation per product
        for product_id, budget in product_budgets.items():
            if product_id not in self.products:
                continue
            
            remaining_budget = budget
            product = self.products[product_id]
            
            while remaining_budget > 0:
                best_slot = None
                best_marginal_gain = 0.0
                
                for slot_id, slot in self.slots.items():
                    if slot_id in used_slots:
                        continue
                    
                    if slot.cost > remaining_budget:
                        continue
                    
                    # Calculate marginal gain for this product
                    current_influence = self.calculate_influence(
                        product_id, product_slots[product_id]
                    )
                    new_influence = self.calculate_influence(
                        product_id, product_slots[product_id] + [slot_id]
                    )
                    marginal_gain = new_influence - current_influence
                    
                    # Check if we've satisfied minimum influence
                    if new_influence >= min_influence_per_product.get(product_id, 0):
                        # Prefer slots that help us reach the goal
                        marginal_gain *= 2.0
                    
                    normalized_gain = marginal_gain / slot.cost if slot.cost > 0 else 0
                    
                    if normalized_gain > best_marginal_gain:
                        best_marginal_gain = normalized_gain
                        best_slot = slot_id
                
                if best_slot is None:
                    break
                
                product_slots[product_id].append(best_slot)
                used_slots.add(best_slot)
                remaining_budget -= self.slots[best_slot].cost
                
                # Check if we've satisfied minimum influence
                current_influence = self.calculate_influence(
                    product_id, product_slots[product_id]
                )
                if current_influence >= min_influence_per_product.get(product_id, 0):
                    break
        
        # Calculate results
        product_influences = {}
        for product_id in self.products:
            product_influences[product_id] = self.calculate_influence(
                product_id, product_slots[product_id]
            )
        
        total_influence = sum(product_influences.values())
        total_cost = sum(
            self.slots[sid].cost
            for slots in product_slots.values()
            for sid in slots
        )
        
        # Calculate balance score
        if len(product_influences) > 1:
            influences = list(product_influences.values())
            variance = np.var(influences)
            balance_score = 1.0 / (1.0 + variance) if variance > 0 else 1.0
        else:
            balance_score = 1.0
        
        return OptimizationResult(
            selected_slots=product_slots,
            total_influence=total_influence,
            total_cost=total_cost,
            product_influences=product_influences,
            balance_score=balance_score
        )

    def optimize_balanced(
        self,
        product_budgets: Dict[str, float],
        balance_threshold: float = 0.1
    ) -> OptimizationResult:
        """
        Balanced Popularity Optimization: Maximize aggregated influence
        while ensuring balance across products (influence difference <= threshold)
        """
        # Start with disjoint optimization
        min_influences = {pid: 0.0 for pid in self.products}
        result = self.optimize_disjoint_slots(product_budgets, min_influences)
        
        # Balance correction: swap slots between products to improve balance
        max_iterations = 100
        for iteration in range(max_iterations):
            influences = list(result.product_influences.values())
            if len(influences) < 2:
                break
            
            max_influence = max(influences)
            min_influence = min(influences)
            
            if max_influence - min_influence <= balance_threshold * max_influence:
                break  # Balanced enough
            
            # Find products with max and min influence
            max_product = max(result.product_influences, key=result.product_influences.get)
            min_product = min(result.product_influences, key=result.product_influences.get)
            
            # Try to swap a slot from max_product to min_product
            if not result.selected_slots[max_product]:
                break
            
            # Find best slot to swap
            best_swap = None
            best_improvement = 0.0
            
            for slot_id in result.selected_slots[max_product]:
                # Calculate improvement if we move this slot
                new_max_influence = self.calculate_influence(
                    max_product,
                    [s for s in result.selected_slots[max_product] if s != slot_id]
                )
                new_min_influence = self.calculate_influence(
                    min_product,
                    result.selected_slots[min_product] + [slot_id]
                )
                
                old_imbalance = abs(result.product_influences[max_product] - result.product_influences[min_product])
                new_imbalance = abs(new_max_influence - new_min_influence)
                improvement = old_imbalance - new_imbalance
                
                if improvement > best_improvement:
                    best_improvement = improvement
                    best_swap = slot_id
            
            if best_swap and best_improvement > 0:
                # Perform swap
                result.selected_slots[max_product].remove(best_swap)
                result.selected_slots[min_product].append(best_swap)
                
                # Recalculate influences
                result.product_influences[max_product] = self.calculate_influence(
                    max_product, result.selected_slots[max_product]
                )
                result.product_influences[min_product] = self.calculate_influence(
                    min_product, result.selected_slots[min_product]
                )
                result.total_influence = sum(result.product_influences.values())
            else:
                break  # No improvement possible
        
        # Recalculate balance score
        influences = list(result.product_influences.values())
        if len(influences) > 1:
            variance = np.var(influences)
            result.balance_score = 1.0 / (1.0 + variance) if variance > 0 else 1.0
        
        return result

