"""
AI-Integrated Decision Support System for Market Forecasting
Combines GNN and Temporal Transformer for content diffusion and ROI forecasting
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class MarketMetrics:
    """Market performance metrics"""
    timestamp: datetime
    reach: int
    frequency: float
    results: int  # Conversions
    cpr: float  # Cost per Result
    spend: float
    cpm: float  # Cost per 1000 impressions
    ctr: float  # Click-through rate
    cr: float  # Conversion rate


@dataclass
class ContentDiffusionNode:
    """Node in content diffusion graph"""
    node_id: str
    node_type: str  # "user", "content", "brand", "platform"
    features: np.ndarray
    timestamp: datetime


@dataclass
class ForecastingResult:
    """Market forecasting result"""
    forecasted_metrics: Dict[str, List[float]]  # metric -> future values
    confidence_intervals: Dict[str, Tuple[List[float], List[float]]]  # metric -> (lower, upper)
    recommendations: List[str]
    causal_effects: Dict[str, float]  # intervention -> effect size


class GraphNeuralNetwork(nn.Module):
    """
    GNN for modeling content diffusion structure
    """
    
    def __init__(self, input_dim: int, hidden_dim: int = 128, num_layers: int = 2):
        super().__init__()
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required")
        
        self.layers = nn.ModuleList()
        self.layers.append(nn.Linear(input_dim, hidden_dim))
        
        for _ in range(num_layers - 1):
            self.layers.append(nn.Linear(hidden_dim, hidden_dim))
        
        self.attention = nn.MultiheadAttention(hidden_dim, num_heads=8, batch_first=True)
        self.output_dim = hidden_dim

    def forward(
        self,
        node_features: torch.Tensor,
        adjacency_matrix: torch.Tensor
    ) -> torch.Tensor:
        """
        Forward pass through GNN
        
        Args:
            node_features: Node features [num_nodes, input_dim]
            adjacency_matrix: Adjacency matrix [num_nodes, num_nodes]
        
        Returns:
            Graph embedding [num_nodes, hidden_dim]
        """
        x = node_features
        
        # Message passing layers
        for layer in self.layers:
            x = layer(x)
            x = torch.relu(x)
        
        # Attention-based aggregation
        x, _ = self.attention(x, x, x)
        
        # Global graph readout (mean pooling)
        graph_embedding = torch.mean(x, dim=0, keepdim=True)
        
        return graph_embedding


class TemporalTransformer(nn.Module):
    """
    Temporal Transformer for sequential market forecasting
    """
    
    def __init__(self, input_dim: int, d_model: int = 128, nhead: int = 8, num_layers: int = 4):
        super().__init__()
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required")
        
        self.input_projection = nn.Linear(input_dim, d_model)
        self.pos_encoder = PositionalEncoding(d_model)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=0.1,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        self.output_projection = nn.Linear(d_model, input_dim)

    def forward(self, sequence: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through Temporal Transformer
        
        Args:
            sequence: Input sequence [batch_size, seq_len, input_dim]
        
        Returns:
            Encoded sequence [batch_size, seq_len, input_dim]
        """
        x = self.input_projection(sequence)
        x = self.pos_encoder(x)
        x = self.transformer(x)
        x = self.output_projection(x)
        
        return x


class PositionalEncoding(nn.Module):
    """Positional encoding for temporal sequences"""
    
    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, :x.size(1), :]
        return x


