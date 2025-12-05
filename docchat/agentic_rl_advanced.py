"""Reinforcement Learning Avanzado para Agentic Workflows.

Implementa algoritmos RL más avanzados:
- Q-Learning para selección de acciones
- Policy Gradient para optimización de políticas
- Experience Replay para aprendizaje estable
"""

from __future__ import annotations

import json
import random
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import sqlite3


@dataclass
class RLState:
    """Estado en el espacio de RL."""
    workflow_id: str
    agent_id: str
    state_features: Dict[str, Any]  # Features del estado actual
    timestamp: str = field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())


@dataclass
class RLAction:
    """Acción en el espacio de RL."""
    action_id: str
    action_type: str
    parameters: Dict[str, Any]


@dataclass
class RLExperience:
    """Experiencia para experience replay."""
    state: RLState
    action: RLAction
    reward: float
    next_state: Optional[RLState]
    done: bool
    timestamp: str = field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())


class QLearningAgent:
    """Agente Q-Learning para selección de acciones óptimas."""
    
    def __init__(
        self,
        agent_id: str,
        learning_rate: float = 0.1,
        discount_factor: float = 0.9,
        epsilon: float = 0.1,  # Exploration rate
        epsilon_decay: float = 0.995,
        min_epsilon: float = 0.01,
    ):
        self.agent_id = agent_id
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        
        # Q-table: state -> action -> Q-value
        self.q_table: Dict[str, Dict[str, float]] = {}
        
        # Experience buffer
        self.experience_buffer: List[RLExperience] = []
        self.max_buffer_size = 1000
    
    def get_state_key(self, state: RLState) -> str:
        """Convierte estado a clave para Q-table."""
        # Crear clave basada en features relevantes
        features = state.state_features
        key_parts = [
            str(features.get("workflow_step", "")),
            str(features.get("agent_status", "")),
            str(features.get("context_hash", "")),
        ]
        return "|".join(key_parts)
    
    def get_action_key(self, action: RLAction) -> str:
        """Convierte acción a clave."""
        return f"{action.action_type}:{action.action_id}"
    
    def select_action(
        self,
        state: RLState,
        available_actions: List[RLAction],
    ) -> RLAction:
        """Selecciona acción usando epsilon-greedy policy."""
        if not available_actions:
            raise ValueError("No hay acciones disponibles")
        
        # Exploration: acción aleatoria
        if random.random() < self.epsilon:
            return random.choice(available_actions)
        
        # Exploitation: mejor acción según Q-table
        state_key = self.get_state_key(state)
        
        if state_key not in self.q_table:
            # Estado nuevo, acción aleatoria
            return random.choice(available_actions)
        
        # Encontrar acción con mayor Q-value
        best_action = None
        best_q_value = float('-inf')
        
        for action in available_actions:
            action_key = self.get_action_key(action)
            q_value = self.q_table[state_key].get(action_key, 0.0)
            
            if q_value > best_q_value:
                best_q_value = q_value
                best_action = action
        
        return best_action or random.choice(available_actions)
    
    def update_q_value(
        self,
        state: RLState,
        action: RLAction,
        reward: float,
        next_state: Optional[RLState],
    ):
        """Actualiza Q-value usando Q-Learning update rule."""
        state_key = self.get_state_key(state)
        action_key = self.get_action_key(action)
        
        # Inicializar Q-table si es necesario
        if state_key not in self.q_table:
            self.q_table[state_key] = {}
        if action_key not in self.q_table[state_key]:
            self.q_table[state_key][action_key] = 0.0
        
        # Calcular Q-value futuro
        if next_state:
            next_state_key = self.get_state_key(next_state)
            if next_state_key in self.q_table:
                max_next_q = max(self.q_table[next_state_key].values()) if self.q_table[next_state_key] else 0.0
            else:
                max_next_q = 0.0
        else:
            max_next_q = 0.0
        
        # Q-Learning update: Q(s,a) = Q(s,a) + α[r + γ*max(Q(s',a')) - Q(s,a)]
        current_q = self.q_table[state_key][action_key]
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_next_q - current_q)
        self.q_table[state_key][action_key] = new_q
        
        # Decay epsilon
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)
    
    def add_experience(
        self,
        state: RLState,
        action: RLAction,
        reward: float,
        next_state: Optional[RLState],
        done: bool,
    ):
        """Agrega experiencia al buffer para experience replay."""
        experience = RLExperience(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done,
        )
        
        self.experience_buffer.append(experience)
        
        # Limitar tamaño del buffer
        if len(self.experience_buffer) > self.max_buffer_size:
            self.experience_buffer.pop(0)
    
    def replay_experiences(self, batch_size: int = 32):
        """Replay de experiencias pasadas para aprendizaje estable."""
        if len(self.experience_buffer) < batch_size:
            return
        
        # Sample aleatorio de experiencias
        batch = random.sample(self.experience_buffer, batch_size)
        
        for exp in batch:
            self.update_q_value(
                state=exp.state,
                action=exp.action,
                reward=exp.reward,
                next_state=exp.next_state,
            )


