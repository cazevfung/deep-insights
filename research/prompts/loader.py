"""Utilities for loading and rendering prompts from the filesystem."""

import os
import json
from typing import Dict, List, Optional
from core.config import Config, find_project_root


_CACHE: Dict[str, Dict[str, object]] = {}


def _get_base_dir() -> str:
    # 1) env override
    base_dir = os.environ.get("PROMPTS_BASE_DIR")
    if base_dir:
        return base_dir
    # 2) config.yaml setting
    try:
        cfg = Config()
        cfg_dir = cfg.get("prompts.base_dir", None)
        if cfg_dir:
            # Resolve relative path against project root to avoid CWD issues during tests
            if not os.path.isabs(cfg_dir):
                project_root = str(find_project_root())
                return os.path.normpath(os.path.join(project_root, cfg_dir))
            return cfg_dir
    except Exception:
        pass
    # 3) default relative to this file: research/prompts
    return os.path.dirname(os.path.abspath(__file__))


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _maybe_cached(path: str) -> Optional[str]:
    try:
        stat = os.stat(path)
    except FileNotFoundError:
        return None
    cache_entry = _CACHE.get(path)
    if cache_entry and cache_entry.get("mtime") == stat.st_mtime:
        return cache_entry["content"]  # type: ignore[index]
    content = _read_text(path)
    _CACHE[path] = {"mtime": stat.st_mtime, "content": content}
    return content


def _resolve_phase_dir(phase: str, locale: Optional[str] = None, variant: Optional[str] = None) -> List[str]:
    base = _get_base_dir()
    candidates: List[str] = []
    # locale-specific under _locales
    if locale:
        candidates.append(os.path.join(base, "_locales", locale, phase))
    # variant-specific under phase/_variants
    if variant:
        candidates.append(os.path.join(base, phase, "_variants", variant))
    # default phase directory
    candidates.append(os.path.join(base, phase))
    return candidates


def load_prompt(phase: str, role: str = "instructions", *, locale: Optional[str] = None, variant: Optional[str] = None) -> str:
    """
    Load a prompt file for a given phase and role.

    role should match a filename without extension (e.g., "system", "instructions").
    """
    for root in _resolve_phase_dir(phase, locale=locale, variant=variant):
        path = os.path.join(root, f"{role}.md")
        if os.path.exists(path):
            content = _maybe_cached(path)
            if content is not None:
                return _apply_partials(content, os.path.dirname(path))
    raise FileNotFoundError(f"Prompt not found for phase='{phase}', role='{role}'")


def load_schema(phase: str, name: str = "output_schema.json", *, locale: Optional[str] = None, variant: Optional[str] = None) -> Optional[dict]:
    for root in _resolve_phase_dir(phase, locale=locale, variant=variant):
        path = os.path.join(root, name)
        if os.path.exists(path):
            return _read_json(path)
    return None


def render_prompt(template: str, context: Dict[str, object]) -> str:
    try:
        return template.format(**context)
    except KeyError as e:
        missing = str(e).strip("'")
        raise KeyError(f"Missing placeholder '{missing}' in context while rendering prompt")


def compose_messages(
    phase: str,
    context: Dict[str, object],
    *,
    locale: Optional[str] = None,
    variant: Optional[str] = None,
) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    # optional system message
    try:
        system_tmpl = load_prompt(phase, role="system", locale=locale, variant=variant)
        system_msg = render_prompt(system_tmpl, context)
        if system_msg.strip():
            messages.append({"role": "system", "content": system_msg})
    except FileNotFoundError:
        pass

    # required instructions/user message
    instructions_tmpl = load_prompt(phase, role="instructions", locale=locale, variant=variant)
    instructions_msg = render_prompt(instructions_tmpl, context)
    messages.append({"role": "user", "content": instructions_msg})

    return messages


def _apply_partials(content: str, phase_dir: str) -> str:
    """Simple include mechanism: {{> filename.md}} resolved from phase_dir or prompts/_partials."""
    base = _get_base_dir()
    partials_dir = os.path.join(base, "_partials")

    def replace_once(text: str) -> str:
        start = 0
        while True:
            idx = text.find("{{>", start)
            if idx == -1:
                return text
            end = text.find("}}", idx)
            if end == -1:
                return text
            token = text[idx + 3 : end].strip()
            candidate_paths = [
                os.path.join(phase_dir, token),
                os.path.join(partials_dir, token),
            ]
            included = None
            for p in candidate_paths:
                if os.path.exists(p):
                    included = _maybe_cached(p)
                    break
            if included is None:
                included = f"<!-- Missing partial: {token} -->"
            text = text[:idx] + included + text[end + 2 :]
            start = idx + len(included)
        
    prev = None
    curr = content
    # iterate until no more includes are found (prevent infinite loops by cap)
    for _ in range(16):
        prev = curr
        curr = replace_once(curr)
        if curr == prev:
            break
    return curr


