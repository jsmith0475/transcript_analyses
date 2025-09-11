"""
Premises-Assertions Analyzer for Stage A transcript analysis.
Extracts foundational assumptions and claims from conversations.
"""

from typing import Dict, Any, List
from src.analyzers.base_analyzer import BaseAnalyzer
import json
import re


class PremisesAssertionsAnalyzer(BaseAnalyzer):
    """Analyzes premises and assertions in conversations."""
    
    def __init__(self):
        super().__init__(
            name="premises_assertions",
            stage="stage_a"
        )
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the premises-assertions analysis response."""
        result = {
            "premises": [],
            "assertions": [],
            "logical_connections": [],
            "logical_gaps": [],
            "argument_structures": []
        }
        
        # Extract premises section
        premises_match = re.search(
            r'(?:PREMISES?|ASSUMPTIONS?|FOUNDATIONS?)[:\s]*\n(.*?)(?=\n(?:ASSERTIONS?|CLAIMS?|LOGICAL|GAPS?|ARGUMENTS?|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if premises_match:
            premise_lines = premises_match.group(1).strip().split('\n')
            for line in premise_lines:
                cleaned = line.strip().lstrip('- •*').strip()
                if cleaned and not cleaned.startswith('#'):
                    # Try to extract structured premise info
                    if ':' in cleaned:
                        parts = cleaned.split(':', 1)
                        result["premises"].append({
                            "label": parts[0].strip(),
                            "statement": parts[1].strip()
                        })
                    else:
                        result["premises"].append({
                            "statement": cleaned
                        })
        
        # Extract assertions section
        assertions_match = re.search(
            r'(?:ASSERTIONS?|CLAIMS?|CONCLUSIONS?)[:\s]*\n(.*?)(?=\n(?:LOGICAL|CONNECTIONS?|GAPS?|ARGUMENTS?|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if assertions_match:
            assertion_lines = assertions_match.group(1).strip().split('\n')
            for line in assertion_lines:
                cleaned = line.strip().lstrip('- •*').strip()
                if cleaned and not cleaned.startswith('#'):
                    # Try to extract structured assertion info
                    if ':' in cleaned:
                        parts = cleaned.split(':', 1)
                        result["assertions"].append({
                            "label": parts[0].strip(),
                            "claim": parts[1].strip()
                        })
                    else:
                        result["assertions"].append({
                            "claim": cleaned
                        })
        
        # Extract logical connections
        connections_match = re.search(
            r'(?:LOGICAL CONNECTIONS?|CONNECTIONS?|RELATIONSHIPS?)[:\s]*\n(.*?)(?=\n(?:GAPS?|ARGUMENTS?|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if connections_match:
            connection_lines = connections_match.group(1).strip().split('\n')
            for line in connection_lines:
                cleaned = line.strip().lstrip('- •*').strip()
                if cleaned and not cleaned.startswith('#'):
                    result["logical_connections"].append(cleaned)
        
        # Extract logical gaps
        gaps_match = re.search(
            r'(?:LOGICAL GAPS?|GAPS?|FALLACIES?|WEAKNESSES?)[:\s]*\n(.*?)(?=\n(?:ARGUMENTS?|STRUCTURES?|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if gaps_match:
            gap_lines = gaps_match.group(1).strip().split('\n')
            for line in gap_lines:
                cleaned = line.strip().lstrip('- •*').strip()
                if cleaned and not cleaned.startswith('#'):
                    result["logical_gaps"].append(cleaned)
        
        # Extract argument structures
        arguments_match = re.search(
            r'(?:ARGUMENT STRUCTURES?|ARGUMENTS?|REASONING)[:\s]*\n(.*?)$',
            response, re.IGNORECASE | re.DOTALL
        )
        if arguments_match:
            argument_lines = arguments_match.group(1).strip().split('\n')
            current_argument = None
            for line in argument_lines:
                cleaned = line.strip()
                if cleaned and not cleaned.startswith('#'):
                    # Check if this is a new argument header
                    if re.match(r'^\d+\.|\w+\)', cleaned):
                        if current_argument:
                            result["argument_structures"].append(current_argument)
                        current_argument = {
                            "description": cleaned.lstrip('0123456789. ').strip(),
                            "components": []
                        }
                    elif current_argument and cleaned.startswith(('- ', '• ', '* ')):
                        current_argument["components"].append(cleaned.lstrip('- •*').strip())
                    elif not current_argument:
                        result["argument_structures"].append({
                            "description": cleaned
                        })
            
            if current_argument:
                result["argument_structures"].append(current_argument)
        
        # Fallback: Extract from general content if no structured sections found
        if not any([result["premises"], result["assertions"]]):
            lines = response.strip().split('\n')
            current_section = None
            
            for line in lines:
                line_lower = line.lower().strip()
                
                # Detect section headers
                if any(word in line_lower for word in ['premise', 'assumption', 'foundation']):
                    current_section = 'premises'
                elif any(word in line_lower for word in ['assertion', 'claim', 'conclusion']):
                    current_section = 'assertions'
                elif any(word in line_lower for word in ['connection', 'relationship', 'link']):
                    current_section = 'logical_connections'
                elif any(word in line_lower for word in ['gap', 'fallacy', 'weakness']):
                    current_section = 'logical_gaps'
                elif any(word in line_lower for word in ['argument', 'reasoning', 'structure']):
                    current_section = 'argument_structures'
                elif current_section and line.strip():
                    cleaned = line.strip().lstrip('- •*').strip()
                    if cleaned and not cleaned.startswith('#'):
                        if current_section == 'premises':
                            result[current_section].append({"statement": cleaned})
                        elif current_section == 'assertions':
                            result[current_section].append({"claim": cleaned})
                        elif current_section == 'argument_structures':
                            result[current_section].append({"description": cleaned})
                        else:
                            result[current_section].append(cleaned)
        
        return result
    
    def format_as_markdown(self, analysis_result: Dict[str, Any]) -> str:
        """Format the analysis result as markdown."""
        md_lines = ["# Premises-Assertions Analysis\n"]
        
        if analysis_result.get("premises"):
            md_lines.append("## Premises (Foundational Assumptions)\n")
            for i, premise in enumerate(analysis_result["premises"], 1):
                if isinstance(premise, dict):
                    if "label" in premise:
                        md_lines.append(f"{i}. **{premise['label']}**: {premise.get('statement', '')}")
                    else:
                        md_lines.append(f"{i}. {premise.get('statement', '')}")
                else:
                    md_lines.append(f"{i}. {premise}")
            md_lines.append("")
        
        if analysis_result.get("assertions"):
            md_lines.append("## Assertions (Claims Made)\n")
            for i, assertion in enumerate(analysis_result["assertions"], 1):
                if isinstance(assertion, dict):
                    if "label" in assertion:
                        md_lines.append(f"{i}. **{assertion['label']}**: {assertion.get('claim', '')}")
                    else:
                        md_lines.append(f"{i}. {assertion.get('claim', '')}")
                else:
                    md_lines.append(f"{i}. {assertion}")
            md_lines.append("")
        
        if analysis_result.get("logical_connections"):
            md_lines.append("## Logical Connections\n")
            for connection in analysis_result["logical_connections"]:
                md_lines.append(f"- {connection}")
            md_lines.append("")
        
        if analysis_result.get("logical_gaps"):
            md_lines.append("## Logical Gaps & Weaknesses\n")
            for gap in analysis_result["logical_gaps"]:
                md_lines.append(f"- ⚠️ {gap}")
            md_lines.append("")
        
        if analysis_result.get("argument_structures"):
            md_lines.append("## Argument Structures\n")
            for i, arg in enumerate(analysis_result["argument_structures"], 1):
                if isinstance(arg, dict):
                    md_lines.append(f"\n### Argument {i}: {arg.get('description', 'Unnamed')}\n")
                    if arg.get('components'):
                        for component in arg['components']:
                            md_lines.append(f"  - {component}")
                else:
                    md_lines.append(f"\n### Argument {i}\n")
                    md_lines.append(f"{arg}")
            md_lines.append("")
        
        # Add metadata
        md_lines.append("---\n")
        md_lines.append("## Analysis Metadata\n")
        if "metadata" in analysis_result:
            metadata = analysis_result["metadata"]
            md_lines.append(f"- **Analyzer**: {metadata.get('analyzer', 'Premises-Assertions')}")
            md_lines.append(f"- **Processing Time**: {metadata.get('processing_time', 'N/A')} seconds")
            md_lines.append(f"- **Token Usage**: {metadata.get('token_usage', {}).get('total_tokens', 'N/A')} tokens")
            md_lines.append(f"- **Model**: {metadata.get('model', 'N/A')}")
        
        return "\n".join(md_lines)
