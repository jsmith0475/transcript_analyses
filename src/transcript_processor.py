"""
Transcript processor for parsing and structuring meeting transcripts.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from loguru import logger

from src.models import (
    TranscriptSegment,
    Speaker,
    TranscriptMetadata,
    ProcessedTranscript
)


class TranscriptProcessor:
    """Process raw transcripts into structured format."""
    
    def __init__(self):
        """Initialize the transcript processor."""
        # Patterns for speaker detection
        self.speaker_patterns = [
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*:\s*(.+)$',  # Name: text
            r'^\[([^\]]+)\]\s*(.+)$',  # [Name] text
            r'^-\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*:\s*(.+)$',  # - Name: text
            r'^•\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*:\s*(.+)$',  # • Name: text
        ]
        
        # Patterns for metadata extraction
        self.metadata_patterns = {
            'date': [
                r'Date:\s*(\d{4}-\d{2}-\d{2})',
                r'Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
                r'Meeting Date:\s*([^\n]+)',
            ],
            'title': [
                r'Title:\s*([^\n]+)',
                r'Meeting:\s*([^\n]+)',
                r'Subject:\s*([^\n]+)',
                r'^#\s+(.+)$',  # Markdown header
            ],
            'duration': [
                r'Duration:\s*([^\n]+)',
                r'Length:\s*([^\n]+)',
            ],
            'attendees': [
                r'Attendees?:\s*([^\n]+)',
                r'Participants?:\s*([^\n]+)',
            ]
        }
    
    def process(self, raw_transcript: str, filename: Optional[str] = None) -> ProcessedTranscript:
        """
        Process a raw transcript into structured format.
        
        Args:
            raw_transcript: The raw transcript text
            filename: Optional filename for metadata
            
        Returns:
            ProcessedTranscript object
        """
        logger.info("Processing transcript...")
        
        # Extract metadata
        metadata = self._extract_metadata(raw_transcript, filename)
        
        # Split into lines for processing
        lines = raw_transcript.strip().split('\n')
        
        # Detect if transcript has speaker names
        has_speakers = self._detect_speakers(lines)
        
        # Process segments
        if has_speakers:
            segments, speakers = self._process_with_speakers(lines)
        else:
            segments = self._process_without_speakers(lines)
            speakers = []
        
        # Update metadata
        metadata.word_count = sum(len(seg.text.split()) for seg in segments)
        metadata.segment_count = len(segments)
        metadata.speaker_count = len(speakers)
        
        # Create processed transcript
        processed = ProcessedTranscript(
            segments=segments,
            speakers=speakers,
            metadata=metadata,
            raw_text=raw_transcript,
            has_speaker_names=has_speakers
        )
        
        logger.info(f"Processed transcript: {len(segments)} segments, {len(speakers)} speakers")
        
        return processed
    
    def _extract_metadata(self, text: str, filename: Optional[str] = None) -> TranscriptMetadata:
        """Extract metadata from transcript text."""
        metadata = TranscriptMetadata()
        
        if filename:
            metadata.filename = filename
        
        # Try to extract date
        for pattern in self.metadata_patterns['date']:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    # Try different date formats
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                        try:
                            metadata.date = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass
                break
        
        # Try to extract title
        for pattern in self.metadata_patterns['title']:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                metadata.title = match.group(1).strip()
                break
        
        # Try to extract duration
        for pattern in self.metadata_patterns['duration']:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                metadata.duration = match.group(1).strip()
                break
        
        return metadata
    
    def _detect_speakers(self, lines: List[str]) -> bool:
        """Detect if the transcript has speaker names."""
        speaker_count = 0
        total_lines = 0
        
        for line in lines[:50]:  # Check first 50 lines
            line = line.strip()
            if not line:
                continue
            
            total_lines += 1
            for pattern in self.speaker_patterns:
                if re.match(pattern, line):
                    speaker_count += 1
                    break
        
        # If more than 30% of lines have speaker patterns, assume it has speakers
        if total_lines > 0:
            ratio = speaker_count / total_lines
            return ratio > 0.3
        
        return False
    
    def _process_with_speakers(self, lines: List[str]) -> Tuple[List[TranscriptSegment], List[Speaker]]:
        """Process transcript with speaker names."""
        segments = []
        speakers_dict = {}
        current_speaker = None
        current_text = []
        segment_id = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                # Empty line might indicate segment break
                if current_text and current_speaker:
                    text = ' '.join(current_text)
                    segments.append(TranscriptSegment(
                        segment_id=segment_id,
                        speaker=current_speaker,
                        text=text
                    ))
                    
                    # Update speaker stats
                    if current_speaker not in speakers_dict:
                        speakers_dict[current_speaker] = Speaker(
                            id=current_speaker.lower().replace(' ', '_'),
                            name=current_speaker,
                            segments_count=0,
                            total_words=0
                        )
                    speakers_dict[current_speaker].segments_count += 1
                    speakers_dict[current_speaker].total_words += len(text.split())
                    
                    segment_id += 1
                    current_text = []
                continue
            
            # Check for speaker pattern
            speaker_found = False
            for pattern in self.speaker_patterns:
                match = re.match(pattern, line)
                if match:
                    # Save previous segment if exists
                    if current_text and current_speaker:
                        text = ' '.join(current_text)
                        segments.append(TranscriptSegment(
                            segment_id=segment_id,
                            speaker=current_speaker,
                            text=text
                        ))
                        
                        # Update speaker stats
                        if current_speaker not in speakers_dict:
                            speakers_dict[current_speaker] = Speaker(
                                id=current_speaker.lower().replace(' ', '_'),
                                name=current_speaker,
                                segments_count=0,
                                total_words=0
                            )
                        speakers_dict[current_speaker].segments_count += 1
                        speakers_dict[current_speaker].total_words += len(text.split())
                        
                        segment_id += 1
                    
                    # Start new segment
                    current_speaker = match.group(1).strip()
                    current_text = [match.group(2).strip()]
                    speaker_found = True
                    break
            
            if not speaker_found:
                # Continue current segment
                current_text.append(line)
        
        # Add final segment
        if current_text and current_speaker:
            text = ' '.join(current_text)
            segments.append(TranscriptSegment(
                segment_id=segment_id,
                speaker=current_speaker,
                text=text
            ))
            
            # Update speaker stats
            if current_speaker not in speakers_dict:
                speakers_dict[current_speaker] = Speaker(
                    id=current_speaker.lower().replace(' ', '_'),
                    name=current_speaker,
                    segments_count=0,
                    total_words=0
                )
            speakers_dict[current_speaker].segments_count += 1
            speakers_dict[current_speaker].total_words += len(text.split())
        
        return segments, list(speakers_dict.values())
    
    def _process_without_speakers(self, lines: List[str]) -> List[TranscriptSegment]:
        """Process transcript without speaker names."""
        segments = []
        current_text = []
        segment_id = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                # Empty line indicates segment break
                if current_text:
                    segments.append(TranscriptSegment(
                        segment_id=segment_id,
                        speaker=None,
                        text=' '.join(current_text)
                    ))
                    segment_id += 1
                    current_text = []
            else:
                current_text.append(line)
        
        # Add final segment
        if current_text:
            segments.append(TranscriptSegment(
                segment_id=segment_id,
                speaker=None,
                text=' '.join(current_text)
            ))
        
        # If no segments were created, treat entire text as one segment
        if not segments and lines:
            segments.append(TranscriptSegment(
                segment_id=0,
                speaker=None,
                text=' '.join(line.strip() for line in lines if line.strip())
            ))
        
        return segments
    
    def load_from_file(self, filepath: Path) -> ProcessedTranscript:
        """
        Load and process a transcript from a file.
        
        Args:
            filepath: Path to the transcript file
            
        Returns:
            ProcessedTranscript object
        """
        logger.info(f"Loading transcript from {filepath}")
        
        # Read file content
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Process transcript
        return self.process(content, filename=filepath.name)
    
    def extract_speakers_list(self, processed: ProcessedTranscript) -> List[str]:
        """
        Extract a list of speaker names from processed transcript.
        
        Args:
            processed: ProcessedTranscript object
            
        Returns:
            List of speaker names
        """
        if processed.speakers:
            return [speaker.name for speaker in processed.speakers if speaker.name]
        
        # Try to extract from segments
        speakers = set()
        for segment in processed.segments:
            if segment.speaker:
                speakers.add(segment.speaker)
        
        return sorted(list(speakers))
    
    def get_speaker_segments(self, processed: ProcessedTranscript, speaker_name: str) -> List[TranscriptSegment]:
        """
        Get all segments for a specific speaker.
        
        Args:
            processed: ProcessedTranscript object
            speaker_name: Name of the speaker
            
        Returns:
            List of segments for the speaker
        """
        return [
            segment for segment in processed.segments
            if segment.speaker and segment.speaker.lower() == speaker_name.lower()
        ]
    
    def format_for_display(self, processed: ProcessedTranscript, include_speakers: bool = True) -> str:
        """
        Format processed transcript for display.
        
        Args:
            processed: ProcessedTranscript object
            include_speakers: Whether to include speaker names
            
        Returns:
            Formatted transcript text
        """
        lines = []
        
        # Add metadata if available
        if processed.metadata.title:
            lines.append(f"# {processed.metadata.title}\n")
        
        if processed.metadata.date:
            lines.append(f"**Date:** {processed.metadata.date.strftime('%Y-%m-%d')}")
        
        if processed.metadata.duration:
            lines.append(f"**Duration:** {processed.metadata.duration}")
        
        if processed.speakers:
            speaker_names = [s.name for s in processed.speakers if s.name]
            if speaker_names:
                lines.append(f"**Speakers:** {', '.join(speaker_names)}")
        
        if lines:
            lines.append("\n---\n")
        
        # Add segments
        for segment in processed.segments:
            if include_speakers and segment.speaker:
                lines.append(f"**{segment.speaker}:** {segment.text}\n")
            else:
                lines.append(f"{segment.text}\n")
        
        return '\n'.join(lines)


# Global processor instance
_processor: Optional[TranscriptProcessor] = None


def get_transcript_processor() -> TranscriptProcessor:
    """Get the global transcript processor instance."""
    global _processor
    if _processor is None:
        _processor = TranscriptProcessor()
    return _processor


def reset_transcript_processor():
    """Reset the global transcript processor instance."""
    global _processor
    _processor = None
