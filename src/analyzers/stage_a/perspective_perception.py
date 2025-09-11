"""
Perspective-Perception Analyzer for Stage A transcript analysis.
Identifies different viewpoints and perception gaps in conversations.
"""

from typing import Dict, Any, List
from src.analyzers.base_analyzer import BaseAnalyzer
import json
import re


class PerspectivePerceptionAnalyzer(BaseAnalyzer):
    """Analyzes different viewpoints and perception gaps in conversations."""
    
    def __init__(self):
        super().__init__(
            name="perspective_perception",
            stage="stage_a"
        )
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the perspective-perception analysis response."""
        result = {
            "perspectives": [],
            "perception_gaps": [],
            "viewpoint_alignments": [],
            "conflicting_views": [],
            "key_insights": []
        }
        
        # Extract perspectives section
        perspectives_match = re.search(
            r'(?:PERSPECTIVES?|VIEWPOINTS?)[:\s]*\n(.*?)(?=\n(?:PERCEPTION|GAPS|ALIGNMENTS?|CONFLICTS?|KEY|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if perspectives_match:
            perspective_lines = perspectives_match.group(1).strip().split('\n')
            for line in perspective_lines:
                cleaned = line.strip().lstrip('- •*').strip()
                if cleaned and not cleaned.startswith('#'):
                    result["perspectives"].append(cleaned)
        
        # Extract perception gaps
        gaps_match = re.search(
            r'(?:PERCEPTION GAPS?|GAPS?)[:\s]*\n(.*?)(?=\n(?:ALIGNMENTS?|CONFLICTS?|KEY|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if gaps_match:
            gap_lines = gaps_match.group(1).strip().split('\n')
            for line in gap_lines:
                cleaned = line.strip().lstrip('- •*').strip()
                if cleaned and not cleaned.startswith('#'):
                    result["perception_gaps"].append(cleaned)
        
        # Extract alignments
        alignments_match = re.search(
            r'(?:ALIGNMENTS?|AGREEMENTS?|CONSENSUS)[:\s]*\n(.*?)(?=\n(?:CONFLICTS?|KEY|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if alignments_match:
            alignment_lines = alignments_match.group(1).strip().split('\n')
            for line in alignment_lines:
                cleaned = line.strip().lstrip('- •*').strip()
                if cleaned and not cleaned.startswith('#'):
                    result["viewpoint_alignments"].append(cleaned)
        
        # Extract conflicts
        conflicts_match = re.search(
            r'(?:CONFLICTS?|DISAGREEMENTS?|TENSIONS?)[:\s]*\n(.*?)(?=\n(?:KEY|INSIGHTS?|$))',
            response, re.IGNORECASE | re.DOTALL
        )
        if conflicts_match:
            conflict_lines = conflicts_match.group(1).strip().split('\n')
            for line in conflict_lines:
                cleaned = line.strip().lstrip('- •*').strip()
                if cleaned and not cleaned.startswith('#'):
                    result["conflicting_views"].append(cleaned)
        
        # Extract key insights
        insights_match = re.search(
            r'(?:KEY INSIGHTS?|INSIGHTS?|SUMMARY)[:\s]*\n(.*?)$',
            response, re.IGNORECASE | re.DOTALL
        )
        if insights_match:
            insight_lines = insights_match.group(1).strip().split('\n')
            for line in insight_lines:
                cleaned = line.strip().lstrip('- •*').strip()
                if cleaned and not cleaned.startswith('#'):
                    result["key_insights"].append(cleaned)
        
        # If no structured sections found, try to extract from general content
        if not any(result.values()):
            lines = response.strip().split('\n')
            current_section = None
            
            for line in lines:
                line_lower = line.lower().strip()
                
                # Detect section headers
                if any(word in line_lower for word in ['perspective', 'viewpoint']):
                    current_section = 'perspectives'
                elif any(word in line_lower for word in ['gap', 'misunderstanding']):
                    current_section = 'perception_gaps'
                elif any(word in line_lower for word in ['alignment', 'agreement', 'consensus']):
                    current_section = 'viewpoint_alignments'
                elif any(word in line_lower for word in ['conflict', 'disagreement', 'tension']):
                    current_section = 'conflicting_views'
                elif any(word in line_lower for word in ['insight', 'key', 'summary']):
                    current_section = 'key_insights'
                elif current_section and line.strip():
                    # Add content to current section
                    cleaned = line.strip().lstrip('- •*').strip()
                    if cleaned and not cleaned.startswith('#'):
                        result[current_section].append(cleaned)
        
        return result
    
    def format_as_markdown(self, analysis_result: Dict[str, Any]) -> str:
        """Format the analysis result as markdown."""
        md_lines = ["# Perspective-Perception Analysis\n"]
        
        if analysis_result.get("perspectives"):
            md_lines.append("## Perspectives Identified\n")
            for perspective in analysis_result["perspectives"]:
                md_lines.append(f"- {perspective}")
            md_lines.append("")
        
        if analysis_result.get("perception_gaps"):
            md_lines.append("## Perception Gaps\n")
            for gap in analysis_result["perception_gaps"]:
                md_lines.append(f"- {gap}")
            md_lines.append("")
        
        if analysis_result.get("viewpoint_alignments"):
            md_lines.append("## Areas of Alignment\n")
            for alignment in analysis_result["viewpoint_alignments"]:
                md_lines.append(f"- {alignment}")
            md_lines.append("")
        
        if analysis_result.get("conflicting_views"):
            md_lines.append("## Conflicting Views\n")
            for conflict in analysis_result["conflicting_views"]:
                md_lines.append(f"- {conflict}")
            md_lines.append("")
        
        if analysis_result.get("key_insights"):
            md_lines.append("## Key Insights\n")
            for insight in analysis_result["key_insights"]:
                md_lines.append(f"- {insight}")
            md_lines.append("")
        
        # Add metadata
        md_lines.append("---\n")
        md_lines.append("## Analysis Metadata\n")
        if "metadata" in analysis_result:
            metadata = analysis_result["metadata"]
            md_lines.append(f"- **Analyzer**: {metadata.get('analyzer', 'Perspective-Perception')}")
            md_lines.append(f"- **Processing Time**: {metadata.get('processing_time', 'N/A')} seconds")
            md_lines.append(f"- **Token Usage**: {metadata.get('token_usage', {}).get('total_tokens', 'N/A')} tokens")
            md_lines.append(f"- **Model**: {metadata.get('model', 'N/A')}")
        
        return "\n".join(md_lines)
