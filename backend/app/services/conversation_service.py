"""
Conversation context management and LLM orchestration for right-column feedback.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
import asyncio
import json
import threading
import uuid
from string import Template
from typing import TYPE_CHECKING, Deque, Dict, List, Optional, Tuple, Literal, Any

from loguru import logger

from app.services.conversation_storage import (
    load_conversation_state,
    save_conversation_state,
)
from core.config import Config

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.websocket.manager import WebSocketManager

try:
    from research.client import QwenStreamingClient
except Exception as exc:  # pragma: no cover - handled lazily
    logger.warning(f"Unable to import QwenStreamingClient at module load: {exc}")
    QwenStreamingClient = None  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SESSION_DIR = PROJECT_ROOT / "data" / "research" / "sessions"

ConversationRole = Literal["user", "assistant", "system"]
MessageStatus = Literal["queued", "in_progress", "completed", "error"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ConversationMessage:
    id: str
    role: ConversationRole
    content: str
    status: MessageStatus
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = self.created_at
        payload["updated_at"] = self.updated_at
        return payload


@dataclass
class ProceduralPromptState:
    prompt_id: str
    prompt: str
    choices: List[str]
    created_at: str = field(default_factory=_now_iso)
    awaiting_response: bool = True


@dataclass
class StreamSnapshot:
    stream_id: str
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    phase: Optional[str] = None
    updated_at: str = field(default_factory=_now_iso)


@dataclass
class PhaseHistoryEntry:
    phase: str
    completed_at: str
    summary: Optional[str] = None


@dataclass
class ContextRequirement:
    key: str
    label: str
    description: str
    required: bool = True
    fulfilled: bool = False


@dataclass
class ContextAttachment:
    id: str
    request_id: str
    slot_key: str
    label: str
    content: str
    provided_by: str = "user"
    provided_at: str = field(default_factory=_now_iso)


@dataclass
class ContextRequest:
    id: str
    user_message_id: str
    reason: str
    created_at: str = field(default_factory=_now_iso)
    status: Literal["pending", "satisfied", "expired", "cancelled"] = "pending"
    requirements: List[ContextRequirement] = field(default_factory=list)
    attachments: List[ContextAttachment] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchConversationState:
    batch_id: str
    session_id: Optional[str] = None
    active_phase: Optional[str] = None
    phase_history: List[PhaseHistoryEntry] = field(default_factory=list)
    goals: List[Dict[str, Any]] = field(default_factory=list)
    plan: List[Dict[str, Any]] = field(default_factory=list)
    synthesized_goal: Optional[Dict[str, Any]] = None
    stream_snapshot: Optional[StreamSnapshot] = None
    procedural_prompt: Optional[ProceduralPromptState] = None
    deferred_messages: Deque[Tuple[str, str]] = field(default_factory=deque)
    conversation_messages: Dict[str, ConversationMessage] = field(default_factory=dict)
    conversation_order: Deque[str] = field(default_factory=lambda: deque(maxlen=100))
    known_constraints: List[str] = field(default_factory=list)
    last_context_refresh: str = field(default_factory=_now_iso)
    hydrated_session_id: Optional[str] = None
    session_snapshot_mtime: Optional[float] = None
    writing_style: str = "explanatory"
    data_abstract: Optional[str] = None
    user_guidance: Optional[str] = None
    system_role_description: Optional[str] = None
    research_role_rationale: Optional[str] = None
    phase3_summaries: List[Dict[str, Any]] = field(default_factory=list)
    phase3_points: List[Dict[str, Any]] = field(default_factory=list)
    context_requests: Dict[str, ContextRequest] = field(default_factory=dict)
    context_request_order: Deque[str] = field(default_factory=lambda: deque(maxlen=50))
    awaiting_context_for_message: Dict[str, str] = field(default_factory=dict)
    # Deduplication: track recently processed messages (content hash -> timestamp)
    recent_messages: Dict[str, float] = field(default_factory=dict)


@dataclass
class ConversationResult:
    status: Literal["ok", "queued", "context_required"]
    user_message_id: str
    assistant_message_id: Optional[str] = None
    reply: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    context_bundle: Optional[Dict[str, Any]] = None
    queued_reason: Optional[str] = None
    context_request_id: Optional[str] = None
    required_context: Optional[List[Dict[str, Any]]] = None


class ConversationContextService:
    """
    Tracks per-batch research context and orchestrates conversational replies.
    """

    def __init__(self):
        self._states: Dict[str, BatchConversationState] = {}
        self._lock = threading.RLock()
        self._llm_client: Optional[QwenStreamingClient] = None
        self._ws_manager: Optional["WebSocketManager"] = None
        try:
            self._config = Config()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"Failed to load config.yaml: {exc}")
            self._config = None
        self._session_dir = SESSION_DIR
        self._style_cache: Dict[str, str] = {}
        self._prompt_template: Optional[Template] = None
        self._prompt_template_path = (
            PROJECT_ROOT
            / "research"
            / "prompts"
            / "right_column_chat"
            / "context_sheet.md"
        )
        self._phase_playbook: Dict[str, str] = {
            "phase0": "Phase 0 focuses on validating scraped data quality, coverage, and readiness.",
            "phase0_5": "Phase 0.5 synthesizes an initial research role and tone calibration.",
            "phase1": "Phase 1 discovers research goals and clarifies investigative angles.",
            "phase2": "Phase 2 finalizes research goals into a unified comprehensive topic.",
            "phase3": "Phase 3 executes the plan step-by-step, extracting findings and evidence.",
            "phase4": "Phase 4 compiles final reports, ensuring coherence and coverage.",
            "research": "Research mode coordinates streaming outputs across active phases.",
        }

    def set_websocket_manager(self, manager: Optional["WebSocketManager"]):
        """Attach websocket manager for streaming conversation updates."""
        self._ws_manager = manager

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_state(self, batch_id: str) -> BatchConversationState:
        with self._lock:
            state = self._states.get(batch_id)
            if state is None:
                state = BatchConversationState(batch_id=batch_id)
                self._restore_state_from_disk(batch_id, state)
                self._states[batch_id] = state
            return state

    def _restore_state_from_disk(self, batch_id: str, state: BatchConversationState):
        snapshot = load_conversation_state(batch_id)
        if not snapshot:
            return

        with self._lock:
            state.session_id = snapshot.get("session_id") or state.session_id
            state.active_phase = snapshot.get("active_phase") or state.active_phase
            state.goals = snapshot.get("goals") or state.goals
            state.plan = snapshot.get("plan") or state.plan
            state.synthesized_goal = snapshot.get("synthesized_goal") or state.synthesized_goal
            state.known_constraints = snapshot.get("known_constraints") or state.known_constraints

            phase_history = snapshot.get("phase_history") or []
            state.phase_history = [
                PhaseHistoryEntry(
                    phase=item.get("phase", ""),
                    completed_at=item.get("completed_at", _now_iso()),
                    summary=item.get("summary"),
                )
                for item in phase_history
                if isinstance(item, dict) and item.get("phase")
            ]

            messages = snapshot.get("messages") or []
            for item in messages:
                if not isinstance(item, dict):
                    continue
                try:
                    message = ConversationMessage(
                        id=item.get("id", f"restored-{uuid.uuid4().hex}"),
                        role=item.get("role", "assistant"),
                        content=item.get("content", ""),
                        status=item.get("status", "completed"),
                        created_at=item.get("created_at", _now_iso()),
                        updated_at=item.get("updated_at", _now_iso()),
                        metadata=item.get("metadata") or {},
                    )
                except Exception:
                    continue
                state.conversation_messages[message.id] = message
                if message.id in state.conversation_order:
                    state.conversation_order.remove(message.id)
                state.conversation_order.append(message.id)

            state.writing_style = snapshot.get("writing_style", state.writing_style)
            state.data_abstract = snapshot.get("data_abstract", state.data_abstract)
            state.user_guidance = snapshot.get("user_guidance", state.user_guidance)
            state.system_role_description = snapshot.get("system_role_description", state.system_role_description)
            state.research_role_rationale = snapshot.get("research_role_rationale", state.research_role_rationale)
            state.phase3_summaries = snapshot.get("phase3_summaries", state.phase3_summaries)
            state.phase3_points = snapshot.get("phase3_points", state.phase3_points)
            request_items = snapshot.get("context_requests") or []
            state.context_requests.clear()
            state.context_request_order.clear()
            for item in request_items:
                try:
                    requirements = [
                        ContextRequirement(
                            key=req.get("key", f"slot-{uuid.uuid4().hex[:6]}"),
                            label=req.get("label", "未命名需求"),
                            description=req.get("description", ""),
                            required=req.get("required", True),
                            fulfilled=req.get("fulfilled", False),
                        )
                        for req in item.get("requirements", [])
                    ]
                    attachments = [
                        ContextAttachment(
                            id=att.get("id", f"attachment-{uuid.uuid4().hex[:6]}"),
                            request_id=item.get("id", ""),
                            slot_key=att.get("slot_key", "unknown"),
                            label=att.get("label", "附件"),
                            content=att.get("content", ""),
                            provided_by=att.get("provided_by", "user"),
                            provided_at=att.get("provided_at", _now_iso()),
                        )
                        for att in item.get("attachments", [])
                    ]
                    request = ContextRequest(
                        id=item.get("id", f"ctx-{uuid.uuid4().hex[:6]}"),
                        user_message_id=item.get("user_message_id", ""),
                        reason=item.get("reason", ""),
                        created_at=item.get("created_at", _now_iso()),
                        status=item.get("status", "pending"),
                        requirements=requirements,
                        attachments=attachments,
                        metadata=item.get("metadata") or {},
                    )
                except Exception:
                    continue
                state.context_requests[request.id] = request
                if request.id in state.context_request_order:
                    state.context_request_order.remove(request.id)
                state.context_request_order.append(request.id)
            awaiting_map = snapshot.get("awaiting_context_for_message") or {}
            state.awaiting_context_for_message = dict(awaiting_map)

    def _persist_state(self, batch_id: str):
        with self._lock:
            state = self._states.get(batch_id)
            if not state:
                return
            ordered_ids = list(state.conversation_order)
            messages = []
            for message_id in ordered_ids:
                message = state.conversation_messages.get(message_id)
                if message:
                    messages.append(message.to_payload())

            payload = {
                "batch_id": batch_id,
                "session_id": state.session_id,
                "active_phase": state.active_phase,
                "phase_history": [asdict(entry) for entry in state.phase_history],
                "goals": state.goals,
                "plan": state.plan,
                "synthesized_goal": state.synthesized_goal,
                "known_constraints": state.known_constraints,
                "updated_at": _now_iso(),
                "messages": messages,
                "writing_style": state.writing_style,
                "data_abstract": state.data_abstract,
                "user_guidance": state.user_guidance,
                "system_role_description": state.system_role_description,
                "research_role_rationale": state.research_role_rationale,
                "phase3_summaries": state.phase3_summaries,
                "phase3_points": state.phase3_points,
                "context_requests": [
                    self._serialize_context_request(state.context_requests[request_id])
                    for request_id in state.context_request_order
                    if request_id in state.context_requests
                ],
                "awaiting_context_for_message": state.awaiting_context_for_message,
            }

        save_conversation_state(batch_id, payload)

    def _serialize_context_request(self, request: ContextRequest) -> Dict[str, Any]:
        return {
            "id": request.id,
            "user_message_id": request.user_message_id,
            "reason": request.reason,
            "created_at": request.created_at,
            "status": request.status,
            "requirements": [asdict(req) for req in request.requirements],
            "attachments": [asdict(att) for att in request.attachments],
            "metadata": request.metadata,
        }

    def _context_request_to_dict(self, request: ContextRequest) -> Dict[str, Any]:
        return {
            "id": request.id,
            "user_message_id": request.user_message_id,
            "reason": request.reason,
            "status": request.status,
            "created_at": request.created_at,
            "requirements": [asdict(req) for req in request.requirements],
            "attachments": [
                {
                    "id": att.id,
                    "slot_key": att.slot_key,
                    "label": att.label,
                    "content_preview": att.content[:280],
                    "provided_by": att.provided_by,
                    "provided_at": att.provided_at,
                }
                for att in request.attachments
            ],
            "metadata": request.metadata,
        }

    def _find_first_combined_abstract(self, session_data: Dict[str, Any]) -> Optional[str]:
        artifacts = session_data.get("phase_artifacts") or {}
        for phase_payload in artifacts.values():
            if not isinstance(phase_payload, dict):
                continue
            data = phase_payload.get("data") or {}
            if isinstance(data, dict):
                candidate = (
                    data.get("combined_abstract")
                    or data.get("data_abstract")
                )
                if isinstance(candidate, str) and candidate.strip():
                    return candidate
        metadata = session_data.get("metadata") or {}
        candidate = metadata.get("combined_abstract")
        if isinstance(candidate, str) and candidate.strip():
            return candidate
        return None

    def _extract_phase3_highlights(
        self, session_data: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        artifacts = session_data.get("phase_artifacts") or {}
        phase3 = artifacts.get("phase3") or {}
        data = phase3.get("data") or {}
        result = data.get("phase3_result") or {}
        findings = result.get("findings") or []
        summaries: List[Dict[str, Any]] = []
        poi_entries: List[Dict[str, Any]] = []

        for entry in findings:
            if not isinstance(entry, dict):
                continue
            step_id = entry.get("step_id")
            nested = entry.get("findings") or {}
            nested_findings = nested.get("findings") or {}
            summary = nested_findings.get("summary")
            if isinstance(summary, str) and summary.strip():
                summaries.append(
                    {
                        "step_id": step_id,
                        "summary": self._truncate_text(summary.strip(), 1200),
                    }
                )
            poi_block = nested_findings.get("points_of_interest") or {}
            key_claims = poi_block.get("key_claims")
            if isinstance(key_claims, list) and key_claims:
                bullets: List[str] = []
                for claim in key_claims[:3]:
                    if not isinstance(claim, dict):
                        continue
                    claim_text = claim.get("claim")
                    if not isinstance(claim_text, str) or not claim_text.strip():
                        continue
                    evidence = claim.get("supporting_evidence")
                    line = f"- {claim_text.strip()}"
                    if isinstance(evidence, str) and evidence.strip():
                        line += f"（证据：{self._truncate_text(evidence.strip(), 140)}）"
                    bullets.append(line)
                if bullets:
                    poi_entries.append(
                        {
                            "step_id": step_id,
                            "points": "\n".join(bullets),
                        }
                    )
        return summaries[:8], poi_entries[:8]

    def _truncate_text(self, value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[: limit - 3] + "..."

    def _load_style_fragment(self, style_key: Optional[str]) -> str:
        key = (style_key or "explanatory").lower()
        if key in self._style_cache:
            return self._style_cache[key]

        candidates = [
            PROJECT_ROOT / "research" / "prompts" / "_partials" / f"style_{key}_cn.md",
            PROJECT_ROOT
            / "research"
            / "prompts"
            / "phase0_5_role_generation"
            / "styles"
            / f"style_{key}_cn.md",
        ]
        content = ""
        for path in candidates:
            try:
                if path.exists():
                    content = path.read_text(encoding="utf-8").strip()
                    break
            except Exception as exc:  # pragma: no cover
                logger.debug(f"Failed to load style fragment {path}: {exc}")
        if not content:
            content = "保持专业、清晰且结构化的中文表达。"
        self._style_cache[key] = content
        return content

    def _get_prompt_template(self) -> Template:
        if self._prompt_template is None:
            try:
                template_text = self._prompt_template_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                template_text = (
                    "## 用户输入\n${user_input}\n\n## 系统上下文\n${system_context_sections}"
                )
            self._prompt_template = Template(template_text)
        return self._prompt_template

    def _format_supplied_context(self, attachments: List[ContextAttachment]) -> str:
        if not attachments:
            return "（尚未提供额外上下文）"
        lines = []
        for attachment in attachments:
            label = attachment.label or attachment.slot_key
            lines.append(
                f"- {label}（由 {attachment.provided_by} 提供）\n{self._truncate_text(attachment.content, 800)}"
            )
        return "\n".join(lines)

    def _render_system_sections(self, context_bundle: Dict[str, Any]) -> str:
        sections = []
        metadata = context_bundle.get("session_metadata") or {}
        meta_lines = [
            f"Batch ID: {metadata.get('batch_id')}",
            f"Session ID: {metadata.get('session_id') or '未记录'}",
            f"Active Phase: {metadata.get('active_phase')}",
            f"Procedural Prompt Active: {metadata.get('procedural_prompt_active')}",
        ]
        sections.append("## Session Metadata\n" + "\n".join(meta_lines))

        playbook = context_bundle.get("phase_playbook_excerpt")
        if playbook:
            sections.append(f"## Phase Playbook Guidance\n{playbook}")

        goal_outline = context_bundle.get("goals_outline")
        if goal_outline:
            sections.append(f"## Current Goals\n{goal_outline}")

        plan_outline = context_bundle.get("plan_outline")
        if plan_outline:
            sections.append(f"## Current Plan\n{plan_outline}")

        completed = context_bundle.get("completed_phase_summaries")
        if completed:
            sections.append(f"## Completed Phase Summaries\n{completed}")

        stream_snapshot = context_bundle.get("active_stream_snapshot")
        if stream_snapshot:
            sections.append(
                "## Active Stream Snapshot\n"
                f"- Stream ID: {stream_snapshot.get('stream_id')}\n"
                f"- Phase: {stream_snapshot.get('phase')}\n"
                f"- Last Updated: {stream_snapshot.get('updated_at')}\n"
                "### Recent Content\n"
                f"{stream_snapshot.get('content')}"
            )

        history_entries = context_bundle.get("user_message_history") or []
        if history_entries:
            formatted_history = []
            for entry in history_entries:
                formatted_history.append(
                    f"{entry['timestamp']} [{entry['role']}]: {entry['content']}"
                )
            sections.append("## Recent Conversation\n" + "\n".join(formatted_history))

        constraints = context_bundle.get("known_constraints") or []
        if constraints:
            sections.append("## Known Constraints\n" + "\n".join(f"- {c}" for c in constraints))

        return "\n\n".join(sections)

    def _prepare_template_payload(
        self,
        context_bundle: Dict[str, Any],
        *,
        user_input: str,
        supplied_context: Optional[List[ContextAttachment]] = None,
    ) -> Dict[str, Any]:
        role_desc = context_bundle.get("role_description") or ""
        role_rationale = context_bundle.get("role_rationale") or ""
        role_block = role_desc or "未指定研究角色"
        if role_rationale:
            role_block += f"。{role_rationale}"

        history_entries = context_bundle.get("user_message_history") or []
        chat_history = []
        for entry in history_entries:
            chat_history.append(f"- {entry['timestamp']} [{entry['role']}]: {entry['content']}")
        chat_history_text = "\n".join(chat_history) if chat_history else "（暂无历史对话）"

        phase3_summary_block = "（暂无 Phase 3 摘要）"
        summaries = context_bundle.get("phase3_summaries") or []
        if summaries:
            lines = []
            for item in summaries:
                lines.append(f"- Step {item.get('step_id')}: {item.get('summary')}")
            phase3_summary_block = "\n".join(lines)

        points_block = "（暂无 Phase 3 关键结论）"
        poi_entries = context_bundle.get("phase3_points") or []
        if poi_entries:
            lines = []
            for item in poi_entries:
                lines.append(f"### Step {item.get('step_id')}\n{item.get('points')}")
            points_block = "\n".join(lines)

        attachments_text = self._format_supplied_context(supplied_context or [])

        system_sections = self._render_system_sections(context_bundle)

        synthesized_text = "（暂无综合研究目标）"
        synth_obj = context_bundle.get("synthesized_goal")
        if isinstance(synth_obj, dict):
            pieces = []
            topic = synth_obj.get("comprehensive_topic")
            if topic:
                pieces.append(f"主题：{topic}")
            questions = synth_obj.get("component_questions") or []
            if questions:
                pieces.append(
                    "子问题：\n" + "\n".join(f"- {q}" for q in questions[:6])
                )
            if synth_obj.get("unifying_theme"):
                pieces.append(f"统一主题：{synth_obj['unifying_theme']}")
            if pieces:
                synthesized_text = "\n".join(pieces)
        elif isinstance(synth_obj, str) and synth_obj.strip():
            synthesized_text = synth_obj.strip()

        return {
            "user_input": user_input,
            "chat_history": chat_history_text,
            "style_fragment": context_bundle.get("style_fragment") or "保持专业、清晰且结构化的中文表达。",
            "data_abstract": context_bundle.get("data_abstract") or "（暂无数据摘要）",
            "user_guidance": context_bundle.get("user_guidance") or "（暂无用户指导）",
            "role_block": role_block,
            "synthesized_goal": synthesized_text,
            "phase3_summary_block": phase3_summary_block,
            "phase3_points_block": points_block,
            "supplied_context_block": attachments_text,
            "system_context_sections": system_sections,
        }

    def _refresh_cached_research_assets(
        self, state: BatchConversationState, session_data: Dict[str, Any]
    ):
        metadata = session_data.get("metadata") or {}
        writing_style = metadata.get("writing_style") or state.writing_style or "explanatory"
        state.writing_style = writing_style
        state.user_guidance = (
            metadata.get("user_initial_guidance")
            or metadata.get("phase_feedback_pre_role")
            or state.user_guidance
        )
        state.system_role_description = (
            (metadata.get("research_role") or {}).get("role")
            or state.system_role_description
        )
        state.research_role_rationale = (
            (metadata.get("research_role") or {}).get("rationale")
            or state.research_role_rationale
        )
        abstract = (
            metadata.get("data_abstract")
            or metadata.get("combined_abstract")
            or self._find_first_combined_abstract(session_data)
            or state.data_abstract
        )
        state.data_abstract = abstract

        summaries, poi_entries = self._extract_phase3_highlights(session_data)
        if summaries:
            state.phase3_summaries = summaries
        if poi_entries:
            state.phase3_points = poi_entries

    def _analyze_context_needs(
        self,
        state: BatchConversationState,
    ) -> List[ContextRequirement]:
        requirements: List[ContextRequirement] = []
        if not state.phase3_summaries:
            requirements.append(
                ContextRequirement(
                    key="phase3_summary",
                    label="Phase 3 摘要",
                    description="请提供阶段 3 的步骤总结或关键发现摘录。",
                )
            )
        if not state.phase3_points:
            requirements.append(
                ContextRequirement(
                    key="phase3_points",
                    label="Phase 3 兴趣点",
                    description="请附上 Phase 3 的 key_claims 或 points_of_interest。",
                )
            )
        if not state.data_abstract:
            requirements.append(
                ContextRequirement(
                    key="data_abstract",
                    label="数据摘要",
                    description="请提供 {data_abstract} 字段内容或等效摘要。",
                )
            )
        return requirements

    def _register_context_request(
        self,
        batch_id: str,
        user_message_id: str,
        requirements: List[ContextRequirement],
    ) -> ContextRequest:
        request = ContextRequest(
            id=f"ctx-{uuid.uuid4().hex[:10]}",
            user_message_id=user_message_id,
            reason="研究上下文缺失",
            requirements=requirements,
        )
        with self._lock:
            state = self._get_state(batch_id)
            state.context_requests[request.id] = request
            if request.id in state.context_request_order:
                state.context_request_order.remove(request.id)
            state.context_request_order.append(request.id)
            state.awaiting_context_for_message[user_message_id] = request.id
        self._persist_state(batch_id)
        asyncio.create_task(
            self._broadcast_context_event(
                batch_id,
                "conversation:context_request",
                {"request": self._context_request_to_dict(request)},
            )
        )
        return request

    async def _broadcast_context_event(
        self,
        batch_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ):
        if not self._ws_manager:
            return
        await self._ws_manager.broadcast(
            batch_id,
            {
                "type": event_type,
                **payload,
            },
        )

    def _hydrate_state_from_session_file(self, batch_id: str, session_id: str):
        session_path = self._session_dir / f"session_{session_id}.json"
        if not session_path.exists():
            return

        try:
            mtime = session_path.stat().st_mtime
        except OSError:
            mtime = None

        with self._lock:
            state = self._get_state(batch_id)
            if (
                state.hydrated_session_id == session_id
                and mtime is not None
                and state.session_snapshot_mtime == mtime
            ):
                return

        try:
            with open(session_path, "r", encoding="utf-8") as handle:
                session_data = json.load(handle)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"Failed to hydrate session context for {batch_id}: {exc}")
            return

        metadata = session_data.get("metadata") or {}
        phase_artifacts = session_data.get("phase_artifacts") or {}

        goals = metadata.get("phase1_confirmed_goals") or []
        plan = (
            metadata.get("research_plan")
            or phase_artifacts.get("phase2", {}).get("plan")
            or []
        )
        synthesized_goal = (
            metadata.get("synthesized_goal")
            or phase_artifacts.get("phase2", {}).get("synthesized_goal")
        )
        known_constraints = metadata.get("known_constraints") or []

        with self._lock:
            state.session_id = session_id or state.session_id
            if goals:
                state.goals = goals
            if plan:
                state.plan = plan
            if synthesized_goal:
                state.synthesized_goal = synthesized_goal
            if known_constraints:
                state.known_constraints = known_constraints
            state.hydrated_session_id = session_id
            state.session_snapshot_mtime = mtime
            state.last_context_refresh = _now_iso()
        self._refresh_cached_research_assets(state, session_data)
        self._persist_state(batch_id)

    def ensure_batch(self, batch_id: str):
        self._get_state(batch_id)

    def _ensure_llm_client(self) -> QwenStreamingClient:
        if self._llm_client is None:
            if QwenStreamingClient is None:
                raise RuntimeError("QwenStreamingClient unavailable; cannot initialize conversation client.")
            self._llm_client = QwenStreamingClient()
        return self._llm_client

    def _get_phase_model_config(self, phase: Optional[str]) -> Dict[str, Any]:
        """
        Resolve per-phase model configuration from config.yaml (research.phases.*).
        """
        if self._config is None:
            return {}

        phase_key = (phase or "").strip()
        if phase_key not in self._phase_playbook:
            phase_key = "phase3"

        phase_config = self._config.get(f"research.phases.{phase_key}", {}) or {}
        if phase_config:
            return phase_config

        # Fallback to phase3 defaults if specific entry missing
        fallback = self._config.get("research.phases.phase3", {}) or {}
        return fallback

    def _get_chat_config(self) -> Dict[str, Any]:
        """
        Return dedicated chat configuration (research.chat.*) if defined.
        """
        if self._config is None:
            return {}
        return self._config.get("research.chat", {}) or {}

    def _add_message(self, batch_id: str, message: ConversationMessage):
        state = self._get_state(batch_id)
        with self._lock:
            state.conversation_messages[message.id] = message
            if message.id in state.conversation_order:
                state.conversation_order.remove(message.id)
            state.conversation_order.append(message.id)
        self._persist_state(batch_id)

    def _update_message_status(
        self,
        batch_id: str,
        message_id: str,
        status: MessageStatus,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        state = self._get_state(batch_id)
        with self._lock:
            message = state.conversation_messages.get(message_id)
            if not message:
                logger.warning(f"Conversation message {message_id} not found for batch {batch_id}")
                return None
            message.status = status
            message.updated_at = _now_iso()
            if metadata:
                message.metadata.update(metadata)
        self._persist_state(batch_id)
        return message

    # ------------------------------------------------------------------
    # Context capture methods (invoked by WebSocketUI)
    # ------------------------------------------------------------------
    def record_phase_change(self, batch_id: str, phase: str, message: Optional[str] = None):
        state = self._get_state(batch_id)
        with self._lock:
            previous_phase = state.active_phase
            if previous_phase and previous_phase != phase:
                state.phase_history.append(
                    PhaseHistoryEntry(phase=previous_phase, completed_at=_now_iso(), summary=message)
                )
            state.active_phase = phase
            state.last_context_refresh = _now_iso()
        self._persist_state(batch_id)

    def set_session_id(self, batch_id: str, session_id: Optional[str]):
        state = self._get_state(batch_id)
        with self._lock:
            state.session_id = session_id
            state.last_context_refresh = _now_iso()
        self._persist_state(batch_id)

    def record_goals(self, batch_id: str, goals: List[Dict[str, Any]]):
        state = self._get_state(batch_id)
        with self._lock:
            state.goals = goals or []
            state.last_context_refresh = _now_iso()
        self._persist_state(batch_id)

    def record_plan(self, batch_id: str, plan: List[Dict[str, Any]]):
        state = self._get_state(batch_id)
        with self._lock:
            state.plan = plan or []
            state.last_context_refresh = _now_iso()
        self._persist_state(batch_id)

    def record_synthesized_goal(self, batch_id: str, synthesized_goal: Dict[str, Any]):
        state = self._get_state(batch_id)
        with self._lock:
            state.synthesized_goal = synthesized_goal or None
            state.last_context_refresh = _now_iso()
        self._persist_state(batch_id)

    def start_stream(self, batch_id: str, stream_id: str, phase: Optional[str], metadata: Optional[Dict[str, Any]]):
        state = self._get_state(batch_id)
        with self._lock:
            state.stream_snapshot = StreamSnapshot(
                stream_id=stream_id,
                metadata=metadata or {},
                phase=phase,
            )

    def append_stream_token(self, batch_id: str, stream_id: str, token: str):
        state = self._get_state(batch_id)
        with self._lock:
            if state.stream_snapshot and state.stream_snapshot.stream_id == stream_id:
                state.stream_snapshot.content += token
                state.stream_snapshot.updated_at = _now_iso()

    def end_stream(self, batch_id: str, stream_id: str):
        state = self._get_state(batch_id)
        with self._lock:
            if state.stream_snapshot and state.stream_snapshot.stream_id == stream_id:
                state.stream_snapshot.updated_at = _now_iso()

    def record_procedural_prompt(self, batch_id: str, prompt_id: str, prompt: str, choices: Optional[List[str]]):
        state = self._get_state(batch_id)
        with self._lock:
            state.procedural_prompt = ProceduralPromptState(
                prompt_id=prompt_id,
                prompt=prompt,
                choices=choices or [],
            )
            state.last_context_refresh = _now_iso()
        self._persist_state(batch_id)

    # ------------------------------------------------------------------
    # Context bundle generation
    # ------------------------------------------------------------------
    def _format_goals(self, goals: List[Dict[str, Any]]) -> str:
        if not goals:
            return "暂无研究目标。"
        lines = []
        for goal in goals[:6]:
            text = goal.get("goal_text") or goal.get("goal") or ""
            if not text:
                continue
            uses = goal.get("uses") or []
            uses_str = f"（用途: {', '.join(uses)}）" if uses else ""
            lines.append(f"- {text}{uses_str}")
        return "\n".join(lines) if lines else "暂无研究目标。"

    def _format_plan(self, plan: List[Dict[str, Any]]) -> str:
        if not plan:
            return "暂无研究计划。"
        lines = []
        for step in plan[:6]:
            step_id = step.get("step_id")
            goal = step.get("goal") or "未指定目标"
            required = step.get("required_data")
            chunk = step.get("chunk_strategy")
            detail_parts = []
            if required:
                detail_parts.append(f"数据: {required}")
            if chunk:
                detail_parts.append(f"策略: {chunk}")
            details = f" ({'; '.join(detail_parts)})" if detail_parts else ""
            lines.append(f"- 步骤 {step_id}: {goal}{details}")
        return "\n".join(lines)

    def _format_phase_history(self, history: List[PhaseHistoryEntry]) -> str:
        if not history:
            return ""
        lines = []
        for entry in history[-6:]:
            summary = entry.summary or "完成阶段无额外摘要。"
            lines.append(f"- {entry.phase} ({entry.completed_at}): {summary}")
        return "\n".join(lines)

    def _format_conversation_history(self, batch_id: str, limit: int = 5) -> List[Dict[str, str]]:
        state = self._get_state(batch_id)
        with self._lock:
            ordered_ids = list(state.conversation_order)[-limit:]
            history = []
            for message_id in ordered_ids:
                message = state.conversation_messages.get(message_id)
                if not message:
                    continue
                history.append(
                    {
                        "role": message.role,
                        "content": message.content,
                        "status": message.status,
                        "timestamp": message.created_at,
                    }
                )
        return history

    def build_context_bundle(
        self,
        batch_id: str,
        *,
        supplied_context: Optional[List[ContextAttachment]] = None,
    ) -> Dict[str, Any]:
        state = self._get_state(batch_id)
        with self._lock:
            active_phase = state.active_phase or "research"
            session_metadata = {
                "batch_id": batch_id,
                "session_id": state.session_id,
                "active_phase": active_phase,
                "procedural_prompt_active": state.procedural_prompt is not None,
                "known_constraints": state.known_constraints,
            }
            playbook_excerpt = self._phase_playbook.get(active_phase, "")
            completed_summary = self._format_phase_history(state.phase_history)
            stream_snapshot = None
            if state.stream_snapshot:
                stream_snapshot = {
                    "stream_id": state.stream_snapshot.stream_id,
                    "phase": state.stream_snapshot.phase,
                    "content": state.stream_snapshot.content[-1200:],
                    "metadata": state.stream_snapshot.metadata,
                    "updated_at": state.stream_snapshot.updated_at,
                }
            conversation_recent = self._format_conversation_history(batch_id)

        bundle = {
            "session_metadata": session_metadata,
            "phase_playbook_excerpt": playbook_excerpt,
            "completed_phase_summaries": completed_summary,
            "active_stream_snapshot": stream_snapshot,
            "user_message_history": conversation_recent,
            "known_constraints": session_metadata["known_constraints"],
            "goals_outline": self._format_goals(state.goals),
            "plan_outline": self._format_plan(state.plan),
            "synthesized_goal": state.synthesized_goal,
            "style_fragment": self._load_style_fragment(state.writing_style),
            "data_abstract": state.data_abstract,
            "user_guidance": state.user_guidance,
            "role_description": state.system_role_description,
            "role_rationale": state.research_role_rationale,
            "phase3_summaries": state.phase3_summaries,
            "phase3_points": state.phase3_points,
            "supplied_context": supplied_context or [],
        }
        return bundle

    def _render_context_for_prompt(
        self,
        context_bundle: Dict[str, Any],
        *,
        user_input: str,
        supplied_context: Optional[List[ContextAttachment]] = None,
    ) -> str:
        template = self._get_prompt_template()
        payload = self._prepare_template_payload(
            context_bundle,
            user_input=user_input,
            supplied_context=supplied_context,
        )
        return template.safe_substitute(payload)

    async def _broadcast_message_payload(self, batch_id: str, message_id: str):
        if not self._ws_manager:
            return
        payload = self.get_message_payload(batch_id, message_id)
        if not payload:
            return
        await self._ws_manager.broadcast(
            batch_id,
            {
                "type": "conversation:message",
                "message": payload,
            },
        )

    def _schedule_delta_broadcast(self, batch_id: str, message_id: str, chunk: str):
        if not chunk or not self._ws_manager:
            return
        asyncio.create_task(self._broadcast_delta(batch_id, message_id, chunk))

    async def _broadcast_delta(self, batch_id: str, message_id: str, chunk: str):
        if not self._ws_manager or not chunk:
            return
        await self._ws_manager.broadcast(
            batch_id,
            {
                "type": "conversation:delta",
                "message": {
                    "id": message_id,
                    "role": "assistant",
                    "delta": chunk,
                    "timestamp": _now_iso(),
                },
            },
        )

    # ------------------------------------------------------------------
    # Conversation handling
    # ------------------------------------------------------------------
    async def handle_user_message(
        self,
        batch_id: str,
        message: str,
        *,
        session_id: Optional[str] = None,
    ) -> ConversationResult:
        message = (message or "").strip()
        if not message:
            raise ValueError("Message content must not be empty.")

        if session_id:
            self.set_session_id(batch_id, session_id)
            self._hydrate_state_from_session_file(batch_id, session_id)

        # Deduplication check: prevent processing same message twice in quick succession
        state = self._get_state(batch_id)
        import hashlib
        import time
        message_hash = hashlib.sha256(message.encode()).hexdigest()[:16]
        current_time = time.time()
        
        with self._lock:
            # Clean up old entries (older than 10 seconds)
            state.recent_messages = {
                h: t for h, t in state.recent_messages.items()
                if current_time - t < 10.0
            }
            
            # Check if this exact message was processed very recently
            if message_hash in state.recent_messages:
                time_since = current_time - state.recent_messages[message_hash]
                if time_since < 5.0:  # 5 second window
                    logger.warning(
                        f"Duplicate message detected for batch {batch_id}: '{message[:50]}...' "
                        f"(last seen {time_since:.1f}s ago). Ignoring."
                    )
                    # Return a dummy result to avoid error
                    return ConversationResult(
                        status="ok",
                        user_message_id=f"duplicate-{uuid.uuid4().hex}",
                        reply="消息已在处理中，请勿重复提交。",
                    )
            
            # Record this message
            state.recent_messages[message_hash] = current_time

        user_message = ConversationMessage(
            id=f"user-{uuid.uuid4().hex}",
            role="user",
            content=message,
            status="in_progress",
        )
        self._add_message(batch_id, user_message)

        state = self._get_state(batch_id)
        with self._lock:
            prompt_state = state.procedural_prompt
            if prompt_state and prompt_state.awaiting_response:
                state.deferred_messages.append((user_message.id, message))
                user_message.status = "queued"
                user_message.updated_at = _now_iso()
                logger.info(
                    f"Queued conversation message {user_message.id} for batch {batch_id} "
                    f"due to active procedural prompt {prompt_state.prompt_id}"
                )
                return ConversationResult(
                    status="queued",
                    user_message_id=user_message.id,
                    queued_reason="Procedural prompt awaiting user response.",
                )

        requirements = self._analyze_context_needs(state)
        if requirements:
            request = self._register_context_request(batch_id, user_message.id, requirements)
            self._update_message_status(batch_id, user_message.id, "queued")
            return ConversationResult(
                status="context_required",
                user_message_id=user_message.id,
                queued_reason="等待补充研究上下文。",
                context_request_id=request.id,
                required_context=[asdict(req) for req in requirements],
            )

        # No procedural prompt active, process immediately
        try:
            result = await self._process_message(batch_id, user_message.id, message)
            return result
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(f"Conversation processing failed: {exc}", exc_info=True)
            self._update_message_status(batch_id, user_message.id, "error", {"error": str(exc)})
            raise

    async def _process_message(
        self,
        batch_id: str,
        user_message_id: str,
        message: str,
        supplied_context: Optional[List[ContextAttachment]] = None,
    ) -> ConversationResult:
        self._update_message_status(batch_id, user_message_id, "in_progress")
        context_bundle = self.build_context_bundle(batch_id, supplied_context=supplied_context)
        context_rendered = self._render_context_for_prompt(
            context_bundle,
            user_input=message,
            supplied_context=supplied_context,
        )

        system_prompt = (
            "You are the Research Tool Copilot. Provide grounded, pragmatic feedback.\n"
            "Always cross-check the provided context before recommending actions.\n"
            "Highlight risks or blockers explicitly. If information is missing, state the gap."
        )
        developer_instruction = (
            "Adhere to the active research workflow. Respect current goals and plan.\n"
            "When users ask for changes that contradict locked decisions, suggest clarification steps."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": developer_instruction},
            {"role": "user", "content": context_rendered},
        ]

        assistant_message = ConversationMessage(
            id=f"assistant-{uuid.uuid4().hex}",
            role="assistant",
            content="",
            status="in_progress",
            metadata={"in_reply_to": user_message_id},
        )
        self._add_message(batch_id, assistant_message)
        await self._broadcast_message_payload(batch_id, assistant_message.id)

        llm_client = self._ensure_llm_client()
        loop = asyncio.get_running_loop()

        def _invoke() -> Tuple[str, Dict[str, Any]]:
            tokens: List[str] = []
            for chunk in llm_client.stream_completion(
                messages,
                temperature=0.35,
                max_tokens=900,
                model="qwen-plus",
                enable_thinking=False,
                stream_options={"include_usage": True},
            ):
                tokens.append(chunk)
                loop.call_soon_threadsafe(
                    self._schedule_delta_broadcast,
                    batch_id,
                    assistant_message.id,
                    chunk,
                )
            reply_text = "".join(tokens).strip()
            metadata = llm_client.last_call_metadata or {}
            usage = getattr(llm_client, "usage", None) or {}
            metadata = {**metadata, "usage": usage}
            return reply_text, metadata

        try:
            reply_text, metadata = await loop.run_in_executor(None, _invoke)
        except Exception as exc:
            self._update_message_status(batch_id, assistant_message.id, "error", {"error": str(exc)})
            await self._broadcast_message_payload(batch_id, assistant_message.id)
            raise

        self._update_message_status(batch_id, user_message_id, "completed", {"llm": "qwen-plus"})

        self._update_message_status(
            batch_id,
            assistant_message.id,
            "completed",
            {"llm": "qwen-plus", **(metadata or {})},
        )
        with self._lock:
            state = self._states.get(batch_id)
            if state:
                record = state.conversation_messages.get(assistant_message.id)
                if record:
                    record.content = reply_text
                    record.metadata.setdefault("in_reply_to", user_message_id)
                    record.updated_at = _now_iso()
        self._persist_state(batch_id)
        # Final payload will be broadcast by API/websocket manager caller

        return ConversationResult(
            status="ok",
            user_message_id=user_message_id,
            assistant_message_id=assistant_message.id,
            reply=reply_text,
            metadata=metadata,
            context_bundle=context_bundle,
        )

    async def resolve_procedural_prompt(self, batch_id: str, prompt_id: Optional[str], response: Optional[str]):
        state = self._get_state(batch_id)
        with self._lock:
            prompt_state = state.procedural_prompt
            if prompt_state and prompt_state.prompt_id == prompt_id:
                prompt_state.awaiting_response = False
                state.procedural_prompt = None
                deferred = list(state.deferred_messages)
                state.deferred_messages.clear()
            else:
                deferred = []

        if not deferred:
            return []

        logger.info(
            f"Processing {len(deferred)} deferred conversation message(s) for batch {batch_id} "
            f"after resolving prompt {prompt_id}"
        )
        results = []
        for message_id, content in deferred:
            try:
                result = await self._process_message(batch_id, message_id, content)
                results.append(result)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error(f"Deferred conversation processing failed for {message_id}: {exc}", exc_info=True)
                self._update_message_status(batch_id, message_id, "error", {"error": str(exc)})
        return results

    async def supply_context(
        self,
        batch_id: str,
        request_id: str,
        supplies: List[Dict[str, str]],
        *,
        provided_by: str = "user",
    ) -> ConversationResult:
        if not supplies:
            raise ValueError("No context payload supplied.")

        state = self._get_state(batch_id)
        with self._lock:
            request = state.context_requests.get(request_id)
            if not request:
                raise ValueError("Context request not found.")
            if request.status != "pending":
                raise ValueError("Context request already resolved.")

        new_attachments: List[ContextAttachment] = []
        for item in supplies:
            if not isinstance(item, dict):
                continue
            content = (item.get("content") or "").strip()
            if not content:
                continue
            slot_key = item.get("slot_key") or "custom"
            label = item.get("label") or slot_key
            attachment = ContextAttachment(
                id=f"ctxatt-{uuid.uuid4().hex[:10]}",
                request_id=request_id,
                slot_key=slot_key,
                label=label,
                content=content,
                provided_by=provided_by,
            )
            new_attachments.append(attachment)

        if not new_attachments:
            raise ValueError("Context payload is empty.")

        with self._lock:
            request.attachments.extend(new_attachments)
            for attachment in new_attachments:
                for requirement in request.requirements:
                    if requirement.key == attachment.slot_key:
                        requirement.fulfilled = True
            all_fulfilled = all(
                (not req.required) or req.fulfilled for req in request.requirements
            )
            self._persist_state(batch_id)

        await self._broadcast_context_event(
            batch_id,
            "conversation:context_update",
            {"request": self._context_request_to_dict(request)},
        )

        if not all_fulfilled:
            return ConversationResult(
                status="queued",
                user_message_id=request.user_message_id,
                queued_reason="已接收部分上下文，仍需更多附件。",
                context_request_id=request.id,
                required_context=[asdict(req) for req in request.requirements],
            )

        with self._lock:
            request.status = "satisfied"
            attachments_snapshot = list(request.attachments)
            pending_message_id = request.user_message_id
            state.awaiting_context_for_message.pop(pending_message_id, None)
            self._persist_state(batch_id)

        await self._broadcast_context_event(
            batch_id,
            "conversation:context_resolved",
            {"request": self._context_request_to_dict(request)},
        )

        user_message = state.conversation_messages.get(pending_message_id)
        if not user_message:
            raise RuntimeError("Queued user message not found for context resume.")

        return await self._process_message(
            batch_id,
            pending_message_id,
            user_message.content,
            supplied_context=attachments_snapshot,
        )

    # ------------------------------------------------------------------
    # Retrieval helpers
    # ------------------------------------------------------------------
    def get_conversation_messages(self, batch_id: str) -> List[Dict[str, Any]]:
        state = self._get_state(batch_id)
        with self._lock:
            ordered_ids = list(state.conversation_order)
            return [
                state.conversation_messages[mid].to_payload()
                for mid in ordered_ids
                if mid in state.conversation_messages
            ]

    def get_message_payload(self, batch_id: str, message_id: str) -> Optional[Dict[str, Any]]:
        state = self._get_state(batch_id)
        with self._lock:
            message = state.conversation_messages.get(message_id)
            if not message:
                return None
            return message.to_payload()

    async def generate_suggested_questions(
        self,
        batch_id: str,
        session_id: Optional[str] = None,
        conversation_context: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[List[str], str]:
        """
        Generate 3 suggested questions using the configured model for the active phase.
        
        Returns:
            Tuple of (questions list, model_used)
        """
        state = self._get_state(batch_id)
        
        # Hydrate session data if session_id provided
        if session_id:
            self._hydrate_state_from_session_file(batch_id, session_id)
        
        # Prepare conversation history
        conversation_history = ""
        if conversation_context:
            history_lines = []
            for msg in conversation_context[-10:]:  # Last 10 messages
                role = msg.get("role", "user")
                content = msg.get("content", "").strip()
                if content:
                    role_label = "用户" if role == "user" else "助手"
                    history_lines.append(f"{role_label}: {content}")
            conversation_history = "\n".join(history_lines) if history_lines else "暂无对话历史"
        else:
            # Fallback: use state messages
            with self._lock:
                ordered_ids = list(state.conversation_order)[-10:]
                messages = [state.conversation_messages.get(msg_id) for msg_id in ordered_ids if state.conversation_messages.get(msg_id)]
            
            if messages:
                history_lines = []
                for msg in messages:
                    role_label = "用户" if msg.role == "user" else "助手"
                    history_lines.append(f"{role_label}: {msg.content}")
                conversation_history = "\n".join(history_lines)
            else:
                conversation_history = "暂无对话历史"
        
        # Prepare session context
        with self._lock:
            current_phase = state.active_phase or "未知"
            synthesized_goal = ""
            if state.synthesized_goal:
                if isinstance(state.synthesized_goal, dict):
                    synthesized_goal = state.synthesized_goal.get("goal", "") or str(state.synthesized_goal)
                else:
                    synthesized_goal = str(state.synthesized_goal)
            
            phase3_summary = ""
            if state.phase3_summaries:
                phase3_summary = "\n".join([
                    s.get("summary", "") if isinstance(s, dict) else str(s)
                    for s in state.phase3_summaries[-3:]  # Last 3 summaries
                ])
            
            phase3_points = ""
            if state.phase3_points:
                phase3_points = "\n".join([
                    p.get("point", "") if isinstance(p, dict) else str(p)
                    for p in state.phase3_points[-5:]  # Last 5 points
                ])
        
        # Load prompt template
        prompt_path = PROJECT_ROOT / "research" / "prompts" / "right_column_chat" / "suggest_questions.md"
        try:
            template_text = prompt_path.read_text(encoding="utf-8")
        except Exception:
            # Fallback template
            template_text = """你是一个智能研究助手。基于以下对话历史和会话信息，生成3个相关的后续问题。

