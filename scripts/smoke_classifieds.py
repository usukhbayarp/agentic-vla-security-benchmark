from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:9980/"

with sync_playwright() as pw:
    browser = pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    )
    context = browser.new_context(
        viewport={"width": 1400, "height": 1100},
        device_scale_factor=1,
    )
    page = context.new_page()
    page.goto(URL, wait_until="networkidle")
    print("TITLE:", page.title())
    print("URL:", page.url)
    page.screenshot(path="classifieds_home.png")
    browser.close()
