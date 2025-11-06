"""Qwen3-max Streaming API Client.

This module provides a client for interacting with the Qwen3-max API using
the OpenAI-compatible HTTP interface (DashScope compatible-mode) with
Server-Sent Events (SSE) streaming, without relying on the OpenAI SDK.
"""

import os
import json
import re
from typing import Iterator, Dict, Any, List, Optional, Callable
import requests
from loguru import logger


class QwenStreamingClient:
    """
    Qwen3-max Streaming API Client
    
    Uses OpenAI-compatible SDK with DashScope endpoints.
    Protocol: Server-Sent Events (SSE)
    Documentation: https://help.aliyun.com/zh/model-studio/stream
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: Optional[str] = None
    ):
        """
        Initialize Qwen streaming client.
        
        Args:
            api_key: API key (defaults to DASHSCOPE_API_KEY env var or config.yaml)
            base_url: Base URL for API (Beijing or Singapore region)
            model: Model name (defaults to config.yaml qwen.model or "qwen3-max")
        """
        # API key: from parameter, env var, or config
        self.api_key = api_key
        if not self.api_key:
            # Try environment variables first
            self.api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        if not self.api_key:
            # Fallback to config.yaml
            try:
                from core.config import Config
                config = Config()
                self.api_key = config.get("qwen.api_key")
            except Exception:
                pass  # Config may not be available
        if not self.api_key:
            raise ValueError(
                "API key must be provided or set in one of:\n"
                "  - DASHSCOPE_API_KEY/QWEN_API_KEY env var\n"
                "  - config.yaml (qwen.api_key)\n"
                "  - api_key parameter"
            )
        
        self.base_url = base_url
        
        # Model: from parameter or config.yaml (default: "qwen3-max")
        if model is None:
            try:
                from core.config import Config
                config = Config()
                self.model = config.get("qwen.model", "qwen3-max")
            except Exception:
                self.model = "qwen3-max"  # Fallback default
        else:
            self.model = model
        
        # HTTP session for streaming requests
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        
        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        
        logger.info(f"Initialized QwenStreamingClient with model: {self.model}")
    
    def stream_completion(
        self, 
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream_options: Optional[Dict] = None,
        callback: Optional[Callable[[str], None]] = None,
        enable_thinking: bool = False
    ) -> Iterator[str]:
        """
        Stream completion from Qwen API using SSE protocol.
        
        Args:
            messages: List of message dicts [{"role": "user", "content": "..."}]
            model: Model name (overrides default)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens (32K limit for qwen3-max)
            stream_options: Optional stream options (e.g., {"include_usage": True})
            callback: Optional callback for each token chunk
            enable_thinking: Enable thinking mode (returns reasoning_content)
            
        Yields:
            String tokens from the stream
        """
        model = model or self.model
        stream_options = stream_options or {"include_usage": True}

        # Build request payload for DashScope-compatible endpoint
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
        }

        # Respect 32K cap
        if max_tokens:
            payload["max_tokens"] = min(max_tokens, 32000)

        # Include stream options if provided
        if stream_options:
            payload["stream_options"] = stream_options

        # Thinking mode is supported via extra_body on DashScope compatible API
        if enable_thinking:
            payload["extra_body"] = {"enable_thinking": True}

        url = self.base_url.rstrip("/") + "/chat/completions"
        logger.debug(f"Starting streaming request to {url} ({model})")

        try:
            with self.session.post(url, data=json.dumps(payload), stream=True, timeout=300) as resp:
                if resp.status_code != 200:
                    # Try to read any JSON error
                    try:
                        err = resp.json()
                    except Exception:
                        err = {"message": resp.text}
                    raise Exception(f"HTTP {resp.status_code}: {err}")

                # SSE stream: lines usually start with 'data: '
                for raw_line in resp.iter_lines(decode_unicode=True):
                    if not raw_line:
                        continue
                    line = raw_line.strip()
                    if not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()

                    if data_str == "[DONE]":
                        break

                    # Parse event JSON
                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        # If partial JSON appears, skip until complete
                        continue

                    # Usage info can appear at the tail event in some implementations
                    usage = event.get("usage") or {}
                    if usage:
                        # Fallback keys for different providers
                        self.total_input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
                        self.total_output_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
                        logger.debug(
                            f"Token usage - Input: {self.total_input_tokens}, "
                            f"Output: {self.total_output_tokens}, "
                            f"Total: {self.total_input_tokens + self.total_output_tokens}"
                        )

                    # Extract delta from choices[0].delta
                    choices = event.get("choices") or []
                    if not choices:
                        continue
                    delta = (choices[0] or {}).get("delta", {})

                    # Thinking first when enabled
                    if enable_thinking and delta.get("reasoning_content"):
                        piece = delta.get("reasoning_content") or ""
                        if piece:
                            if callback:
                                callback(piece)
                            yield piece

                    # Then normal content
                    piece = delta.get("content") or ""
                    if piece:
                        if callback:
                            callback(piece)
                        yield piece

        except Exception as e:
            logger.error(f"Streaming API error: {str(e)}")
            raise Exception(f"Streaming API error: {str(e)}")
    
    def stream_and_collect(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> tuple[str, Dict]:
        """
        Stream completion and collect full response.
        
        Returns:
            (full_response, usage_info)
        """
        content_parts = []
        usage_info = {}
        
        for chunk in self.stream_completion(messages, **kwargs):
            content_parts.append(chunk)
        
        full_response = "".join(content_parts)
        usage_info = {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens
        }
        
        return full_response, usage_info
    
    def parse_json_from_stream(
        self, 
        stream: Iterator[str],
        max_wait_time: float = 60.0
    ) -> Dict[str, Any]:
        """
        Parse complete JSON from streaming output.
        
        Handles partial JSON during streaming by buffering until complete.
        Attempts to find JSON object boundaries.
        
        Args:
            stream: Iterator of string chunks
            max_wait_time: Maximum time to wait for complete JSON (seconds)
            
        Returns:
            Parsed JSON dictionary
            
        Raises:
            ValueError: If valid JSON cannot be parsed
        """
        buffer = ""
        json_started = False
        brace_count = 0
        
        # Collect all chunks
        for chunk in stream:
            buffer += chunk
            
            # Try to find JSON boundaries
            # Look for first '{' as JSON start
            if not json_started and '{' in buffer:
                start_idx = buffer.index('{')
                buffer = buffer[start_idx:]
                json_started = True
                brace_count = 0
            
            # Count braces to detect complete JSON
            if json_started:
                for char in buffer:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                
                # Try parsing when braces are balanced
                if brace_count == 0:
                    try:
                        return json.loads(buffer)
                    except json.JSONDecodeError:
                        # Continue collecting if parsing fails
                        continue
        
        # Final attempt: try to extract JSON from buffer
        # Look for JSON object pattern
        json_match = re.search(r'\{.*\}', buffer, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Try parsing entire buffer
        try:
            return json.loads(buffer)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Could not parse JSON from stream. Buffer preview: {buffer[:200]}... "
                f"Error: {str(e)}"
            )
    
    def get_usage_info(self) -> Dict[str, int]:
        """Get current token usage information."""
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens
        }