class PolicyGradientAgent:
    """Agente Policy Gradient para optimización de políticas."""
    
    def __init__(
        self,
        agent_id: str,
        learning_rate: float = 0.01,
    ):
        self.agent_id = agent_id
        self.learning_rate = learning_rate
        
        # Policy: state -> action -> probability
        self.policy: Dict[str, Dict[str, float]] = {}
        
        # Episode buffer
        self.episode_buffer: List[Tuple[RLState, RLAction, float]] = []
    
    def get_state_key(self, state: RLState) -> str:
        """Convierte estado a clave."""
        features = state.state_features
        key_parts = [
            str(features.get("workflow_step", "")),
            str(features.get("agent_status", "")),
        ]
        return "|".join(key_parts)
    
    def get_action_key(self, action: RLAction) -> str:
        """Convierte acción a clave."""
        return f"{action.action_type}:{action.action_id}"
    
    def get_action_probability(
        self,
        state: RLState,
        action: RLAction,
        available_actions: List[RLAction],
    ) -> float:
        """Obtiene probabilidad de una acción según la política."""
        state_key = self.get_state_key(state)
        action_key = self.get_action_key(action)
        
        if state_key not in self.policy:
            # Estado nuevo: distribución uniforme
            return 1.0 / len(available_actions) if available_actions else 0.0
        
        if action_key not in self.policy[state_key]:
            return 1.0 / len(available_actions) if available_actions else 0.0
        
        # Normalizar probabilidades
        total_prob = sum(self.policy[state_key].values())
        if total_prob == 0:
            return 1.0 / len(available_actions) if available_actions else 0.0
        
        return self.policy[state_key][action_key] / total_prob
    
    def select_action(
        self,
        state: RLState,
        available_actions: List[RLAction],
    ) -> RLAction:
        """Selecciona acción según política (stochastic)."""
        if not available_actions:
            raise ValueError("No hay acciones disponibles")
        
        # Calcular probabilidades
        probs = [
            self.get_action_probability(state, action, available_actions)
            for action in available_actions
        ]
        
        # Normalizar
        total_prob = sum(probs)
        if total_prob == 0:
            return random.choice(available_actions)
        
        probs = [p / total_prob for p in probs]
        
        # Sample según distribución
        return random.choices(available_actions, weights=probs)[0]
    
    def update_policy(
        self,
        episode_rewards: List[float],
    ):
        """Actualiza política usando Policy Gradient."""
        if not self.episode_buffer:
            return
        
        # Calcular returns (recompensas acumuladas)
        returns = []
        cumulative_reward = 0.0
        for reward in reversed(episode_rewards):
            cumulative_reward = reward + cumulative_reward * 0.9  # Discount
            returns.insert(0, cumulative_reward)
        
        # Normalizar returns
        if returns:
            mean_return = sum(returns) / len(returns)
            std_return = math.sqrt(sum((r - mean_return) ** 2 for r in returns) / len(returns))
            if std_return > 0:
                returns = [(r - mean_return) / std_return for r in returns]
        
        # Actualizar política
        for (state, action, _), return_value in zip(self.episode_buffer, returns):
            state_key = self.get_state_key(state)
            action_key = self.get_action_key(action)
            
            if state_key not in self.policy:
                self.policy[state_key] = {}
            
            if action_key not in self.policy[state_key]:
                self.policy[state_key][action_key] = 0.0
            
            # Policy gradient update (simplificado)
            current_prob = self.policy[state_key][action_key]
            self.policy[state_key][action_key] = current_prob + self.learning_rate * return_value
        
        # Limpiar buffer
        self.episode_buffer = []
    
    def add_to_episode(
        self,
        state: RLState,
        action: RLAction,
        reward: float,
    ):
        """Agrega experiencia al episodio actual."""
        self.episode_buffer.append((state, action, reward))


class AdvancedRLManager:
    """Manager para RL avanzado en agentic workflows."""
    
    def __init__(self, config: Any):
        self.config = config
        self.rl_dir = config.cache_dir / "agentic_rl"
        self.rl_dir.mkdir(parents=True, exist_ok=True)
        
        # Agentes RL por agent_id
        self.q_learning_agents: Dict[str, QLearningAgent] = {}
        self.policy_gradient_agents: Dict[str, PolicyGradientAgent] = {}
    
    def get_q_learning_agent(self, agent_id: str) -> QLearningAgent:
        """Obtiene o crea un agente Q-Learning."""
        if agent_id not in self.q_learning_agents:
            self.q_learning_agents[agent_id] = QLearningAgent(agent_id=agent_id)
        return self.q_learning_agents[agent_id]
    
    def get_policy_gradient_agent(self, agent_id: str) -> PolicyGradientAgent:
        """Obtiene o crea un agente Policy Gradient."""
        if agent_id not in self.policy_gradient_agents:
            self.policy_gradient_agents[agent_id] = PolicyGradientAgent(agent_id=agent_id)
        return self.policy_gradient_agents[agent_id]
    
    def select_optimal_action(
        self,
        agent_id: str,
        state: RLState,
        available_actions: List[RLAction],
        algorithm: str = "q_learning",
    ) -> RLAction:
        """Selecciona acción óptima usando RL."""
        if algorithm == "q_learning":
            agent = self.get_q_learning_agent(agent_id)
            return agent.select_action(state, available_actions)
        elif algorithm == "policy_gradient":
            agent = self.get_policy_gradient_agent(agent_id)
            return agent.select_action(state, available_actions)
        else:
            # Fallback: acción aleatoria
            return random.choice(available_actions) if available_actions else None
    
    def update_from_reward(
        self,
        agent_id: str,
        state: RLState,
        action: RLAction,
        reward: float,
        next_state: Optional[RLState],
        algorithm: str = "q_learning",
    ):
        """Actualiza agente RL desde recompensa."""
        if algorithm == "q_learning":
            agent = self.get_q_learning_agent(agent_id)
            agent.update_q_value(state, action, reward, next_state)
            agent.add_experience(state, action, reward, next_state, done=False)
        elif algorithm == "policy_gradient":
            agent = self.get_policy_gradient_agent(agent_id)
            agent.add_to_episode(state, action, reward)

