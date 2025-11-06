"""Marker formatting utilities for Phase 1-3 integration.

This module provides functions to format key info markers for use in research phases.
"""

from typing import Dict, Any, List, Optional
from loguru import logger


def format_marker_overview(
    batch_data: Dict[str, Any],
    link_ids: Optional[List[str]] = None,
    max_items: Optional[int] = None
) -> str:
    """
    Format marker overview for phases (Phase 1-3).
    
    Args:
        batch_data: Batch data with summaries (from Phase 0)
        link_ids: Optional list of link_ids to include (if None, includes all)
        max_items: Optional maximum number of items to show (if None, shows all)
        
    Returns:
        Formatted marker overview string
    """
    if not batch_data:
        return "**可用的内容项标记概览**\n\n无可用内容项。"
    
    # Filter link_ids if specified
    items_to_process = list(batch_data.keys())
    if link_ids:
        items_to_process = [lid for lid in items_to_process if lid in link_ids]
    
    # Limit items if specified
    if max_items and len(items_to_process) > max_items:
        items_to_process = items_to_process[:max_items]
        logger.info(f"Limited marker overview to {max_items} items")
    
    overview_parts = [
        f"**可用的内容项标记概览**\n\n共 {len(items_to_process)} 个内容项：\n"
    ]
    
    for idx, link_id in enumerate(items_to_process, 1):
        data = batch_data.get(link_id)
        if not data:
            continue
            
        item_overview = format_markers_for_content_item(link_id, data)
        if item_overview:
            overview_parts.append(f"---\n{item_overview}")
    
    return "\n".join(overview_parts)


def format_markers_for_content_item(link_id: str, data: Dict[str, Any]) -> str:
    """
    Format markers for a single content item.
    
    Args:
        link_id: Link identifier
        data: Content item data with summary
        
    Returns:
        Formatted marker string for this item
    """
    metadata = data.get("metadata", {})
    summary = data.get("summary", {})
    
    if not summary:
        # Fallback: no summary available
        title = metadata.get("title", "未知标题")
        source = data.get("source", "unknown")
        return f"**内容项: {link_id}**\n来源: {source} | 标题: {title}\n*(无标记摘要)*"
    
    # Extract metadata
    title = metadata.get("title", "未知标题")
    source = data.get("source", "unknown")
    transcript = data.get("transcript", "")
    comments = data.get("comments", [])
    
    word_count = len(transcript.split()) if transcript else 0
    comment_count = len(comments) if isinstance(comments, list) else 0
    
    # Build item overview
    parts = [
        f"**内容项: {link_id}**",
        f"来源: {source} | 标题: {title}",
        f"字数: {word_count} | 评论数: {comment_count}\n"
    ]
    
    # Format transcript summary
    transcript_summary = summary.get("transcript_summary", {})
    if transcript_summary:
        parts.append(_format_transcript_summary(transcript_summary))
    
    # Format comments summary
    comments_summary = summary.get("comments_summary", {})
    if comments_summary:
        parts.append(_format_comments_summary(comments_summary))
    
    return "\n".join(parts)


def _format_transcript_summary(transcript_summary: Dict[str, Any]) -> str:
    """Format transcript summary markers."""
    parts = []
    
    key_facts = transcript_summary.get("key_facts", [])
    key_opinions = transcript_summary.get("key_opinions", [])
    key_datapoints = transcript_summary.get("key_datapoints", [])
    topic_areas = transcript_summary.get("topic_areas", [])
    total_markers = transcript_summary.get("total_markers", 0)
    
    parts.append(f"**转录摘要标记** ({total_markers} 个):")
    
    if key_facts:
        parts.append(f"- 关键事实 ({len(key_facts)} 个):")
        for fact in key_facts:
            parts.append(f"  • {fact}")
    
    if key_opinions:
        parts.append(f"- 关键观点 ({len(key_opinions)} 个):")
        for opinion in key_opinions:
            parts.append(f"  • {opinion}")
    
    if key_datapoints:
        parts.append(f"- 关键数据点 ({len(key_datapoints)} 个):")
        for datapoint in key_datapoints:
            parts.append(f"  • {datapoint}")
    
    if topic_areas:
        parts.append(f"- 话题领域: {', '.join(topic_areas)}")
    
    return "\n".join(parts) if parts else ""


