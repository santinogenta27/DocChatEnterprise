"""
MindFuse: Marketing Strategy Co-Creation with Explainable GenAI
Implements content pillar identification, persona mining, and narrative generation
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json
import os

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


@dataclass
class ContentPillar:
    """Represents a content pillar extracted from ads"""
    pillar_id: str
    name: str
    description: str
    customer_need: str
    product_category: str
    emotional_appeal: str
    style_tone: str
    frequency: int  # How often this pillar appears


@dataclass
class CustomerPersona:
    """Represents a customer persona discovered from ad data"""
    persona_id: str
    name: str
    description: str
    psychological_profile: str
    behavioral_patterns: List[str]
    content_preferences: List[str]
    ad_count: int


@dataclass
class CommunicationTheme:
    """Represents a communication theme/challenge"""
    theme_id: str
    name: str
    description: str
    pain_points: List[str]
    value_propositions: List[str]
    ad_count: int


@dataclass
class CampaignNarrative:
    """Generated campaign narrative combining persona and theme"""
    narrative_id: str
    persona: CustomerPersona
    theme: CommunicationTheme
    story: str
    campaign_insight: str
    content_brief: str
    suggested_offerings: List[str]


class MindFuseStrategyCoCreator:
    """
    MindFuse: Co-creates marketing strategies using GenAI
    with explainability and content-aware analysis
    """

    def __init__(self, config: Any, llm_model: str = "gpt-4o"):
        """
        Initialize MindFuse Strategy Co-Creator
        
        Args:
            config: AppConfig object
            llm_model: LLM model name
        """
        self.config = config
        self.llm_model = llm_model
        
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is required for MindFuseStrategyCoCreator")
        
        openai_api_key = os.getenv("OPENAI_API_KEY") or getattr(config, "openai_api_key", None)
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        
        self.llm = ChatOpenAI(
            model_name=llm_model,
            temperature=0.7,
            api_key=openai_api_key
        )
        
        self.content_pillars: Dict[str, ContentPillar] = {}
        self.personas: Dict[str, CustomerPersona] = {}
        self.themes: Dict[str, CommunicationTheme] = {}

    def extract_content_pillars(
        self,
        ad_corpus: List[Dict[str, Any]]
    ) -> List[ContentPillar]:
        """
        Extract content pillars from ad corpus
        
        Args:
            ad_corpus: List of ad data with images, text, metadata
        
        Returns:
            List of ContentPillar objects
        """
        prompt = """Analyze the following advertising content and extract structured content pillars.
For each ad, identify:
1. Customer need targeted
2. Product category
3. Emotional appeal
4. Style/tone
5. Key messaging themes