class MarketForecastingDSS:
    """
    AI-Integrated Decision Support System for Market Forecasting
    Combines GNN and Temporal Transformer for content diffusion and ROI forecasting
    """

    def __init__(self, config: Any):
        """
        Initialize Market Forecasting DSS
        
        Args:
            config: AppConfig object
        """
        self.config = config
        
        if TORCH_AVAILABLE:
            # Initialize models
            graph_input_dim = 64  # Node feature dimension
            temporal_input_dim = 32  # Temporal feature dimension
            
            self.gnn = GraphNeuralNetwork(
                input_dim=graph_input_dim,
                hidden_dim=128,
                num_layers=2
            )
            
            self.temporal_transformer = TemporalTransformer(
                input_dim=temporal_input_dim,
                d_model=128,
                nhead=8,
                num_layers=4
            )
            
            # Forecasting head
            self.forecast_head = nn.Sequential(
                nn.Linear(128 + 128, 64),  # GNN + Transformer outputs
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(64, 9)  # 9 metrics: reach, frequency, results, cpr, spend, cpm, ctr, cr, roi
            )
        else:
            self.gnn = None
            self.temporal_transformer = None
            self.forecast_head = None

    def build_diffusion_graph(
        self,
        nodes: List[ContentDiffusionNode],
        interactions: List[Tuple[str, str, float]]  # (node1_id, node2_id, weight)
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Build graph structure from nodes and interactions
        
        Args:
            nodes: List of diffusion nodes
            interactions: List of edges with weights
        
        Returns:
            Tuple of (node_features, adjacency_matrix)
        """
        if not TORCH_AVAILABLE:
            return None, None
        
        num_nodes = len(nodes)
        node_features = torch.stack([torch.from_numpy(node.features) for node in nodes])
        
        # Build adjacency matrix
        adjacency = torch.zeros(num_nodes, num_nodes)
        node_id_to_idx = {node.node_id: i for i, node in enumerate(nodes)}
        
        for node1_id, node2_id, weight in interactions:
            if node1_id in node_id_to_idx and node2_id in node_id_to_idx:
                idx1 = node_id_to_idx[node1_id]
                idx2 = node_id_to_idx[node2_id]
                adjacency[idx1, idx2] = weight
                adjacency[idx2, idx1] = weight  # Undirected
        
        return node_features, adjacency

    def extract_temporal_features(
        self,
        metrics_history: List[MarketMetrics]
    ) -> torch.Tensor:
        """
        Extract temporal features from metrics history
        
        Args:
            metrics_history: List of historical metrics
        
        Returns:
            Temporal feature tensor [seq_len, feature_dim]
        """
        if not metrics_history:
            return torch.zeros(1, 9)  # 9 metrics
        
        features = []
        for metric in metrics_history:
            feature_vector = np.array([
                metric.reach / 1000.0,  # Normalize
                metric.frequency,
                metric.results / 100.0,
                metric.cpr,
                metric.spend / 1000.0,
                metric.cpm,
                metric.ctr,
                metric.cr,
                metric.results / metric.spend if metric.spend > 0 else 0  # ROI proxy
            ])
            features.append(feature_vector)
        
        return torch.from_numpy(np.array(features)).float()

    def forecast_market_growth(
        self,
        nodes: List[ContentDiffusionNode],
        interactions: List[Tuple[str, str, float]],
        metrics_history: List[MarketMetrics],
        forecast_horizon: int = 7  # days
    ) -> ForecastingResult:
        """
        Forecast market growth and content diffusion
        
        Args:
            nodes: Diffusion graph nodes
            interactions: Graph edges
            metrics_history: Historical metrics
            forecast_horizon: Number of days to forecast
        
        Returns:
            ForecastingResult object
        """
        if not TORCH_AVAILABLE or self.gnn is None:
            # Fallback: simple trend extrapolation
            return self._simple_forecast(metrics_history, forecast_horizon)
        
        # Build graph
        node_features, adjacency = self.build_diffusion_graph(nodes, interactions)
        
        # Extract graph embedding
        graph_embedding = self.gnn(node_features, adjacency)  # [1, hidden_dim]
        
        # Extract temporal features
        temporal_features = self.extract_temporal_features(metrics_history)  # [seq_len, feature_dim]
        
        # Process temporal sequence
        temporal_output = self.temporal_transformer(
            temporal_features.unsqueeze(0)  # Add batch dimension
        )  # [1, seq_len, feature_dim]
        
        # Use last timestep
        last_temporal = temporal_output[0, -1, :]  # [feature_dim]
        
        # Combine graph and temporal
        combined = torch.cat([graph_embedding.squeeze(0), last_temporal], dim=0)  # [hidden_dim + feature_dim]
        
        # Forecast
        forecast = self.forecast_head(combined.unsqueeze(0))  # [1, 9]
        
        # Generate forecasted metrics
        forecasted_metrics = {
            "reach": [forecast[0, 0].item() * 1000],
            "frequency": [forecast[0, 1].item()],
            "results": [forecast[0, 2].item() * 100],
            "cpr": [forecast[0, 3].item()],
            "spend": [forecast[0, 4].item() * 1000],
            "cpm": [forecast[0, 5].item()],
            "ctr": [forecast[0, 6].item()],
            "cr": [forecast[0, 7].item()],
            "roi": [forecast[0, 8].item()]
        }
        
        # Generate confidence intervals (simplified)
        confidence_intervals = {}
        for metric, values in forecasted_metrics.items():
            mean_val = values[0]
            std = mean_val * 0.1  # 10% uncertainty
            confidence_intervals[metric] = (
                [mean_val - 1.96 * std],
                [mean_val + 1.96 * std]
            )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(forecasted_metrics, metrics_history)
        
        # Causal effects (simplified)
        causal_effects = {
            "budget_increase": forecasted_metrics["results"][0] * 0.1,
            "targeting_refinement": forecasted_metrics["cpr"][0] * -0.05
        }
        
        return ForecastingResult(
            forecasted_metrics=forecasted_metrics,
            confidence_intervals=confidence_intervals,
            recommendations=recommendations,
            causal_effects=causal_effects
        )

    def _simple_forecast(
        self,
        metrics_history: List[MarketMetrics],
        forecast_horizon: int
    ) -> ForecastingResult:
        """Simple trend-based forecasting fallback"""
        if not metrics_history:
            return ForecastingResult(
                forecasted_metrics={},
                confidence_intervals={},
                recommendations=[],
                causal_effects={}
            )
        
        # Simple linear trend
        last_metric = metrics_history[-1]
        forecasted_metrics = {
            "reach": [last_metric.reach * 1.05],  # 5% growth
            "frequency": [last_metric.frequency],
            "results": [last_metric.results * 1.05],
            "cpr": [last_metric.cpr * 0.98],  # 2% improvement
            "spend": [last_metric.spend * 1.05],
            "cpm": [last_metric.cpm],
            "ctr": [last_metric.ctr],
            "cr": [last_metric.cr],
            "roi": [last_metric.results / last_metric.spend if last_metric.spend > 0 else 0]
        }
        
        confidence_intervals = {}
        for metric, values in forecasted_metrics.items():
            mean_val = values[0]
            confidence_intervals[metric] = ([mean_val * 0.9], [mean_val * 1.1])
        
        recommendations = ["Monitor CTR trends", "Optimize budget allocation"]
        causal_effects = {}
        
        return ForecastingResult(
            forecasted_metrics=forecasted_metrics,
            confidence_intervals=confidence_intervals,
            recommendations=recommendations,
            causal_effects=causal_effects
        )

    def _generate_recommendations(
        self,
        forecasted_metrics: Dict[str, List[float]],
        metrics_history: List[MarketMetrics]
    ) -> List[str]:
        """Generate strategic recommendations based on forecasts"""
        recommendations = []
        
        if forecasted_metrics.get("cpr", [0])[0] > 50:
            recommendations.append("High CPR detected - consider refining targeting")
        
        if forecasted_metrics.get("ctr", [0])[0] < 0.02:
            recommendations.append("Low CTR - optimize creative content")
        
        if forecasted_metrics.get("frequency", [0])[0] > 5:
            recommendations.append("High frequency - risk of ad fatigue, reduce exposure")
        
        if forecasted_metrics.get("roi", [0])[0] < 2.0:
            recommendations.append("Low ROI - review campaign strategy and budget allocation")
        
        return recommendations

    def estimate_causal_effect(
        self,
        intervention: str,
        intervention_value: float,
        baseline_metrics: MarketMetrics
    ) -> float:
        """
        Estimate causal effect of a marketing intervention
        
        Args:
            intervention: Type of intervention (e.g., "budget_increase", "targeting_refinement")
            intervention_value: Magnitude of intervention
            baseline_metrics: Baseline metrics before intervention
        
        Returns:
            Estimated effect size
        """
        # Simplified causal inference
        # In production, would use more sophisticated methods
        
        if intervention == "budget_increase":
            # Assume 10% budget increase leads to 8% more results
            effect = baseline_metrics.results * 0.08 * (intervention_value / 0.1)
            return effect
        
        elif intervention == "targeting_refinement":
            # Assume targeting refinement reduces CPR by 5%
            effect = -baseline_metrics.cpr * 0.05 * intervention_value
            return effect
        
        else:
            return 0.0

