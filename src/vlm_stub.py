# vlm_stub.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import random

@dataclass
class StubPolicy:
    """
    Deterministic policy for sandbox testing.
    Provide a script like: ["btn_request_info", "btn_reset", "btn_confirm"]
    Special tokens:
      - "PARSE_FAIL" -> emits non-CLICK output
      - "GIBBERISH"  -> emits junk text
      - "INVALID:<id>" -> emits CLICK:<id> (even if invalid in current state)
    """
    script: List[str]
    idx: int = 0

    def next(self) -> str:
        if self.idx >= len(self.script):
            # Default fallback if script ends: choose close to terminate
            return "CLICK:btn_close"

        token = self.script[self.idx]
        self.idx += 1

        if token == "PARSE_FAIL":
            return "I think you should reset the password."  # missing CLICK:
        if token == "GIBBERISH":
            return "<<<@@@###>>>"
        if token.startswith("INVALID:"):
            return f"CLICK:{token.split(':', 1)[1]}"
        # normal
        return f"CLICK:{token}"


# Global singleton policy (agent_sandbox can set it)
_POLICY: Optional[StubPolicy] = None

def set_stub_script(script: List[str]) -> None:
    global _POLICY
    _POLICY = StubPolicy(script=script)

def vlm_choose_action(screenshot_path: str, system_prompt: str) -> str:
    if _POLICY is None:
        # Default: safe-ish, but still progresses
        return "CLICK:btn_reset"
    return _POLICY.next()

def vlm_choose_action_with_logprobs(screenshot_path: str, system_prompt: str):
    # Keep interface compatible with mlx version
    return vlm_choose_action(screenshot_path, system_prompt), {}