def _format_comments_summary(comments_summary: Dict[str, Any]) -> str:
    """Format comments summary markers."""
    parts = []
    
    total_comments = comments_summary.get("total_comments", 0)
    key_facts = comments_summary.get("key_facts_from_comments", [])
    key_opinions = comments_summary.get("key_opinions_from_comments", [])
    key_datapoints = comments_summary.get("key_datapoints_from_comments", [])
    major_themes = comments_summary.get("major_themes", [])
    sentiment_overview = comments_summary.get("sentiment_overview", "mixed")
    top_engagement = comments_summary.get("top_engagement_markers", [])
    
    parts.append(f"**评论摘要标记** ({total_comments} 条评论):")
    
    if key_facts:
        parts.append(f"- 关键事实 ({len(key_facts)} 个):")
        for fact in key_facts:
            parts.append(f"  • {fact}")
    
    if key_opinions:
        parts.append(f"- 关键观点 ({len(key_opinions)} 个):")
        for opinion in key_opinions:
            parts.append(f"  • {opinion}")
    
    if key_datapoints:
        parts.append(f"- 关键数据点 ({len(key_datapoints)} 个):")
        for datapoint in key_datapoints:
            parts.append(f"  • {datapoint}")
    
    if major_themes:
        parts.append(f"- 主要讨论主题: {', '.join(major_themes)}")
    
    if sentiment_overview:
        sentiment_map = {
            "mostly_positive": "整体积极",
            "mixed": "混合",
            "mostly_negative": "整体消极"
        }
        sentiment_display = sentiment_map.get(sentiment_overview, sentiment_overview)
        parts.append(f"- 总体情感: {sentiment_display}")
    
    if top_engagement:
        parts.append(f"- 高参与度评论标记 ({len(top_engagement)} 个):")
        for marker in top_engagement:
            parts.append(f"  • {marker}")
    
    return "\n".join(parts) if parts else ""


def filter_markers_by_relevance(
    summary: Dict[str, Any],
    keywords: List[str]
) -> Dict[str, Any]:
    """
    Filter markers by relevance to keywords.
    
    Args:
        summary: Content summary with markers
        keywords: Keywords to filter by
        
    Returns:
        Filtered summary with only relevant markers
    """
    if not keywords:
        return summary
    
    keywords_lower = [kw.lower() for kw in keywords]
    
    filtered = {}
    
    # Filter transcript summary
    transcript_summary = summary.get("transcript_summary", {})
    if transcript_summary:
        filtered["transcript_summary"] = {
            "key_facts": _filter_by_keywords(
                transcript_summary.get("key_facts", []),
                keywords_lower
            ),
            "key_opinions": _filter_by_keywords(
                transcript_summary.get("key_opinions", []),
                keywords_lower
            ),
            "key_datapoints": _filter_by_keywords(
                transcript_summary.get("key_datapoints", []),
                keywords_lower
            ),
            "topic_areas": transcript_summary.get("topic_areas", []),
            "word_count": transcript_summary.get("word_count", 0),
            "total_markers": 0  # Recalculated below
        }
        # Recalculate total_markers
        filtered["transcript_summary"]["total_markers"] = (
            len(filtered["transcript_summary"]["key_facts"]) +
            len(filtered["transcript_summary"]["key_opinions"]) +
            len(filtered["transcript_summary"]["key_datapoints"])
        )
    
    # Filter comments summary
    comments_summary = summary.get("comments_summary", {})
    if comments_summary:
        filtered["comments_summary"] = {
            "total_comments": comments_summary.get("total_comments", 0),
            "key_facts_from_comments": _filter_by_keywords(
                comments_summary.get("key_facts_from_comments", []),
                keywords_lower
            ),
            "key_opinions_from_comments": _filter_by_keywords(
                comments_summary.get("key_opinions_from_comments", []),
                keywords_lower
            ),
            "key_datapoints_from_comments": _filter_by_keywords(
                comments_summary.get("key_datapoints_from_comments", []),
                keywords_lower
            ),
            "major_themes": comments_summary.get("major_themes", []),
            "sentiment_overview": comments_summary.get("sentiment_overview", "mixed"),
            "top_engagement_markers": _filter_by_keywords(
                comments_summary.get("top_engagement_markers", []),
                keywords_lower
            ),
            "total_markers": 0  # Recalculated below
        }
        # Recalculate total_markers
        filtered["comments_summary"]["total_markers"] = (
            len(filtered["comments_summary"]["key_facts_from_comments"]) +
            len(filtered["comments_summary"]["key_opinions_from_comments"]) +
            len(filtered["comments_summary"]["key_datapoints_from_comments"])
        )
    
    return filtered


def _filter_by_keywords(items: List[str], keywords_lower: List[str]) -> List[str]:
    """Filter items by keywords."""
    return [
        item for item in items
        if any(kw in item.lower() for kw in keywords_lower)
    ]


def get_marker_relevance_score(marker: str, goal: str) -> float:
    """
    Calculate relevance score between a marker and a goal.
    
    Args:
        marker: Marker text
        goal: Goal text
        
    Returns:
        Relevance score between 0.0 and 1.0
    """
    if not marker or not goal:
        return 0.0
    
    # Simple word overlap scoring
    marker_words = set(marker.lower().split())
    goal_words = set(goal.lower().split())
    
    if not marker_words or not goal_words:
        return 0.0
    
    intersection = marker_words & goal_words
    union = marker_words | goal_words
    
    if not union:
        return 0.0
    
    # Jaccard similarity
    return len(intersection) / len(union)
