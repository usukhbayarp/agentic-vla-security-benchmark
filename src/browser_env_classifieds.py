from playwright.sync_api import sync_playwright

CLASSIFIEDS_URL = "http://127.0.0.1:9980/"

def make_page_classifieds():
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    )
    context = browser.new_context(
        viewport={"width": 1400, "height": 1100},
        device_scale_factor=1,
    )
    page = context.new_page()
    page.goto(CLASSIFIEDS_URL, wait_until="networkidle")
    return page, browser, pw
