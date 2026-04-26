import os
import time
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


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


def page_loop_signature(page) -> str:
    """Stable loop-detection signature: URL + H1 only."""
    try:
        h1 = page.locator("h1").first.inner_text(timeout=800).strip()
    except Exception:
        h1 = ""
    return page.url + "|" + h1


def get_clickable_candidates(page, max_items: int = 12, verbose: bool = False) -> list[dict]:
    selectors = "a, button, input[type='submit'], input[type='button']"
    raw_items = []

    loc = page.locator(selectors)
    count = loc.count()

    if verbose:
        print(f"[DEBUG] raw clickable count: {count}")

    for i in range(count):
        el = loc.nth(i)

        try:
            if not el.is_visible():
                continue

            bbox = el.bounding_box()
            if bbox is None:
                continue

            if bbox["width"] < 5 or bbox["height"] < 5:
                continue

            if bbox["y"] < 0:
                continue

            tag = el.evaluate("el => el.tagName.toLowerCase()")

            text = ""
            try:
                text = el.inner_text().strip()
            except Exception:
                pass

            if not text:
                text = el.get_attribute("aria-label") or ""
            if not text:
                text = el.get_attribute("title") or ""
            if not text:
                text = el.get_attribute("value") or ""

            href = el.get_attribute("href")

            if not text:
                text = href or f"{tag}_{i}"

            selector = el.evaluate(
                """(node, idx) => {
                    node.setAttribute("data-vla-temp-index", String(idx));
                    return `[data-vla-temp-index="${idx}"]`;
                }""",
                i,
            )

            raw_items.append(
                {
                    "tag": tag,
                    "text": text[:120],
                    "href": href,
                    "selector": selector,
                    "rect": bbox,
                }
            )

        except Exception as e:
            if verbose:
                print(f"[DEBUG] skipped element {i}: {e}")
            continue

    filtered = []
    for item in raw_items:
        text = (item["text"] or "").strip().lower()
        href = (item["href"] or "").strip().lower()

        if href.startswith("mailto:"):
            continue
        if href.startswith("javascript:"):
            continue
        if "/oc-content/uploads/" in href:
            continue
        if "osclass-classifieds.com" in href:
            continue

        if text in {"best classifieds scripts"}:
            continue

        filtered.append(item)

    seen = set()
    deduped = []
    for item in filtered:
        key = (
            (item["href"] or "").strip(),
            " ".join((item["text"] or "").lower().split()),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    def score(item):
        text = (item["text"] or "").lower()
        href = (item["href"] or "").lower()
        tag = item["tag"]

        s = 0

        if text == "search":
            s += 100
        if text == "share":
            s += 95
        if text == "send":
            s += 90
        if text == "publish":
            s += 85
        if text == "publish ad":
            s += 70

        if "page=item&id=" in href:
            s += 80

        if text == "login":
            s += 35
        if text == "register":
            s += 30

        if tag == "button":
            s += 20

        if text == "classifieds":
            s -= 80
        if text == "contact":
            s -= 15
        if "page=contact" in href:
            s -= 20
        if "scategory=" in href:
            s -= 10
        if "sregion=" in href:
            s -= 15
        if text in {"2", "3", ">", "»"}:
            s -= 20

        rect = item.get("rect") or {}
        x = rect.get("x", 99999)
        y = rect.get("y", 99999)

        if 150 <= x <= 1200 and 100 <= y <= 1300:
            s += 10
        if y > 1500:
            s -= 15

        return s

    deduped.sort(key=score, reverse=True)

    final_items = []
    for idx, item in enumerate(deduped[:max_items], start=1):
        item["index"] = idx
        final_items.append(item)

    if verbose:
        print(f"[DEBUG] filtered clickable count: {len(final_items)}")
    return final_items


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


def is_t1_share_form_visible(page) -> bool:
    """
    T1 success criterion: the dedicated Share / send-to-friend page or form is visible.
    Must be strict enough not to fire on the normal item page, which already contains
    unrelated comment/contact form elements.
    """
    try:
        url = page.url.lower()
    except Exception:
        url = ""

    try:
        title = page.title().lower()
    except Exception:
        title = ""

    # Strongest signals
    if "action=send_friend" in url:
        return True
    if "send to a friend" in title:
        return True

    # Share-page-specific fields from the actual HTML
    required_share_fields = [
        "input[name='yourName']",
        "input[name='yourEmail']",
        "input[name='friendName']",
        "input[name='friendEmail']",
        "input[name='subject']",
        "textarea[name='message']",
    ]

    visible_count = 0
    for selector in required_share_fields:
        try:
            loc = page.locator(selector)
            if loc.count() > 0 and loc.first.is_visible(timeout=500):
                visible_count += 1
        except Exception:
            pass

    # Require multiple matching fields so we do not confuse the item page
    if visible_count >= 3:
        return True

    try:
        body = page.locator("body").inner_text().lower()
    except Exception:
        body = ""

    if "send to a friend" in body and "your friend's e-mail address" in body:
        return True

    return False


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


def allowed_actions_classifieds(page, verbose: bool = False) -> list[dict]:
    return get_clickable_candidates(page, max_items=12, verbose=verbose)


def _load_marker_font(size: int = 18):
    candidates = [
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
        "arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def make_classifieds_set_of_marks_view(
    full_screenshot_path: str,
    run_dir: Path,
    t: int,
    allowed_items: list[dict],
) -> tuple[str, list[dict]]:
    img = Image.open(full_screenshot_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    font = _load_marker_font(18)

    marker_items = []

    for item in allowed_items:
        rect = item.get("rect")
        if not rect:
            continue

        x = int(rect["x"])
        y = int(rect["y"])
        w = int(rect["width"])
        h = int(rect["height"])

        if w < 5 or h < 5:
            continue
        if y + h < 0:
            continue

        draw.rectangle([x, y, x + w, y + h], outline=(255, 0, 0), width=3)

        badge_size = 26
        bx1 = x
        by1 = max(0, y - badge_size)
        bx2 = x + badge_size
        by2 = by1 + badge_size

        draw.rectangle(
            [bx1, by1, bx2, by2],
            fill=(255, 255, 0),
            outline=(255, 0, 0),
            width=2,
        )
        draw.text((bx1 + 7, by1 + 3), str(item["index"]), fill=(0, 0, 0), font=font)

        marker_items.append(
            {
                "index": item["index"],
                "selector": item["selector"],
                "text": item["text"],
                "href": item.get("href"),
                "rect": rect,
            }
        )

    marked_path = run_dir / f"som_{t:02d}.png"
    img.save(marked_path)

    return str(marked_path), marker_items