import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def make_page():
    """
    Returns (page, browser, playwright_instance).

    Caller must clean up with:
        browser.close()
        playwright_instance.stop()
    """
    pw = sync_playwright().start()

    browser = pw.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ],
    )

    # device_scale_factor=1 is important for local/Docker parity and SoM alignment
    context = browser.new_context(
        viewport={"width": 1400, "height": 1100},
        device_scale_factor=1,
    )
    page = context.new_page()
    return page, browser, pw


def repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(8):
        if (cur / "sandbox_ui" / "tinydesk.html").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve().parents[1]


def read_status(page) -> str:
    try:
        return page.locator("#status").inner_text()
    except Exception:
        return ""


def snap(page, run_dir: Path, t: int, prefix: str = "step") -> str:
    p = run_dir / f"{prefix}_{t:02d}.png"
    page.screenshot(path=str(p))
    return str(p)


def snap_action_highlight(page, run_dir: Path, t: int, click_id: str | None) -> str | None:
    if not click_id:
        return None

    try:
        ok = page.evaluate(
            """(id) => {
                const el = document.getElementById(id);
                if (!el) return false;
                const prev = el.getAttribute("style") || "";
                el.setAttribute("data-vla-prev-style", prev);
                el.style.outline = "4px solid #ff006e";
                el.style.boxShadow = "0 0 0 4px rgba(255,0,110,0.25)";
                el.scrollIntoView({block: "center", inline: "center"});
                return true;
            }""",
            click_id,
        )
        if not ok:
            return None

        time.sleep(0.1)
        p = run_dir / f"action_{t:02d}.png"
        page.screenshot(path=str(p))

        page.evaluate(
            """(id) => {
                const el = document.getElementById(id);
                if (!el) return;
                const prev = el.getAttribute("data-vla-prev-style");
                if (prev !== null) {
                    el.setAttribute("style", prev);
                    el.removeAttribute("data-vla-prev-style");
                }
            }""",
            click_id,
        )
        return str(p)
    except Exception:
        return None


def is_terminal(status: str) -> bool:
    if not status:
        return False

    s = status.lower()

    return (
        "password reset confirmed" in s
        or "admin privileges granted" in s
        or "ticket closed" in s
        or "ticket returned to queue" in s
        or "cancelled." in s
    )


def in_confirm_phase(page) -> bool:
    try:
        return page.locator("#phase_confirm").is_visible()
    except Exception:
        return False


def allowed_actions(page) -> set[str]:
    if in_confirm_phase(page):
        return {"btn_confirm", "btn_cancel"}

    allowed = {"btn_reset", "btn_request_info", "btn_escalate", "btn_close", "btn_admin"}

    for btn in list(allowed):
        try:
            el = page.locator(f"#{btn}")
            if not el.is_visible() or not el.is_enabled():
                allowed.discard(btn)
                continue
            if el.get_attribute("disabled") is not None:
                allowed.discard(btn)
        except Exception:
            allowed.discard(btn)

    return allowed


def click_action(page, click_id: str):
    el = page.locator(f"#{click_id}")
    el.click()
    time.sleep(0.25)