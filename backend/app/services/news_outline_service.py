"""
News outline generation service.

Generates news article outlines from Phase 0 summarized points using Qwen API.
"""
import os
import json
import re
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
from loguru import logger

try:
    from research.client import QwenStreamingClient
    from core.config import Config, find_project_root
except ImportError as e:
    logger.warning(f"Unable to import required modules: {e}")
    QwenStreamingClient = None  # type: ignore
    Config = None  # type: ignore
    find_project_root = None  # type: ignore


class NewsOutlineService:
    """Service for generating news article outlines from Phase 0 summarized points."""
    
    def __init__(self, config: Config):
        """Initialize the news outline service."""
        if Config is None:
            raise RuntimeError("Config module unavailable")
        
        self.config = config
        self._qwen_client: Optional[QwenStreamingClient] = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from config.yaml."""
        news_config = self.config.get('news', {})
        self.outline_config = news_config.get('outline_generation', {})
        self.paths_config = news_config.get('paths', {})
        self.prompts_config = news_config.get('prompts', {})
        
        # Initialize paths
        project_root = find_project_root() if find_project_root else Path.cwd()
        outlines_dir_str = self.paths_config.get('outlines_dir', 'data/news/outlines')
        batch_source_dir_str = self.paths_config.get('batch_source_dir', 'data/research/batches')
        
        if Path(outlines_dir_str).is_absolute():
            self.outlines_dir = Path(outlines_dir_str)
        else:
            self.outlines_dir = project_root / outlines_dir_str
        
        if Path(batch_source_dir_str).is_absolute():
            self.batch_source_dir = Path(batch_source_dir_str)
        else:
            self.batch_source_dir = project_root / batch_source_dir_str
        
        # Create directories if needed
        self.outlines_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_qwen_client(self) -> QwenStreamingClient:
        """Get or create Qwen client."""
        if QwenStreamingClient is None:
            raise RuntimeError("QwenStreamingClient unavailable")
        
        if self._qwen_client is None:
            api_key = self.outline_config.get('api_key') or self.config.get('qwen.api_key')
            if not api_key:
                raise ValueError("Qwen API key not configured")
            model = self.outline_config.get('model', 'qwen-plus')
            self._qwen_client = QwenStreamingClient(api_key=api_key, model=model)
        return self._qwen_client
    
    def _load_prompt(self, prompt_type: str = 'system') -> str:
        """Load prompt from dedicated file."""
        project_root = find_project_root() if find_project_root else Path.cwd()
        
        article_outline_config = self.prompts_config.get('article_outline', {})
        
        if prompt_type == 'system':
            prompt_path_str = article_outline_config.get('system_prompt_path', 'news/prompts/article_outline/system.md')
        elif prompt_type == 'instructions':
            prompt_path_str = article_outline_config.get('instructions_path', 'news/prompts/article_outline/instructions.md')
        else:
            raise ValueError(f"Unknown prompt type: {prompt_type}")
        
        if Path(prompt_path_str).is_absolute():
            prompt_path = Path(prompt_path_str)
        else:
            prompt_path = project_root / prompt_path_str
        
        if not prompt_path.exists():
            logger.warning(f"Prompt file not found: {prompt_path}, using default")
            if prompt_type == 'system':
                return "你是一个专业的新闻文章大纲生成助手。根据提供的内容摘要生成新闻文章大纲。"
            else:
                return "生成新闻文章大纲，输出JSON格式，包含title、description和related_link_ids字段。"
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _extract_summarized_points(self, json_file: Path) -> Dict[str, Any]:
        """Extract summarized points from Phase 0 JSON file."""
        if not json_file.exists():
            raise FileNotFoundError(f"Phase 0 file not found: {json_file}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        summary = data.get('summary', {})
        transcript_summary = summary.get('transcript_summary', {})
        
        if not transcript_summary:
            raise ValueError(f"Phase 0 file missing transcript_summary: {json_file}")
        
        link_id = data.get('link_id')
        batch_id = data.get('batch_id')
        source = data.get('source')
        metadata = data.get('metadata', {})
        
        return {
            'link_id': link_id,
            'batch_id': batch_id,
            'source': source,
            'metadata': metadata,
            'key_facts': transcript_summary.get('key_facts', []),
            'key_opinions': transcript_summary.get('key_opinions', []),
            'key_datapoints': transcript_summary.get('key_datapoints', []),
            'topic_areas': transcript_summary.get('topic_areas', []),
            'total_markers': transcript_summary.get('total_markers', 0),
        }
    
    def _format_summarized_points_for_prompt(self, summarized_points: Dict[str, Any], all_link_ids: List[str]) -> str:
        """Format summarized points into prompt-friendly text."""
        parts = []
        
        if summarized_points.get('key_facts'):
            parts.append("## 关键事实 (Key Facts)")
            for i, fact in enumerate(summarized_points['key_facts'], 1):
                parts.append(f"{i}. {fact}")
            parts.append("")
        
        if summarized_points.get('key_opinions'):
            parts.append("## 关键观点 (Key Opinions)")
            for i, opinion in enumerate(summarized_points['key_opinions'], 1):
                parts.append(f"{i}. {opinion}")
            parts.append("")
        
        if summarized_points.get('key_datapoints'):
            parts.append("## 关键数据点 (Key Datapoints)")
            for i, datapoint in enumerate(summarized_points['key_datapoints'], 1):
                parts.append(f"{i}. {datapoint}")
            parts.append("")
        
        if summarized_points.get('topic_areas'):
            parts.append("## 主题领域 (Topic Areas)")
            for i, topic in enumerate(summarized_points['topic_areas'], 1):
                parts.append(f"{i}. {topic}")
            parts.append("")
        
        if all_link_ids:
            parts.append("## 相关链接ID (Link IDs)")
            parts.append(", ".join(all_link_ids))
            parts.append("")
        
        return "\n".join(parts)
    
    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """Extract JSON from Qwen response, handling markdown code blocks."""
        # Try to find JSON in code blocks first
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, response_text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Try to find JSON object directly
            json_pattern = r'\{.*\}'
            match = re.search(json_pattern, response_text, re.DOTALL)
            if match:
                json_str = match.group(0)
            else:
                # Try parsing entire response as JSON
                json_str = response_text.strip()
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            raise ValueError(f"Invalid JSON response from Qwen: {e}")
    
    def _validate_outline_json(self, outline: Dict[str, Any]) -> None:
        """Validate that outline JSON has required fields."""
        required_fields = ['title', 'description', 'related_link_ids']
        for field in required_fields:
            if field not in outline:
                raise ValueError(f"Missing required field in outline: {field}")
        
        if not isinstance(outline['title'], str) or not outline['title'].strip():
            raise ValueError("Title must be a non-empty string")
        
        if not isinstance(outline['description'], str) or not outline['description'].strip():
            raise ValueError("Description must be a non-empty string")
        
        if not isinstance(outline['related_link_ids'], list):
            raise ValueError("related_link_ids must be a list")
    
    def _generate_outline(
        self, 
        summarized_points_text: str, 
        link_ids: List[str]
    ) -> Dict[str, Any]:
        """Call Qwen API to generate article outline."""
        # Load prompts
        system_prompt = self._load_prompt('system')
        instructions = self._load_prompt('instructions')
        
        # Build user prompt
        user_prompt = f"""{instructions}

