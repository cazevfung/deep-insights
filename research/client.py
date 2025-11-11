"""Qwen3-max Streaming API Client.

This module provides a client for interacting with the Qwen3-max API using
the OpenAI-compatible HTTP interface (DashScope compatible-mode) with
Server-Sent Events (SSE) streaming, without relying on the OpenAI SDK.
"""

import os
import json
import re
import time
from typing import Iterator, Dict, Any, List, Optional, Callable, Tuple

import requests
from loguru import logger


class QwenAPIError(Exception):
    """Base exception for Qwen client failures."""

    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        payload: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.status = status
        self.payload = payload or {}

        error_block = {}
        if isinstance(self.payload, dict):
            error_block = self.payload.get("error") or {}

        self.error_code = error_block.get("code")
        self.request_id = (
            self.payload.get("request_id")
            or error_block.get("request_id")
            or self.payload.get("id")
            or error_block.get("id")
        )
        self.message = message


class DataInspectionFailedError(QwenAPIError):
    """Raised when DashScope blocks the request during safety inspection."""


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
        model: Optional[str] = None,
    ):
        """
        Initialize Qwen streaming client.

        Args:
            api_key: API key (defaults to DASHSCOPE_API_KEY env var or config.yaml)
            base_url: Base URL for API (Beijing or Singapore region)
            model: Model name (defaults to config.yaml qwen.model or "qwen3-max")
        """
        self.base_url = base_url
        self._config = None
        try:
            from core.config import Config

            self._config = Config()
        except Exception:
            self._config = None

        self.api_key = (
            api_key
            or os.getenv("DASHSCOPE_API_KEY")
            or os.getenv("QWEN_API_KEY")
            or self._get_config_value("qwen.api_key")
        )

        if not self.api_key:
            raise ValueError(
                "API key must be provided or set in one of:\n"
                "  - DASHSCOPE_API_KEY/QWEN_API_KEY env var\n"
                "  - config.yaml (qwen.api_key)\n"
                "  - api_key parameter"
            )

        # Model: from parameter or config.yaml (default: "qwen3-max")
        self.model = model or self._get_config_value("qwen.model", "qwen3-max")

        # HTTP session for streaming requests
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

        # Token tracking and telemetry state
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.last_call_metadata: Dict[str, Any] = {}

        # Safety / retry configuration
        self._retry_delay_seconds = float(
            self._get_config_value("llm.fallback.retry_delay_seconds", 2.0) or 2.0
        )
        self._max_prompt_chars = int(
            self._get_config_value("llm.fallback.max_prompt_chars", 20000) or 20000
        )
        self._safety_patterns = [
            re.compile(r"(?i)\b(suicide|self\-?harm|kill yourself|murder)\b"),
            re.compile(r"(?i)\b(rape|sexual\s+assault|porn(?:ography)?)\b"),
            re.compile(r"(?i)\b(extremist|terroris[mt])\b"),
        ]
        self._keyword_masks = [
            "色情",
            "暴力",
            "自杀",
            "袭击",
            "恐怖",
        ]

        # Optional fallback provider configuration
        fallback_config: Dict[str, Any] = self._get_config_value("llm.fallback", {}) or {}
        self._fallback_enabled = bool(fallback_config.get("enabled", False))
        self._fallback_provider: Optional[str] = fallback_config.get("provider", "openai")
        self._fallback_model: Optional[str] = fallback_config.get("model", "gpt-4o-mini")
        self._fallback_api_key_env: Optional[str] = fallback_config.get("api_key_env", "OPENAI_API_KEY")
        self._fallback_api_key_value: Optional[str] = fallback_config.get("api_key")
        self._fallback_base_url: Optional[str] = fallback_config.get("base_url")
        self._fallback_timeout: int = int(fallback_config.get("timeout_seconds", 60) or 60)

        # Clamp retry delay to sane bounds
        if self._retry_delay_seconds < 0.5:
            self._retry_delay_seconds = 0.5

        if self._fallback_enabled:
            logger.info(
                "Fallback provider enabled: %s (%s)",
                self._fallback_provider,
                self._fallback_model,
            )
        else:
            logger.info("Fallback provider disabled")

        logger.info("Initialized QwenStreamingClient with model: %s", self.model)

    def stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream_options: Optional[Dict] = None,
        callback: Optional[Callable[[str], None]] = None,
        enable_thinking: bool = False,
    ) -> Iterator[str]:
        """
        Stream completion from Qwen API using SSE protocol with safety fallbacks.

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
        target_model = model or self.model
        stream_options = stream_options or {"include_usage": True}

        self._reset_usage_counters()
        self.last_call_metadata = {
            "provider": "qwen",
            "fallback_used": False,
            "sanitized_retry": False,
            "attempts": [],
        }

        sanitized_attempted = False
        sanitized_meta: Dict[str, Any] = {}
        fallback_ready = False

        retry_messages = [dict(msg) for msg in messages]

        while True:
            attempt_index = len(self.last_call_metadata["attempts"]) + 1
            attempt_record = {
                "attempt": attempt_index,
                "provider": self._fallback_provider if fallback_ready else "qwen",
                "sanitized": sanitized_attempted and not fallback_ready,
            }
            self.last_call_metadata["attempts"].append(attempt_record)
            current_attempt = self.last_call_metadata["attempts"][-1]

            try:
                if fallback_ready:
                    for chunk in self._stream_via_fallback(
                        retry_messages,
                        model=target_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        callback=callback,
                    ):
                        yield chunk

                    self.last_call_metadata.update(
                        {
                            "fallback_used": True,
                            "fallback_provider": self._fallback_provider,
                            "fallback_model": self._fallback_model,
                            "fallback_reason": current_attempt.get("reason"),
                        }
                    )
                    return

                for chunk in self._iter_qwen_stream(
                    retry_messages,
                    model=target_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream_options=stream_options,
                    callback=callback,
                    enable_thinking=enable_thinking,
                ):
                    yield chunk

                if sanitized_attempted:
                    self.last_call_metadata["sanitized_retry"] = True
                    self.last_call_metadata["sanitized_details"] = sanitized_meta
                return

            except DataInspectionFailedError as err:
                logger.warning(
                    "Qwen data inspection rejected the request (request_id=%s, reason=%s)",
                    err.request_id,
                    err.message,
                )
                current_attempt["error"] = err.error_code or "data_inspection_failed"

                self.last_call_metadata.update(
                    {
                        "error_code": err.error_code,
                        "request_id": err.request_id,
                        "error_message": err.message,
                    }
                )

                if not sanitized_attempted:
                    retry_messages, sanitized_meta = self._sanitize_messages_for_retry(messages)
                    sanitized_attempted = True
                    self.last_call_metadata["sanitized_retry"] = True
                    self.last_call_metadata["sanitized_details"] = sanitized_meta
                    current_attempt["action"] = "sanitized_retry"
                    logger.info(
                        "Retrying Qwen request with sanitized prompt (redactions=%s, truncated=%s)",
                        sanitized_meta.get("redacted_segments", 0),
                        sanitized_meta.get("truncated", False),
                    )
                    time.sleep(self._retry_delay_seconds)
                    continue

                if self._fallback_enabled and self._can_use_fallback():
                    fallback_ready = True
                    current_attempt["action"] = "fallback"
                    current_attempt["reason"] = "data_inspection_failed"
                    logger.warning(
                        "Qwen data inspection failed twice; switching to fallback provider %s",
                        self._fallback_provider,
                    )
                    continue

                logger.error("Fallback unavailable or already attempted; re-raising error.")
                raise

            except QwenAPIError as err:
                logger.error(
                    "Qwen API error (status=%s code=%s request_id=%s): %s",
                    err.status,
                    err.error_code,
                    err.request_id,
                    err.message,
                )
                current_attempt["error"] = err.error_code or "http_error"

                self.last_call_metadata.update(
                    {
                        "error_code": err.error_code,
                        "request_id": err.request_id,
                        "error_message": err.message,
                    }
                )

                if self._fallback_enabled and self._can_use_fallback():
                    fallback_ready = True
                    current_attempt["action"] = "fallback"
                    current_attempt["reason"] = err.error_code or "http_error"
                    logger.warning(
                        "Switching to fallback provider %s due to Qwen API error",
                        self._fallback_provider,
                    )
                    continue

                raise

            except Exception as exc:
                logger.error("Streaming API error: %s", exc)
                current_attempt["error"] = "exception"

                if self._fallback_enabled and self._can_use_fallback():
                    fallback_ready = True
                    current_attempt["action"] = "fallback"
                    current_attempt["reason"] = "unhandled_exception"
                    logger.warning(
                        "Switching to fallback provider %s due to unexpected exception",
                        self._fallback_provider,
                    )
                    continue

                raise QwenAPIError(f"Streaming API error: {exc}") from exc

    def stream_and_collect(
        self,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> Tuple[str, Dict]:
        """
        Stream completion and collect full response.

        Returns:
            (full_response, usage_info)
        """
        content_parts: List[str] = []

        for chunk in self.stream_completion(messages, **kwargs):
            content_parts.append(chunk)

        full_response = "".join(content_parts)
        usage_info = {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
        }

        return full_response, usage_info

    def parse_json_from_stream(
        self,
        stream: Iterator[str],
        max_wait_time: float = 60.0,
    ) -> Dict[str, Any]:
        """
        Parse complete JSON from streaming output.

        Handles partial JSON during streaming by buffering until complete.
        Attempts to find JSON object boundaries.
        """
        buffer = ""
        json_started = False
        brace_count = 0

        # Collect all chunks
        for chunk in stream:
            buffer += chunk

            # Try to find JSON boundaries
            if not json_started and "{" in buffer:
                start_idx = buffer.index("{")
                buffer = buffer[start_idx:]
                json_started = True
                brace_count = 0

            # Count braces to detect complete JSON
            if json_started:
                for char in buffer:
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1

                # Try parsing when braces are balanced
                if brace_count == 0:
                    try:
                        return json.loads(buffer)
                    except json.JSONDecodeError:
                        continue

        # Final attempt: try to extract JSON from buffer
        json_match = re.search(r"\{.*\}", buffer, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Try parsing entire buffer
        try:
            return json.loads(buffer)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Could not parse JSON from stream. Buffer preview: {buffer[:200]}... "
                f"Error: {exc}"
            )

    def get_usage_info(self) -> Dict[str, int]:
        """Get current token usage information."""
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_config_value(self, key_path: str, default: Optional[Any] = None) -> Any:
        if self._config is None:
            return default
        try:
            return self._config.get(key_path, default)
        except Exception:
            return default

    def _reset_usage_counters(self) -> None:
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def _can_use_fallback(self) -> bool:
        if not self._fallback_enabled:
            return False
        provider = (self._fallback_provider or "").lower()
        if provider == "openai":
            return bool(self._resolve_fallback_api_key())
        logger.warning("Fallback provider '%s' is not supported.", provider)
        return False

    def _resolve_fallback_api_key(self) -> Optional[str]:
        if self._fallback_api_key_value:
            return self._fallback_api_key_value
        if self._fallback_api_key_env:
            key = os.getenv(self._fallback_api_key_env)
            if key:
                return key
        return os.getenv("OPENAI_API_KEY")

    def _sanitize_messages_for_retry(
        self,
        messages: List[Dict[str, str]],
    ) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        sanitized_messages: List[Dict[str, str]] = []
        redacted_segments = 0
        truncated_any = False

        for msg in messages:
            content = msg.get("content", "")
            sanitized_content, redactions, truncated = self._apply_safety_filters(content)
            redacted_segments += redactions
            truncated_any = truncated_any or truncated
            sanitized_messages.append(
                {
                    **msg,
                    "content": sanitized_content,
                }
            )

        sanitized_messages = self._inject_safety_preamble(sanitized_messages)

        metadata = {
            "redacted_segments": redacted_segments,
            "truncated": truncated_any,
        }
        return sanitized_messages, metadata

    def _apply_safety_filters(
        self,
        content: str,
    ) -> Tuple[str, int, bool]:
        if not content:
            return content, 0, False

        redactions = 0
        sanitized = content

        for pattern in self._safety_patterns:
            sanitized, count = pattern.subn("[敏感词已省略]", sanitized)
            redactions += count

        for keyword in self._keyword_masks:
            if keyword in sanitized:
                sanitized = sanitized.replace(keyword, f"{keyword[0]}***")
                redactions += 1

        sanitized, url_count = re.subn(r"https?://\S+", "[链接已替换]", sanitized)
        redactions += url_count

        truncated = False
        if len(sanitized) > self._max_prompt_chars:
            sanitized = (
                sanitized[: self._max_prompt_chars]
                + "\n\n[内容已截断以通过安全审查]"
            )
            truncated = True

        return sanitized, redactions, truncated

    def _inject_safety_preamble(
        self,
        messages: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        preamble = (
            "系统提示：输入材料可能包含引用的敏感或不当用语，这些仅用于分析。"
            "请在回答时聚焦事实与结论，避免逐字复述敏感片段，并保持专业、客观的语气。"
        )
        preamble_message = {"role": "system", "content": preamble}

        for existing in messages:
            if existing.get("content") == preamble:
                return messages

        if messages and messages[0].get("role") == "system":
            return [messages[0], preamble_message, *messages[1:]]

        return [preamble_message, *messages]

    def _iter_qwen_stream(
        self,
        messages: List[Dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        stream_options: Optional[Dict[str, Any]],
        callback: Optional[Callable[[str], None]],
        enable_thinking: bool,
    ) -> Iterator[str]:
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = min(max_tokens, 32000)

        if stream_options:
            payload["stream_options"] = stream_options

        if enable_thinking:
            payload["extra_body"] = {"enable_thinking": True}

        url = self.base_url.rstrip("/") + "/chat/completions"
        logger.debug("Starting streaming request to %s (%s)", url, model)

        with self.session.post(url, data=json.dumps(payload), stream=True, timeout=300) as resp:
            if resp.status_code != 200:
                try:
                    err_payload = resp.json()
                except Exception:
                    err_payload = {"message": resp.text}

                error_message = (
                    (err_payload.get("error") or {}).get("message")
                    or err_payload.get("message")
                    or f"HTTP {resp.status_code}"
                )

                error_code = (err_payload.get("error") or {}).get("code")

                if error_code == "data_inspection_failed":
                    raise DataInspectionFailedError(
                        f"HTTP {resp.status_code}: {error_message}",
                        status=resp.status_code,
                        payload=err_payload,
                    )

                raise QwenAPIError(
                    f"HTTP {resp.status_code}: {error_message}",
                    status=resp.status_code,
                    payload=err_payload,
                )

            for raw_line in resp.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                line = raw_line.strip()
                if not line.startswith("data:"):
                    continue
                data_str = line[len("data:") :].strip()

                if data_str == "[DONE]":
                    break

                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                usage = event.get("usage") or {}
                if usage:
                    self.total_input_tokens = (
                        usage.get("prompt_tokens")
                        or usage.get("input_tokens")
                        or self.total_input_tokens
                    )
                    self.total_output_tokens = (
                        usage.get("completion_tokens")
                        or usage.get("output_tokens")
                        or self.total_output_tokens
                    )
                    logger.debug(
                        "Token usage - Input: %s, Output: %s, Total: %s",
                        self.total_input_tokens,
                        self.total_output_tokens,
                        self.total_input_tokens + self.total_output_tokens,
                    )

                choices = event.get("choices") or []
                if not choices:
                    continue
                delta = (choices[0] or {}).get("delta", {})

                if enable_thinking and delta.get("reasoning_content"):
                    piece = delta.get("reasoning_content") or ""
                    if piece:
                        if callback:
                            callback(piece)
                        yield piece

                piece = delta.get("content") or ""
                if piece:
                    if callback:
                        callback(piece)
                    yield piece

    def _stream_via_fallback(
        self,
        messages: List[Dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        callback: Optional[Callable[[str], None]],
    ) -> Iterator[str]:
        provider = (self._fallback_provider or "").lower()
        if provider == "openai":
            yield from self._stream_openai_completion(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                callback=callback,
            )
            return

        raise QwenAPIError(f"Unsupported fallback provider '{self._fallback_provider}'")

    def _stream_openai_completion(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float,
        max_tokens: Optional[int],
        callback: Optional[Callable[[str], None]],
    ) -> Iterator[str]:
        api_key = self._resolve_fallback_api_key()
        if not api_key:
            raise QwenAPIError("Fallback provider requires an API key but none was found.")

        base_url = self._fallback_base_url or "https://api.openai.com/v1"
        url = base_url.rstrip("/") + "/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self._fallback_model or "gpt-4o-mini",
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        response = requests.post(url, headers=headers, json=payload, timeout=self._fallback_timeout)
        if response.status_code != 200:
            try:
                err_payload = response.json()
            except Exception:
                err_payload = {"message": response.text}
            error_message = (
                (err_payload.get("error") or {}).get("message")
                or err_payload.get("message")
                or f"HTTP {response.status_code}"
            )
            raise QwenAPIError(
                f"Fallback provider error: {error_message}",
                status=response.status_code,
                payload=err_payload,
            )

        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise QwenAPIError("Fallback provider returned no choices.")

        content = (choices[0] or {}).get("message", {}).get("content") or ""
        if callback and content:
            callback(content)
        if content:
            yield content

        usage = data.get("usage") or {}
        self.total_input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or self.total_input_tokens
        self.total_output_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or self.total_output_tokens


