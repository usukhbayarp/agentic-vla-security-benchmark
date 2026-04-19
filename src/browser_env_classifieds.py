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


def get_clickable_candidates(page, max_items: int = 12) -> list[dict]:
    selectors = "a, button, input[type='submit'], input[type='button']"
    raw_items = []

    loc = page.locator(selectors)
    count = loc.count()

    print(f"[DEBUG] raw clickable count: {count}")

    for i in range(count):
        el = loc.nth(i)

        try:
            if not el.is_visible():
                continue

            bbox = el.bounding_box()
            if bbox is None or bbox["width"] < 5 or bbox["height"] < 5:
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
            print(f"[DEBUG] skipped element {i}: {e}")
            continue

    # Deduplicate by href+text
    seen = set()
    deduped = []
    for item in raw_items:
        key = ((item["href"] or "").strip(), item["text"].strip().lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    def score(item):
        text = item["text"].lower()
        href = (item["href"] or "").lower()

        s = 0
        if "publish ad" in text: s += 50
        if "login" in text: s += 40
        if "register" in text: s += 30
        if item["tag"] == "button": s += 20
        if "page=item&id=" in href: s += 25
        if "search" in text: s += 15
        if text == "classifieds": s -= 50
        if "category" in href or "scategory" in href: s -= 10
        return -s  # lower sorts first

    deduped.sort(key=score)
    deduped = deduped[:max_items]

    items = []
    for idx, item in enumerate(deduped, start=1):
        item["index"] = idx
        items.append(item)

    print(f"[DEBUG] filtered clickable count: {len(items)}")
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
    """
    Render a SoM screenshot for Classifieds using precomputed clickable candidates.
    Each candidate is expected to have:
      - index
      - selector
      - text
      - rect {x, y, width, height}
    """

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

        # Skip offscreen / degenerate boxes
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