Return structured JSON with content pillars."""

        # Process ads in batches
        all_pillars = []
        
        for ad in ad_corpus[:100]:  # Limit for efficiency
            ad_text = ad.get("text", "")
            ad_metadata = ad.get("metadata", {})
            
            messages = [
                SystemMessage(content="You are an expert marketing strategist. Extract structured insights from advertising content."),
                HumanMessage(content=f"{prompt}\n\nAd Text: {ad_text}\nMetadata: {json.dumps(ad_metadata)}")
            ]
            
            try:
                response = self.llm.invoke(messages)
                # Parse response to extract pillars
                # In production, use structured output parsing
                pillar_data = self._parse_pillar_response(response.content)
                all_pillars.extend(pillar_data)
            except Exception as e:
                print(f"Error processing ad: {e}")
                continue
        
        # Aggregate and deduplicate pillars
        aggregated_pillars = self._aggregate_pillars(all_pillars)
        
        return aggregated_pillars

    def _parse_pillar_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse LLM response to extract content pillars"""
        # Simplified parsing - in production use structured output
        pillars = []
        # Extract structured data from response
        # This is a placeholder - implement proper JSON parsing
        return pillars

    def _aggregate_pillars(self, raw_pillars: List[Dict[str, Any]]) -> List[ContentPillar]:
        """Aggregate and deduplicate content pillars"""
        pillar_map = {}
        
        for pillar_data in raw_pillars:
            key = f"{pillar_data.get('customer_need', '')}_{pillar_data.get('product_category', '')}"
            if key not in pillar_map:
                pillar_map[key] = {
                    "frequency": 0,
                    "data": pillar_data
                }
            pillar_map[key]["frequency"] += 1
        
        aggregated = []
        for i, (key, value) in enumerate(pillar_map.items()):
            data = value["data"]
            pillar = ContentPillar(
                pillar_id=f"pillar_{i}",
                name=data.get("name", f"Pillar {i}"),
                description=data.get("description", ""),
                customer_need=data.get("customer_need", ""),
                product_category=data.get("product_category", ""),
                emotional_appeal=data.get("emotional_appeal", ""),
                style_tone=data.get("style_tone", ""),
                frequency=value["frequency"]
            )
            aggregated.append(pillar)
        
        return aggregated

    def mine_personas(
        self,
        ad_corpus: List[Dict[str, Any]],
        audience_pillar: str = "Audience"
    ) -> List[CustomerPersona]:
        """
        Mine customer personas from ad corpus using clustering
        
        Args:
            ad_corpus: List of ad data
            audience_pillar: Pillar name to use for persona extraction
        
        Returns:
            List of CustomerPersona objects
        """
        # Extract audience information from ads
        audience_data = []
        for ad in ad_corpus:
            if audience_pillar in ad.get("pillars", {}):
                audience_data.append(ad["pillars"][audience_pillar])
        
        # Use LLM to cluster and summarize personas
        prompt = f"""Analyze the following audience data from advertisements and identify distinct customer personas.
For each persona, provide:
1. Name
2. Psychological profile
3. Behavioral patterns
4. Content preferences

Audience Data: {json.dumps(audience_data[:50])}"""
        
        messages = [
            SystemMessage(content="You are an expert in customer segmentation and persona development."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        personas = self._parse_personas_response(response.content)
        
        return personas

    def _parse_personas_response(self, response_text: str) -> List[CustomerPersona]:
        """Parse LLM response to extract personas"""
        # Simplified - implement proper parsing
        personas = []
        # Extract persona data from response
        return personas

    def mine_themes(
        self,
        ad_corpus: List[Dict[str, Any]],
        insights_pillar: str = "Insights"
    ) -> List[CommunicationTheme]:
        """
        Mine communication themes/challenges from ad corpus
        
        Args:
            ad_corpus: List of ad data
            insights_pillar: Pillar name to use for theme extraction
        
        Returns:
            List of CommunicationTheme objects
        """
        # Extract insights from ads
        insights_data = []
        for ad in ad_corpus:
            if insights_pillar in ad.get("pillars", {}):
                insights_data.append(ad["pillars"][insights_pillar])
        
        prompt = f"""Analyze the following insights from advertisements and identify recurring communication themes.
For each theme, provide:
1. Theme name
2. Description
3. Pain points addressed
4. Value propositions

Insights Data: {json.dumps(insights_data[:50])}"""
        
        messages = [
            SystemMessage(content="You are an expert in marketing communication and strategic messaging."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        themes = self._parse_themes_response(response.content)
        
        return themes

    def _parse_themes_response(self, response_text: str) -> List[CommunicationTheme]:
        """Parse LLM response to extract themes"""
        # Simplified - implement proper parsing
        themes = []
        return themes

    def generate_campaign_narrative(
        self,
        persona: CustomerPersona,
        theme: CommunicationTheme,
        product_info: Dict[str, Any]
    ) -> CampaignNarrative:
        """
        Generate a campaign narrative combining persona and theme
        
        Args:
            persona: CustomerPersona to target
            theme: CommunicationTheme to address
            product_info: Product/service information
        
        Returns:
            CampaignNarrative object
        """
        prompt = f"""Create a compelling campaign narrative that combines:
- Target Persona: {persona.name} - {persona.description}
- Communication Theme: {theme.name} - {theme.description}
- Product/Service: {json.dumps(product_info)}

Generate:
1. A story/narrative (like "Samuel Tan" example)
2. Campaign insight
3. Content brief
4. Suggested offerings"""
        
        messages = [
            SystemMessage(content="You are a creative marketing strategist. Create compelling campaign narratives that connect personas with themes."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        narrative_data = self._parse_narrative_response(response.content)
        
        return CampaignNarrative(
            narrative_id=f"narrative_{len(self.personas)}_{len(self.themes)}",
            persona=persona,
            theme=theme,
            story=narrative_data.get("story", ""),
            campaign_insight=narrative_data.get("insight", ""),
            content_brief=narrative_data.get("brief", ""),
            suggested_offerings=narrative_data.get("offerings", [])
        )

    def _parse_narrative_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response to extract narrative components"""
        # Simplified parsing
        return {
            "story": response_text,
            "insight": "",
            "brief": "",
            "offerings": []
        }

    def analyze_campaign_performance(
        self,
        campaign_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze campaign performance using GenAI as performance marketer
        
        Interprets metrics and provides strategic recommendations
        """
        prompt = f"""Analyze the following campaign performance metrics and provide strategic insights:
- Reach: {campaign_metrics.get('reach', 0)}
- Frequency: {campaign_metrics.get('frequency', 0)}
- Results (Conversions): {campaign_metrics.get('results', 0)}
- Cost per Result (CPR): {campaign_metrics.get('cpr', 0)}
- Spend: {campaign_metrics.get('spend', 0)}
- CPM: {campaign_metrics.get('cpm', 0)}
- CTR: {campaign_metrics.get('ctr', 0)}
- CR (Click-to-Result): {campaign_metrics.get('cr', 0)}

Provide:
1. Performance assessment
2. Key insights
3. Recommended actions
4. Optimization suggestions"""
        
        messages = [
            SystemMessage(content="You are a senior performance marketing lead. Analyze campaign data and provide decisive, insight-driven guidance."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        
        return {
            "analysis": response.content,
            "recommendations": self._extract_recommendations(response.content)
        }

    def _extract_recommendations(self, analysis_text: str) -> List[str]:
        """Extract actionable recommendations from analysis"""
        # Simplified extraction
        recommendations = []
        # Parse recommendations from text
        return recommendations

