import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from browser_env_classifieds import make_page_classifieds, get_clickable_candidates

def main():
    page, browser, pw = make_page_classifieds()
    try:
        print("TITLE:", page.title())
        print("URL:", page.url)

        raw_count = page.locator("a, button, input[type='submit'], input[type='button']").count()
        print("RAW LOCATOR COUNT:", raw_count)

        items = get_clickable_candidates(page, max_items=30)
        print("NUM ITEMS:", len(items))

        for item in items:
            print(item)

        page.screenshot(path="classifieds_debug_actions.png")
    finally:
        browser.close()
        pw.stop()

if __name__ == "__main__":
    main()