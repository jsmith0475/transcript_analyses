"""
First Principles Analyzer for Stage B.

Breaks down complex insights from Stage A into fundamental truths.
"""

from typing import Dict, Any, List
from src.analyzers.base_analyzer import BaseAnalyzer
import re


class FirstPrinciplesAnalyzer(BaseAnalyzer):
    """
    Applies First Principles thinking to Stage A results.
    
    This analyzer:
    1. Identifies fundamental truths from Stage A insights
    2. Separates assumptions from facts
    3. Builds up from basic principles to complex conclusions
    4. Creates a hierarchy of derived insights
    """
    
    def __init__(self):
        """Initialize the First Principles analyzer."""
        super().__init__(
            name="first_principles",
            stage="stage_b"
        )
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the First Principles analysis response.
        
        Expected sections:
        - Fundamental Truths: Core facts that cannot be reduced further
        - Assumptions: Things taken as true but not proven
        - Derivations: Insights built from fundamental truths
        - First Principles Breakdown: Hierarchical structure
        """
        result = {
            "fundamental_truths": [],
            "assumptions": [],
            "derivations": [],
            "first_principles_breakdown": {
                "core_principles": [],
                "derived_insights": [],
                "logical_chain": []
            },
            "challenged_assumptions": [],
            "reconstructed_understanding": []
        }
        
        # Extract fundamental truths
        truths_match = re.search(
            r'(?:FUNDAMENTAL TRUTHS?|FIRST PRINCIPLES?|CORE FACTS?)[:\s]*\n(.*?)(?=\n(?:ASSUMPTIONS?|DERIVATIONS?|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if truths_match:
            truths_text = truths_match.group(1).strip()
            for line in truths_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Clean up the line
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["fundamental_truths"].append(clean_line)
                        # Also add to core principles
                        result["first_principles_breakdown"]["core_principles"].append(clean_line)
        
        # Extract assumptions
        assumptions_match = re.search(
            r'(?:ASSUMPTIONS?|ASSUMED|PRESUPPOSITIONS?)[:\s]*\n(.*?)(?=\n(?:DERIVATIONS?|CHALLENGED|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if assumptions_match:
            assumptions_text = assumptions_match.group(1).strip()
            for line in assumptions_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["assumptions"].append(clean_line)
        
        # Extract challenged assumptions
        challenged_match = re.search(
            r'(?:CHALLENGED|QUESTIONED|INVALID ASSUMPTIONS?)[:\s]*\n(.*?)(?=\n(?:DERIVATIONS?|RECONSTRUCTED|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if challenged_match:
            challenged_text = challenged_match.group(1).strip()
            for line in challenged_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["challenged_assumptions"].append(clean_line)
        
        # Extract derivations
        derivations_match = re.search(
            r'(?:DERIVATIONS?|DERIVED|BUILT FROM|CONCLUSIONS?)[:\s]*\n(.*?)(?=\n(?:BREAKDOWN|LOGICAL|RECONSTRUCTED|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if derivations_match:
            derivations_text = derivations_match.group(1).strip()
            for line in derivations_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["derivations"].append(clean_line)
                        # Also add to derived insights
                        result["first_principles_breakdown"]["derived_insights"].append(clean_line)
        
        # Extract logical chain
        chain_match = re.search(
            r'(?:LOGICAL CHAIN|REASONING CHAIN|LOGIC FLOW)[:\s]*\n(.*?)(?=\n(?:RECONSTRUCTED|UNDERSTANDING|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if chain_match:
            chain_text = chain_match.group(1).strip()
            step_number = 1
            for line in chain_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*→]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["first_principles_breakdown"]["logical_chain"].append({
                            "step": step_number,
                            "reasoning": clean_line
                        })
                        step_number += 1
        
        # Extract reconstructed understanding
        reconstructed_match = re.search(
            r'(?:RECONSTRUCTED|NEW UNDERSTANDING|REBUILT|SYNTHESIS)[:\s]*\n(.*?)$',
            response, re.IGNORECASE | re.DOTALL
        )
        if reconstructed_match:
            reconstructed_text = reconstructed_match.group(1).strip()
            for line in reconstructed_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["reconstructed_understanding"].append(clean_line)
        
        # If no logical chain was found but we have truths and derivations, create one
        if not result["first_principles_breakdown"]["logical_chain"] and \
           (result["fundamental_truths"] or result["derivations"]):
            step = 1
            for truth in result["fundamental_truths"][:3]:  # First few truths
                result["first_principles_breakdown"]["logical_chain"].append({
                    "step": step,
                    "reasoning": f"Foundation: {truth}"
                })
                step += 1
            for derivation in result["derivations"][:3]:  # First few derivations
                result["first_principles_breakdown"]["logical_chain"].append({
                    "step": step,
                    "reasoning": f"Therefore: {derivation}"
                })
                step += 1
        
        return result
