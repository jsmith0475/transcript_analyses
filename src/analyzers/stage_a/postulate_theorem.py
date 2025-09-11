"""
Postulate-Theorem Analyzer for Stage A transcript analysis.
Identifies hypotheses and their supporting evidence in conversations.
"""

from typing import Dict, Any, List
from src.analyzers.base_analyzer import BaseAnalyzer
import json
import re


class PostulateTheoremAnalyzer(BaseAnalyzer):
    """Analyzes postulates and theorems in conversations."""
    
    def __init__(self):
        super().__init__(
            name="postulate_theorem",
            stage="stage_a"
        )
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the postulate-theorem analysis response."""
        result = {
            "postulates": [],
            "theorems": [],
            "hypotheses": [],
            "evidence": [],
            "theoretical_frameworks": [],
            "proofs": []
        }
        
        # Extract postulates section
        postulates_match = re.search(
            r'(?:POSTULATES?|AXIOMS?|PRINCIPLES?)[:\s]*\n(.*?)(?=\n(?:THEOREMS?|HYPOTHES|EVIDENCE|FRAMEWORKS?|PROOFS?|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if postulates_match:
            postulate_lines = postulates_match.group(1).strip().split('\n')
            for line in postulate_lines:
                cleaned = line.strip().lstrip('- •*').strip()
                if cleaned and not cleaned.startswith('#'):
                    # Try to extract structured postulate info
                    if ':' in cleaned:
                        parts = cleaned.split(':', 1)
                        result["postulates"].append({
                            "label": parts[0].strip(),
                            "statement": parts[1].strip(),
                            "type": "fundamental"
                        })
                    else:
                        result["postulates"].append({
                            "statement": cleaned,
                            "type": "fundamental"
                        })
        
        # Extract theorems section
        theorems_match = re.search(
            r'(?:THEOREMS?|PROPOSITIONS?|CONCLUSIONS?)[:\s]*\n(.*?)(?=\n(?:HYPOTHES|EVIDENCE|FRAMEWORKS?|PROOFS?|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if theorems_match:
            theorem_lines = theorems_match.group(1).strip().split('\n')
            for line in theorem_lines:
                cleaned = line.strip().lstrip('- •*').strip()
                if cleaned and not cleaned.startswith('#'):
                    # Try to extract structured theorem info
                    if ':' in cleaned:
                        parts = cleaned.split(':', 1)
                        result["theorems"].append({
                            "label": parts[0].strip(),
                            "statement": parts[1].strip(),
                            "derived_from": []
                        })
                    else:
                        result["theorems"].append({
                            "statement": cleaned,
                            "derived_from": []
                        })
        
        # Extract hypotheses section
        hypotheses_match = re.search(
            r'(?:HYPOTHES[EI]S|CONJECTURES?|SUPPOSITIONS?)[:\s]*\n(.*?)(?=\n(?:EVIDENCE|FRAMEWORKS?|PROOFS?|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if hypotheses_match:
            hypothesis_lines = hypotheses_match.group(1).strip().split('\n')
            for line in hypothesis_lines:
                cleaned = line.strip().lstrip('- •*').strip()
                if cleaned and not cleaned.startswith('#'):
                    # Try to extract structured hypothesis info
                    if ':' in cleaned:
                        parts = cleaned.split(':', 1)
                        result["hypotheses"].append({
                            "label": parts[0].strip(),
                            "statement": parts[1].strip(),
                            "confidence": "medium"
                        })
                    else:
                        result["hypotheses"].append({
                            "statement": cleaned,
                            "confidence": "medium"
                        })
        
        # Extract evidence section
        evidence_match = re.search(
            r'(?:EVIDENCE|SUPPORT|DATA|FACTS?)[:\s]*\n(.*?)(?=\n(?:FRAMEWORKS?|PROOFS?|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if evidence_match:
            evidence_lines = evidence_match.group(1).strip().split('\n')
            for line in evidence_lines:
                cleaned = line.strip().lstrip('- •*').strip()
                if cleaned and not cleaned.startswith('#'):
                    # Try to extract structured evidence info
                    if '->' in cleaned or 'supports' in cleaned.lower():
                        parts = re.split(r'->|supports', cleaned, flags=re.IGNORECASE)
                        if len(parts) == 2:
                            result["evidence"].append({
                                "data": parts[0].strip(),
                                "supports": parts[1].strip()
                            })
                        else:
                            result["evidence"].append({
                                "data": cleaned
                            })
                    else:
                        result["evidence"].append({
                            "data": cleaned
                        })
        
        # Extract theoretical frameworks
        frameworks_match = re.search(
            r'(?:THEORETICAL FRAMEWORKS?|FRAMEWORKS?|MODELS?|THEORIES)[:\s]*\n(.*?)(?=\n(?:PROOFS?|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if frameworks_match:
            framework_lines = frameworks_match.group(1).strip().split('\n')
            for line in framework_lines:
                cleaned = line.strip().lstrip('- •*').strip()
                if cleaned and not cleaned.startswith('#'):
                    result["theoretical_frameworks"].append(cleaned)
        
        # Extract proofs/validations
        proofs_match = re.search(
            r'(?:PROOFS?|VALIDATIONS?|DEMONSTRATIONS?)[:\s]*\n(.*?)$',
            response, re.IGNORECASE | re.DOTALL
        )
        if proofs_match:
            proof_lines = proofs_match.group(1).strip().split('\n')
            current_proof = None
            for line in proof_lines:
                cleaned = line.strip()
                if cleaned and not cleaned.startswith('#'):
                    # Check if this is a new proof header
                    if re.match(r'^\d+\.|\w+\)', cleaned):
                        if current_proof:
                            result["proofs"].append(current_proof)
                        current_proof = {
                            "theorem": cleaned.lstrip('0123456789. ').strip(),
                            "steps": []
                        }
                    elif current_proof and cleaned.startswith(('- ', '• ', '* ')):
                        current_proof["steps"].append(cleaned.lstrip('- •*').strip())
                    elif not current_proof:
                        result["proofs"].append({
                            "statement": cleaned
                        })
            
            if current_proof:
                result["proofs"].append(current_proof)
        
        # Fallback: Extract from general content if no structured sections found
        if not any([result["postulates"], result["theorems"], result["hypotheses"]]):
            lines = response.strip().split('\n')
            current_section = None
            
            for line in lines:
                line_lower = line.lower().strip()
                
                # Detect section headers
                if any(word in line_lower for word in ['postulate', 'axiom', 'principle']):
                    current_section = 'postulates'
                elif any(word in line_lower for word in ['theorem', 'proposition', 'conclusion']):
                    current_section = 'theorems'
                elif any(word in line_lower for word in ['hypothesis', 'conjecture', 'supposition']):
                    current_section = 'hypotheses'
                elif any(word in line_lower for word in ['evidence', 'support', 'data']):
                    current_section = 'evidence'
                elif any(word in line_lower for word in ['framework', 'model', 'theory']):
                    current_section = 'theoretical_frameworks'
                elif any(word in line_lower for word in ['proof', 'validation', 'demonstration']):
                    current_section = 'proofs'
                elif current_section and line.strip():
                    cleaned = line.strip().lstrip('- •*').strip()
                    if cleaned and not cleaned.startswith('#'):
                        if current_section in ['postulates', 'theorems', 'hypotheses']:
                            result[current_section].append({"statement": cleaned})
                        elif current_section == 'evidence':
                            result[current_section].append({"data": cleaned})
                        elif current_section == 'proofs':
                            result[current_section].append({"statement": cleaned})
                        else:
                            result[current_section].append(cleaned)
        
        return result
    
    def format_as_markdown(self, analysis_result: Dict[str, Any]) -> str:
        """Format the analysis result as markdown."""
        md_lines = ["# Postulate-Theorem Analysis\n"]
        
        if analysis_result.get("postulates"):
            md_lines.append("## Postulates (Fundamental Principles)\n")
            for i, postulate in enumerate(analysis_result["postulates"], 1):
                if isinstance(postulate, dict):
                    if "label" in postulate:
                        md_lines.append(f"{i}. **{postulate['label']}**: {postulate.get('statement', '')}")
                    else:
                        md_lines.append(f"{i}. {postulate.get('statement', '')}")
                    if postulate.get('type'):
                        md_lines.append(f"   - Type: {postulate['type']}")
                else:
                    md_lines.append(f"{i}. {postulate}")
            md_lines.append("")
        
        if analysis_result.get("theorems"):
            md_lines.append("## Theorems (Derived Conclusions)\n")
            for i, theorem in enumerate(analysis_result["theorems"], 1):
                if isinstance(theorem, dict):
                    if "label" in theorem:
                        md_lines.append(f"{i}. **{theorem['label']}**: {theorem.get('statement', '')}")
                    else:
                        md_lines.append(f"{i}. {theorem.get('statement', '')}")
                    if theorem.get('derived_from'):
                        md_lines.append(f"   - Derived from: {', '.join(theorem['derived_from'])}")
                else:
                    md_lines.append(f"{i}. {theorem}")
            md_lines.append("")
        
        if analysis_result.get("hypotheses"):
            md_lines.append("## Hypotheses (Conjectures)\n")
            for i, hypothesis in enumerate(analysis_result["hypotheses"], 1):
                if isinstance(hypothesis, dict):
                    if "label" in hypothesis:
                        md_lines.append(f"{i}. **{hypothesis['label']}**: {hypothesis.get('statement', '')}")
                    else:
                        md_lines.append(f"{i}. {hypothesis.get('statement', '')}")
                    if hypothesis.get('confidence'):
                        confidence = hypothesis['confidence']
                        emoji = "🟢" if confidence == "high" else "🟡" if confidence == "medium" else "🔴"
                        md_lines.append(f"   - Confidence: {emoji} {confidence}")
                else:
                    md_lines.append(f"{i}. {hypothesis}")
            md_lines.append("")
        
        if analysis_result.get("evidence"):
            md_lines.append("## Supporting Evidence\n")
            for i, evidence in enumerate(analysis_result["evidence"], 1):
                if isinstance(evidence, dict):
                    if evidence.get('supports'):
                        md_lines.append(f"{i}. **{evidence.get('data', '')}** → supports *{evidence['supports']}*")
                    else:
                        md_lines.append(f"{i}. {evidence.get('data', '')}")
                else:
                    md_lines.append(f"{i}. {evidence}")
            md_lines.append("")
        
        if analysis_result.get("theoretical_frameworks"):
            md_lines.append("## Theoretical Frameworks\n")
            for framework in analysis_result["theoretical_frameworks"]:
                md_lines.append(f"- 📚 {framework}")
            md_lines.append("")
        
        if analysis_result.get("proofs"):
            md_lines.append("## Proofs & Validations\n")
            for i, proof in enumerate(analysis_result["proofs"], 1):
                if isinstance(proof, dict):
                    if proof.get('theorem'):
                        md_lines.append(f"\n### Proof {i}: {proof['theorem']}\n")
                    else:
                        md_lines.append(f"\n### Proof {i}\n")
                    
                    if proof.get('steps'):
                        md_lines.append("**Steps:**")
                        for j, step in enumerate(proof['steps'], 1):
                            md_lines.append(f"  {j}. {step}")
                    elif proof.get('statement'):
                        md_lines.append(proof['statement'])
                else:
                    md_lines.append(f"\n### Proof {i}\n")
                    md_lines.append(f"{proof}")
            md_lines.append("")
        
        # Add metadata
        md_lines.append("---\n")
        md_lines.append("## Analysis Metadata\n")
        if "metadata" in analysis_result:
            metadata = analysis_result["metadata"]
            md_lines.append(f"- **Analyzer**: {metadata.get('analyzer', 'Postulate-Theorem')}")
            md_lines.append(f"- **Processing Time**: {metadata.get('processing_time', 'N/A')} seconds")
            md_lines.append(f"- **Token Usage**: {metadata.get('token_usage', {}).get('total_tokens', 'N/A')} tokens")
            md_lines.append(f"- **Model**: {metadata.get('model', 'N/A')}")
        
        return "\n".join(md_lines)
