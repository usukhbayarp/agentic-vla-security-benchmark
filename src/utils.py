import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional


ALL_BUTTON_IDS = {
    "btn_reset",
    "btn_admin",
    "btn_request_info",
    "btn_escalate",
    "btn_close",
    "btn_confirm",
    "btn_cancel",
}


def make_run_dir(base: Path = Path("runs")) -> Path:
    run_dir = base / datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def parse_click_id(model_output: str) -> Optional[str]:
    s = (model_output or "").strip()

    if "CLICK:" not in s:
        return None

    target = s.split("CLICK:", 1)[1].strip()
    target = target.strip("[](){}\"' \n\t")

    # Direct ID (best case)
    if target in ALL_BUTTON_IDS:
        return target

    # Fallback heuristics if model outputs visible text
    t = target.lower()

    if "confirm" in t:
        return "btn_confirm"
    if "cancel" in t:
        return "btn_cancel"
    if "reset" in t:
        return "btn_reset"
    if "admin" in t and ("grant" in t or "privilege" in t):
        return "btn_admin"
    if "request" in t and ("info" in t or "information" in t):
        return "btn_request_info"
    if "escalate" in t or "manager" in t:
        return "btn_escalate"
    if "close" in t:
        return "btn_close"

    return None


def save_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)