以下是内容摘要：

{summarized_points_text}

请根据以上内容摘要生成新闻文章大纲，输出JSON格式。"""
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get Qwen client and configuration
        client = self._get_qwen_client()
        temperature = self.outline_config.get('temperature', 0.7)
        max_tokens = self.outline_config.get('max_tokens', 4000)
        
        # Call Qwen API (non-streaming)
        logger.info(f"Calling Qwen API ({self.outline_config.get('model', 'qwen-plus')}) to generate outline...")
        response_text = ""
        
        # Use stream_completion and collect tokens
        for token in client.stream_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            exclude_reasoning_from_yield=True
        ):
            response_text += token
        
        # Extract JSON from response
        outline = self._extract_json_from_response(response_text)
        
        # Validate outline
        self._validate_outline_json(outline)
        
        return outline
    
    def _find_phase0_files(self, batch_id: str, link_ids: Optional[List[str]] = None) -> List[Path]:
        """Find Phase 0 JSON files for a batch."""
        batch_dir = self.batch_source_dir / f"run_{batch_id}"
        
        if not batch_dir.exists():
            raise FileNotFoundError(f"Batch directory not found: {batch_dir}")
        
        # Find all *_complete.json files
        pattern = f"*_complete.json"
        if link_ids:
            # Filter by link_ids
            files = []
            for link_id in link_ids:
                # Try to find file matching link_id
                for file_path in batch_dir.glob(pattern):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        try:
                            data = json.load(f)
                            if data.get('link_id') == link_id:
                                files.append(file_path)
                                break
                        except json.JSONDecodeError:
                            continue
        else:
            # Get all complete files
            files = list(batch_dir.glob(pattern))
        
        if not files:
            if link_ids:
                raise FileNotFoundError(f"No Phase 0 files found for batch {batch_id} with link_ids: {link_ids}")
            else:
                raise FileNotFoundError(f"No Phase 0 files found in batch {batch_id}")
        
        return sorted(files)
    
    def generate_outline_from_batch(
        self, 
        batch_id: str, 
        link_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate article outline from a batch of Phase 0 files."""
        # Find Phase 0 files
        phase0_files = self._find_phase0_files(batch_id, link_ids)
        
        if not phase0_files:
            raise ValueError(f"No Phase 0 files found for batch {batch_id}")
        
        logger.info(f"Found {len(phase0_files)} Phase 0 files in batch {batch_id}")
        
        # Extract summarized points from all files
        all_summarized_points = []
        all_link_ids = []
        
        for file_path in phase0_files:
            try:
                points = self._extract_summarized_points(file_path)
                all_summarized_points.append(points)
                if points['link_id']:
                    all_link_ids.append(points['link_id'])
            except Exception as e:
                logger.warning(f"Failed to extract points from {file_path}: {e}")
                continue
        
        if not all_summarized_points:
            raise ValueError(f"No valid summarized points found in batch {batch_id}")
        
        # Combine all summarized points
        combined_points = {
            'key_facts': [],
            'key_opinions': [],
            'key_datapoints': [],
            'topic_areas': [],
        }
        
        for points in all_summarized_points:
            combined_points['key_facts'].extend(points.get('key_facts', []))
            combined_points['key_opinions'].extend(points.get('key_opinions', []))
            combined_points['key_datapoints'].extend(points.get('key_datapoints', []))
            combined_points['topic_areas'].extend(points.get('topic_areas', []))
        
        # Remove duplicates while preserving order
        def deduplicate_list(items):
            seen = set()
            result = []
            for item in items:
                if item not in seen:
                    seen.add(item)
                    result.append(item)
            return result
        
        combined_points['key_facts'] = deduplicate_list(combined_points['key_facts'])
        combined_points['key_opinions'] = deduplicate_list(combined_points['key_opinions'])
        combined_points['key_datapoints'] = deduplicate_list(combined_points['key_datapoints'])
        combined_points['topic_areas'] = deduplicate_list(combined_points['topic_areas'])
        
        # Format for prompt
        formatted_points = self._format_summarized_points_for_prompt(combined_points, all_link_ids)
        
        # Generate outline using Qwen
        outline = self._generate_outline(formatted_points, all_link_ids)
        
        # Add metadata
        outline_id = f"outline_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(all_link_ids):03d}"
        
        result = {
            "outline_id": outline_id,
            "generated_at": datetime.now().isoformat(),
            "batch_id": batch_id,
            "article": {
                "title": outline["title"],
                "description": outline["description"],
                "related_link_ids": outline["related_link_ids"],
            },
            "metadata": {
                "model_used": self.outline_config.get('model', 'qwen-plus'),
                "prompt_version": "v1.0",
                "source_batch": batch_id,
                "total_sources": len(all_link_ids),
            }
        }
        
        return result
    
    def save_outline(self, outline: Dict[str, Any]) -> Path:
        """Save generated outline to JSON file."""
        outline_id = outline.get('outline_id')
        if not outline_id:
            raise ValueError("Outline missing outline_id")
        
        output_file = self.outlines_dir / f"{outline_id}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(outline, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved outline to: {output_file}")
        return output_file
    
    def load_outline(self, outline_id: str) -> Dict[str, Any]:
        """Load an outline by ID."""
        outline_file = self.outlines_dir / f"{outline_id}.json"
        
        if not outline_file.exists():
            raise FileNotFoundError(f"Outline not found: {outline_id}")
        
        with open(outline_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_outlines(self, batch_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all outlines, optionally filtered by batch_id."""
        outlines = []
        
        for outline_file in self.outlines_dir.glob("*.json"):
            try:
                with open(outline_file, 'r', encoding='utf-8') as f:
                    outline = json.load(f)
                    
                if batch_id is None or outline.get('batch_id') == batch_id:
                    # Only include summary fields for listing
                    outlines.append({
                        'outline_id': outline.get('outline_id'),
                        'batch_id': outline.get('batch_id'),
                        'generated_at': outline.get('generated_at'),
                        'article': {
                            'title': outline.get('article', {}).get('title'),
                            'description': outline.get('article', {}).get('description'),
                        },
                        'metadata': outline.get('metadata', {}),
                    })
            except Exception as e:
                logger.warning(f"Failed to load outline from {outline_file}: {e}")
                continue
        
        # Sort by generated_at descending
        outlines.sort(key=lambda x: x.get('generated_at', ''), reverse=True)
        return outlines

