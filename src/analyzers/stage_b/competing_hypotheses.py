"""
Competing Hypotheses Analyzer for Stage B.

Applies Analysis of Competing Hypotheses (ACH) methodology to Stage A results.
"""

from typing import Dict, Any, List, Optional
from src.analyzers.base_analyzer import BaseAnalyzer
import json
import re


class CompetingHypothesesAnalyzer(BaseAnalyzer):
    """
    Applies Analysis of Competing Hypotheses methodology to Stage A results.
    
    This analyzer:
    1. Generates plausible hypotheses from Stage A insights
    2. Creates an evidence matrix mapping evidence to hypotheses
    3. Identifies diagnostic evidence that differentiates hypotheses
    4. Ranks hypotheses by likelihood based on evidence
    """
    
    def __init__(self):
        """Initialize the Competing Hypotheses analyzer."""
        super().__init__(
            name="competing_hypotheses",
            stage="stage_b"  # Stage B processes context, not transcript
        )
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the ACH analysis response.
        
        Expected sections:
        - Hypotheses: List of plausible explanations
        - Evidence Matrix: Mapping of evidence to hypotheses
        - Diagnosticity: Most diagnostic evidence
        - Rankings: Hypotheses ranked by likelihood
        """
        result = {
            "hypotheses": [],
            "evidence_matrix": {},
            "diagnostic_evidence": [],
            "inconsistencies": [],
            "rankings": [],
            "interim_judgments": {}
        }
        
        # Extract hypotheses section
        hypotheses_match = re.search(
            r'(?:1\)|HYPOTHESES?)[:\s]*\n(.*?)(?=\n(?:2\)|EVIDENCE|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if hypotheses_match:
            hypothesis_lines = hypotheses_match.group(1).strip().split('\n')
            for line in hypothesis_lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Clean up hypothesis text
                    hypothesis = re.sub(r'^[-•*]\s*', '', line)
                    hypothesis = re.sub(r'^H\d+[:\s]*', '', hypothesis)
                    if hypothesis:
                        result["hypotheses"].append(hypothesis)
        
        # Extract evidence matrix
        matrix_match = re.search(
            r'(?:2\)|EVIDENCE MATRIX)[:\s]*\n(.*?)(?=\n(?:3\)|INCONSISTENCIES|DIAGNOSTICITY|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if matrix_match:
            matrix_text = matrix_match.group(1).strip()
            # Parse evidence relationships
            current_hypothesis = None
            for line in matrix_text.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                # Check if this is a hypothesis header
                if any(h in line for h in result["hypotheses"]):
                    for h in result["hypotheses"]:
                        if h in line:
                            current_hypothesis = h
                            result["evidence_matrix"][h] = {
                                "supporting": [],
                                "contradicting": [],
                                "ambiguous": []
                            }
                            break
                elif current_hypothesis:
                    # Categorize evidence
                    line_lower = line.lower()
                    if 'support' in line_lower or '+' in line:
                        result["evidence_matrix"][current_hypothesis]["supporting"].append(line)
                    elif 'contradict' in line_lower or '-' in line:
                        result["evidence_matrix"][current_hypothesis]["contradicting"].append(line)
                    elif 'ambiguous' in line_lower or '?' in line:
                        result["evidence_matrix"][current_hypothesis]["ambiguous"].append(line)
        
        # Extract diagnostic evidence and inconsistencies
        diagnostic_match = re.search(
            r'(?:3\)|INCONSISTENCIES|DIAGNOSTICITY)[:\s]*\n(.*?)(?=\n(?:4\)|INTERIM|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if diagnostic_match:
            diagnostic_text = diagnostic_match.group(1).strip()
            for line in diagnostic_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    if 'inconsisten' in line.lower() or 'gap' in line.lower():
                        result["inconsistencies"].append(clean_line)
                    else:
                        result["diagnostic_evidence"].append(clean_line)
        
        # Extract interim judgments
        judgments_match = re.search(
            r'(?:4\)|INTERIM JUDGMENTS?)[:\s]*\n(.*?)(?=\n(?:5\)|CONCLUSION|RANKING|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if judgments_match:
            judgments_text = judgments_match.group(1).strip()
            current_hypothesis = None
            for line in judgments_text.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                # Check if this line contains a hypothesis
                for h in result["hypotheses"]:
                    if h in line:
                        # Extract judgment (Likely/Plausible/Unlikely)
                        if 'likely' in line.lower():
                            if 'unlikely' in line.lower():
                                judgment = "Unlikely"
                            else:
                                judgment = "Likely"
                        elif 'plausible' in line.lower():
                            judgment = "Plausible"
                        else:
                            judgment = "Unknown"
                        
                        result["interim_judgments"][h] = {
                            "judgment": judgment,
                            "rationale": line
                        }
                        break
        
        # Extract rankings
        rankings_match = re.search(
            r'(?:5\)|CONCLUSION|RANKING)[:\s]*\n(.*?)$',
            response, re.IGNORECASE | re.DOTALL
        )
        if rankings_match:
            rankings_text = rankings_match.group(1).strip()
            rank_number = 1
            for line in rankings_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Clean up ranking text
                    clean_line = re.sub(r'^[\d.)\s]+', '', line)
                    clean_line = re.sub(r'^[-•*]\s*', '', clean_line)
                    if clean_line:
                        # Try to match with existing hypotheses
                        matched = False
                        for h in result["hypotheses"]:
                            if h in clean_line or any(word in clean_line for word in h.split()[:3]):
                                result["rankings"].append({
                                    "rank": rank_number,
                                    "hypothesis": h,
                                    "explanation": clean_line
                                })
                                rank_number += 1
                                matched = True
                                break
                        if not matched and len(clean_line) > 10:
                            # Add as new ranking if substantial
                            result["rankings"].append({
                                "rank": rank_number,
                                "hypothesis": clean_line.split('.')[0] if '.' in clean_line else clean_line[:100],
                                "explanation": clean_line
                            })
                            rank_number += 1
        
        return result
