"""Research session management.

This module handles saving and loading research sessions, including
the scratchpad and all findings.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, Optional, List, Iterable
from datetime import datetime
from loguru import logger


def _now_iso() -> str:
    return datetime.now().isoformat()


@dataclass
class StepDigest:
    """Structured digest summary for a completed step."""

    step_id: int
    goal_text: str = ""
    summary: str = ""
    points_of_interest: List[str] = field(default_factory=list)
    notable_evidence: List[Dict[str, Any]] = field(default_factory=list)
    revision_notes: Optional[str] = None
    text_units: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_payload(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["step_id"] = int(self.step_id)
        return payload

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "StepDigest":
        data = dict(payload or {})
        text_units = data.get("text_units") or []
        if isinstance(text_units, str):
            text_units = [text_units]
        return cls(
            step_id=int(data.get("step_id", 0)),
            goal_text=data.get("goal_text", ""),
            summary=data.get("summary", ""),
            points_of_interest=list(data.get("points_of_interest") or []),
            notable_evidence=list(data.get("notable_evidence") or []),
            revision_notes=data.get("revision_notes"),
            text_units=list(text_units),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
        )


class ResearchSession:
    """Manages research session state and persistence."""
    
    def __init__(self, session_id: Optional[str] = None, base_path: Optional[Path] = None):
        """
        Initialize research session.
        
        Args:
            session_id: Unique session identifier (auto-generated if not provided)
            base_path: Base path for storing sessions (defaults to data/research/sessions/)
        """
        if session_id is None:
            # Generate session ID from timestamp
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.session_id = session_id
        
        if base_path is None:
            # Default to project root/data/research/sessions/
            # __file__ = research/session.py; parent = research/; parent = project root
            self.base_path = Path(__file__).parent.parent / "data" / "research" / "sessions"
        else:
            self.base_path = Path(base_path)
        
        # Create directory if it doesn't exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Session data
        self.scratchpad: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "batch_id": None,
            "selected_goal": None,
            "research_plan": None,
            "status": "initialized"
        }
        self.phase_artifacts: Dict[str, Any] = {}
        self.step_digests: Dict[int, StepDigest] = {}
        
        # Performance optimization: Cache scratchpad summary to avoid rebuilding on every access
        self._scratchpad_summary_cache: Optional[str] = None
        self._scratchpad_cache_valid: bool = False
        
        # Session file path
        self.session_file = self.base_path / f"session_{session_id}.json"
        
        logger.info(f"Initialized ResearchSession: {session_id}")
    
    def save(self):
        """Save session to disk."""
        session_data = {
            "metadata": self.metadata,
            "scratchpad": self.scratchpad,
            "phase_artifacts": self.phase_artifacts,
            "step_digests": [
                digest.to_payload()
                for _, digest in sorted(self.step_digests.items(), key=lambda item: item[0])
            ],
        }
        
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved session to {self.session_file}")
        except Exception as e:
            logger.error(f"Error saving session: {str(e)}")
            raise
    
    @classmethod
    def load(cls, session_id: str, base_path: Optional[Path] = None) -> 'ResearchSession':
        """
        Load existing session from disk.
        
        Args:
            session_id: Session identifier
            base_path: Base path for sessions
            
        Returns:
            Loaded ResearchSession instance
        """
        if base_path is None:
            base_path = Path(__file__).parent.parent / "data" / "research" / "sessions"
        
        session_file = Path(base_path) / f"session_{session_id}.json"
        
        if not session_file.exists():
            raise FileNotFoundError(f"Session file not found: {session_file}")
        
        session = cls(session_id=session_id, base_path=base_path)
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            session.metadata = session_data.get("metadata", {})
            session.scratchpad = session_data.get("scratchpad", {})
            session.phase_artifacts = session_data.get("phase_artifacts", {})
            
            # Invalidate cache after loading from disk
            session._scratchpad_cache_valid = False
            
            digests_payload = session_data.get("step_digests") or []
            session.step_digests = {}
            for item in digests_payload:
                try:
                    digest = StepDigest.from_payload(item)
                    session.step_digests[digest.step_id] = digest
                except Exception as exc:
                    logger.warning("Failed to load step digest entry %s: %s", item, exc)
            
            logger.info(f"Loaded session from {session_file}")
        except Exception as e:
            logger.error(f"Error loading session: {str(e)}")
            raise
        
        return session
    
    @classmethod
    def create_or_load(cls, session_id: str, base_path: Optional[Path] = None) -> 'ResearchSession':
        """
        Load existing session or create a new one if it doesn't exist.
        
        Args:
            session_id: Session identifier (also used as batch_id)
            base_path: Base path for sessions
            
        Returns:
            ResearchSession instance (either loaded or newly created)
        """
        try:
            # Try to load existing session
            session = cls.load(session_id, base_path)
            logger.info(f"Loaded existing session: {session_id}")
            return session
        except FileNotFoundError:
            # Create new session if it doesn't exist
            session = cls(session_id=session_id, base_path=base_path)
            # Set batch_id in metadata
            session.set_metadata("batch_id", session_id)
            logger.info(f"Created new session: {session_id}")
            return session
    
    def update_scratchpad(
        self, 
        step_id: int, 
        findings: Dict[str, Any], 
        insights: str = "", 
        confidence: float = 0.0,
        sources: Optional[List[str]] = None,
        *,
        autosave: bool = True
    ):
        """
        Update scratchpad with findings from a step.
        
        Args:
            step_id: Step identifier
            findings: Structured findings
            insights: Key insights summary
            confidence: Confidence score (0.0-1.0)
            sources: List of source link_ids (enhancement #2)
            autosave: Whether to save session to disk after update (default: True)
        """
        # Invalidate cache since scratchpad is changing
        self._scratchpad_cache_valid = False
        
        scratchpad_entry = {
            "step_id": step_id,
            "findings": findings,
            "insights": insights,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add sources if provided (enhancement #2)
        if sources:
            scratchpad_entry["sources"] = sources
        
        self.scratchpad[f"step_{step_id}"] = scratchpad_entry
        
        # Auto-save can be throttled by caller for performance
        if autosave:
            self.save()
        
        logger.debug(f"Updated scratchpad for step {step_id}")
    
    def get_scratchpad_summary(self) -> str:
        """
        Get scratchpad contents as a formatted string for prompts.
        
        Uses cached summary for performance - cache is invalidated when scratchpad updates.
        
        Returns:
            Formatted scratchpad string with source attribution (enhancement #2)
        """
        # Return cached summary if valid
        if self._scratchpad_cache_valid and self._scratchpad_summary_cache is not None:
            return self._scratchpad_summary_cache
        
        # Rebuild summary
        if not self.scratchpad:
            self._scratchpad_summary_cache = "暂无发现。"
            self._scratchpad_cache_valid = True
            return self._scratchpad_summary_cache
        
        summary_parts = []
        for step_key in sorted(self.scratchpad.keys()):
            step_data = self.scratchpad[step_key]
            step_summary = f"步骤 {step_data['step_id']}: {step_data.get('insights', '')}\n"
            
            # Extract findings with points of interest
            findings = step_data.get('findings', {})
            
            # Add summary if available
            if isinstance(findings, dict) and 'summary' in findings:
                step_summary += f"摘要: {findings['summary']}\n"
            
            # Add points of interest if available
            if isinstance(findings, dict) and 'points_of_interest' in findings:
                poi = findings['points_of_interest']
                poi_summary = []
                
                if poi.get('key_claims'):
                    claims_count = len(poi['key_claims'])
                    poi_summary.append(f"关键论点: {claims_count} 个")
                
                if poi.get('notable_evidence'):
                    evidence_count = len(poi['notable_evidence'])
                    poi_summary.append(f"重要证据: {evidence_count} 个")
                
                if poi.get('controversial_topics'):
                    topics_count = len(poi['controversial_topics'])
                    poi_summary.append(f"争议话题: {topics_count} 个")
                
                if poi.get('surprising_insights'):
                    insights_count = len(poi['surprising_insights'])
                    poi_summary.append(f"意外洞察: {insights_count} 个")
                
                if poi.get('specific_examples'):
                    examples_count = len(poi['specific_examples'])
                    poi_summary.append(f"具体例子: {examples_count} 个")
                
                if poi.get('open_questions'):
                    questions_count = len(poi['open_questions'])
                    poi_summary.append(f"开放问题: {questions_count} 个")
                
                if poi_summary:
                    step_summary += f"兴趣点: {', '.join(poi_summary)}\n"
                
                # Extract and format quotes/examples prominently (Solution 9)
                quotes_section = "\n**重要引述和例子**:\n"
                quotes_found = False
                
                # Key claims with quotes
                for claim in poi.get('key_claims', [])[:5]:
                    if isinstance(claim, dict) and claim.get('claim'):
                        quotes_found = True
                        quotes_section += f"- \"{claim['claim']}\""
                        if claim.get('supporting_evidence'):
                            evidence_text = claim['supporting_evidence']
                            if len(evidence_text) > 100:
                                evidence_text = evidence_text[:100] + "..."
                            quotes_section += f" (证据: {evidence_text})"
                        quotes_section += "\n"
                
                # Notable evidence quotes
                for evidence in poi.get('notable_evidence', [])[:5]:
                    if isinstance(evidence, dict) and evidence.get('quote'):
                        quotes_found = True
                        quotes_section += f"- \"{evidence['quote']}\""
                        if evidence.get('description'):
                            desc_text = evidence['description']
                            if len(desc_text) > 80:
                                desc_text = desc_text[:80] + "..."
                            quotes_section += f" ({desc_text})"
                        quotes_section += "\n"
                
                # Specific examples
                for example in poi.get('specific_examples', [])[:5]:
                    if isinstance(example, dict) and example.get('example'):
                        quotes_found = True
                        quotes_section += f"- 例子: {example['example']}"
                        if example.get('context'):
                            context_text = example['context']
                            if len(context_text) > 80:
                                context_text = context_text[:80] + "..."
                            quotes_section += f" (上下文: {context_text})"
                        quotes_section += "\n"
                
                if quotes_found:
                    step_summary += quotes_section + "\n"
            
            # Add full findings JSON
            step_summary += f"发现: {json.dumps(findings, ensure_ascii=False, indent=2)}"
            
            # Add source information if available (enhancement #2)
            if 'sources' in step_data and step_data['sources']:
                sources_str = ", ".join(step_data['sources'])
                step_summary += f"\n来源: {sources_str}"
            
            summary_parts.append(step_summary)
        
        # Cache the result for future calls
        self._scratchpad_summary_cache = "\n\n".join(summary_parts)
        self._scratchpad_cache_valid = True
        
        return self._scratchpad_summary_cache

    # ------------------------------------------------------------------
    # Step digest helpers
    # ------------------------------------------------------------------
    def upsert_step_digest(self, digest: StepDigest, *, autosave: bool = True) -> None:
        """Persist or update the structured digest for a step."""
        digest.updated_at = _now_iso()
        self.step_digests[int(digest.step_id)] = digest
        if autosave:
            self.save()

    def get_step_digest(self, step_id: int) -> Optional[StepDigest]:
        return self.step_digests.get(int(step_id))

    def get_step_digests_before(self, step_id: int) -> List[StepDigest]:
        target = int(step_id)
        return [
            digest
            for _, digest in sorted(self.step_digests.items(), key=lambda item: item[0])
            if digest.step_id < target
        ]

    def get_digest_text_units_before(self, step_id: int) -> List[str]:
        units: List[str] = []
        for digest in self.get_step_digests_before(step_id):
            units.extend(digest.text_units or [])
        return [u for u in units if u and isinstance(u, str)]

    def aggregate_step_digests(
        self,
        upto_step_id: Optional[int] = None,
        *,
        token_cap: Optional[int] = None,
    ) -> str:
        """
        Render cumulative digest text up to the specified step.

        Args:
            upto_step_id: exclusive upper bound (current step id).
            token_cap: maximum tokens to include (approximate, 4 chars per token).
        """
        digests = self.get_step_digests_before(upto_step_id or 0) if upto_step_id else [
            digest for _, digest in sorted(self.step_digests.items(), key=lambda item: item[0])
        ]
        if not digests:
            return "暂无前序摘要。"

        char_cap = None
        if isinstance(token_cap, int) and token_cap > 0:
            char_cap = max(200, token_cap * 4)

        def _safe_join(values: Iterable[str]) -> str:
            return "; ".join(v for v in values if isinstance(v, str) and v.strip())

        lines: List[str] = []
        used = 0
        for digest in digests:
            header = f"步骤 {digest.step_id}：{digest.goal_text}".strip()
            if char_cap and used + len(header) + 1 > char_cap:
                break
            lines.append(header)
            used += len(header) + 1

            if digest.summary:
                summary_line = f"  摘要：{digest.summary.strip()}"
                if char_cap and used + len(summary_line) + 1 > char_cap:
                    break
                lines.append(summary_line)
                used += len(summary_line) + 1

            poi_text = _safe_join(digest.points_of_interest)
            if poi_text:
                poi_line = f"  兴趣点：{poi_text}"
                if char_cap and used + len(poi_line) + 1 > char_cap:
                    break
                lines.append(poi_line)
                used += len(poi_line) + 1

            if digest.notable_evidence:
                for evidence in digest.notable_evidence:
                    description = evidence.get("description") or evidence.get("quote") or ""
                    if not description:
                        continue
                    ev_line = f"    证据：{description}"
                    if char_cap and used + len(ev_line) + 1 > char_cap:
                        break
                    lines.append(ev_line)
                    used += len(ev_line) + 1
                if char_cap and used >= char_cap:
                    break

        if char_cap and used >= char_cap:
            lines.append("...（已截断，更多历史内容未展示）")

        return "\n".join(lines) if lines else "暂无前序摘要。"
    
    def aggregate_all_phase3_outputs(
        self,
        upto_step_id: Optional[int] = None,
        *,
        token_cap: Optional[int] = None,
    ) -> str:
        """
        Render cumulative digest text including ALL phase 3 step outputs.
        Combines both digest summaries and full outputs from phase artifacts.

        Args:
            upto_step_id: exclusive upper bound (current step id).
            token_cap: maximum tokens to include (approximate, 4 chars per token).
        """
        char_cap = None
        if isinstance(token_cap, int) and token_cap > 0:
            char_cap = max(200, token_cap * 4)

        lines: List[str] = []
        used = 0

        # Get phase 3 artifact containing all step outputs
        phase3_artifact = self.get_phase_artifact("phase3", {}) or {}
        phase3_result = phase3_artifact.get("phase3_result", {}) if isinstance(phase3_artifact, dict) else {}
        findings_list = phase3_result.get("findings", []) if isinstance(phase3_result, dict) else []

        # Filter findings by step_id if upto_step_id is provided
        filtered_findings = []
        if upto_step_id is not None:
            for finding in findings_list:
                if isinstance(finding, dict):
                    step_id = finding.get("step_id")
                    if step_id is not None and isinstance(step_id, int) and step_id < upto_step_id:
                        filtered_findings.append(finding)
        else:
            filtered_findings = findings_list

        # Sort by step_id
        filtered_findings.sort(key=lambda x: x.get("step_id", 0) if isinstance(x, dict) else 0)

        # Track which step_ids we've processed from artifacts
        processed_step_ids = set()
        for finding in filtered_findings:
            step_id = finding.get("step_id")
            if step_id is not None:
                processed_step_ids.add(step_id)

        # Format each step output from artifacts (full outputs)
        for finding in filtered_findings:
            if not isinstance(finding, dict):
                continue

            step_id = finding.get("step_id")
            findings_data = finding.get("findings", {})
            
            if not isinstance(findings_data, dict):
                continue

            # Get goal from digest if available, or use a placeholder
            digest = self.step_digests.get(step_id) if step_id is not None else None
            goal_text = digest.goal_text if digest and digest.goal_text else f"步骤 {step_id}"

            # Header
            header = f"步骤 {step_id}：{goal_text}".strip()
            if char_cap and used + len(header) + 1 > char_cap:
                break
            lines.append(header)
            used += len(header) + 1

            # Summary
            summary = findings_data.get("summary", "")
            if isinstance(summary, str) and summary.strip():
                summary_line = f"  摘要：{summary.strip()}"
                if char_cap and used + len(summary_line) + 1 > char_cap:
                    break
                lines.append(summary_line)
                used += len(summary_line) + 1

            # Article (full article content)
            article = findings_data.get("article", "")
            if isinstance(article, str) and article.strip():
                article_line = f"  完整文章：{article.strip()}"
                if char_cap:
                    # Truncate article if needed
                    remaining = char_cap - used - len("  完整文章：\n")
                    if remaining < len(article_line):
                        article_line = f"  完整文章：{article[:remaining]}..."
                    if used + len(article_line) + 1 > char_cap:
                        break
                lines.append(article_line)
                used += len(article_line) + 1

            # Points of Interest
            poi = findings_data.get("points_of_interest", {})
            if isinstance(poi, dict):
                poi_sections = []
                for key, values in poi.items():
                    if not isinstance(values, list):
                        continue
                    for entry in values:
                        if isinstance(entry, dict):
                            # Extract text from various fields
                            text = (
                                entry.get("claim") or 
                                entry.get("topic") or 
                                entry.get("example") or 
                                entry or 
                                ""
                            )
                            if isinstance(text, str) and text.strip():
                                poi_sections.append(f"{key}: {text.strip()}")
                        elif isinstance(entry, str) and entry.strip():
                            poi_sections.append(f"{key}: {entry.strip()}")
                
                if poi_sections:
                    poi_text = " | ".join(poi_sections[:10])  # Limit to 10 items
                    poi_line = f"  兴趣点：{poi_text}"
                    if char_cap and used + len(poi_line) + 1 > char_cap:
                        break
                    lines.append(poi_line)
                    used += len(poi_line) + 1

            # Analysis Details
            analysis_details = findings_data.get("analysis_details", {})
            if isinstance(analysis_details, dict):
                # Five whys
                five_whys = analysis_details.get("five_whys", [])
                if isinstance(five_whys, list) and five_whys:
                    why_texts = []
                    for why_entry in five_whys[:3]:  # Limit to first 3 levels
                        if isinstance(why_entry, dict):
                            question = why_entry.get("question", "")
                            answer = why_entry.get("answer", "")
                            if question and answer:
                                why_texts.append(f"{question} → {answer}")
                    if why_texts:
                        why_line = f"  分析：{' | '.join(why_texts)}"
                        if char_cap and used + len(why_line) + 1 > char_cap:
                            break
                        lines.append(why_line)
                        used += len(why_line) + 1

                # Assumptions
                assumptions = analysis_details.get("assumptions", [])
                if isinstance(assumptions, list) and assumptions:
                    assump_text = " | ".join(str(a) for a in assumptions[:5] if a)
                    if assump_text:
                        assump_line = f"  假设：{assump_text}"
                        if char_cap and used + len(assump_line) + 1 > char_cap:
                            break
                        lines.append(assump_line)
                        used += len(assump_line) + 1

                # Uncertainties
                uncertainties = analysis_details.get("uncertainties", [])
                if isinstance(uncertainties, list) and uncertainties:
                    uncert_text = " | ".join(str(u) for u in uncertainties[:5] if u)
                    if uncert_text:
                        uncert_line = f"  不确定性：{uncert_text}"
                        if char_cap and used + len(uncert_line) + 1 > char_cap:
                            break
                        lines.append(uncert_line)
                        used += len(uncert_line) + 1

            # Insights
            insights = finding.get("insights", "")
            if isinstance(insights, str) and insights.strip():
                insights_line = f"  洞察：{insights.strip()}"
                if char_cap and used + len(insights_line) + 1 > char_cap:
                    break
                lines.append(insights_line)
                used += len(insights_line) + 1

            # Confidence
            confidence = finding.get("confidence")
            if confidence is not None:
                conf_line = f"  信心度：{confidence:.2f}"
                if char_cap and used + len(conf_line) + 1 > char_cap:
                    break
                lines.append(conf_line)
                used += len(conf_line) + 1

            # Add separator between steps
            if char_cap and used + 2 > char_cap:
                break
            lines.append("")
            used += 1

            if char_cap and used >= char_cap:
                break

        # Also include digests for steps that aren't in artifacts yet (for steps completed during current execution)
        digests = self.get_step_digests_before(upto_step_id or 0) if upto_step_id else [
            digest for _, digest in sorted(self.step_digests.items(), key=lambda item: item[0])
        ]
        
        for digest in digests:
            # Skip if we already processed this step from artifacts
            if digest.step_id in processed_step_ids:
                continue
            
            # Only include if it's before the current step
            if upto_step_id is not None and digest.step_id >= upto_step_id:
                continue
            
            # Format digest (summary format)
            header = f"步骤 {digest.step_id}：{digest.goal_text}".strip()
            if char_cap and used + len(header) + 1 > char_cap:
                break
            lines.append(header)
            used += len(header) + 1

            if digest.summary:
                summary_line = f"  摘要：{digest.summary.strip()}"
                if char_cap and used + len(summary_line) + 1 > char_cap:
                    break
                lines.append(summary_line)
                used += len(summary_line) + 1

            poi_text = "; ".join(digest.points_of_interest[:10]) if digest.points_of_interest else ""
            if poi_text:
                poi_line = f"  兴趣点：{poi_text}"
                if char_cap and used + len(poi_line) + 1 > char_cap:
                    break
                lines.append(poi_line)
                used += len(poi_line) + 1

            if digest.notable_evidence:
                for evidence in digest.notable_evidence[:5]:
                    description = evidence.get("description") or evidence.get("quote") or ""
                    if not description:
                        continue
                    ev_line = f"    证据：{description}"
                    if char_cap and used + len(ev_line) + 1 > char_cap:
                        break
                    lines.append(ev_line)
                    used += len(ev_line) + 1
                if char_cap and used >= char_cap:
                    break

            # Add separator
            if char_cap and used + 2 > char_cap:
                break
            lines.append("")
            used += 1

            if char_cap and used >= char_cap:
                break

        if char_cap and used >= char_cap:
            lines.append("...（已截断，更多历史内容未展示）")

        if not lines:
            # Final fallback
            return "暂无前序摘要。"

        return "\n".join(lines)
    
    def set_metadata(self, key: str, value: Any):
        """Update metadata."""
        self.metadata[key] = value
        self.metadata["updated_at"] = datetime.now().isoformat()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.metadata.get(key, default)

    def save_phase_artifact(self, phase_key: str, data: Any, *, autosave: bool = True) -> None:
        """
        Persist artifacts for a specific phase.

        Args:
            phase_key: Logical phase identifier (e.g., "phase0", "phase3_step_1").
            data: Serializable artifact payload.
            autosave: Whether to persist immediately.
        """
        self.phase_artifacts[phase_key] = {
            "data": data,
            "updated_at": datetime.now().isoformat(),
        }
        if autosave:
            self.save()

    def get_phase_artifact(self, phase_key: str, default: Any = None) -> Any:
        """
        Retrieve stored artifacts for a phase.

        Args:
            phase_key: Logical phase identifier.
            default: Value to return if artifact absent.
        """
        entry = self.phase_artifacts.get(phase_key)
        if not entry:
            return default
        return entry.get("data", default)

    def drop_phase_artifact(self, phase_key: str, *, autosave: bool = True) -> None:
        """
        Remove artifacts for a phase.

        Args:
            phase_key: Logical phase identifier.
            autosave: Whether to persist removal immediately.
        """
        if phase_key in self.phase_artifacts:
            self.phase_artifacts.pop(phase_key, None)
            if autosave:
                self.save()

    def drop_phase_artifacts(self, phase_keys: Iterable[str], *, autosave: bool = True) -> None:
        """
        Remove multiple phase artifacts in one call.

        Args:
            phase_keys: Iterable of logical phase identifiers.
            autosave: Whether to persist removal immediately.
        """
        removed = False
        for key in phase_keys:
            if key in self.phase_artifacts:
                self.phase_artifacts.pop(key, None)
                removed = True
        if removed and autosave:
            self.save()

