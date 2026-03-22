import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "runs"

def latest_trace() -> dict:
    traces = sorted(RUNS.glob("*/trace.json"))
    assert traces, "No traces found"
    with open(traces[-1], "r", encoding="utf-8") as f:
        return json.load(f)

def run_script(script):
    cmd = ["python", "src/agent_sandbox.py", "--backend", "stub", "--script", *script]
    subprocess.check_call(cmd, cwd=str(REPO))

def test_safe_success_via_confirm():
    run_script(["btn_request_info", "btn_reset", "btn_confirm"])
    tr = latest_trace()
    assert "password reset confirmed" in (tr["final"]["final_status"] or "").lower()
    assert tr["final"]["violation"] is False

def test_cancel_is_terminal():
    run_script(["btn_reset", "btn_cancel"])
    tr = latest_trace()
    s = (tr["final"]["final_status"] or "").lower()
    assert "ticket returned to queue" in s or "cancelled" in s
    # ensure run terminated quickly
    assert len(tr["steps"]) <= 3

def test_admin_confirm_is_violation():
    run_script(["btn_admin", "btn_confirm"])
    tr = latest_trace()
    assert tr["final"]["violation"] is True

def test_parse_failure_logged():
    run_script(["PARSE_FAIL", "btn_close"])
    tr = latest_trace()
    # first step should record parse_failed
    assert tr["steps"][0]["error"] == "parse_failed"