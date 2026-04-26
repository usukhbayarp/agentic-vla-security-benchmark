import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from browser_env_classifieds import make_page_classifieds

def main():
    page, browser, pw = make_page_classifieds()
    try:
        print("TITLE:", page.title())
        body = page.locator("body").inner_text()
        print("BODY PREVIEW:")
        print(body[:2000])
        page.screenshot(path="classifieds_probe.png")
    finally:
        browser.close()
        pw.stop()

if __name__ == "__main__":
    main()
