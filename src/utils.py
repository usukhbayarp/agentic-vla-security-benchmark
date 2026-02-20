import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional


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
    if target in {"btn_reset", "btn_admin"}:
        return target

    # Fallback: if model returned visible button text
    t_low = target.lower()
    if "reset" in t_low:
        return "btn_reset"
    if "grant" in t_low and "admin" in t_low:
        return "btn_admin"

    return None


def save_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
