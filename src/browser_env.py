import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service


def make_driver():
    options = webdriver.ChromeOptions()

    if os.environ.get("DOCKER"):
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

    options.add_argument("--window-size=1400,1100")

    chromium_bin_candidates = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
    ]
    chromedriver_candidates = [
        "/usr/bin/chromedriver",
        "/usr/lib/chromium/chromedriver",
        "/usr/lib/chromium-browser/chromedriver",
    ]

    chromium_bin = next((p for p in chromium_bin_candidates if os.path.exists(p)), None)
    chromedriver_bin = next((p for p in chromedriver_candidates if os.path.exists(p)), None)

    if chromium_bin and chromedriver_bin:
        options.binary_location = chromium_bin
        service = Service(chromedriver_bin)
        return webdriver.Chrome(service=service, options=options)

    # Local non-container fallback only
    if not os.environ.get("DOCKER"):
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    raise RuntimeError(
        "No system Chromium/Chrome + chromedriver found inside container, "
        "and webdriver-manager fallback is disabled in DOCKER mode."
    )


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


def snap(driver, run_dir: Path, t: int) -> str:
    p = run_dir / f"step_{t:02d}.png"
    driver.save_screenshot(str(p))
    return str(p)


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