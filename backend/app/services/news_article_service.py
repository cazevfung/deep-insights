"""
News article generation service.

Generates full news articles in markdown format from outlines using full content.
"""
import json
from typing import Optional, Dict, Any, List, Tuple
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


class NewsArticleService:
    """Service for generating news articles from outlines using full content."""
    
    def __init__(self, config: Config):
        """Initialize the news article service."""
        if Config is None:
            raise RuntimeError("Config module unavailable")
        
        self.config = config
        self._qwen_client: Optional[QwenStreamingClient] = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from config.yaml."""
        news_config = self.config.get('news', {})
        self.article_config = news_config.get('article_generation', {})
        self.paths_config = news_config.get('paths', {})
        self.prompts_config = news_config.get('prompts', {})
        
        # Initialize paths
        project_root = find_project_root() if find_project_root else Path.cwd()
        articles_dir_str = self.paths_config.get('articles_dir', 'data/news/articles')
        outlines_dir_str = self.paths_config.get('outlines_dir', 'data/news/outlines')
        batch_source_dir_str = self.paths_config.get('batch_source_dir', 'data/research/batches')
        
        # Convert to Path objects (handle absolute/relative)
        if Path(articles_dir_str).is_absolute():
            self.articles_dir = Path(articles_dir_str)
        else:
            self.articles_dir = project_root / articles_dir_str
        
        if Path(outlines_dir_str).is_absolute():
            self.outlines_dir = Path(outlines_dir_str)
        else:
            self.outlines_dir = project_root / outlines_dir_str
        
        if Path(batch_source_dir_str).is_absolute():
            self.batch_source_dir = Path(batch_source_dir_str)
        else:
            self.batch_source_dir = project_root / batch_source_dir_str
        
        # Create directories if needed
        self.articles_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_qwen_client(self) -> QwenStreamingClient:
        """Get or create Qwen client."""
        if QwenStreamingClient is None:
            raise RuntimeError("QwenStreamingClient unavailable")
        
        if self._qwen_client is None:
            api_key = self.article_config.get('api_key') or self.config.get('qwen.api_key')
            if not api_key:
                raise ValueError("Qwen API key not configured")
            model = self.article_config.get('model', 'qwen-plus')
            self._qwen_client = QwenStreamingClient(api_key=api_key, model=model)
        return self._qwen_client
    
    def _load_prompt(self, prompt_type: str = 'system') -> str:
        """Load prompt from dedicated file."""
        project_root = find_project_root() if find_project_root else Path.cwd()
        
        article_gen_config = self.prompts_config.get('article_generation', {})
        
        if prompt_type == 'system':
            prompt_path_str = article_gen_config.get('system_prompt_path', 'news/prompts/article_generation/system.md')
        elif prompt_type == 'instructions':
            prompt_path_str = article_gen_config.get('instructions_path', 'news/prompts/article_generation/instructions.md')
        else:
            raise ValueError(f"Unknown prompt type: {prompt_type}")
        
        if Path(prompt_path_str).is_absolute():
            prompt_path = Path(prompt_path_str)
        else:
            prompt_path = project_root / prompt_path_str
        
        if not prompt_path.exists():
            logger.warning(f"Prompt file not found: {prompt_path}, using default")
            if prompt_type == 'system':
                return "你是一个专业的新闻文章撰写助手。根据提供的大纲和完整内容生成新闻文章。"
            else:
                return "生成新闻文章，输出Markdown格式。"
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _load_outline(self, outline_id: str) -> Dict[str, Any]:
        """Load outline JSON by ID."""
        outline_file = self.outlines_dir / f"{outline_id}.json"
        
        if not outline_file.exists():
            raise FileNotFoundError(f"Outline not found: {outline_id}")
        
        with open(outline_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _find_batch_file(self, batch_id: str, link_id: str) -> Optional[Path]:
        """Find batch JSON file for a given link_id."""
        batch_dir = self.batch_source_dir / f"run_{batch_id}"
        
        if not batch_dir.exists():
            logger.warning(f"Batch directory not found: {batch_dir}")
            return None
        
        # Find file matching pattern: {batch_id}_{link_id}_complete.json
        pattern = f"*_{link_id}_complete.json"
        files = list(batch_dir.glob(pattern))
        
        if not files:
            logger.warning(f"Batch file not found for link_id {link_id} in batch {batch_id}")
            return None
        
        # Also try: {batch_id}_{link_id}_complete.json (without wildcard)
        exact_pattern = f"{batch_id}_{link_id}_complete.json"
        exact_file = batch_dir / exact_pattern
        if exact_file.exists():
            return exact_file
        
        # Return first matching file
        return files[0]
    
    def _extract_content_from_batch_file(self, batch_file: Path) -> str:
        """Extract full content from batch JSON file."""
        if not batch_file.exists():
            return ""
        
        with open(batch_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse batch file {batch_file}: {e}")
                return ""
        
        # For videos (bilibili, youtube): use transcript
        # For articles: use content
        source = data.get('source', '').lower()
        
        if source in ['bilibili', 'youtube']:
            content = data.get('transcript', '')
        else:
            content = data.get('content', '')
        
        return content if content else ""
    
    def _retrieve_all_content(self, outline: Dict[str, Any]) -> List[str]:
        """Retrieve full content for all related_link_ids."""
        batch_id = outline.get('batch_id')
        related_link_ids = outline.get('article', {}).get('related_link_ids', [])
        
        if not batch_id:
            raise ValueError("Outline missing batch_id")
        
        if not related_link_ids:
            raise ValueError("Outline missing related_link_ids")
        
        content_texts = []
        
        for link_id in related_link_ids:
            batch_file = self._find_batch_file(batch_id, link_id)
            
            if not batch_file:
                logger.warning(f"Skipping link_id {link_id} - batch file not found")
                continue
            
            content = self._extract_content_from_batch_file(batch_file)
            
            if not content:
                logger.warning(f"No content found for link_id {link_id}")
                continue
            
            content_texts.append(content)
            logger.debug(f"Retrieved content for {link_id}: {len(content)} characters")
        
        if not content_texts:
            raise ValueError(f"No content retrieved for any link_ids: {related_link_ids}")
        
        logger.info(f"Retrieved {len(content_texts)} content items out of {len(related_link_ids)} link_ids")
        
        return content_texts
    
    def _stitch_content(self, outline: Dict[str, Any], content_texts: List[str]) -> str:
        """Stitch all content together in structured format for prompt."""
        article_info = outline.get('article', {})
        title = article_info.get('title', 'Untitled Article')
        description = article_info.get('description', '')
        related_link_ids = article_info.get('related_link_ids', [])
        
        parts = []
        parts.append("## 文章大纲")
        parts.append("")
        parts.append(f"**标题**: {title}")
        parts.append("")
        parts.append(f"**描述**: {description}")
        parts.append("")
        parts.append(f"**相关来源ID**: {', '.join(related_link_ids)}")
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append("## 完整内容")
        parts.append("")
        
        for i, (link_id, content_text) in enumerate(zip(related_link_ids[:len(content_texts)], content_texts), 1):
            parts.append(f"### 来源 {i}: {link_id}")
            parts.append("")
            parts.append(content_text)
            parts.append("")
            parts.append("---")
            parts.append("")
        
        return "\n".join(parts)
    
    def _generate_article(self, content_pack: str) -> str:
        """Call Qwen API to generate article in markdown format."""
        # Load prompts
        system_prompt = self._load_prompt('system')
        instructions = self._load_prompt('instructions')
        
        # Build user prompt
        user_prompt = f"""{instructions}

