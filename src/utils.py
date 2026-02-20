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
    click_id = s.split("CLICK:", 1)[1].strip()
    click_id = click_id.strip("[](){}\"' \n\t")
    if not click_id or any(ch.isspace() for ch in click_id):
        return None
    return click_id


def save_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)