from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


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


def get_visible_actionable_elements(page, allowed: set[str]):
    items = []
    idx = 1

    for element_id in sorted(allowed):
        try:
            el = page.locator(f"#{element_id}")
            if not el.is_visible():
                continue

            bbox = el.bounding_box()
            if bbox is None:
                continue

            items.append({
                "index": idx,
                "element_id": element_id,
                "text": el.inner_text().strip(),
                "rect": bbox,  # keys: x, y, width, height
            })
            idx += 1
        except Exception:
            continue

    return items


def make_set_of_marks_view(page, full_screenshot_path: str, run_dir: Path, t: int, allowed: set[str]):
    items = get_visible_actionable_elements(page, allowed)

    img = Image.open(full_screenshot_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    font = _load_marker_font(18)

    try:
        dpr = float(page.evaluate("window.devicePixelRatio || 1.0"))
    except Exception:
        dpr = 1.0

    for item in items:
        r = item["rect"]
        x = int(r["x"] * dpr)
        y = int(r["y"] * dpr)
        w = int(r["width"] * dpr)
        h = int(r["height"] * dpr)

        draw.rectangle([x, y, x + w, y + h], outline=(255, 0, 0), width=3)

        badge_size = 26
        bx1 = x
        by1 = max(0, y - badge_size)
        bx2 = x + badge_size
        by2 = by1 + badge_size

        draw.rectangle([bx1, by1, bx2, by2], fill=(255, 255, 0), outline=(255, 0, 0), width=2)
        draw.text((bx1 + 7, by1 + 3), str(item["index"]), fill=(0, 0, 0), font=font)

    marked_path = run_dir / f"step_{t:02d}_som.png"
    img.save(marked_path)

    return str(marked_path), items