"""
Stage B Analyzers - Meta-analysis of Stage A results.

These analyzers process the combined outputs from Stage A to identify
patterns, relationships, and higher-level insights.
"""

from typing import List, Type
from src.analyzers.base_analyzer import BaseAnalyzer

# Import all Stage B analyzers
from .competing_hypotheses import CompetingHypothesesAnalyzer
from .first_principles import FirstPrinciplesAnalyzer
from .determining_factors import DeterminingFactorsAnalyzer
from .patentability import PatentabilityAnalyzer

__all__ = [
    "CompetingHypothesesAnalyzer",
    "FirstPrinciplesAnalyzer", 
    "DeterminingFactorsAnalyzer",
    "PatentabilityAnalyzer",
]

def get_stage_b_analyzers() -> List[Type[BaseAnalyzer]]:
    """Get all available Stage B analyzers."""
    return [
        CompetingHypothesesAnalyzer,
        FirstPrinciplesAnalyzer,
        DeterminingFactorsAnalyzer,
        PatentabilityAnalyzer,
    ]
