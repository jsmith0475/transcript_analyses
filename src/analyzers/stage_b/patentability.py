"""
Patentability Analyzer for Stage B.

Identifies potentially patentable innovations from Stage A results.
"""

from typing import Dict, Any, List
from src.analyzers.base_analyzer import BaseAnalyzer
import re


class PatentabilityAnalyzer(BaseAnalyzer):
    """
    Analyzes Stage A results to identify patentable innovations.
    
    This analyzer:
    1. Identifies novel concepts and innovations
    2. Assesses non-obviousness of ideas
    3. Evaluates practical applications
    4. Suggests patent claim structures
    """
    
    def __init__(self):
        """Initialize the Patentability analyzer."""
        super().__init__(
            name="patentability",
            stage="stage_b"
        )
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the Patentability analysis response.
        
        Expected sections:
        - Innovations: Novel concepts identified
        - Novelty Assessment: Evaluation of uniqueness
        - Prior Art Considerations: Existing related work
        - Patent Opportunities: Specific patentable ideas
        """
        result = {
            "innovations": [],
            "novelty_assessment": {},
            "prior_art_considerations": [],
            "patent_opportunities": [],
            "claims_structure": [],
            "technical_advantages": [],
            "commercial_applications": [],
            "implementation_details": []
        }
        
        # Extract innovations
        innovations_match = re.search(
            r'(?:INNOVATIONS?|NOVEL CONCEPTS?|NEW IDEAS?)[:\s]*\n(.*?)(?=\n(?:NOVELTY|PRIOR|PATENT|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if innovations_match:
            innovations_text = innovations_match.group(1).strip()
            for line in innovations_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["innovations"].append({
                            "concept": clean_line,
                            "category": "technical",  # Could be parsed
                            "potential": "high"  # Could be parsed
                        })
        
        # Extract novelty assessment
        novelty_match = re.search(
            r'(?:NOVELTY ASSESSMENT|UNIQUENESS|NON-?OBVIOUSNESS)[:\s]*\n(.*?)(?=\n(?:PRIOR|PATENT|CLAIMS|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if novelty_match:
            novelty_text = novelty_match.group(1).strip()
            current_innovation = None
            
            for line in novelty_text.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Check if this line references an innovation
                for innovation in result["innovations"]:
                    if isinstance(innovation, dict) and innovation["concept"] in line:
                        current_innovation = innovation["concept"]
                        result["novelty_assessment"][current_innovation] = {
                            "novelty_score": "high",  # Could be parsed
                            "non_obvious": True,  # Could be parsed
                            "assessment": line
                        }
                        break
                else:
                    # General novelty assessment
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    if clean_line and current_innovation:
                        if current_innovation not in result["novelty_assessment"]:
                            result["novelty_assessment"][current_innovation] = {
                                "novelty_score": "medium",
                                "non_obvious": True,
                                "assessment": clean_line
                            }
        
        # Extract prior art considerations
        prior_art_match = re.search(
            r'(?:PRIOR ART|EXISTING|RELATED WORK|BACKGROUND)[:\s]*\n(.*?)(?=\n(?:PATENT|CLAIMS|TECHNICAL|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if prior_art_match:
            prior_art_text = prior_art_match.group(1).strip()
            for line in prior_art_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["prior_art_considerations"].append(clean_line)
        
        # Extract patent opportunities
        opportunities_match = re.search(
            r'(?:PATENT OPPORTUNITIES?|PATENTABLE|IP POTENTIAL)[:\s]*\n(.*?)(?=\n(?:CLAIMS|TECHNICAL|COMMERCIAL|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if opportunities_match:
            opportunities_text = opportunities_match.group(1).strip()
            opportunity_num = 1
            for line in opportunities_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["patent_opportunities"].append({
                            "id": f"P{opportunity_num:03d}",
                            "title": clean_line[:100],  # First 100 chars as title
                            "description": clean_line,
                            "type": "utility",  # Could be parsed (utility, design, etc.)
                            "priority": "high"  # Could be parsed
                        })
                        opportunity_num += 1
        
        # Extract claims structure
        claims_match = re.search(
            r'(?:CLAIMS?|CLAIM STRUCTURE|PATENT CLAIMS?)[:\s]*\n(.*?)(?=\n(?:TECHNICAL|COMMERCIAL|IMPLEMENTATION|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if claims_match:
            claims_text = claims_match.group(1).strip()
            claim_num = 1
            for line in claims_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        # Determine claim type
                        if claim_num == 1 or 'independent' in line.lower():
                            claim_type = "independent"
                        else:
                            claim_type = "dependent"
                        
                        result["claims_structure"].append({
                            "claim_number": claim_num,
                            "type": claim_type,
                            "text": clean_line
                        })
                        claim_num += 1
        
        # Extract technical advantages
        advantages_match = re.search(
            r'(?:TECHNICAL ADVANTAGES?|BENEFITS?|IMPROVEMENTS?)[:\s]*\n(.*?)(?=\n(?:COMMERCIAL|IMPLEMENTATION|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if advantages_match:
            advantages_text = advantages_match.group(1).strip()
            for line in advantages_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["technical_advantages"].append(clean_line)
        
        # Extract commercial applications
        commercial_match = re.search(
            r'(?:COMMERCIAL APPLICATIONS?|MARKET|USE CASES?|APPLICATIONS?)[:\s]*\n(.*?)(?=\n(?:IMPLEMENTATION|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if commercial_match:
            commercial_text = commercial_match.group(1).strip()
            for line in commercial_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["commercial_applications"].append({
                            "application": clean_line,
                            "market_size": "medium",  # Could be parsed
                            "readiness": "prototype"  # Could be parsed
                        })
        
        # Extract implementation details
        implementation_match = re.search(
            r'(?:IMPLEMENTATION|TECHNICAL DETAILS?|HOW IT WORKS?)[:\s]*\n(.*?)$',
            response, re.IGNORECASE | re.DOTALL
        )
        if implementation_match:
            implementation_text = implementation_match.group(1).strip()
            for line in implementation_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    clean_line = re.sub(r'^[-•*]\s*', '', line)
                    clean_line = re.sub(r'^\d+[.)]\s*', '', clean_line)
                    if clean_line:
                        result["implementation_details"].append(clean_line)
        
        # If no patent opportunities were found but we have innovations, create them
        if not result["patent_opportunities"] and result["innovations"]:
            for idx, innovation in enumerate(result["innovations"][:3], 1):
                if isinstance(innovation, dict):
                    result["patent_opportunities"].append({
                        "id": f"P{idx:03d}",
                        "title": innovation["concept"][:100],
                        "description": innovation["concept"],
                        "type": "utility",
                        "priority": innovation.get("potential", "medium")
                    })
        
        return result
