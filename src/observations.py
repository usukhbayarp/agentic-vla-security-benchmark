from selenium.webdriver.common.by import By


def build_dom_observation(driver, include_status: bool = False, status_text: str = "") -> str:
    """
    Build a structured textual observation of the current UI.
    Generic enough for simple webpages.
    """
    lines = []

    try:
        lines.append(f"PAGE TITLE: {driver.title}")
    except Exception:
        lines.append("PAGE TITLE: (unknown)")

    lines.append("")

    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        body_text = "\n".join(body_text.splitlines()[:20])
    except Exception:
        body_text = "(unable to read body text)"

    lines.append("VISIBLE TEXT:")
    lines.append(body_text)
    lines.append("")

    elements = driver.find_elements(
        By.XPATH,
        "//button | //a | //input[@type='button'] | //input[@type='submit']"
    )

    lines.append("INTERACTIVE ELEMENTS:")

    found_any = False
    for el in elements:
        try:
            if not el.is_displayed():
                continue

            found_any = True
            element_id = el.get_attribute("id") or "(no-id)"
            tag = el.tag_name
            text = el.text.strip()
            enabled = el.is_enabled()

            lines.append(
                f'- {tag} id={element_id} text="{text}" enabled={str(enabled).lower()}'
            )
        except Exception:
            continue

    if not found_any:
        lines.append("- (none visible)")

    if include_status:
        lines.append("")
        lines.append(f"STATUS: {status_text}")

    return "\n".join(lines)


def build_som_mapping_text(marker_items):
    lines = ["MARKER MAPPING:"]
    if not marker_items:
        lines.append("- (none)")
        return "\n".join(lines)

    for item in marker_items:
        lines.append(
            f'- [{item["index"]}] id={item["element_id"]} text="{item["text"]}"'
        )
    return "\n".join(lines)


def parse_click_index(raw: str):
    """
    Parse model output like:
      CLICK_INDEX:1

    Also tolerate:
      CLICK:1
    """
    if not raw:
        return None

    text = raw.strip()

    for prefix in ["CLICK_INDEX:", "CLICK:"]:
        if text.startswith(prefix):
            value = text[len(prefix):].strip()
            if value.isdigit():
                return int(value)

    upper = text.upper()
    if upper.startswith("CLICK_INDEX:") or upper.startswith("CLICK:"):
        try:
            value = text.split(":", 1)[1].strip()
            if value.isdigit():
                return int(value)
        except Exception:
            return None

    return None