"""Content summarization using qwen-flash for Phase 0."""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger

# Try to import Qwen client - adjust import path as needed
try:
    from research.client import QwenStreamingClient
except ImportError:
    try:
        from core.qwen_client import QwenStreamingClient
    except ImportError:
        try:
            from core.qwen import QwenStreamingClient
        except ImportError:
            QwenStreamingClient = None
            logger.warning("QwenStreamingClient not found - summarization will need API client setup")


class ContentSummarizer:
    """Summarize content items using qwen-flash to extract marker lists."""
    
    def __init__(self, client=None, config=None, ui=None):
        """
        Initialize content summarizer.
        
        Args:
            client: QwenStreamingClient instance (optional, will try to create if not provided)
            config: Config instance for getting API settings
            ui: Optional UI interface for streaming updates
        """
        if client is None and QwenStreamingClient:
            # Try to create client if not provided
            if config:
                try:
                    api_key = config.get("qwen.api_key")
                    if api_key:
                        self.client = QwenStreamingClient(api_key=api_key)
                    else:
                        self.client = None
                except Exception as e:
                    logger.warning(f"Failed to create QwenStreamingClient: {e}")
                    self.client = None
            else:
                self.client = None
        else:
            self.client = client
        
        self.config = config
        # Use phase0 model from config if available, otherwise default to qwen-flash
        if config:
            self.model = config.get("research.phases.phase0.model", "qwen-flash")
        else:
            self.model = "qwen-flash"  # Fast, cheap model for summarization
        self.ui = ui
        
        # Load prompt files
        self.prompt_dir = Path(__file__).parent.parent / "prompts" / "content_summarization"
        self.system_prompt = self._load_prompt("system.md")
        self.transcript_instructions = self._load_prompt("transcript_instructions.md")
        self.comments_instructions = self._load_prompt("comments_instructions.md")
    
    def _load_prompt(self, filename: str) -> str:
        """Load prompt file content."""
        prompt_path = self.prompt_dir / filename
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        else:
            logger.warning(f"Prompt file not found: {prompt_path}")
            return ""
    
    def summarize_content_item(
        self,
        link_id: str,
        transcript: Optional[str] = None,
        comments: Optional[List] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create structured summary for a content item.
        
        Returns:
            {
                "transcript_summary": {...},
                "comments_summary": {...},
                "created_at": "...",
                "model_used": "qwen-flash"
            }
        """
        summary = {
            "transcript_summary": {},
            "comments_summary": {},
            "created_at": datetime.now().isoformat(),
            "model_used": self.model
        }
        
        # Summarize transcript if available
        if transcript:
            try:
                summary["transcript_summary"] = self._summarize_transcript(transcript, link_id)
            except Exception as e:
                logger.error(f"Failed to summarize transcript for {link_id}: {e}")
                summary["transcript_summary"] = {
                    "key_facts": [],
                    "key_opinions": [],
                    "key_datapoints": [],
                    "topic_areas": [],
                    "word_count": len(transcript.split()) if transcript else 0,
                    "total_markers": 0,
                    "error": str(e)
                }
        
        # Summarize comments if available
        if comments:
            try:
                summary["comments_summary"] = self._summarize_comments(comments, link_id)
            except Exception as e:
                logger.error(f"Failed to summarize comments for {link_id}: {e}")
                total_comments = len(comments) if isinstance(comments, list) else 0
                summary["comments_summary"] = {
                    "total_comments": total_comments,
                    "key_facts_from_comments": [],
                    "key_opinions_from_comments": [],
                    "key_datapoints_from_comments": [],
                    "major_themes": [],
                    "sentiment_overview": "mixed",
                    "top_engagement_markers": [],
                    "total_markers": 0,
                    "error": str(e)
                }
        
        return summary
    
    def _summarize_transcript(self, transcript: str, link_id: str = "unknown") -> Dict[str, Any]:
        """
        Extract lists of key facts, opinions, and data points from transcript.
        
        Args:
            transcript: The transcript text to summarize
            link_id: The link identifier for tracking/metadata
        
        Returns lists that serve as markers for retrieval, not narrative summaries.
        """
        if not self.client:
            raise ValueError("Qwen client not available - cannot summarize transcript")
        
        # Calculate word count
        word_count = len(transcript.split())
        
        # Prepare prompt
        full_prompt = f"{self.system_prompt}\n\n{self.transcript_instructions}\n\n## Transcript Content\n\n{transcript}"
        
        # Call API with qwen-flash model
        try:
            # Get phase config for thinking settings
            enable_thinking = False
            thinking_budget = None
            if self.config:
                enable_thinking = self.config.get("research.phases.phase0.enable_thinking", False)
                thinking_budget = self.config.get("research.phases.phase0.thinking_budget")
            
            messages = [{"role": "user", "content": full_prompt}]
            response_text = ""
            stream_token_count = 0
            
            # Check if client has stream_and_collect (QwenStreamingClient)
            if hasattr(self.client, 'stream_and_collect'):
                # Collect all streamed tokens with reasoning support
                stream_id = None
                if self.ui:
                    metadata = {
                        "component": "transcript",
                        "phase_label": "0",
                        "phase": "phase0",
                        "link_id": link_id,
                        "word_count": word_count,
                    }
                    stream_id = f"summarization:{link_id}:transcript"
                    self.ui.clear_stream_buffer(stream_id)
                    self.ui.notify_stream_start(stream_id, "phase0", metadata)
                    logger.debug(
                        "Summarization stream started",
                        stream_id=stream_id,
                        link_id=link_id,
                        component="transcript",
                        enable_thinking=enable_thinking,
                    )
                
                def callback(token: str, reasoning_content: str = "None", content: str = "None"):
                    """Callback for streaming tokens with reasoning support."""
                    nonlocal response_text, stream_token_count
                    
                    # Debug logging for reasoning tokens
                    if reasoning_content != "None":
                        logger.debug(
                            f"💭 Phase 0 reasoning token (transcript): stream_id={stream_id}, "
                            f"length={len(reasoning_content)}, preview={reasoning_content[:30]}"
                        )
                    
                    # Collect content tokens for final response
                    if content != "None":
                        response_text += content
                    elif reasoning_content != "None":
                        # Also collect reasoning tokens for debugging/analysis
                        response_text += reasoning_content
                    
                    stream_token_count += 1
                    if self.ui and stream_id:
                        # Pass through both reasoning_content and content
                        self.ui.display_stream(token, stream_id, reasoning_content=reasoning_content, content=content)
                
                try:
                    # Prepare kwargs for stream_and_collect
                    stream_kwargs = {
                        "model": self.model,
                        "temperature": 0.3,  # Lower temperature for more consistent extraction
                        "max_tokens": 2000,
                        "enable_thinking": enable_thinking,
                    }
                    
                    # Add thinking_budget if configured
                    if thinking_budget is not None:
                        stream_kwargs["thinking_budget"] = thinking_budget
                    
                    # Use stream_and_collect with callback
                    response, usage = self.client.stream_and_collect(
                        messages=messages,
                        callback=callback,
                        exclude_reasoning_content=True,  # Only collect content tokens in final response
                        **stream_kwargs
                    )
                    # response_text is already populated by callback
                finally:
                    if self.ui and stream_id:
                        metadata = {
                            "component": "transcript",
                            "phase_label": "0",
                            "phase": "phase0",
                            "link_id": link_id,
                            "word_count": word_count,
                            "tokens": stream_token_count,
                        }
                        self.ui.notify_stream_end(stream_id, "phase0", metadata)
                        logger.debug(
                            "Summarization stream completed",
                            stream_id=stream_id,
                            link_id=link_id,
                            component="transcript",
                            tokens=stream_token_count,
                        )
            elif hasattr(self.client, 'stream_completion'):
                # Fallback to stream_completion if stream_and_collect not available
                stream_id = None
                if self.ui:
                    metadata = {
                        "component": "transcript",
                        "phase_label": "0",
                        "phase": "phase0",
                        "link_id": link_id,
                        "word_count": word_count,
                    }
                    stream_id = f"summarization:{link_id}:transcript"
                    self.ui.clear_stream_buffer(stream_id)
                    self.ui.notify_stream_start(stream_id, "phase0", metadata)
                try:
                    for token in self.client.stream_completion(
                        messages=messages,
                        model=self.model,
                        temperature=0.3,
                        max_tokens=2000
                    ):
                        response_text += token
                        stream_token_count += 1
                        if self.ui and stream_id:
                            self.ui.display_stream(token, stream_id, reasoning_content="None", content=token)
                finally:
                    if self.ui and stream_id:
                        metadata = {
                            "component": "transcript",
                            "phase_label": "0",
                            "phase": "phase0",
                            "link_id": link_id,
                            "word_count": word_count,
                            "tokens": stream_token_count,
                        }
                        self.ui.notify_stream_end(stream_id, "phase0", metadata)
            elif hasattr(self.client, 'generate_completion'):
                # Fallback: try generate_completion if it exists
                response_text = self.client.generate_completion(
                    prompt=full_prompt,
                    model=self.model,
                    temperature=0.3,
                    max_tokens=2000
                )
            elif hasattr(self.client, 'call'):
                # Alternative interface
                response_text = self.client.call(
                    messages=messages,
                    model=self.model,
                    temperature=0.3,
                    max_tokens=2000
                )
            else:
                # Try direct API call as last resort
                response_text = self._call_qwen_api_direct(full_prompt)
            
            # Parse JSON response
            result = self._parse_json_response(response_text, word_count)
            return result
            
        except Exception as e:
            logger.error(f"Error calling Qwen API for transcript summarization: {e}")
            raise
    
    def _summarize_comments(self, comments: List, link_id: str = "unknown") -> Dict[str, Any]:
        """
        Extract lists of key facts, opinions, and data points from comments.
        
        Args:
            comments: The comments list to summarize
            link_id: The link identifier for tracking/metadata
        
        Returns lists that serve as markers for retrieval, not narrative summaries.
        """
        if not self.client:
            raise ValueError("Qwen client not available - cannot summarize comments")
        
        total_comments = len(comments) if isinstance(comments, list) else 0
        
        # Format comments for prompt
        # Handle both YouTube format (list of strings) and Bilibili format (list of objects)
        comments_text = self._format_comments_for_summary(comments)
        
        # Limit comment content if too long
        max_chars = self.config.get("research.summarization.max_comments_for_summary", 50000) if self.config else 50000
        if len(comments_text) > max_chars:
            comments_text = comments_text[:max_chars] + "\n\n[注意: 评论内容被截断以便总结]"
        
        # Prepare prompt
        full_prompt = f"{self.system_prompt}\n\n{self.comments_instructions}\n\n## Comments Content\n\nTotal comments: {total_comments}\n\n{comments_text}"
        
        # Call API with qwen-flash model
        try:
            # Get phase config for thinking settings
            enable_thinking = False
            thinking_budget = None
            if self.config:
                enable_thinking = self.config.get("research.phases.phase0.enable_thinking", False)
                thinking_budget = self.config.get("research.phases.phase0.thinking_budget")
            
            messages = [{"role": "user", "content": full_prompt}]
            response_text = ""
            stream_token_count = 0
            
            # Check if client has stream_and_collect (QwenStreamingClient)
            if hasattr(self.client, 'stream_and_collect'):
                # Collect all streamed tokens with reasoning support
                stream_id = None
                if self.ui:
                    metadata = {
                        "component": "comments",
                        "phase_label": "0",
                        "phase": "phase0",
                        "link_id": link_id,
                        "total_comments": total_comments,
                    }
                    stream_id = f"summarization:{link_id}:comments"
                    self.ui.clear_stream_buffer(stream_id)
                    self.ui.notify_stream_start(stream_id, "phase0", metadata)
                    logger.debug(
                        "Summarization stream started",
                        stream_id=stream_id,
                        link_id=link_id,
                        component="comments",
                        enable_thinking=enable_thinking,
                    )
                
                def callback(token: str, reasoning_content: str = "None", content: str = "None"):
                    """Callback for streaming tokens with reasoning support."""
                    nonlocal response_text, stream_token_count
                    
                    # Debug logging for reasoning tokens
                    if reasoning_content != "None":
                        logger.debug(
                            f"💭 Phase 0 reasoning token (comments): stream_id={stream_id}, "
                            f"length={len(reasoning_content)}, preview={reasoning_content[:30]}"
                        )
                    
                    # Collect content tokens for final response
                    if content != "None":
                        response_text += content
                    elif reasoning_content != "None":
                        # Also collect reasoning tokens for debugging/analysis
                        response_text += reasoning_content
                    
                    stream_token_count += 1
                    if self.ui and stream_id:
                        # Pass through both reasoning_content and content
                        self.ui.display_stream(token, stream_id, reasoning_content=reasoning_content, content=content)
                
                try:
                    # Prepare kwargs for stream_and_collect
                    stream_kwargs = {
                        "model": self.model,
                        "temperature": 0.3,
                        "max_tokens": 2000,
                        "enable_thinking": enable_thinking,
                    }
                    
                    # Add thinking_budget if configured
                    if thinking_budget is not None:
                        stream_kwargs["thinking_budget"] = thinking_budget
                    
                    # Use stream_and_collect with callback
                    response, usage = self.client.stream_and_collect(
                        messages=messages,
                        callback=callback,
                        exclude_reasoning_content=True,  # Only collect content tokens in final response
                        **stream_kwargs
                    )
                    # response_text is already populated by callback
                finally:
                    if self.ui and stream_id:
                        metadata = {
                            "component": "comments",
                            "phase_label": "0",
                            "phase": "phase0",
                            "link_id": link_id,
                            "total_comments": total_comments,
                            "tokens": stream_token_count,
                        }
                        self.ui.notify_stream_end(stream_id, "phase0", metadata)
                        logger.debug(
                            "Summarization stream completed",
                            stream_id=stream_id,
                            link_id=link_id,
                            component="comments",
                            tokens=stream_token_count,
                        )
            elif hasattr(self.client, 'stream_completion'):
                # Fallback to stream_completion if stream_and_collect not available
                stream_id = None
                if self.ui:
                    metadata = {
                        "component": "comments",
                        "phase_label": "0",
                        "phase": "phase0",
                        "link_id": link_id,
                        "total_comments": total_comments,
                    }
                    stream_id = f"summarization:{link_id}:comments"
                    self.ui.clear_stream_buffer(stream_id)
                    self.ui.notify_stream_start(stream_id, "phase0", metadata)
                try:
                    for token in self.client.stream_completion(
                        messages=messages,
                        model=self.model,
                        temperature=0.3,
                        max_tokens=2000
                    ):
                        response_text += token
                        stream_token_count += 1
                        if self.ui and stream_id:
                            self.ui.display_stream(token, stream_id, reasoning_content="None", content=token)
                finally:
                    if self.ui and stream_id:
                        metadata = {
                            "component": "comments",
                            "phase_label": "0",
                            "phase": "phase0",
                            "link_id": link_id,
                            "total_comments": total_comments,
                            "tokens": stream_token_count,
                        }
                        self.ui.notify_stream_end(stream_id, "phase0", metadata)
            elif hasattr(self.client, 'generate_completion'):
                response_text = self.client.generate_completion(
                    prompt=full_prompt,
                    model=self.model,
                    temperature=0.3,
                    max_tokens=2000
                )
            elif hasattr(self.client, 'call'):
                response_text = self.client.call(
                    messages=messages,
                    model=self.model,
                    temperature=0.3,
                    max_tokens=2000
                )
            else:
                response_text = self._call_qwen_api_direct(full_prompt)
            
            # Parse JSON response
            result = self._parse_comments_json_response(response_text, total_comments)
            return result
            
        except Exception as e:
            logger.error(f"Error calling Qwen API for comments summarization: {e}")
            raise
    
    def _format_comments_for_summary(self, comments: List) -> str:
        """Format comments for summary prompt."""
        if not comments:
            return ""
        
        formatted = []
        for i, comment in enumerate(comments[:1000], 1):  # Limit to 1000 comments
            if isinstance(comment, str):
                # YouTube format: simple string
                formatted.append(f"Comment {i}: {comment}")
            elif isinstance(comment, dict):
                # Bilibili format: dict with content, likes, replies
                content = comment.get("content", comment.get("text", ""))
                likes = comment.get("likes", 0)
                replies = comment.get("replies", 0)
                formatted.append(f"Comment {i} [点赞:{likes}, 回复:{replies}]: {content}")
            else:
                formatted.append(f"Comment {i}: {str(comment)}")
        
        return "\n".join(formatted)
    
    def _call_qwen_api_direct(self, prompt: str) -> str:
        """
        Direct API call fallback if client doesn't have expected interface.
        This should be adjusted based on actual Qwen API implementation.
        """
        import requests
        
        if not self.config:
            raise ValueError("Config required for direct API calls")
        
        api_key = self.config.get("qwen.api_key")
        api_url = self.config.get("qwen.api_url", "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": {
                "messages": [{"role": "user", "content": prompt}]
            },
            "parameters": {
                "temperature": 0.3,
                "max_tokens": 2000,
                "result_format": "message"
            }
        }
        
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        # Extract text from response - adjust based on actual API response format
        if "output" in result and "choices" in result["output"]:
            return result["output"]["choices"][0]["message"]["content"]
        elif "output" in result and "text" in result["output"]:
            return result["output"]["text"]
        else:
            return str(result)
    
    def _parse_json_response(self, response_text: str, word_count: int) -> Dict[str, Any]:
        """Parse JSON response from transcript summarization."""
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response_text
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON, attempting to extract data manually")
            # Fallback: try to extract lists manually
            data = self._extract_lists_from_text(response_text)
        
        # Ensure all required fields exist
        result = {
            "key_facts": data.get("key_facts", []),
            "key_opinions": data.get("key_opinions", []),
            "key_datapoints": data.get("key_datapoints", []),
            "topic_areas": data.get("topic_areas", []),
            "word_count": word_count,
            "total_markers": len(data.get("key_facts", [])) + 
                           len(data.get("key_opinions", [])) + 
                           len(data.get("key_datapoints", []))
        }
        
        return result
    
    def _parse_comments_json_response(self, response_text: str, total_comments: int) -> Dict[str, Any]:
        """Parse JSON response from comments summarization."""
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response_text
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON, attempting to extract data manually")
            data = self._extract_comments_lists_from_text(response_text)
        
        # Ensure all required fields exist
        result = {
            "total_comments": total_comments,
            "key_facts_from_comments": data.get("key_facts_from_comments", []),
            "key_opinions_from_comments": data.get("key_opinions_from_comments", []),
            "key_datapoints_from_comments": data.get("key_datapoints_from_comments", []),
            "major_themes": data.get("major_themes", []),
            "sentiment_overview": data.get("sentiment_overview", "mixed"),
            "top_engagement_markers": data.get("top_engagement_markers", []),
            "total_markers": len(data.get("key_facts_from_comments", [])) + 
                           len(data.get("key_opinions_from_comments", [])) + 
                           len(data.get("key_datapoints_from_comments", []))
        }
        
        return result
    
    def _extract_lists_from_text(self, text: str) -> Dict[str, List]:
        """Fallback: extract lists from text if JSON parsing fails."""
        # Simple regex-based extraction
        result = {
            "key_facts": [],
            "key_opinions": [],
            "key_datapoints": [],
            "topic_areas": []
        }
        
        # Try to find FACT:, OPINION:, DATA: markers
        for line in text.split("\n"):
            if "FACT:" in line or "事实:" in line:
                result["key_facts"].append(line.strip())
            elif "OPINION:" in line or "观点:" in line:
                result["key_opinions"].append(line.strip())
            elif "DATA:" in line or "数据:" in line:
                result["key_datapoints"].append(line.strip())
        
        return result
    
    def _extract_comments_lists_from_text(self, text: str) -> Dict[str, Any]:
        """Fallback: extract lists from text for comments."""
        result = {
            "key_facts_from_comments": [],
            "key_opinions_from_comments": [],
            "key_datapoints_from_comments": [],
            "major_themes": [],
            "sentiment_overview": "mixed",
            "top_engagement_markers": []
        }
        
        # Simple extraction logic
        for line in text.split("\n"):
            if "FACT:" in line or "事实:" in line:
                result["key_facts_from_comments"].append(line.strip())
            elif "OPINION:" in line or "观点:" in line:
                result["key_opinions_from_comments"].append(line.strip())
            elif "DATA:" in line or "数据:" in line:
                result["key_datapoints_from_comments"].append(line.strip())
            elif "Theme:" in line or "主题:" in line:
                result["major_themes"].append(line.strip())
            elif "sentiment" in line.lower() or "情感" in line:
                if "positive" in line.lower() or "积极" in line:
                    result["sentiment_overview"] = "mostly_positive"
                elif "negative" in line.lower() or "消极" in line:
                    result["sentiment_overview"] = "mostly_negative"
        
        return result
