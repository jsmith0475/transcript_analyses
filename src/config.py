"""
Configuration management for the Transcript Analysis Tool.
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMConfig(BaseModel):
    """Configuration for LLM integration."""
    provider: str = "openai"
    model: str = Field(default="gpt-4o-mini")
    api_key: Optional[str] = None
    api_base: str = "https://api.openai.com/v1"
    max_tokens: int = 8000
    temperature: float = 1.0  # GPT-5 only supports temperature=1
    reasoning_effort: str = "medium"  # For GPT-5: minimal, low, medium, high
    text_verbosity: str = "medium"    # For GPT-5: low, medium, high
    timeout: int = 120
    max_retries: int = 3
    retry_delay: float = 1.0
    
    @validator('api_key', always=True)
    def validate_api_key(cls, v):
        # Defer hard validation to runtime LLM calls so the app can boot without a key
        if v:
            return v
        env_key = os.getenv('OPENAI_API_KEY')
        if env_key:
            return env_key
        # Allow None here; endpoints that invoke LLM will fail until a key is provided
        return None
    
    @validator('model')
    def validate_model(cls, v):
        if not v:
            v = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        return v


class ProcessingConfig(BaseModel):
    """Configuration for processing pipeline."""
    parallel: bool = True
    max_concurrent: int = 3
    chunk_size: int = 4000  # For chunking long transcripts
    chunk_overlap: int = 400
    stage_b_context_token_budget: int = 8000  # Target token budget for Stage B context injection
    stage_b_min_tokens_per_analyzer: int = 500  # Minimum tokens guaranteed per Stage A analyzer in Stage B context
    # Final stage options
    final_include_transcript: bool = True
    final_transcript_mode: str = "full"  # "full" or "summary"
    final_transcript_char_limit: int = 20000
    # Optional token budget for Final stage combined context; 0 disables trimming
    final_context_token_budget: int = 0
    # Summary feature (map-reduce) configuration
    summary_enabled: bool = True
    summary_map_chunk_tokens: int = 2000
    summary_map_overlap_tokens: int = 200
    summary_stage_b_target_tokens: int = 1000
    summary_final_target_tokens: int = 2000
    summary_single_pass_max_tokens: int = 6000
    summary_map_model: Optional[str] = None
    summary_reduce_model: Optional[str] = None
    # LLM-based Insights extraction
    insights_llm_enabled: bool = True
    insights_llm_model: Optional[str] = None
    insights_llm_max_items: int = 50
    insights_llm_max_tokens: int = 2000
    stop_on_error: bool = False
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hour
    session_timeout: int = 1800  # 30 minutes


class OutputConfig(BaseModel):
    """Configuration for output generation."""
    format: str = "obsidian"  # obsidian, markdown, json
    directory: Path = Path("./output")
    date_prefix: bool = True
    include_metadata: bool = True
    include_token_usage: bool = True
    max_insights_per_analyzer: int = 10
    max_concepts_per_analyzer: int = 20
    # Display-only truncation controls for intermediate markdown raw_output section
    truncate_raw_output: bool = True
    raw_output_max_chars: int = 5000
    
    @validator('directory')
    def ensure_directory_exists(cls, v):
        v.mkdir(parents=True, exist_ok=True)
        return v


class ObsidianConfig(BaseModel):
    """Configuration for Obsidian-specific formatting."""
    enable_wikilinks: bool = True
    enable_tags: bool = True
    enable_frontmatter: bool = True
    default_tags: List[str] = Field(default_factory=lambda: ["transcript-analysis", "meeting-notes"])
    link_concepts: bool = True
    concept_threshold: float = 0.7  # Confidence threshold for linking


class NotificationsConfig(BaseModel):
    """Configuration for proactive notifications."""
    enabled: bool = False
    channels: List[str] = Field(default_factory=list)  # e.g., ["desktop","slack","webhook","file"]
    slack_webhook_url: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_headers: Dict[str, str] = Field(default_factory=dict)
    secret_token: Optional[str] = None
    desktop_enabled: bool = False
    desktop_strategy: str = "plyer"  # or "macos_say" | "terminal_notifier"
    desktop_speak_on_complete: bool = False
    throttle_seconds: int = 5
    include_links: bool = True
    file_path: Optional[str] = None  # JSONL output for autonomous tests

class WebConfig(BaseModel):
    """Configuration for web application."""
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    secret_key: Optional[str] = None
    max_content_length: int = 10 * 1024 * 1024  # 10MB
    upload_folder: Path = Path("./uploads")
    allowed_extensions: List[str] = Field(default_factory=lambda: [".txt", ".md", ".markdown"])
    
    # Redis configuration
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    
    # Celery configuration
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_task_time_limit: int = 600  # 10 minutes
    
    # WebSocket configuration
    socketio_async_mode: str = "eventlet"
    socketio_cors_allowed_origins: str = "*"
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if not v:
            v = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
        return v
    
    @validator('upload_folder')
    def ensure_upload_folder_exists(cls, v):
        v.mkdir(parents=True, exist_ok=True)
        return v


class AnalyzerConfig(BaseModel):
    """Configuration for individual analyzers."""
    enabled: bool = True
    prompt_file: Optional[Path] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    timeout: Optional[int] = None
    
    def merge_with_llm_config(self, llm_config: LLMConfig) -> Dict[str, Any]:
        """Merge analyzer-specific config with global LLM config."""
        config = llm_config.dict()
        
        if self.max_tokens is not None:
            config['max_tokens'] = self.max_tokens
        if self.temperature is not None:
            config['temperature'] = self.temperature
        if self.timeout is not None:
            config['timeout'] = self.timeout
            
        return config


class AppConfig(BaseSettings):
    """Main application configuration."""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    obsidian: ObsidianConfig = Field(default_factory=ObsidianConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    
    # Analyzer configurations
    analyzers: Dict[str, AnalyzerConfig] = Field(default_factory=dict)
    
    # Stage definitions
    stage_a_analyzers: List[str] = Field(
        default_factory=lambda: [
            'say_means',
            'perspective_perception',
            'premises_assertions',
            'postulate_theorem'
        ]
    )
    
    stage_b_analyzers: List[str] = Field(
        default_factory=lambda: [
            'competing_hypotheses',
            'first_principles',
            'determining_factors',
            'patentability'
        ]
    )
    
    final_stage_analyzers: List[str] = Field(
        default_factory=lambda: ['meeting_notes', 'composite_note']
    )
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        env_prefix = 'TRANSCRIPT_ANALYZER_'
        extra = 'ignore'
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Create configuration from environment variables."""
        config = cls()
        
        # Override with environment variables
        if os.getenv('OPENAI_API_KEY'):
            config.llm.api_key = os.getenv('OPENAI_API_KEY')
        
        if os.getenv('OPENAI_MODEL'):
            config.llm.model = os.getenv('OPENAI_MODEL')
        
        if os.getenv('TRANSCRIPT_ANALYZER_REASONING_EFFORT'):
            config.llm.reasoning_effort = os.getenv('TRANSCRIPT_ANALYZER_REASONING_EFFORT')
        
        if os.getenv('TRANSCRIPT_ANALYZER_TEXT_VERBOSITY'):
            config.llm.text_verbosity = os.getenv('TRANSCRIPT_ANALYZER_TEXT_VERBOSITY')
        
        if os.getenv('TRANSCRIPT_ANALYZER_MAX_TOKENS'):
            config.llm.max_tokens = int(os.getenv('TRANSCRIPT_ANALYZER_MAX_TOKENS'))
        
        if os.getenv('TRANSCRIPT_ANALYZER_OUTPUT_DIR'):
            config.output.directory = Path(os.getenv('TRANSCRIPT_ANALYZER_OUTPUT_DIR'))
        
        if os.getenv('TRANSCRIPT_ANALYZER_FORMAT'):
            config.output.format = os.getenv('TRANSCRIPT_ANALYZER_FORMAT')
        
        if os.getenv('TRANSCRIPT_ANALYZER_PARALLEL'):
            config.processing.parallel = os.getenv('TRANSCRIPT_ANALYZER_PARALLEL').lower() == 'true'
        # Optional env overrides for Stage B budgeting to validate fairness under tighter limits
        if os.getenv('TRANSCRIPT_ANALYZER_STAGE_B_CONTEXT_TOKEN_BUDGET'):
            try:
                config.processing.stage_b_context_token_budget = int(os.getenv('TRANSCRIPT_ANALYZER_STAGE_B_CONTEXT_TOKEN_BUDGET'))
            except Exception:
                pass
        if os.getenv('TRANSCRIPT_ANALYZER_STAGE_B_MIN_TOKENS_PER_ANALYZER'):
            try:
                config.processing.stage_b_min_tokens_per_analyzer = int(os.getenv('TRANSCRIPT_ANALYZER_STAGE_B_MIN_TOKENS_PER_ANALYZER'))
            except Exception:
                pass
        if os.getenv('TRANSCRIPT_ANALYZER_FINAL_CONTEXT_TOKEN_BUDGET'):
            try:
                config.processing.final_context_token_budget = int(os.getenv('TRANSCRIPT_ANALYZER_FINAL_CONTEXT_TOKEN_BUDGET'))
            except Exception:
                pass
        # Summary env overrides (optional)
        if os.getenv('TRANSCRIPT_ANALYZER_SUMMARY_ENABLED'):
            try:
                config.processing.summary_enabled = os.getenv('TRANSCRIPT_ANALYZER_SUMMARY_ENABLED').lower() == 'true'
            except Exception:
                pass
        for key_env, attr, cast in [
            ('TRANSCRIPT_ANALYZER_SUMMARY_MAP_CHUNK_TOKENS', 'summary_map_chunk_tokens', int),
            ('TRANSCRIPT_ANALYZER_SUMMARY_MAP_OVERLAP_TOKENS', 'summary_map_overlap_tokens', int),
            ('TRANSCRIPT_ANALYZER_SUMMARY_STAGE_B_TARGET_TOKENS', 'summary_stage_b_target_tokens', int),
            ('TRANSCRIPT_ANALYZER_SUMMARY_FINAL_TARGET_TOKENS', 'summary_final_target_tokens', int),
            ('TRANSCRIPT_ANALYZER_SUMMARY_SINGLE_PASS_MAX_TOKENS', 'summary_single_pass_max_tokens', int),
        ]:
            if os.getenv(key_env):
                try:
                    setattr(config.processing, attr, cast(os.getenv(key_env)))
                except Exception:
                    pass
        if os.getenv('TRANSCRIPT_ANALYZER_SUMMARY_MAP_MODEL'):
            config.processing.summary_map_model = os.getenv('TRANSCRIPT_ANALYZER_SUMMARY_MAP_MODEL')
        if os.getenv('TRANSCRIPT_ANALYZER_SUMMARY_REDUCE_MODEL'):
            config.processing.summary_reduce_model = os.getenv('TRANSCRIPT_ANALYZER_SUMMARY_REDUCE_MODEL')
        # Insights LLM env overrides
        if os.getenv('TRANSCRIPT_ANALYZER_INSIGHTS_LLM_ENABLED'):
            try:
                config.processing.insights_llm_enabled = os.getenv('TRANSCRIPT_ANALYZER_INSIGHTS_LLM_ENABLED').lower() == 'true'
            except Exception:
                pass
        if os.getenv('TRANSCRIPT_ANALYZER_INSIGHTS_LLM_MODEL'):
            config.processing.insights_llm_model = os.getenv('TRANSCRIPT_ANALYZER_INSIGHTS_LLM_MODEL')
        if os.getenv('TRANSCRIPT_ANALYZER_INSIGHTS_LLM_MAX_ITEMS'):
            try:
                config.processing.insights_llm_max_items = int(os.getenv('TRANSCRIPT_ANALYZER_INSIGHTS_LLM_MAX_ITEMS'))
            except Exception:
                pass
        if os.getenv('TRANSCRIPT_ANALYZER_INSIGHTS_LLM_MAX_TOKENS'):
            try:
                config.processing.insights_llm_max_tokens = int(os.getenv('TRANSCRIPT_ANALYZER_INSIGHTS_LLM_MAX_TOKENS'))
            except Exception:
                pass
        
        if os.getenv('REDIS_URL'):
            config.web.redis_url = os.getenv('REDIS_URL')
            config.web.celery_broker_url = os.getenv('REDIS_URL') + '/0'
            config.web.celery_result_backend = os.getenv('REDIS_URL') + '/0'

        # Notifications from ENV (prefixed)
        if os.getenv('TRANSCRIPT_ANALYZER_NOTIFICATIONS_ENABLED'):
            config.notifications.enabled = os.getenv('TRANSCRIPT_ANALYZER_NOTIFICATIONS_ENABLED').lower() == 'true'
        if os.getenv('TRANSCRIPT_ANALYZER_NOTIFICATIONS_CHANNELS'):
            chans = os.getenv('TRANSCRIPT_ANALYZER_NOTIFICATIONS_CHANNELS')
            config.notifications.channels = [c.strip() for c in chans.split(',') if c.strip()]
        if os.getenv('TRANSCRIPT_ANALYZER_SLACK_WEBHOOK_URL'):
            config.notifications.slack_webhook_url = os.getenv('TRANSCRIPT_ANALYZER_SLACK_WEBHOOK_URL')
        if os.getenv('TRANSCRIPT_ANALYZER_WEBHOOK_URL'):
            config.notifications.webhook_url = os.getenv('TRANSCRIPT_ANALYZER_WEBHOOK_URL')
        if os.getenv('TRANSCRIPT_ANALYZER_WEBHOOK_HEADERS'):
            # Expect JSON string e.g. {"X-Token":"abc"}
            try:
                import json as _json
                config.notifications.webhook_headers = _json.loads(os.getenv('TRANSCRIPT_ANALYZER_WEBHOOK_HEADERS'))
            except Exception:
                pass
        if os.getenv('TRANSCRIPT_ANALYZER_SECRET_TOKEN'):
            config.notifications.secret_token = os.getenv('TRANSCRIPT_ANALYZER_SECRET_TOKEN')
        if os.getenv('TRANSCRIPT_ANALYZER_DESKTOP_ENABLED'):
            config.notifications.desktop_enabled = os.getenv('TRANSCRIPT_ANALYZER_DESKTOP_ENABLED').lower() == 'true'
        if os.getenv('TRANSCRIPT_ANALYZER_DESKTOP_STRATEGY'):
            config.notifications.desktop_strategy = os.getenv('TRANSCRIPT_ANALYZER_DESKTOP_STRATEGY')
        if os.getenv('TRANSCRIPT_ANALYZER_DESKTOP_SPEAK_ON_COMPLETE'):
            config.notifications.desktop_speak_on_complete = os.getenv('TRANSCRIPT_ANALYZER_DESKTOP_SPEAK_ON_COMPLETE').lower() == 'true'
        if os.getenv('TRANSCRIPT_ANALYZER_NOTIFICATIONS_THROTTLE_SECONDS'):
            try:
                config.notifications.throttle_seconds = int(os.getenv('TRANSCRIPT_ANALYZER_NOTIFICATIONS_THROTTLE_SECONDS'))
            except Exception:
                pass
        if os.getenv('TRANSCRIPT_ANALYZER_NOTIFICATIONS_INCLUDE_LINKS'):
            config.notifications.include_links = os.getenv('TRANSCRIPT_ANALYZER_NOTIFICATIONS_INCLUDE_LINKS').lower() == 'true'
        if os.getenv('TRANSCRIPT_ANALYZER_NOTIFICATIONS_FILE_PATH'):
            config.notifications.file_path = os.getenv('TRANSCRIPT_ANALYZER_NOTIFICATIONS_FILE_PATH')
        
        # Output/truncation controls from ENV (display-only for intermediate markdown)
        if os.getenv('TRANSCRIPT_ANALYZER_TRUNCATE_RAW_OUTPUT'):
            try:
                config.output.truncate_raw_output = os.getenv('TRANSCRIPT_ANALYZER_TRUNCATE_RAW_OUTPUT').lower() == 'true'
            except Exception:
                pass
        if os.getenv('TRANSCRIPT_ANALYZER_RAW_OUTPUT_MAX_CHARS'):
            try:
                config.output.raw_output_max_chars = int(os.getenv('TRANSCRIPT_ANALYZER_RAW_OUTPUT_MAX_CHARS'))
            except Exception:
                pass

        return config
    
    @classmethod
    def from_yaml(cls, path: Path) -> 'AppConfig':
        """Create configuration from YAML file."""
        import yaml
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(**data)
    
    def get_analyzer_config(self, analyzer_name: str) -> AnalyzerConfig:
        """Get configuration for a specific analyzer."""
        if analyzer_name in self.analyzers:
            return self.analyzers[analyzer_name]
        return AnalyzerConfig()
    
    def get_prompt_path(self, analyzer_name: str) -> Path:
        """Get the prompt file path for an analyzer."""
        # Map analyzer names to prompt files
        prompt_mapping = {
            'say_means': 'prompts/stage a transcript analyses/1 say-means.md',
            'perspective_perception': 'prompts/stage a transcript analyses/2 perspective-perception.md',
            'premises_assertions': 'prompts/stage a transcript analyses/3 premsises-assertions.md',
            'postulate_theorem': 'prompts/stage a transcript analyses/4 postulate-theorem.md',
            'competing_hypotheses': 'prompts/stage b results analyses/1 analysis of competing hyptheses.md',
            'first_principles': 'prompts/stage b results analyses/2 first principles.md',
            'determining_factors': 'prompts/stage b results analyses/3 determining factors.md',
            'patentability': 'prompts/stage b results analyses/4 patentability.md',
            'meeting_notes': 'prompts/final output stage/2 meeting notes.md',
            'composite_note': 'prompts/final output stage/1 composite note.md',
        }
        
        if analyzer_name in prompt_mapping:
            return Path(prompt_mapping[analyzer_name])
        
        # Check if custom prompt path is configured
        analyzer_config = self.get_analyzer_config(analyzer_name)
        if analyzer_config.prompt_file:
            return analyzer_config.prompt_file
        
        raise ValueError(f"No prompt file configured for analyzer: {analyzer_name}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'llm': self.llm.dict(),
            'processing': self.processing.dict(),
            'output': {
                **self.output.dict(),
                'directory': str(self.output.directory)
            },
            'obsidian': self.obsidian.dict(),
            'web': {
                **self.web.dict(),
                'upload_folder': str(self.web.upload_folder)
            },
            'notifications': self.notifications.dict(),
            'analyzers': {
                name: config.dict() 
                for name, config in self.analyzers.items()
            },
            'stage_a_analyzers': self.stage_a_analyzers,
            'stage_b_analyzers': self.stage_b_analyzers,
            'final_stage_analyzers': self.final_stage_analyzers
        }


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = AppConfig.from_env()
        # Discover prompt files as analyzers at boot, then merge registry
        try:
            from src.analyzers.registry import (
                merge_registry_into_config,
                rebuild_registry_from_prompts,
            )
            # Rebuild registry from filesystem on boot for determinism
            try:
                _ = rebuild_registry_from_prompts()
            except Exception:
                pass
            merge_registry_into_config(_config)
        except Exception:
            # Non-fatal: proceed with built-ins only if registry is missing/invalid
            pass
    return _config


def set_config(config: AppConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config


def reset_config() -> None:
    """Reset the global configuration instance."""
    global _config
    _config = None
