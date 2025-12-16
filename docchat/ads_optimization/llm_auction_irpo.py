"""
LLM-AUCTION IRPO: Iterative Reward-Preference Optimization
Implementación del algoritmo IRPO para optimizar LLMs en publicidad nativa
Basado en: LLM-AUCTION paper - Section 4.1.2
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import asyncio

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


@dataclass
class ResponsePair:
    """Par de respuestas para DPO"""
    winning_response: str
    losing_response: str
    reward_difference: float


@dataclass
class RewardModel:
    """Modelo de recompensa para IRPO"""
    pctr_model: Any  # Modelo de pCTR
    lambda_param: float = 1.0  # Peso para user experience
    
    def compute_reward(
        self,
        response: str,
        ads: List[Dict[str, Any]],
        bids: List[float],
        user_query: str,
        user_profile: Dict[str, Any]
    ) -> float:
        """
        Calcula reward usando pCTR y user experience
        R(x, h, a, b, y) = Σ(bi * pctri * 1{ai ∈ y}) + λ * s_resp_u(y)
        """
        total_reward = 0.0
        
        # Reward de ads expuestos
        for i, ad in enumerate(ads):
            if ad["id"] in response:  # Ad está en la respuesta
                pctr = self.pctr_model.predict(
                    query=user_query,
                    response=response,
                    ad=ad,
                    user_profile=user_profile
                )
                total_reward += bids[i] * pctr
        
        # User experience term (simplificado)
        user_exp_score = self._compute_user_experience(response, ads)
        total_reward += self.lambda_param * user_exp_score
        
        return total_reward
    
    def _compute_user_experience(self, response: str, ads: List[Dict[str, Any]]) -> float:
        """Calcula score de user experience"""
        # Penalizar demasiados ads
        num_ads = sum(1 for ad in ads if ad["id"] in response)
        if num_ads > 3:
            return -10 * (num_ads - 3) ** 2
        
        # Penalizar formato incorrecto
        if "@" not in response or "[" not in response:
            return -500
        
        return 0.0


class IRPOOptimizer:
    """
    Iterative Reward-Preference Optimization
    Optimiza LLM iterativamente alternando entre actualizar reward model y LLM
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.llm = None
        self.reward_model = None
        
        if LLM_AVAILABLE and hasattr(config, 'openai_api_key') and config.openai_api_key:
            self.llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0.7,
                api_key=config.openai_api_key
            )
        
        # Inicializar reward model
        self.reward_model = RewardModel(
            pctr_model=self._create_pctr_model(),
            lambda_param=1.0
        )
        
        # Historial de optimización
        self.optimization_history: List[Dict[str, Any]] = []
    
    def _create_pctr_model(self) -> Any:
        """Crea modelo de pCTR (simplificado)"""
        # En producción, esto sería un modelo entrenado
        class SimplePCTRModel:
            def predict(self, query: str, response: str, ad: Dict[str, Any], user_profile: Dict[str, Any]) -> float:
                # Simulación: pCTR basado en relevancia simple
                relevance = 0.5
                if ad["title"].lower() in query.lower():
                    relevance += 0.3
                if ad["title"].lower() in response.lower():
                    relevance += 0.2
                return min(1.0, max(0.0, relevance))
        
        return SimplePCTRModel()
    
    async def optimize_llm(
        self,
        user_query: str,
        user_profile: Dict[str, Any],
        candidate_ads: List[Dict[str, Any]],
        bids: List[float],
        num_iterations: int = 3,
        num_samples_per_iter: int = 5,
        dpo_threshold: float = 10.0
    ) -> str:
        """
        Optimiza LLM usando IRPO
        """
        current_prompt = self._get_base_prompt()
        
        for iteration in range(num_iterations):
            # Fase 1: Actualizar reward model con datos online
            online_data = await self._collect_online_data(
                user_query, user_profile, candidate_ads, bids, num_samples_per_iter
            )
            self._update_reward_model(online_data)
            
            # Fase 2: Actualizar LLM usando DPO
            response_pairs = self._create_dpo_pairs(
                user_query, user_profile, candidate_ads, bids, current_prompt, dpo_threshold
            )
            
            if response_pairs:
                current_prompt = await self._update_llm_with_dpo(
                    current_prompt, response_pairs, iteration
                )
            
            # Guardar historial
            self.optimization_history.append({
                "iteration": iteration,
                "num_pairs": len(response_pairs),
                "timestamp": datetime.now().isoformat()
            })
        
        return current_prompt
    
    async def _collect_online_data(
        self,
        query: str,
        profile: Dict[str, Any],
        ads: List[Dict[str, Any]],
        bids: List[float],
        num_samples: int
    ) -> List[Dict[str, Any]]:
        """Recolecta datos online para actualizar reward model"""
        data = []
        
        for _ in range(num_samples):
            # Generar respuesta con LLM actual
            response = await self._generate_response(query, profile, ads, bids)
            
            # Simular click feedback (en producción sería real)
            clicks = self._simulate_clicks(response, ads, profile)
            
            data.append({
                "query": query,
                "response": response,
                "clicks": clicks,
                "ads": ads,
                "bids": bids
            })
        
        return data
    
    def _update_reward_model(self, online_data: List[Dict[str, Any]]):
        """Actualiza reward model con datos online"""
        # En producción, esto entrenaría el modelo pCTR
        # Por ahora, solo actualizamos parámetros
        pass
    
    def _create_dpo_pairs(
        self,
        query: str,
        profile: Dict[str, Any],
        ads: List[Dict[str, Any]],
        bids: List[float],
        prompt: str,
        threshold: float
    ) -> List[ResponsePair]:
        """Crea pares DPO basados en diferencias de reward"""
        # Generar múltiples respuestas
        responses = []
        rewards = []
        
        for _ in range(5):  # Generar 5 respuestas
            response = asyncio.run(self._generate_response(query, profile, ads, bids))
            reward = self.reward_model.compute_reward(response, ads, bids, query, profile)
            responses.append(response)
            rewards.append(reward)
        
            # Seleccionar winner
            if NUMPY_AVAILABLE:
                winner_idx = np.argmax(rewards)
            else:
                winner_idx = rewards.index(max(rewards))
            winner_response = responses[winner_idx]
            winner_reward = rewards[winner_idx]
        
        # Crear pares con losers que tengan diferencia > threshold
        pairs = []
        for i, (response, reward) in enumerate(zip(responses, rewards)):
            if i != winner_idx and (winner_reward - reward) > threshold:
                pairs.append(ResponsePair(
                    winning_response=winner_response,
                    losing_response=response,
                    reward_difference=winner_reward - reward
                ))
        
        return pairs
    
    async def _update_llm_with_dpo(
        self,
        current_prompt: str,
        response_pairs: List[ResponsePair],
        iteration: int
    ) -> str:
        """Actualiza prompt del LLM usando DPO"""
        if not self.llm or not response_pairs:
            return current_prompt
        
        # Construir prompt de optimización
        pairs_text = "\n".join([
            f"Winner: {pair.winning_response}\nLoser: {pair.losing_response}\n"
            for pair in response_pairs[:3]  # Limitar a 3 pares
        ])
        
        optimization_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un experto en optimización de prompts para publicidad nativa.
