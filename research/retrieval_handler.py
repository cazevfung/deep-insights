"""Retrieval utilities for interactive, targeted context fetching in Phase 3.

Implements:
- Word-range retrieval from transcripts
- Keyword-window retrieval from transcripts (with merged windows)
- Comment filtering by keywords (with basic sorting)
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Any, Optional

from research.utils.marker_formatter import get_content_display_name


class RetrievalHandler:
    """Provides retrieval methods over in-memory batch data."""

    def __init__(self) -> None:
        pass

    # ----------------------------- Transcript Retrieval -----------------------------
    def retrieve_by_word_range(
        self,
        link_id: str,
        start_word: int,
        end_word: int,
        batch_data: Dict[str, Any]
    ) -> str:
        """Retrieve a specific word range from a transcript for a given link_id."""
        data = batch_data.get(link_id)
        if not data:
            return f"Error: link_id {link_id} not found"

        transcript = data.get("transcript", "")
        if not transcript:
            return f"Error: link_id {link_id} has no transcript"

        words = transcript.split()
        if start_word < 0 or end_word > len(words) or start_word >= end_word:
            return (
                f"Error: Range {start_word}-{end_word} out of bounds (0-{len(words)})"
            )

        selected_words = words[start_word:end_word]
        return " ".join(selected_words)

    def retrieve_by_keywords(
        self,
        link_id: str,
        keywords: List[str],
        batch_data: Dict[str, Any],
        context_window: int = 500
    ) -> str:
        """Retrieve transcript windows that contain any of the keywords, with context."""
        data = batch_data.get(link_id)
        if not data:
            return f"Error: link_id {link_id} not found"

        transcript = data.get("transcript", "")
        if not transcript:
            return f"Error: link_id {link_id} has no transcript"

        words = transcript.split()
        lowered_keywords = [kw.lower() for kw in keywords if kw]
        if not lowered_keywords:
            return "(No keywords provided)"

        # Optimize: scan once and only create windows around matched indices
        matches: List[Tuple[int, int]] = []
        lowered_words = [w.lower() for w in words]

        for i, w in enumerate(lowered_words):
            # Simple containment match per word; avoids rebuilding large window strings
            if any(kw in w for kw in lowered_keywords):
                window_start = max(0, i - context_window)
                window_end = min(len(words), i + context_window)
                matches.append((window_start, window_end))

        if not matches:
            return "(No keyword matches found in transcript)"

        merged = self._merge_ranges(matches)

        parts: List[str] = []
        for start, end in merged:
            parts.append(
                f"[Words {start}-{end}]:\n" + " ".join(words[start:end])
            )
        return "\n\n".join(parts)

    # ----------------------------- Comments Retrieval -----------------------------
    def retrieve_matching_comments(
        self,
        link_id: str,
        keywords: List[str],
        batch_data: Dict[str, Any],
        limit: int = 10,
        sort_by: str = "relevance"
    ) -> str:
        """Filter comments by keywords, return formatted lines."""
        data = batch_data.get(link_id)
        if not data:
            return f"Error: link_id {link_id} not found"

        raw_comments = data.get("comments", [])
        if not isinstance(raw_comments, list) or not raw_comments:
            return "(No comments available)"

        normalized: List[Dict[str, Any]] = []
        for c in raw_comments:
            if isinstance(c, dict):
                content = c.get("content", "")
                if not content:
                    continue
                normalized.append(
                    {
                        "content": content,
                        "likes": c.get("likes", 0),
                        "replies": c.get("replies", 0),
                    }
                )
            else:
                normalized.append({"content": str(c), "likes": 0, "replies": 0})

        lowered_keywords = [kw.lower() for kw in keywords]
        matches: List[Tuple[Dict[str, Any], int]] = []
        for c in normalized:
            cl = c["content"].lower()
            relevance = sum(1 for kw in lowered_keywords if kw in cl)
            if relevance > 0:
                matches.append((c, relevance))

        if not matches:
            return "(No comments matched the given keywords)"

        if sort_by == "likes":
            matches.sort(key=lambda t: t[0].get("likes", 0), reverse=True)
        elif sort_by == "replies":
            matches.sort(key=lambda t: t[0].get("replies", 0), reverse=True)
        else:
            matches.sort(key=lambda t: (t[1], t[0].get("likes", 0)), reverse=True)

        top = [m[0] for m in matches[: max(1, limit)]]
        return self._format_comments(top)

    # ----------------------------- Helpers -----------------------------
    def _merge_ranges(self, ranges: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        if not ranges:
            return []
        ranges.sort(key=lambda r: (r[0], r[1]))
        merged: List[Tuple[int, int]] = []
        cur_start, cur_end = ranges[0]
        for start, end in ranges[1:]:
            if start <= cur_end:
                cur_end = max(cur_end, end)
            else:
                merged.append((cur_start, cur_end))
                cur_start, cur_end = start, end
        merged.append((cur_start, cur_end))
        return merged

    def _format_comments(self, comments: List[Dict[str, Any]]) -> str:
        lines: List[str] = []
        for c in comments:
            likes = c.get("likes", 0)
            replies = c.get("replies", 0)
            content = c.get("content", "").strip()
            lines.append(f"- [Likes:{likes}, Replies:{replies}] {content}")
        return "\n".join(lines)

    # ----------------------------- New Marker-Based Retrieval Methods -----------------------------
    
    def retrieve_full_content_item(
        self,
        link_id: str,
        content_types: List[str],
        batch_data: Dict[str, Any]
    ) -> str:
        """
        Retrieve full, untruncated content item (transcript and/or comments).
        
        Args:
            link_id: Link identifier
            content_types: List of content types to retrieve ("transcript", "comments", or both)
            batch_data: Batch data
            
        Returns:
            Full content formatted string (no truncation)
        """
        data = batch_data.get(link_id)
        if not data:
            return f"Error: link_id {link_id} not found"
        display_name = get_content_display_name(link_id, data)
        
        parts = []
        
        if "transcript" in content_types:
            transcript = data.get("transcript", "")
            if transcript:
                parts.append(f"**完整转录内容**（{display_name}）\n{transcript}")
            else:
                parts.append(f"**转录内容**（{display_name}）\n(无转录内容)")
        
        if "comments" in content_types:
            comments = data.get("comments", [])
            if comments:
                parts.append(f"\n**完整评论内容**（{display_name}）")
                if isinstance(comments[0], dict):
                    # Bilibili format
                    formatted = self._format_comments([
                        {"content": c.get("content", ""), "likes": c.get("likes", 0), "replies": c.get("replies", 0)}
                        for c in comments
                    ])
                else:
                    # YouTube format - simple list of strings
                    formatted = "\n".join([f"- {c}" for c in comments])
                parts.append(formatted)
            else:
                parts.append(f"\n**评论内容**（{display_name}）\n(无评论内容)")
        
        return "\n".join(parts)
    
    def retrieve_by_marker(
        self,
        marker_text: str,
        link_id: str,
        content_type: str,
        context_window: int,
        batch_data: Dict[str, Any]
    ) -> str:
        """
        Retrieve full context around a specific marker.
        
        Args:
            marker_text: Marker text to find context for
            link_id: Link identifier
            content_type: "transcript" or "comments"
            context_window: Number of words around marker to include
            batch_data: Batch data
            
        Returns:
            Full context around marker (no truncation)
        """
        data = batch_data.get(link_id)
        if not data:
            return f"Error: link_id {link_id} not found"
        
        display_name = get_content_display_name(link_id, data)
        
        if content_type == "transcript":
            transcript = data.get("transcript", "")
            if not transcript:
                return f"Error: link_id {link_id} has no transcript"
            
            # Find marker text in transcript
            marker_lower = marker_text.lower()
            transcript_lower = transcript.lower()
            
            # Try to find marker text in transcript
            marker_index = transcript_lower.find(marker_lower)
            if marker_index == -1:
                # Try to find keywords from marker
                marker_words = marker_text.split()
                if marker_words:
                    # Use first few words as keywords
                    keywords = marker_words[:3]
                    return self.retrieve_by_keywords(link_id, keywords, batch_data, context_window)
                return f"(Marker '{marker_text}' not found in transcript)"
            
            # Extract context around marker
            words = transcript.split()
            marker_word_index = len(transcript[:marker_index].split())
            
            start_word = max(0, marker_word_index - context_window)
            end_word = min(len(words), marker_word_index + len(marker_text.split()) + context_window)
            
            context = " ".join(words[start_word:end_word])
            return f"**标记上下文**（{display_name}｜标记: {marker_text[:50]}...）\n{context}"
        
        elif content_type == "comments":
            # For comments, find comments that mention the marker
            keywords = marker_text.split()[:3]  # Use first few words as keywords
            comments_context = self.retrieve_matching_comments(link_id, keywords, batch_data, limit=50, sort_by="relevance")
            return f"**评论上下文**（{display_name}｜标记: {marker_text[:50]}...）\n{comments_context}"
        
        return f"Error: Unknown content_type {content_type}"
    
    def retrieve_by_topic(
        self,
        topic: str,
        source_link_ids: List[str],
        content_types: List[str],
        batch_data: Dict[str, Any]
    ) -> str:
        """
        Retrieve full content items that match a topic.
        
        Args:
            topic: Topic to filter by
            source_link_ids: List of link_ids to search in
            content_types: List of content types ("transcript", "comments", or both)
            batch_data: Batch data
            
        Returns:
            Full content items matching the topic (no truncation)
        """
        parts = []
        topic_lower = topic.lower()
        
        for link_id in source_link_ids:
            data = batch_data.get(link_id)
            if not data:
                continue
            display_name = get_content_display_name(link_id, data)
            
            summary = data.get("summary", {})
            transcript_summary = summary.get("transcript_summary", {})
            comments_summary = summary.get("comments_summary", {})
            
            # Check if topic matches
            topic_areas = transcript_summary.get("topic_areas", [])
            major_themes = comments_summary.get("major_themes", [])
            
            topic_match = (
                any(topic_lower in area.lower() for area in topic_areas) or
                any(topic_lower in theme.lower() for theme in major_themes)
            )
            
            if topic_match:
                # Retrieve full content for this item
                item_content = self.retrieve_full_content_item(link_id, content_types, batch_data)
                parts.append(f"**主题匹配内容项**：{display_name}\n{item_content}\n")
        
        if not parts:
            return f"(No content items found matching topic: {topic})"
        
        return "\n---\n".join(parts)
    
    def retrieve_by_marker_types(
        self,
        marker_types: List[str],
        link_id: str,
        content_type: str,
        batch_data: Dict[str, Any]
    ) -> str:
        """
        Retrieve full context for specific types of markers.
        
        Args:
            marker_types: List of marker types ("key_facts", "key_opinions", "key_datapoints", etc.)
            link_id: Link identifier
            content_type: "transcript" or "comments"
            batch_data: Batch data
            
        Returns:
            Full context for specified marker types (no truncation)
        """
        data = batch_data.get(link_id)
        if not data:
            return f"Error: link_id {link_id} not found"
        
        summary = data.get("summary", {})
        if not summary:
            return f"Error: link_id {link_id} has no summary"
        
        parts = []
        
        if content_type == "transcript":
            transcript_summary = summary.get("transcript_summary", {})
            transcript = data.get("transcript", "")
            
            if "key_facts" in marker_types:
                facts = transcript_summary.get("key_facts", [])
                parts.append(f"**关键事实标记** ({len(facts)} 个):")
                for fact in facts:
                    # Find context for each fact
                    context = self.retrieve_by_marker(fact, link_id, "transcript", 500, batch_data)
                    parts.append(f"\n标记: {fact}\n{context}\n")
            
            if "key_opinions" in marker_types:
                opinions = transcript_summary.get("key_opinions", [])
                parts.append(f"**关键观点标记** ({len(opinions)} 个):")
                for opinion in opinions:
                    context = self.retrieve_by_marker(opinion, link_id, "transcript", 500, batch_data)
                    parts.append(f"\n标记: {opinion}\n{context}\n")
            
            if "key_datapoints" in marker_types:
                datapoints = transcript_summary.get("key_datapoints", [])
                parts.append(f"**关键数据点标记** ({len(datapoints)} 个):")
                for datapoint in datapoints:
                    context = self.retrieve_by_marker(datapoint, link_id, "transcript", 500, batch_data)
                    parts.append(f"\n标记: {datapoint}\n{context}\n")
        
        elif content_type == "comments":
            comments_summary = summary.get("comments_summary", {})
            
            if "key_facts_from_comments" in marker_types:
                facts = comments_summary.get("key_facts_from_comments", [])
                parts.append(f"**评论中的关键事实** ({len(facts)} 个):")
                for fact in facts:
                    keywords = fact.split()[:3]
                    context = self.retrieve_matching_comments(link_id, keywords, batch_data, limit=10)
                    parts.append(f"\n标记: {fact}\n{context}\n")
            
            if "key_opinions_from_comments" in marker_types:
                opinions = comments_summary.get("key_opinions_from_comments", [])
                parts.append(f"**评论中的关键观点** ({len(opinions)} 个):")
                for opinion in opinions:
                    keywords = opinion.split()[:3]
                    context = self.retrieve_matching_comments(link_id, keywords, batch_data, limit=10)
                    parts.append(f"\n标记: {opinion}\n{context}\n")
        
        if not parts:
            return f"(No markers found for types: {marker_types})"
        
        return "\n".join(parts)


