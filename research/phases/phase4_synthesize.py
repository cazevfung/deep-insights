"""Phase 4: Synthesize Final Report."""

import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from core.config import Config
from research.phases.base_phase import BasePhase
from research.phases.phase4_context import Phase4ContextBundle, build_phase4_context_bundle
from research.prompts.loader import load_prompt, render_prompt


class Phase4Synthesize(BasePhase):
    """Phase 4: Generate final research synthesis output."""
    
    def execute(
        self,
        phase1_5_output: Dict[str, Any],
        phase3_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the synthesis phase by assembling context, orchestrating staged prompts,
        and validating the final article.
        """
        self.logger.info("Phase 4: Starting synthesis pipeline")

        cfg = Config()
        enable_auxiliary_artifacts = cfg.get_bool("research.phase4.enable_auxiliary_artifacts", False)

        bundle = build_phase4_context_bundle(
            self.session,
            phase1_5_output,
            phase3_output,
            enable_auxiliary_artifacts=enable_auxiliary_artifacts,
        )
        prompt_context = bundle.to_prompt_context()

        # Persist context bundle for downstream inspection
        try:
            self.session.save_phase_artifact("phase4_context_bundle", bundle.to_dict(), autosave=False)
        except Exception as exc:
            self.logger.warning("Failed to save Phase 4 context bundle: %s", exc)

        system_message = self._render_system_message(prompt_context)

        outline_payload = self._run_outline_stage(system_message, prompt_context)
        coverage_payload = self._run_coverage_stage(system_message, prompt_context, outline_payload, bundle)
        article_text = self._run_article_stage(system_message, prompt_context, outline_payload, coverage_payload, bundle)

        validation = self._validate_article(article_text, outline_payload, coverage_payload, bundle)

        # Persist artifacts for debugging/QA
        try:
            self.session.save_phase_artifact("phase4_outline", outline_payload, autosave=False)
            self.session.save_phase_artifact("phase4_coverage", coverage_payload, autosave=False)
            self.session.save_phase_artifact(
                "phase4_article",
                {
                    "article": article_text,
                    "validation": validation,
                },
                autosave=False,
            )
            self.session.set_metadata("final_report", article_text)
            self.session.set_metadata("status", "completed")
            self.session.save()
        except Exception as exc:
            self.logger.warning("Failed to persist Phase 4 artifacts: %s", exc)

        result = {
            "report": article_text,
            "comprehensive_topic": bundle.selected_goal,
            "component_questions": bundle.component_questions,
            "outline": outline_payload.get("sections", []),
            "appendices": outline_payload.get("appendices", []),
            "coverage": coverage_payload,
            "validation": validation,
            "context_bundle": bundle.to_dict(),
        }
        if validation.get("errors"):
            result["needs_manual_review"] = True

        self.logger.info("Phase 4 complete: synthesis generated with %d outline sections", len(result["outline"]))
        return result

    # ------------------------------------------------------------------
    # Prompt stages
    # ------------------------------------------------------------------

    def _render_system_message(self, context: Dict[str, Any]) -> str:
        try:
            system_template = load_prompt("phase4_synthesize", role="system")
            return render_prompt(system_template, context)
        except FileNotFoundError:
            return ""

    def _run_outline_stage(
        self,
        system_message: str,
        base_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Stage 1: Request structured outline JSON."""
        outline_context = dict(base_context)
        outline_template = load_prompt("phase4_synthesize", role="outline")
        outline_user_message = render_prompt(outline_template, outline_context)

        messages = []
        if system_message.strip():
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": outline_user_message})

        if hasattr(self, "ui") and self.ui:
            self.ui.display_message("正在生成报告大纲...", "info")

        response = self._invoke_model(messages, stage_label="Phase4-Outline")
        outline_payload = self._parse_json_payload(response, "outline")

        if not outline_payload.get("sections"):
            self.logger.warning("Outline JSON parsing failed; falling back to default scaffold.")
            outline_payload = self._default_outline(base_context)

        return outline_payload

    def _run_coverage_stage(
        self,
        system_message: str,
        base_context: Dict[str, Any],
        outline_payload: Dict[str, Any],
        bundle: Phase4ContextBundle,
    ) -> Dict[str, Any]:
        """Stage 2: Ask model to map goals/questions to outline sections and evidence."""
        coverage_context = dict(base_context)
        coverage_context["outline_json"] = json.dumps(outline_payload, ensure_ascii=False, indent=2)

        coverage_template = load_prompt("phase4_synthesize", role="coverage")
        coverage_user_message = render_prompt(coverage_template, coverage_context)

        messages = []
        if system_message.strip():
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": coverage_user_message})

        if hasattr(self, "ui") and self.ui:
            self.ui.display_message("正在生成覆盖检查...", "info")

        response = self._invoke_model(messages, stage_label="Phase4-Coverage")
        coverage_payload = self._parse_json_payload(response, "coverage")

        if not coverage_payload.get("goal_coverage"):
            self.logger.warning("Coverage JSON missing goal_coverage; creating placeholder matrix.")
            coverage_payload = self._default_coverage(bundle, outline_payload)

        return coverage_payload

    def _run_article_stage(
        self,
        system_message: str,
        base_context: Dict[str, Any],
        outline_payload: Dict[str, Any],
        coverage_payload: Dict[str, Any],
        bundle: Phase4ContextBundle,
    ) -> str:
        """Stage 3: Produce the full article using outline + coverage guidance."""
        article_context = dict(base_context)
        article_context["outline_json"] = json.dumps(outline_payload, ensure_ascii=False)
        article_context["coverage_json"] = json.dumps(coverage_payload, ensure_ascii=False)

        if bundle.enable_auxiliary_artifacts:
            article_context["auxiliary_artifacts_required"] = "yes"
        else:
            article_context["auxiliary_artifacts_required"] = "no"

        article_template = load_prompt("phase4_synthesize", role="instructions")
        article_user_message = render_prompt(article_template, article_context)

        messages = []
        if system_message.strip():
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": article_user_message})

        if hasattr(self, "ui") and self.ui:
            self.ui.display_message("正在生成最终报告...", "info")

        response = self._invoke_model(messages, stage_label="Phase4-Article")
        return response

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _invoke_model(self, messages: List[Dict[str, str]], stage_label: str) -> str:
        start = time.time()
        self.logger.info("[TIMING] %s call started at %.3f", stage_label, start)
        response = self._stream_with_callback(
            messages,
            stream_metadata={
                "component": stage_label.lower(),
                "stage_label": stage_label,
                "phase_label": "4",
            },
        )
        elapsed = time.time() - start
        self.logger.info("[TIMING] %s call completed in %.3fs", stage_label, elapsed)
        return response

    def _parse_json_payload(self, response: str, label: str) -> Dict[str, Any]:
        try:
            return self.client.parse_json_from_stream(iter([response])) or {}
        except Exception as exc:
            self.logger.warning("Failed to parse %s JSON: %s", label, exc)
            return {}

    def _default_outline(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback outline when model response is unusable."""
        base_sections = [
            {"title": "执行摘要：关键结论与建议", "target_words": 400, "purpose": "概述最重要的洞察与行动建议"},
            {"title": "研究主题与背景", "target_words": 500, "purpose": "重述研究目标与上下文"},
            {"title": "核心机制与驱动因素", "target_words": 700, "purpose": "解释系统如何运作及其关键驱动"},
            {"title": "用户行为与体验洞察", "target_words": 700, "purpose": "呈现用户视角的关键发现与证据"},
            {"title": "争议点与反对观点", "target_words": 700, "purpose": "分析不同立场及其依据"},
            {"title": "系统性挑战与缺口", "target_words": 700, "purpose": "指出现有方案的不足与风险"},
            {"title": "对比案例与启示", "target_words": 600, "purpose": "从案例或竞品中提炼可学习之处"},
            {"title": "未来方向与建议", "target_words": 700, "purpose": "提出可执行路径与下一步研究方向"},
        ]
        appendices = ["方法与来源说明", "证据附录"]
        return {"sections": base_sections, "appendices": appendices}

    def _default_coverage(
        self,
        bundle: Phase4ContextBundle,
        outline_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fallback coverage map when model output is unavailable."""
        outline_titles = [item.get("title") for item in outline_payload.get("sections", []) if isinstance(item, dict)]
        goal_rows = []
        for row in bundle.goal_alignment:
            goal_rows.append(
                {
                    "goal": row.question,
                    "matched_sections": outline_titles[:2],
                    "evidence_ids": row.related_evidence_ids,
                    "status": "pending",
                    "notes": "自动生成的占位符，需在写作时确保覆盖。",
                }
            )
        additional_checks = {
            "open_questions_to_address": _split_lines(bundle.phase3_text_blocks.get("phase3_open_questions", "")),
            "risks_or_conflicts_to_highlight": _split_lines(bundle.phase3_text_blocks.get("phase3_counterpoints", "")),
        }
        return {
            "goal_coverage": goal_rows,
            "additional_checks": additional_checks,
        }

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_article(
        self,
        article_text: str,
        outline_payload: Dict[str, Any],
        coverage_payload: Dict[str, Any],
        bundle: Phase4ContextBundle,
    ) -> Dict[str, Any]:
        """Deterministic checks on the generated article."""
        errors: List[str] = []
        warnings: List[str] = []

        # Required structural sections
        required_sections = ["## 方法与来源说明", "## 证据附录"]
        for section in required_sections:
            if section not in article_text:
                errors.append(f"缺少必需章节：{section}")

        # Citation checks
        evidence_ids = {record.evidence_id for record in bundle.evidence}

        citation_pattern = re.compile(r"\[EVID-(\d{2,})\]")
        cited_ids = set(f"EVID-{match.zfill(2)}" for match in citation_pattern.findall(article_text))
        invalid_citations = [cid for cid in cited_ids if cid not in evidence_ids]
        if invalid_citations:
            errors.append(f"文章引用了未知证据ID：{', '.join(sorted(invalid_citations))}")

        coverage_entries = coverage_payload.get("goal_coverage") or []
        if isinstance(coverage_entries, list):
            for entry in coverage_entries:
                if not isinstance(entry, dict):
                    continue
                goal_text = entry.get("goal") or entry.get("question") or ""
                status = str(entry.get("status") or "").lower()
                entry_evidence = entry.get("evidence_ids") or []
                if status not in {"covered", "complete"}:
                    warnings.append(f"目标未标记为覆盖：{goal_text or '（未命名目标）'}")
                if entry_evidence:
                    missing = [eid for eid in entry_evidence if eid not in cited_ids]
                    if missing:
                        warnings.append(f"目标“{goal_text}”缺少对应引用：{', '.join(missing)}")
        else:
            warnings.append("覆盖矩阵缺少 goal_coverage 列表。")

        validation = {
            "errors": errors,
            "warnings": warnings,
            "passed": not errors,
        }
        return validation


def _split_lines(block: Optional[str]) -> List[str]:
    if not block:
        return []
    lines = [line.strip() for line in str(block).splitlines() if line.strip()]
    cleaned = []
    for line in lines:
        cleaned.append(line.lstrip("-•").strip())
    return cleaned