Analiza los pares de respuestas ganadoras vs perdedoras y mejora el prompt para generar
respuestas más efectivas que maximicen reward (pCTR * bid + user experience)."""),
            ("user", f"""Prompt actual:
{current_prompt}

Pares de respuestas (Winner vs Loser):
{pairs_text}

Mejora el prompt para que genere más respuestas como las ganadoras.
Retorna solo el prompt mejorado, sin explicaciones adicionales.""")
        ])
        
        try:
            chain = optimization_prompt | self.llm
            response = chain.invoke({})
            return response.content.strip()
        except Exception as e:
            print(f"⚠️ Error actualizando LLM con DPO: {e}")
            return current_prompt
    
    async def _generate_response(
        self,
        query: str,
        profile: Dict[str, Any],
        ads: List[Dict[str, Any]],
        bids: List[float]
    ) -> str:
        """Genera respuesta usando LLM"""
        if not self.llm:
            return "Respuesta generada"
        
        # Construir prompt con ads y bids
        ads_text = "\n".join([
            f"Ad {i+1}: {ad['title']} (Bid: ${bids[i]})"
            for i, ad in enumerate(ads)
        ])
        
        prompt = f"""Usuario pregunta: {query}
Perfil usuario: {json.dumps(profile, ensure_ascii=False)}
Anuncios disponibles:
{ads_text}

Genera una respuesta natural que integre los anuncios más relevantes en formato @Ad Title@[Ad ID]."""
        
        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            print(f"⚠️ Error generando respuesta: {e}")
            return "Respuesta generada"
    
    def _simulate_clicks(self, response: str, ads: List[Dict[str, Any]], profile: Dict[str, Any]) -> Dict[str, bool]:
        """Simula clicks (en producción sería feedback real)"""
        clicks = {}
        for ad in ads:
            # Simulación simple: click si el ad está en la respuesta
            clicks[ad["id"]] = ad["id"] in response
        return clicks
    
    def _get_base_prompt(self) -> str:
        """Retorna prompt base para generación"""
        return """Eres un asistente de IA que ayuda a usuarios con información mientras
integra anuncios relevantes de forma natural. Los anuncios deben aparecer en formato
@Ad Title@[Ad ID] y deben ser relevantes a la consulta del usuario."""
