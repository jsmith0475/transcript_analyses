"""
LLM client for OpenAI API integration with GPT-5 support.
"""

import os
import json
import asyncio
import time
import math
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
try:
    import tiktoken  # type: ignore
except Exception:
    tiktoken = None
from openai import AsyncOpenAI, OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from loguru import logger

from src.models import TokenUsage
from src.config import LLMConfig, get_config
from flask import has_request_context, session  # type: ignore


class LLMClient:
    """Client for interacting with OpenAI's API."""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize the LLM client."""
        self.config = config or get_config().llm
        self.client = OpenAI(api_key=self.config.api_key)
        self.async_client = AsyncOpenAI(api_key=self.config.api_key)
        
        # Initialize tokenizer (optional)
        self.encoding = None
        if tiktoken:
            try:
                if self.config.model.startswith('gpt-5'):
                    # GPT-5 uses the same tokenizer as GPT-4
                    self.encoding = tiktoken.encoding_for_model('gpt-4')
                else:
                    self.encoding = tiktoken.encoding_for_model(self.config.model)
            except Exception:
                try:
                    self.encoding = tiktoken.get_encoding('cl100k_base')
                except Exception:
                    self.encoding = None
        
        logger.info(f"Initialized LLM client with model: {self.config.model}")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens; fall back to heuristic if tokenizer unavailable."""
        if getattr(self, "encoding", None):
            try:
                return len(self.encoding.encode(text))
            except Exception:
                pass
        # Heuristic: ~4 chars/token
        return max(1, math.ceil(len(text) / 4))
    
    def estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Estimate token count for a list of messages."""
        # Rough estimation including message overhead
        token_count = 0
        for message in messages:
            token_count += 4  # Message overhead
            for key, value in message.items():
                token_count += self.count_tokens(str(value))
        token_count += 2  # Reply overhead
        return token_count
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((Exception,))
    )
    async def _make_api_call_async(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Make an async API call with retry logic."""
        try:
            # Merge kwargs with config
            call_params = {
                'model': kwargs.get('model', self.config.model),
                'messages': messages,
                'temperature': kwargs.get('temperature', self.config.temperature),
            }
            
            # Use max_tokens consistently; OpenAI v1 chat.completions expects 'max_tokens'
            call_params['max_tokens'] = kwargs.get('max_tokens', self.config.max_tokens)
            
            # Standard chat completions for all supported models
            response = await self.async_client.chat.completions.create(**call_params)
            
            return response
            
        except Exception as e:
            logger.error(f"API call failed: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((Exception,))
    )
    def _make_api_call_sync(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Make a synchronous API call with retry logic."""
        try:
            # Merge kwargs with config
            call_params = {
                'model': kwargs.get('model', self.config.model),
                'messages': messages,
                'temperature': kwargs.get('temperature', self.config.temperature),
            }
            
            # Use max_tokens consistently; OpenAI v1 chat.completions expects 'max_tokens'
            call_params['max_tokens'] = kwargs.get('max_tokens', self.config.max_tokens)
            
            # Standard chat completions for all supported models
            response = self.client.chat.completions.create(**call_params)
            
            return response
            
        except Exception as e:
            logger.error(f"API call failed: {str(e)}")
            raise
     
    async def _make_responses_call_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """Call Responses API for GPT-5 asynchronously."""
        try:
            input_text = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

            call_params: Dict[str, Any] = {
                "model": kwargs.get("model", self.config.model),
                "input": input_text,
            }

            # Reasoning/text parameters (allow both dict and simple overrides)
            reasoning = kwargs.get("reasoning")
            if not reasoning:
                effort = kwargs.get("reasoning_effort", getattr(self.config, "reasoning_effort", "medium"))
                reasoning = {"effort": effort}
            call_params["reasoning"] = reasoning

            text_param = kwargs.get("text")
            if not text_param:
                verbosity = kwargs.get("text_verbosity", getattr(self.config, "text_verbosity", "medium"))
                text_param = {"verbosity": verbosity}
            call_params["text"] = text_param

            # Optional passthroughs
            for k in ("previous_response_id", "tools", "tool_choice"):
                if k in kwargs and kwargs[k] is not None:
                    call_params[k] = kwargs[k]

            response = await self.async_client.responses.create(**call_params)
            return response
        except Exception as e:
            logger.error(f"Responses API call failed: {str(e)}")
            raise

    def _make_responses_call_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """Call Responses API for GPT-5 synchronously."""
        try:
            input_text = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

            call_params: Dict[str, Any] = {
                "model": kwargs.get("model", self.config.model),
                "input": input_text,
            }

            # Reasoning/text parameters (allow both dict and simple overrides)
            reasoning = kwargs.get("reasoning")
            if not reasoning:
                effort = kwargs.get("reasoning_effort", getattr(self.config, "reasoning_effort", "medium"))
                reasoning = {"effort": effort}
            call_params["reasoning"] = reasoning

            text_param = kwargs.get("text")
            if not text_param:
                verbosity = kwargs.get("text_verbosity", getattr(self.config, "text_verbosity", "medium"))
                text_param = {"verbosity": verbosity}
            call_params["text"] = text_param

            # Optional passthroughs
            for k in ("previous_response_id", "tools", "tool_choice"):
                if k in kwargs and kwargs[k] is not None:
                    call_params[k] = kwargs[k]

            response = self.client.responses.create(**call_params)
            return response
        except Exception as e:
            logger.error(f"Responses API call failed: {str(e)}")
            raise

    async def complete_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> tuple[str, TokenUsage]:
        """
        Generate a completion asynchronously.
        
        Returns:
            Tuple of (response_text, token_usage)
        """
        start_time = time.time()
        
        model_for_call = kwargs.get('model', self.config.model)
        if model_for_call.startswith('gpt-5'):
            # Responses API path
            input_text = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

            # Estimate prompt tokens for telemetry
            prompt_tokens = self.count_tokens(input_text)

            # Check token limits (heuristic)
            if prompt_tokens > self.config.max_tokens * 0.75:
                logger.warning(f"Prompt uses {prompt_tokens} tokens, approaching limit of {self.config.max_tokens}")

            response = await self._make_responses_call_async(prompt, system_prompt, **kwargs)

            # Extract response text robustly
            response_text = None
            try:
                response_text = getattr(response, "output_text", None)
            except Exception:
                response_text = None
            if not response_text:
                try:
                    if hasattr(response, "choices") and response.choices:
                        response_text = response.choices[0].message.content
                    else:
                        response_text = str(response)
                except Exception:
                    response_text = str(response)

            # Token usage
            if hasattr(response, 'usage'):
                token_usage = TokenUsage(
                    prompt_tokens=getattr(response.usage, 'prompt_tokens', prompt_tokens),
                    completion_tokens=getattr(response.usage, 'completion_tokens', self.count_tokens(response_text)),
                    total_tokens=getattr(response.usage, 'total_tokens', prompt_tokens + self.count_tokens(response_text))
                )
            else:
                completion_tokens = self.count_tokens(response_text)
                token_usage = TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens
                )
        else:
            # Chat Completions path
            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Estimate prompt tokens
            prompt_tokens = self.estimate_tokens(messages)
            
            # Check token limits
            if prompt_tokens > self.config.max_tokens * 0.75:
                logger.warning(f"Prompt uses {prompt_tokens} tokens, approaching limit of {self.config.max_tokens}")
            
            # Make API call
            response = await self._make_api_call_async(messages, **kwargs)
            
            # Extract response
            response_text = response.choices[0].message.content
            
            # Calculate token usage
            if hasattr(response, 'usage'):
                token_usage = TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens
                )
            else:
                # Estimate if usage not provided
                completion_tokens = self.count_tokens(response_text)
                token_usage = TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens
                )
        
        # Echo the max_tokens limit actually used to the TokenUsage for telemetry/UI
        try:
            token_usage.max_tokens = kwargs.get('max_tokens', self.config.max_tokens)
        except Exception:
            pass

        elapsed_time = time.time() - start_time
        logger.debug(f"API call completed in {elapsed_time:.2f}s, used {token_usage.total_tokens} tokens")
        
        return response_text, token_usage
    
    def complete_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> tuple[str, TokenUsage]:
        """
        Generate a completion synchronously.
        
        Returns:
            Tuple of (response_text, token_usage)
        """
        start_time = time.time()
        
        model_for_call = kwargs.get('model', self.config.model)
        if model_for_call.startswith('gpt-5'):
            # Responses API path
            input_text = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

            # Estimate prompt tokens for telemetry
            prompt_tokens = self.count_tokens(input_text)

            # Check token limits (heuristic)
            if prompt_tokens > self.config.max_tokens * 0.75:
                logger.warning(f"Prompt uses {prompt_tokens} tokens, approaching limit of {self.config.max_tokens}")

            response = self._make_responses_call_sync(prompt, system_prompt, **kwargs)

            # Extract response text robustly
            response_text = None
            try:
                response_text = getattr(response, "output_text", None)
            except Exception:
                response_text = None
            if not response_text:
                try:
                    if hasattr(response, "choices") and response.choices:
                        response_text = response.choices[0].message.content
                    else:
                        response_text = str(response)
                except Exception:
                    response_text = str(response)

            # Token usage
            if hasattr(response, 'usage'):
                token_usage = TokenUsage(
                    prompt_tokens=getattr(response.usage, 'prompt_tokens', prompt_tokens),
                    completion_tokens=getattr(response.usage, 'completion_tokens', self.count_tokens(response_text)),
                    total_tokens=getattr(response.usage, 'total_tokens', prompt_tokens + self.count_tokens(response_text))
                )
            else:
                completion_tokens = self.count_tokens(response_text)
                token_usage = TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens
                )
        else:
            # Chat Completions path
            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Estimate prompt tokens
            prompt_tokens = self.estimate_tokens(messages)
            
            # Check token limits
            if prompt_tokens > self.config.max_tokens * 0.75:
                logger.warning(f"Prompt uses {prompt_tokens} tokens, approaching limit of {self.config.max_tokens}")
            
            # Make API call
            response = self._make_api_call_sync(messages, **kwargs)
            
            # Extract response
            response_text = response.choices[0].message.content
            
            # Calculate token usage
            if hasattr(response, 'usage'):
                token_usage = TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens
                )
            else:
                # Estimate if usage not provided
                completion_tokens = self.count_tokens(response_text)
                token_usage = TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens
                )
        
        # Echo the max_tokens limit actually used to the TokenUsage for telemetry/UI
        try:
            token_usage.max_tokens = kwargs.get('max_tokens', self.config.max_tokens)
        except Exception:
            pass

        elapsed_time = time.time() - start_time
        logger.debug(f"API call completed in {elapsed_time:.2f}s, used {token_usage.total_tokens} tokens")
        
        return response_text, token_usage
    
    async def complete_with_structured_output(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> tuple[Dict[str, Any], TokenUsage]:
        """
        Generate a completion with structured output.
        
        Returns:
            Tuple of (parsed_response, token_usage)
        """
        # Add instruction for structured output
        if output_schema:
            prompt += f"\n\nPlease provide your response in the following JSON format:\n{json.dumps(output_schema, indent=2)}"
        
        response_text, token_usage = await self.complete_async(prompt, system_prompt, **kwargs)
        
        # Try to parse JSON from response
        try:
            # Look for JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                parsed_response = json.loads(json_match.group())
            else:
                # Fallback to treating entire response as JSON
                parsed_response = json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse structured output, returning raw text")
            parsed_response = {"raw_output": response_text}
        
        return parsed_response, token_usage


class CachedLLMClient(LLMClient):
    """LLM client with caching support."""
    
    def __init__(self, config: Optional[LLMConfig] = None, cache_dir: str = "./cache"):
        """Initialize the cached LLM client."""
        super().__init__(config)
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.cache = {}
        self._load_cache()
    
    def _get_cache_key(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate a cache key for a request."""
        import hashlib
        
        # Only cache if temperature is 0 (deterministic)
        if kwargs.get('temperature', self.config.temperature) != 0:
            return None
        
        cache_data = {
            'model': kwargs.get('model', self.config.model),
            'prompt': prompt,
            'system_prompt': system_prompt,
            'max_tokens': kwargs.get('max_tokens', self.config.max_tokens),
            'temperature': 0
        }
        
        if self.config.model.startswith('gpt-5'):
            cache_data['reasoning_effort'] = kwargs.get('reasoning_effort', self.config.reasoning_effort)
            cache_data['text_verbosity'] = kwargs.get('text_verbosity', self.config.text_verbosity)
        
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()
    
    def _load_cache(self):
        """Load cache from disk."""
        cache_file = os.path.join(self.cache_dir, 'llm_cache.json')
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} cached responses")
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")
                self.cache = {}
    
    def _save_cache(self):
        """Save cache to disk."""
        cache_file = os.path.join(self.cache_dir, 'llm_cache.json')
        try:
            with open(cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    async def complete_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> tuple[str, TokenUsage]:
        """Generate a completion with caching."""
        # Check cache
        cache_key = self._get_cache_key(prompt, system_prompt, **kwargs)
        if cache_key and cache_key in self.cache:
            logger.debug("Cache hit for LLM request")
            cached_response = self.cache[cache_key]
            return cached_response['response'], TokenUsage(**cached_response['token_usage'])
        
        # Make API call
        response_text, token_usage = await super().complete_async(prompt, system_prompt, **kwargs)
        
        # Cache response if deterministic
        if cache_key:
            self.cache[cache_key] = {
                'response': response_text,
                'token_usage': token_usage.dict(),
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache()
        
        return response_text, token_usage
    
    def complete_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> tuple[str, TokenUsage]:
        """Generate a completion with caching."""
        # Check cache
        cache_key = self._get_cache_key(prompt, system_prompt, **kwargs)
        if cache_key and cache_key in self.cache:
            logger.debug("Cache hit for LLM request")
            cached_response = self.cache[cache_key]
            return cached_response['response'], TokenUsage(**cached_response['token_usage'])
        
        # Make API call
        response_text, token_usage = super().complete_sync(prompt, system_prompt, **kwargs)
        
        # Cache response if deterministic
        if cache_key:
            self.cache[cache_key] = {
                'response': response_text,
                'token_usage': token_usage.dict(),
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache()
        
        return response_text, token_usage


# Global client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client(use_cache: bool = True) -> LLMClient:
    """Get the global LLM client instance."""
    # If we are in a request context and the user supplied an API key override,
    # return a non-cached client bound to that key so different users don't share keys.
    try:
        if has_request_context():
            user_key = session.get('user_api_key')
            if isinstance(user_key, str):
                uk = user_key.strip()
                # Minimal validation: OpenAI keys start with 'sk-' and are reasonably long
                if len(uk) >= 20 and uk.startswith('sk-'):
                    base = get_config().llm
                    cfg = LLMConfig(**base.dict())
                    cfg.api_key = uk
                    # Avoid caching per-user clients globally
                    return LLMClient(cfg)
                # If invalid/stale key is present, ignore and fall back to server key
    except Exception:
        pass

    global _llm_client
    if _llm_client is None:
        config = get_config()
        if use_cache and config.processing.cache_enabled:
            _llm_client = CachedLLMClient(config.llm)
        else:
            _llm_client = LLMClient(config.llm)
    return _llm_client


def reset_llm_client():
    """Reset the global LLM client instance."""
    global _llm_client
    _llm_client = None
