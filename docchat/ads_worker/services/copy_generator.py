"""
Copy Generator Service
Generates multiple variations of ad copy using AI
"""
from typing import List, Dict, Any, Optional
import uuid

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI no disponible. Instala con: pip install openai")

from ..models.schemas import AssetAnalysis, CreativeGeneration


class CopyGenerator:
    """Generates multiple ad copy variations using AI"""
    
    def __init__(self, openai_api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.openai_client = None
        if OPENAI_AVAILABLE and openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)
        
        self.model = model
    
    def generate_copies(
        self,
        asset_analysis: AssetAnalysis,
        num_variations: int = 10,
        tone: Optional[str] = None,
        cta_style: Optional[str] = None,
        target_audience: Optional[str] = None,
        product_info: Optional[Dict[str, Any]] = None
    ) -> List[CreativeGeneration]:
        """
        Generate multiple ad copy variations
        
        Args:
            asset_analysis: Analysis results from AssetProcessor
            num_variations: Number of copy variations to generate
            tone: Desired tone (professional, casual, energetic, etc.)
            cta_style: Call-to-action style (direct, question, urgency, etc.)
            target_audience: Target audience description
            product_info: Additional product/service information
            
        Returns:
            List of CreativeGeneration objects with copy variations
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized. Provide openai_api_key.")
        
        # Build context from asset analysis
        context = self._build_context(asset_analysis, product_info)
        
        # Generate copies
        copies = []
        batch_size = min(5, num_variations)  # Generate in batches
        
        for batch_start in range(0, num_variations, batch_size):
            batch_end = min(batch_start + batch_size, num_variations)
            batch_copies = self._generate_batch(
                context,
                batch_end - batch_start,
                tone,
                cta_style,
                target_audience
            )
            copies.extend(batch_copies)
        
        return copies
    
    def _build_context(
        self,
        asset_analysis: AssetAnalysis,
        product_info: Optional[Dict[str, Any]]
    ) -> str:
        """Build context string from asset analysis"""
        context_parts = []
        
        # Asset type and labels
        context_parts.append(f"Asset Type: {asset_analysis.asset_type.value}")
        if asset_analysis.labels:
            context_parts.append(f"Labels: {', '.join(asset_analysis.labels)}")
        
        # Objects detected
        if asset_analysis.objects_detected:
            objects = [obj.get("name", "") for obj in asset_analysis.objects_detected]
            context_parts.append(f"Objects: {', '.join(objects)}")
        
        # Style and emotion
        if asset_analysis.style_tags:
            context_parts.append(f"Style: {', '.join(asset_analysis.style_tags)}")
        if asset_analysis.emotion_tags:
            context_parts.append(f"Emotion: {', '.join(asset_analysis.emotion_tags)}")
        
        # Keywords and topics
        if asset_analysis.keywords:
            context_parts.append(f"Keywords: {', '.join(asset_analysis.keywords)}")
        if asset_analysis.topics:
            context_parts.append(f"Topics: {', '.join(asset_analysis.topics)}")
        
        # Transcript (for videos)
        if asset_analysis.transcript:
            context_parts.append(f"Audio Transcript: {asset_analysis.transcript}")
        
        # Product info
        if product_info:
            for key, value in product_info.items():
                context_parts.append(f"{key}: {value}")
        
        return "\n".join(context_parts)
    
    def _generate_batch(
        self,
        context: str,
        count: int,
        tone: Optional[str],
        cta_style: Optional[str],
        target_audience: Optional[str]
    ) -> List[CreativeGeneration]:
        """Generate a batch of copy variations"""
        # Build prompt
        prompt = self._build_prompt(context, count, tone, cta_style, target_audience)
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert copywriter specializing in high-converting ad copy. 
Generate compelling, persuasive ad copy that drives action. Each variation should be unique and optimized for conversions."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.9,  # Higher temperature for more variation
                max_tokens=500
            )
            
            # Parse response
            content = response.choices[0].message.content
            copies = self._parse_copy_response(content, count)
            
            return copies
            
        except Exception as e:
            print(f"⚠️ Error generando copy: {e}")
            # Fallback: generate simple variations
            return self._generate_fallback_copies(context, count)
    
    def _build_prompt(
        self,
        context: str,
        count: int,
        tone: Optional[str],
        cta_style: Optional[str],
        target_audience: Optional[str]
    ) -> str:
        """Build the prompt for copy generation"""
        prompt_parts = [
            f"Generate {count} unique, high-converting ad copy variations based on this context:",
            "",
            context,
            "",
            "Requirements:",
            "- Each copy must include: headline (max 40 chars), description (max 125 chars), and CTA (max 20 chars)",
            "- Focus on benefits and value proposition",
            "- Use persuasive language that drives action",
            "- Each variation should have a different angle or approach",
        ]
        
        if tone:
            prompt_parts.append(f"- Tone: {tone}")
        
        if cta_style:
            prompt_parts.append(f"- CTA style: {cta_style}")
        
        if target_audience:
            prompt_parts.append(f"- Target audience: {target_audience}")
        
        prompt_parts.append("")
        prompt_parts.append("Return in JSON format:")
        prompt_parts.append('{"copies": [{"headline": "...", "description": "...", "cta": "...", "tone": "..."}, ...]}')
        
        return "\n".join(prompt_parts)
    
    def _parse_copy_response(self, content: str, expected_count: int) -> List[CreativeGeneration]:
        """Parse the AI response into CreativeGeneration objects"""
        import json
        import re
        
        copies = []
        
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                copy_list = data.get("copies", [])
                
                for copy_data in copy_list[:expected_count]:
                    creative = CreativeGeneration(
                        creative_id=str(uuid.uuid4()),
                        asset_id="",  # Will be set by caller
                        creative_type="copy",
                        headline=copy_data.get("headline", ""),
                        description=copy_data.get("description", ""),
                        cta=copy_data.get("cta", "Learn More"),
                        tone=copy_data.get("tone", "professional"),
                        generation_params={
                            "model": self.model,
                            "temperature": 0.9
                        }
                    )
                    copies.append(creative)
            except json.JSONDecodeError:
                # Fallback parsing
                copies = self._parse_text_response(content, expected_count)
        else:
            # Fallback parsing
            copies = self._parse_text_response(content, expected_count)
        
        return copies
    
    def _parse_text_response(self, content: str, expected_count: int) -> List[CreativeGeneration]:
        """Fallback: parse text response"""
        lines = content.split('\n')
        copies = []
        current_copy = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if 'headline' in line.lower() or 'title' in line.lower():
                headline = line.split(':', 1)[-1].strip()
                current_copy['headline'] = headline
            elif 'description' in line.lower() or 'body' in line.lower():
                description = line.split(':', 1)[-1].strip()
                current_copy['description'] = description
            elif 'cta' in line.lower() or 'call' in line.lower():
                cta = line.split(':', 1)[-1].strip()
                current_copy['cta'] = cta
                
                # Create creative when we have all parts
                if all(k in current_copy for k in ['headline', 'description', 'cta']):
                    creative = CreativeGeneration(
                        creative_id=str(uuid.uuid4()),
                        asset_id="",
                        creative_type="copy",
                        headline=current_copy['headline'],
                        description=current_copy['description'],
                        cta=current_copy['cta'],
                        tone="professional"
                    )
                    copies.append(creative)
                    current_copy = {}
                    
                    if len(copies) >= expected_count:
                        break
        
        return copies
    
    def _generate_fallback_copies(self, context: str, count: int) -> List[CreativeGeneration]:
        """Generate simple fallback copies if AI fails"""
        copies = []
        base_headlines = [
            "Discover Amazing Products",
            "Transform Your Experience",
            "Unlock New Possibilities",
            "Experience Excellence",
            "Join the Revolution"
        ]
        
        base_descriptions = [
            "Discover what makes us different and why thousands choose us every day.",
            "Experience quality and innovation like never before. Start your journey today.",
            "Join a community of satisfied customers who trust our products.",
            "Get the best value with our premium offerings designed for you.",
            "Don't miss out on this opportunity to elevate your experience."
        ]
        
        ctas = ["Shop Now", "Learn More", "Get Started", "Discover", "Try Now"]
        
        for i in range(count):
            headline = base_headlines[i % len(base_headlines)]
            description = base_descriptions[i % len(base_descriptions)]
            cta = ctas[i % len(ctas)]
            
            creative = CreativeGeneration(
                creative_id=str(uuid.uuid4()),
                asset_id="",
                creative_type="copy",
                headline=f"{headline} {i+1}",
                description=description,
                cta=cta,
                tone="professional"
            )
            copies.append(creative)
        
        return copies
