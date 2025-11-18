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
        article_text = self._run_article_stage(system_message, prompt_context, outline_payload, bundle)

        validation = self._validate_article(article_text, outline_payload, bundle)

        # Persist artifacts for debugging/QA
        try:
            self.session.save_phase_artifact("phase4_outline", outline_payload, autosave=False)
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
            system_template = load_prompt("phase4_synthesize", role="system", context=context)
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
        outline_template = load_prompt("phase4_synthesize", role="outline", context=outline_context)
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

    def _run_article_stage(
        self,
        system_message: str,
        base_context: Dict[str, Any],
        outline_payload: Dict[str, Any],
        bundle: Phase4ContextBundle,
    ) -> str:
        """Stage 2: Produce the full article using outline guidance."""
        article_context = dict(base_context)
        article_context["outline_json"] = json.dumps(outline_payload, ensure_ascii=False, indent=2)

        if bundle.enable_auxiliary_artifacts:
            article_context["auxiliary_artifacts_required"] = "yes"
        else:
            article_context["auxiliary_artifacts_required"] = "no"

        article_template = load_prompt("phase4_synthesize", role="instructions", context=article_context)
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
                "enable_json_streaming": True,  # Enable real-time JSON parsing
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

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_article(
        self,
        article_text: str,
        outline_payload: Dict[str, Any],
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

        # Check if component questions are likely addressed
        component_questions = bundle.component_questions
        if component_questions:
            questions_text = " ".join(component_questions).lower()
            article_lower = article_text.lower()
            # Simple heuristic: check if question keywords appear in article
            for question in component_questions:
                if len(question) > 10:  # Only check substantial questions
                    # Extract key terms from question (simple approach)
                    key_terms = [w for w in question.lower().split() if len(w) > 3]
                    if key_terms and not any(term in article_lower for term in key_terms[:3]):
                        warnings.append(f"组成问题可能未得到充分回答：{question[:50]}...")

        validation = {
            "errors": errors,
            "warnings": warnings,
            "passed": not errors,
        }
        return validation

