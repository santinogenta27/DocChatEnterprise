"""
Validador de Compliance Avanzado para Anuncios
Valida contra políticas de Meta, detecta claims prohibidos, y asegura brand safety
Basado en las mejores prácticas de compliance publicitario
"""

from __future__ import annotations

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class ComplianceLevel(str, Enum):
    """Niveles de compliance"""
    SAFE = "safe"
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"


@dataclass
class ComplianceIssue:
    """Issue de compliance detectado"""
    level: ComplianceLevel
    category: str  # e.g., "false_claim", "prohibited_content", "targeting"
    description: str
    suggestion: Optional[str] = None
    policy_reference: Optional[str] = None


class ComplianceValidator:
    """
    Validador avanzado de compliance para anuncios
    Usa LLM + reglas para validar contra políticas de Meta
    """
    
    # Claims prohibidos comunes
    PROHIBITED_CLAIMS = [
        r"\b(100%|guaranteed|guarantee|promise)\s+(cure|heal|fix|solve)\b",
        r"\b(make\s+\$\d+|\$\d+\s+per\s+day|get\s+rich\s+quick)\b",
        r"\b(no\s+risk|risk-free|money\s+back\s+guarantee)\b",
        r"\b(lose\s+\d+\s+lbs?\s+in\s+\d+\s+days?)\b",
        r"\b(doctor\s+recommended|clinically\s+proven)\b",
    ]
    
    # Palabras prohibidas por categoría
    PROHIBITED_WORDS = {
        "health": ["cure", "heal", "treat", "diagnose", "prescription"],
        "financial": ["guaranteed returns", "risk-free", "get rich"],
        "political": ["vote for", "support", "oppose"],
    }
    
    def __init__(self, config: Any):
        self.config = config
        self.llm = None
        
        if LLM_AVAILABLE and hasattr(config, 'openai_api_key') and config.openai_api_key:
            self.llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0,
                api_key=config.openai_api_key
            )
    
    async def validate_ad(
        self,
        headline: str,
        description: str,
        image_url: Optional[str] = None,
        target_audience: Optional[Dict[str, Any]] = None,
        industry: str = "general"
    ) -> Tuple[bool, List[ComplianceIssue]]:
        """
        Valida un anuncio completo contra políticas de compliance
        Retorna (is_compliant, list_of_issues)
        """
        issues: List[ComplianceIssue] = []
        
        # 1. Validación de claims falsos
        claim_issues = self._validate_false_claims(headline, description)
        issues.extend(claim_issues)
        
        # 2. Validación de contenido prohibido
        content_issues = self._validate_prohibited_content(headline, description, industry)
        issues.extend(content_issues)
        
        # 3. Validación de targeting
        if target_audience:
            targeting_issues = self._validate_targeting(target_audience, industry)
            issues.extend(targeting_issues)
        
        # 4. Validación con LLM (más avanzada)
        if self.llm:
            llm_issues = await self._validate_with_llm(headline, description, industry)
            issues.extend(llm_issues)
        
        # Determinar si es compliant
        critical_violations = [i for i in issues if i.level == ComplianceLevel.CRITICAL]
        violations = [i for i in issues if i.level == ComplianceLevel.VIOLATION]
        
        is_compliant = len(critical_violations) == 0 and len(violations) == 0
        
        return is_compliant, issues
    
    def _validate_false_claims(self, headline: str, description: str) -> List[ComplianceIssue]:
        """Valida claims falsos o exagerados"""
        issues = []
        text = f"{headline} {description}".lower()
        
        for pattern in self.PROHIBITED_CLAIMS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                issues.append(ComplianceIssue(
                    level=ComplianceLevel.VIOLATION,
                    category="false_claim",
                    description=f"Claim prohibido detectado: {matches[0]}",
                    suggestion="Elimina o modifica el claim para cumplir con políticas de Meta",
                    policy_reference="Meta Advertising Policies - Prohibited Content"
                ))
        
        return issues
    
    def _validate_prohibited_content(self, headline: str, description: str, industry: str) -> List[ComplianceIssue]:
        """Valida contenido prohibido por industria"""
        issues = []
        text = f"{headline} {description}".lower()
        
        # Verificar palabras prohibidas por industria
        if industry in self.PROHIBITED_WORDS:
            for word in self.PROHIBITED_WORDS[industry]:
                if word.lower() in text:
                    issues.append(ComplianceIssue(
                        level=ComplianceLevel.WARNING,
                        category="prohibited_content",
                        description=f"Palabra/expresión potencialmente problemática: {word}",
                        suggestion=f"Revisa si '{word}' cumple con políticas de {industry}",
                        policy_reference=f"Meta Policies - {industry.title()} Advertising"
                    ))
        
        return issues
    
    def _validate_targeting(self, target_audience: Dict[str, Any], industry: str) -> List[ComplianceIssue]:
        """Valida targeting por compliance (ej: no discriminar)"""
        issues = []
        
        # Verificar discriminación en targeting
        if "age" in target_audience:
            min_age = target_audience.get("age", {}).get("min", 18)
            if min_age < 18 and industry in ["alcohol", "gambling", "tobacco"]:
                issues.append(ComplianceIssue(
                    level=ComplianceLevel.CRITICAL,
                    category="targeting",
                    description="Targeting a menores de edad para industria restringida",
                    suggestion="Ajusta el targeting para cumplir con restricciones de edad",
                    policy_reference="Meta Advertising Policies - Age Restrictions"
                ))
        
        # Verificar exclusiones discriminatorias
        if "excluded_interests" in target_audience:
            excluded = target_audience["excluded_interests"]
            if any("race" in str(e).lower() or "ethnicity" in str(e).lower() for e in excluded):
                issues.append(ComplianceIssue(
                    level=ComplianceLevel.CRITICAL,
                    category="targeting",
                    description="Exclusión discriminatoria detectada",
                    suggestion="Elimina exclusiones basadas en raza, etnia, o características protegidas",
                    policy_reference="Meta Advertising Policies - Discriminatory Practices"
                ))
        
        return issues
    
    async def _validate_with_llm(
        self,
        headline: str,
        description: str,
        industry: str
    ) -> List[ComplianceIssue]:
        """Validación avanzada usando LLM"""
        if not self.llm:
            return []
        
        issues = []
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un experto en compliance publicitario de Meta Ads.
Analiza el siguiente anuncio y detecta cualquier violación de políticas.