以下是内容数据：

{content_pack}

请根据以上大纲和完整内容生成一篇新闻文章，输出Markdown格式。"""
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get Qwen client and configuration
        client = self._get_qwen_client()
        temperature = self.article_config.get('temperature', 0.7)
        max_tokens = self.article_config.get('max_tokens', 16000)
        
        # Call Qwen API (non-streaming)
        logger.info(f"Calling Qwen API ({self.article_config.get('model', 'qwen-plus')}) to generate article...")
        response_text = ""
        
        # Use stream_completion and collect tokens
        for token in client.stream_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            exclude_reasoning_from_yield=True
        ):
            response_text += token
        
        logger.info(f"Generated article: {len(response_text)} characters")
        
        return response_text
    
    def generate_article_from_outline(
        self, 
        outline_id: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate article from an outline.
        
        Returns:
            Tuple of (markdown_content, metadata_dict)
        """
        # Load outline
        logger.info(f"Loading outline: {outline_id}")
        outline = self._load_outline(outline_id)
        
        # Retrieve all content
        logger.info(f"Retrieving content for {len(outline.get('article', {}).get('related_link_ids', []))} sources")
        content_texts = self._retrieve_all_content(outline)
        
        # Stitch content together
        logger.info(f"Stitching {len(content_texts)} content items")
        content_pack = self._stitch_content(outline, content_texts)
        
        # Generate article
        logger.info("Generating article with Qwen...")
        markdown_content = self._generate_article(content_pack)
        
        # Create metadata
        article_info = outline.get('article', {})
        article_id = f"article_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(content_texts):03d}"
        
        metadata = {
            "article_id": article_id,
            "outline_id": outline_id,
            "generated_at": datetime.now().isoformat(),
            "batch_id": outline.get('batch_id'),
            "title": article_info.get('title', ''),
            "description": article_info.get('description', ''),
            "markdown_file": f"{article_id}.md",
            "related_link_ids": article_info.get('related_link_ids', []),
            "metadata": {
                "model_used": self.article_config.get('model', 'qwen-plus'),
                "prompt_version": "v1.0",
                "total_sources": len(content_texts),
            }
        }
        
        return markdown_content, metadata
    
    def save_article(self, article: Dict[str, Any], markdown_content: str) -> Tuple[Path, Path]:
        """Save generated article (markdown + JSON metadata)."""
        article_id = article.get('article_id')
        if not article_id:
            raise ValueError("Article missing article_id")
        
        # Save markdown
        md_file = self.articles_dir / f"{article_id}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # Save JSON metadata
        json_file = self.articles_dir / f"{article_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(article, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved article: {article_id} ({md_file}, {json_file})")
        
        return md_file, json_file
    
    def load_article(self, article_id: str) -> Dict[str, Any]:
        """Load article metadata by ID."""
        article_file = self.articles_dir / f"{article_id}.json"
        
        if not article_file.exists():
            raise FileNotFoundError(f"Article not found: {article_id}")
        
        with open(article_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_article_markdown(self, article_id: str) -> str:
        """Get article markdown content by ID."""
        article_file = self.articles_dir / f"{article_id}.md"
        
        if not article_file.exists():
            raise FileNotFoundError(f"Article markdown not found: {article_id}")
        
        with open(article_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    
    def list_articles(self, outline_id: Optional[str] = None, batch_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all generated articles, optionally filtered by outline_id or batch_id."""
        articles = []
        
        for article_file in self.articles_dir.glob("*.json"):
            try:
                with open(article_file, 'r', encoding='utf-8') as f:
                    article = json.load(f)
                    
                # Filter by outline_id if specified
                if outline_id and article.get('outline_id') != outline_id:
                    continue
                
                # Filter by batch_id if specified
                if batch_id and article.get('batch_id') != batch_id:
                    continue
                
                # Only include summary fields for listing
                articles.append({
                    'article_id': article.get('article_id'),
                    'outline_id': article.get('outline_id'),
                    'batch_id': article.get('batch_id'),
                    'generated_at': article.get('generated_at'),
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'metadata': article.get('metadata', {}),
                })
            except Exception as e:
                logger.warning(f"Failed to load article from {article_file}: {e}")
                continue
        
        # Sort by generated_at descending
        articles.sort(key=lambda x: x.get('generated_at', ''), reverse=True)
        
        return articles

