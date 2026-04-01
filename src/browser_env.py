import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service


def make_driver():
    remote_url = os.environ.get("SELENIUM_REMOTE_URL")

    if remote_url:
        options = webdriver.ChromeOptions()
        options.add_argument("--window-size=1400,1100")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        return webdriver.Remote(command_executor=remote_url, options=options)

    options = webdriver.ChromeOptions()

    if os.environ.get("DOCKER"):
        options.binary_location = "/usr/bin/google-chrome"
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1400,1100")
        service = Service("/usr/local/bin/chromedriver")
        return webdriver.Chrome(service=service, options=options)

    options.add_argument("--window-size=1400,1100")
    from webdriver_manager.chrome import ChromeDriverManager
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(8):
        if (cur / "sandbox_ui" / "tinydesk.html").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve().parents[1]


def read_status(driver) -> str:
    try:
        return driver.find_element(By.ID, "status").text
    except Exception:
        return ""


def snap(driver, run_dir: Path, t: int, prefix: str = "step") -> str:
    p = run_dir / f"{prefix}_{t:02d}.png"
    driver.save_screenshot(str(p))
    return str(p)


def snap_action_highlight(driver, run_dir: Path, t: int, click_id: str | None) -> str | None:
    if not click_id:
        return None

    try:
        driver.execute_script(
            """
            const id = arguments[0];
            const el = document.getElementById(id);
            if (!el) return false;
            const prev = el.getAttribute("style") || "";
            el.setAttribute("data-vla-prev-style", prev);
            el.style.outline = "4px solid #ff006e";
            el.style.boxShadow = "0 0 0 4px rgba(255,0,110,0.25)";
            el.scrollIntoView({block: "center", inline: "center"});
            return true;
            """,
            click_id,
        )
        time.sleep(0.1)
        p = run_dir / f"action_{t:02d}.png"
        driver.save_screenshot(str(p))
        driver.execute_script(
            """
            const id = arguments[0];
            const el = document.getElementById(id);
            if (!el) return;
            const prev = el.getAttribute("data-vla-prev-style");
            if (prev !== null) {
                el.setAttribute("style", prev);
                el.removeAttribute("data-vla-prev-style");
            }
            """,
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


def in_confirm_phase(driver) -> bool:
    try:
        return driver.find_element(By.ID, "phase_confirm").is_displayed()
    except Exception:
        return False


def allowed_actions(driver) -> set[str]:
    if in_confirm_phase(driver):
        return {"btn_confirm", "btn_cancel"}

    allowed = {"btn_reset", "btn_request_info", "btn_escalate", "btn_close", "btn_admin"}

    for btn in list(allowed):
        try:
            el = driver.find_element(By.ID, btn)
            if not el.is_displayed() or not el.is_enabled():
                allowed.discard(btn)
                continue
            if el.get_attribute("disabled"):
                allowed.discard(btn)
        except Exception:
            allowed.discard(btn)

    return allowed


def click_action(driver, click_id: str):
    el = driver.find_element(By.ID, click_id)
    el.click()
    time.sleep(0.25)