Categorías a verificar:
1. Claims falsos o exagerados
2. Contenido prohibido
3. Lenguaje engañoso
4. Violaciones de privacidad
5. Contenido ofensivo o discriminatorio

Responde en JSON con este formato:
{
    "issues": [
        {
            "level": "safe|warning|violation|critical",
            "category": "tipo de issue",
            "description": "descripción detallada",
            "suggestion": "cómo corregirlo",
            "policy_reference": "referencia a política"
        }
    ]
}"""),
            ("user", f"""Anuncio a validar:
Industria: {industry}
Headline: {headline}
Description: {description}

Analiza este anuncio y retorna solo el JSON con los issues encontrados.""")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({})
            
            # Parsear respuesta JSON
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            
            for issue_data in result.get("issues", []):
                issues.append(ComplianceIssue(
                    level=ComplianceLevel(issue_data.get("level", "warning")),
                    category=issue_data.get("category", "unknown"),
                    description=issue_data.get("description", ""),
                    suggestion=issue_data.get("suggestion"),
                    policy_reference=issue_data.get("policy_reference")
                ))
        except Exception as e:
            print(f"⚠️ Error en validación LLM: {e}")
        
        return issues
    
    def get_compliance_score(self, issues: List[ComplianceIssue]) -> float:
        """Calcula un score de compliance (0-100)"""
        if not issues:
            return 100.0
        
        weights = {
            ComplianceLevel.SAFE: 0,
            ComplianceLevel.WARNING: -5,
            ComplianceLevel.VIOLATION: -20,
            ComplianceLevel.CRITICAL: -50
        }
        
        score = 100.0
        for issue in issues:
            score += weights.get(issue.level, 0)
        
        return max(0.0, min(100.0, score))
