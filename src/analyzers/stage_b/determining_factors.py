"""
Determining Factors Analyzer for Stage B.

Identifies causal relationships and critical factors from Stage A results.
"""

from typing import Dict, Any, List
from src.analyzers.base_analyzer import BaseAnalyzer
import re


class DeterminingFactorsAnalyzer(BaseAnalyzer):
    """
    Analyzes Stage A results to identify causal relationships and critical factors.
    
    This analyzer:
    1. Distinguishes causal factors from correlations
    2. Identifies critical decision points
    3. Maps dependencies and relationships
    4. Creates a hierarchy of influencing factors
    """
    
    def __init__(self):
        """Initialize the Determining Factors analyzer."""
        super().__init__(
            name="determining_factors",
            stage="stage_b"
        )
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the Determining Factors analysis response.
        
        Expected sections:
        - Causal Factors: Factors that directly cause outcomes
        - Correlations: Related but not necessarily causal
        - Critical Decisions: Key decision points identified
        - Factor Hierarchy: Ranking of factor importance
        """
        result = {
            "causal_factors": [],
            "correlations": [],
            "critical_decisions": [],
            "factor_hierarchy": {
                "primary_factors": [],
                "secondary_factors": [],
                "tertiary_factors": []
            },
            "dependencies": [],
            "constraints": [],
            "enablers": [],
            "risk_factors": []
        }
        
        # Extract causal factors
        causal_match = re.search(
            r'(?:CAUSAL FACTORS?|CAUSES?|DETERMINANTS?)[:\s]*\n(.*?)(?=\n(?:CORRELATIONS?|CRITICAL|DEPENDENCIES|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if causal_match:
            causal_text = causal_match.group(1).strip()
            for line in causal_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        # Try to extract factor and its effect
                        if '→' in clean_line or 'leads to' in clean_line.lower() or 'causes' in clean_line.lower():
                            result["causal_factors"].append({
                                "factor": clean_line.split('→')[0].strip() if '→' in clean_line else clean_line,
                                "relationship": "causal",
                                "description": clean_line
                            })
                        else:
                            result["causal_factors"].append({
                                "factor": clean_line,
                                "relationship": "causal",
                                "description": clean_line
                            })
        
        # Extract correlations
        correlations_match = re.search(
            r'(?:CORRELATIONS?|CORRELATED|ASSOCIATIONS?)[:\s]*\n(.*?)(?=\n(?:CRITICAL|DEPENDENCIES|CONSTRAINTS|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if correlations_match:
            correlations_text = correlations_match.group(1).strip()
            for line in correlations_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["correlations"].append({
                            "factor": clean_line,
                            "relationship": "correlation",
                            "strength": "moderate"  # Could be parsed from text
                        })
        
        # Extract critical decisions
        decisions_match = re.search(
            r'(?:CRITICAL DECISIONS?|KEY DECISIONS?|DECISION POINTS?)[:\s]*\n(.*?)(?=\n(?:FACTOR|DEPENDENCIES|HIERARCHY|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if decisions_match:
            decisions_text = decisions_match.group(1).strip()
            for line in decisions_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["critical_decisions"].append({
                            "decision": clean_line,
                            "impact": "high",  # Could be parsed
                            "timing": "immediate"  # Could be parsed
                        })
        
        # Extract factor hierarchy
        hierarchy_match = re.search(
            r'(?:FACTOR HIERARCHY|IMPORTANCE|RANKING|PRIMARY FACTORS?)[:\s]*\n(.*?)(?=\n(?:DEPENDENCIES|CONSTRAINTS|ENABLERS|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if hierarchy_match:
            hierarchy_text = hierarchy_match.group(1).strip()
            current_level = "primary"
            
            for line in hierarchy_text.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                # Check for level indicators
                line_lower = line.lower()
                if 'primary' in line_lower or 'first' in line_lower or 'most important' in line_lower:
                    current_level = "primary"
                elif 'secondary' in line_lower or 'second' in line_lower:
                    current_level = "secondary"
                elif 'tertiary' in line_lower or 'third' in line_lower:
                    current_level = "tertiary"
                else:
                    # Clean and add to current level
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        if current_level == "primary":
                            result["factor_hierarchy"]["primary_factors"].append(clean_line)
                        elif current_level == "secondary":
                            result["factor_hierarchy"]["secondary_factors"].append(clean_line)
                        else:
                            result["factor_hierarchy"]["tertiary_factors"].append(clean_line)
        
        # Extract dependencies
        dependencies_match = re.search(
            r'(?:DEPENDENCIES|DEPENDS ON|DEPENDENT)[:\s]*\n(.*?)(?=\n(?:CONSTRAINTS|ENABLERS|RISKS?|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if dependencies_match:
            dependencies_text = dependencies_match.group(1).strip()
            for line in dependencies_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["dependencies"].append(clean_line)
        
        # Extract constraints
        constraints_match = re.search(
            r'(?:CONSTRAINTS?|LIMITATIONS?|BARRIERS?)[:\s]*\n(.*?)(?=\n(?:ENABLERS|RISKS?|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if constraints_match:
            constraints_text = constraints_match.group(1).strip()
            for line in constraints_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["constraints"].append(clean_line)
        
        # Extract enablers
        enablers_match = re.search(
            r'(?:ENABLERS?|FACILITATORS?|ACCELERATORS?)[:\s]*\n(.*?)(?=\n(?:RISKS?|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if enablers_match:
            enablers_text = enablers_match.group(1).strip()
            for line in enablers_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["enablers"].append(clean_line)
        
        # Extract risk factors
        risks_match = re.search(
            r'(?:RISKS?|RISK FACTORS?|THREATS?)[:\s]*\n(.*?)$',
            response, re.IGNORECASE | re.DOTALL
        )
        if risks_match:
            risks_text = risks_match.group(1).strip()
            for line in risks_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["risk_factors"].append(clean_line)
        
        # If no primary factors were found but we have causal factors, use those
        if not result["factor_hierarchy"]["primary_factors"] and result["causal_factors"]:
            for factor in result["causal_factors"][:3]:  # Top 3 causal factors
                if isinstance(factor, dict):
                    result["factor_hierarchy"]["primary_factors"].append(factor.get("factor", str(factor)))
                else:
                    result["factor_hierarchy"]["primary_factors"].append(str(factor))
        
        return result