## 对话历史
${conversation_history}

## 会话信息
- 当前阶段: ${current_phase}
- 研究目标: ${synthesized_goal}
- Phase 3 摘要: ${phase3_summary}
- Phase 3 兴趣点: ${phase3_points}

## 要求
1. 生成恰好3个问题
2. 问题应该与对话上下文相关
3. 问题应该有助于探索研究主题
4. 问题应该多样化，不重复
5. 每个问题应该简洁（一句话）
6. 避免重复最近对话中已经问过的问题
7. 专注于深化理解或探索新角度

请直接返回3个问题，每行一个问题，不要编号，不要额外说明。
"""
        
        template = Template(template_text)
        prompt = template.safe_substitute(
            conversation_history=conversation_history,
            current_phase=current_phase,
            synthesized_goal=synthesized_goal or "未设定",
            phase3_summary=phase3_summary or "暂无",
            phase3_points=phase3_points or "暂无",
        )
        
        # Resolve chat configuration (falls back to phase/global defaults)
        chat_config = self._get_chat_config()
        phase_model_config = self._get_phase_model_config(state.active_phase)
        if self._config:
            default_model = self._config.get("qwen.model", "qwen3-max")
        else:
            default_model = "qwen3-max"

        model_name = (
            chat_config.get("model")
            or phase_model_config.get("model")
            or default_model
        )

        chat_enable_thinking = chat_config.get("enable_thinking")
        if chat_enable_thinking is None:
            enable_thinking = bool(phase_model_config.get("enable_thinking", False))
        else:
            enable_thinking = bool(chat_enable_thinking)

        thinking_budget = chat_config.get("thinking_budget")
        if thinking_budget is None:
            thinking_budget = phase_model_config.get("thinking_budget")

        try:
            temperature = float(chat_config.get("temperature", 0.7))
        except (TypeError, ValueError):
            temperature = 0.7

        max_tokens = chat_config.get("max_tokens", 200)
        try:
            max_tokens = int(max_tokens)
        except (TypeError, ValueError):
            max_tokens = 200

        from research.client import QwenStreamingClient
        flash_client = QwenStreamingClient(model=model_name)
        
        messages = [{"role": "user", "content": prompt}]
        
        # Use stream_and_collect to get full response
        try:
            questions_text, _ = flash_client.stream_and_collect(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                enable_thinking=enable_thinking,
                thinking_budget=thinking_budget,
            )
        except Exception as exc:
            logger.error(
                f"Failed to generate questions with model {model_name}: {exc}"
            )
            raise
        
        # Parse questions (one per line, remove numbering)
        questions = []
        for line in questions_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Remove numbering (e.g., "1. ", "1)", etc.)
            line = line.lstrip("0123456789.）) ")
            if line and len(line) > 5:  # Minimum question length
                questions.append(line)
        
        # Ensure exactly 3 questions
        if len(questions) < 3:
            # Pad with generic questions if needed
            generic = [
                "能详细解释一下这个观点吗？",
                "还有哪些相关的信息？",
                "这个结论是如何得出的？",
            ]
            questions.extend(generic[:3 - len(questions)])
        questions = questions[:3]
        
        return questions, model_name

    def generate_fallback_questions(
        self,
        batch_id: str,
        session_id: Optional[str] = None,
    ) -> List[str]:
        """
        Generate fallback questions based on session data when model fails.
        """
        state = self._get_state(batch_id)
        
        # Hydrate session data if session_id provided
        if session_id:
            self._hydrate_state_from_session_file(batch_id, session_id)
        
        questions = []
        
        with self._lock:
            # Generate questions based on session context
            if state.synthesized_goal:
                goal_text = ""
                if isinstance(state.synthesized_goal, dict):
                    # Try to extract meaningful goal text from dict
                    goal_text = (
                        state.synthesized_goal.get("goal") or
                        state.synthesized_goal.get("comprehensive_topic") or
                        state.synthesized_goal.get("topic") or
                        ""
                    )
                    # If still empty, try to get first string value
                    if not goal_text:
                        for value in state.synthesized_goal.values():
                            if isinstance(value, str) and value.strip():
                                goal_text = value.strip()
                                break
                else:
                    goal_text = str(state.synthesized_goal) if state.synthesized_goal else ""
                
                if goal_text and len(goal_text) > 3:
                    # Clean up the goal text (remove extra quotes, etc.)
                    goal_text = goal_text.strip().strip('"\'')
                    if len(goal_text) > 30:
                        goal_text = goal_text[:30] + "..."
                    questions.append(f"关于「{goal_text}」，能详细说明一下吗？")
            
            if state.phase3_summaries:
                questions.append("Phase 3 的研究发现有哪些值得深入探讨的点？")
            
            if state.phase3_points:
                questions.append("这些兴趣点之间有什么关联？")
        
        # Fill with generic questions if needed
        generic_questions = [
            "能详细解释一下这个观点吗？",
            "还有哪些相关的信息？",
            "这个结论是如何得出的？",
            "有哪些不同的观点？",
            "这个主题还有哪些值得探索的方向？",
        ]
        
        while len(questions) < 3:
            for q in generic_questions:
                if q not in questions:
                    questions.append(q)
                    break
            if len(questions) >= 3:
                break
        
        return questions[:3]


__all__ = ["ConversationContextService", "ConversationResult"]

