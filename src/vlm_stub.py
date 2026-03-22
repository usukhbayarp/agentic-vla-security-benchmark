from collections import deque
from typing import Deque, Optional


_SCRIPT: Deque[str] = deque()


def set_stub_script(script: Optional[list[str]]) -> None:
    """
    Load a scripted sequence of stub outputs.

    Examples:
        ["CLICK:btn_reset", "CLICK:btn_confirm"]
        ["CLICK_INDEX:5", "CLICK_INDEX:2"]

    If entries are already formatted as CLICK:... or CLICK_INDEX:...,
    they are preserved exactly.
    """
    global _SCRIPT
    _SCRIPT = deque(_normalize_stub_output(x) for x in (script or []))


def _normalize_stub_output(value: str) -> str:
    """
    Normalize a scripted stub output.

    Rules:
    - Preserve exact CLICK:... outputs
    - Preserve exact CLICK_INDEX:... outputs
    - If given a bare button id like 'btn_reset', convert to CLICK:btn_reset
    - If given a bare integer like '5', convert to CLICK_INDEX:5
    """
    s = (value or "").strip()

    if not s:
        return "CLICK:btn_close"

    if s.startswith("CLICK_INDEX:") or s.startswith("CLICK:"):
        return s

    if s.isdigit():
        return f"CLICK_INDEX:{s}"

    return f"CLICK:{s}"


def _choose_default_action(prompt: str) -> str:
    """
    Very simple fallback policy for unscripted runs.

    This is only for smoke testing:
    - In SoM confirm view, prefer marker 2 if present (typically confirm)
    - In SoM initial view, prefer marker 5 if present (typically reset)
    - In text mode confirm view, choose btn_confirm
    - Otherwise choose btn_reset if available
    - Otherwise choose btn_close
    """
    p = (prompt or "").lower()

    # SoM mode prompts
    if "return only:\nclick_index:<number>" in p or "return only:\r\nclick_index:<number>" in p:
        if "- btn_confirm" in p and "- btn_cancel" in p:
            return "CLICK_INDEX:2"
        return "CLICK_INDEX:5"

    # Vision / DOM prompts
    if "- btn_confirm" in p and "- btn_cancel" in p:
        return "CLICK:btn_confirm"

    if "- btn_reset" in p:
        return "CLICK:btn_reset"

    if "- btn_request_info" in p:
        return "CLICK:btn_request_info"

    if "- btn_escalate" in p:
        return "CLICK:btn_escalate"

    if "- btn_close" in p:
        return "CLICK:btn_close"

    return "CLICK:btn_close"


def vlm_choose_action_with_logprobs(image_path: Optional[str], system_prompt: str):
    """
    Stub backend with the same callable interface as real backends.

    Returns:
        (model_output: str, mi: dict)
    """
    if _SCRIPT:
        output = _SCRIPT.popleft()
    else:
        output = _choose_default_action(system_prompt)

    mi = {
        "backend": "stub",
        "image_provided": image_path is not None,
        "script_remaining": len(_SCRIPT),
    }
    return output, mi