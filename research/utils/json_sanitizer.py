"""Utilities for cleaning up JSON streaming output before parsing."""

from typing import Iterable

# Characters that must always be escaped inside JSON strings.
_CONTROL_CHAR_MAX = 0x20
_EXTRA_UNICODE_NEED_ESCAPE = {0x2028, 0x2029}


def _escape_control_char(ch: str) -> str:
    """Return a JSON-safe escape sequence for a single character."""
    if ch == "\n":
        return "\\n"
    if ch == "\r":
        return "\\r"
    if ch == "\t":
        return "\\t"
    codepoint = ord(ch)
    return f"\\u{codepoint:04x}"


def sanitize_json_stream_text(text: str) -> str:
    """
    Ensure streamed JSON text is syntactically valid by escaping control chars.

    The Qwen streaming API occasionally emits literal control characters
    (especially newlines) *inside* quoted strings. These are not valid JSON and
    cause incremental parsers to fail. We walk the string, track whether we are
    inside a quoted string, and replace any problematic characters with their
    escaped equivalents.
    """
    if not text:
        return text

    in_string = False
    escape_next = False
    pieces: list[str] = []

    for ch in text:
        if escape_next:
            pieces.append(ch)
            escape_next = False
            continue

        if ch == "\\":
            pieces.append(ch)
            escape_next = True
            continue

        if ch == '"':
            in_string = not in_string
            pieces.append(ch)
            continue

        if in_string:
            codepoint = ord(ch)
            if codepoint < _CONTROL_CHAR_MAX or codepoint in _EXTRA_UNICODE_NEED_ESCAPE:
                pieces.append(_escape_control_char(ch))
                continue

        pieces.append(ch)

    return "".join(pieces)


def sanitize_iterable(chunks: Iterable[str]) -> Iterable[str]:
    """Yield sanitized chunks from an iterable of string pieces."""
    for chunk in chunks:
        yield sanitize_json_stream_text(chunk)

