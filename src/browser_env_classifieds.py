import os
import time
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright


CLASSIFIEDS_URL = os.environ.get("CLASSIFIEDS_URL", "http://127.0.0.1:9980/")


def make_page_classifieds():
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

    context = browser.new_context(
        viewport={"width": 1400, "height": 1100},
        device_scale_factor=1,
    )
    page = context.new_page()
    page.goto(CLASSIFIEDS_URL, wait_until="networkidle")
    return page, browser, pw


def goto_classifieds(page, path: str = ""):
    url = urljoin(CLASSIFIEDS_URL, path)
    page.goto(url, wait_until="networkidle")
    time.sleep(0.2)
    return url


def snap(page, run_dir, t: int, prefix: str = "step") -> str:
    p = run_dir / f"{prefix}_{t:02d}.png"
    page.screenshot(path=str(p))
    return str(p)


def snap_action_highlight(page, run_dir, t: int, selector: str | None) -> str | None:
    if not selector:
        return None

    try:
        ok = page.evaluate(
            """(sel) => {
                const el = document.querySelector(sel);
                if (!el) return false;
                const prev = el.getAttribute("style") || "";
                el.setAttribute("data-vla-prev-style", prev);
                el.style.outline = "4px solid #ff006e";
                el.style.boxShadow = "0 0 0 4px rgba(255,0,110,0.25)";
                el.scrollIntoView({block: "center", inline: "center"});
                return true;
            }""",
            selector,
        )
        if not ok:
            return None

        time.sleep(0.1)
        p = run_dir / f"action_{t:02d}.png"
        page.screenshot(path=str(p))

        page.evaluate(
            """(sel) => {
                const el = document.querySelector(sel);
                if (!el) return;
                const prev = el.getAttribute("data-vla-prev-style");
                if (prev !== null) {
                    el.setAttribute("style", prev);
                    el.removeAttribute("data-vla-prev-style");
                }
            }""",
            selector,
        )
        return str(p)
    except Exception:
        return None


def read_status_classifieds(page) -> str:
    try:
        title = page.title()
    except Exception:
        title = "(unknown title)"

    try:
        h1 = page.locator("h1").first.inner_text(timeout=1000)
    except Exception:
        h1 = ""

    try:
        body_preview = page.locator("body").inner_text()[:500]
    except Exception:
        body_preview = ""

    return f"TITLE: {title}\nH1: {h1}\nBODY_PREVIEW: {body_preview}"


def get_clickable_candidates(page, max_items: int = 12) -> list[dict]:
    selectors = "a, button, input[type='submit'], input[type='button']"
    items = []

    for idx, el in enumerate(page.locator(selectors).all(), start=1):
        if len(items) >= max_items:
            break

        try:
            if not el.is_visible():
                continue

            text = el.inner_text().strip()
            if not text:
                text = el.get_attribute("value") or ""

            href = el.get_attribute("href")
            tag = el.evaluate("el => el.tagName.toLowerCase()")
            bbox = el.bounding_box()
            if bbox is None:
                continue

            selector = page.evaluate(
                """(el) => {
                    if (el.id) return `#${el.id}`;
                    const tag = el.tagName.toLowerCase();
                    const cls = (el.className || "").toString().trim().split(/\\s+/).filter(Boolean).slice(0, 2).join(".");
                    if (cls) return `${tag}.${cls}`;
                    return tag;
                }""",
                el,
            )

            items.append(
                {
                    "index": len(items) + 1,
                    "selector": selector,
                    "tag": tag,
                    "text": text[:120],
                    "href": href,
                    "rect": bbox,
                }
            )
        except Exception:
            continue

    return items


def build_classifieds_mapping_text(items: list[dict]) -> str:
    lines = ["MARKER MAPPING:"]
    if not items:
        lines.append("- (none)")
        return "\n".join(lines)

    for item in items:
        href = item["href"] or ""
        lines.append(
            f'- [{item["index"]}] selector="{item["selector"]}" text="{item["text"]}" href="{href}"'
        )
    return "\n".join(lines)


def click_selector(page, selector: str):
    page.locator(selector).first.click()
    time.sleep(0.3)


def is_terminal_classifieds(page) -> bool:
    try:
        url = page.url.lower()
    except Exception:
        url = ""

    if "page=item" in url or "page=search" in url or "page=login" in url:
        return False

    try:
        body = page.locator("body").inner_text().lower()
    except Exception:
        body = ""

    terminal_markers = [
        "contact has been sent",
        "your message has been sent",
        "listing has been published",
        "item has been deleted",
        "you have been logged out",
    ]
    return any(m in body for m in terminal_markers)


def allowed_actions_classifieds(page) -> list[dict]:
    return get_clickable_candidates(page, max_items=12)