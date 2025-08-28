from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


def check_paywall(page, article_url):
    """
    Check if the article page has a paywall by counting
    <p> elements with class 'o3-type-detail'.
    Returns True if paywall exists, False otherwise.
    """
    #browser = p.chromium.launch(headless=True)
    #page = browser.new_page()
    try:
        page.goto(article_url, timeout=60000)
        count = page.locator("p.o3-type-detail").count()
        return count > 0
    except Exception:
        return False
    finally:
        pass #browser.close()

def fetch_article_free(page, article_url):
    """
    Fetch article content directly if it is free.
    Returns BeautifulSoup object or None on failure.
    """
    #browser = p.chromium.launch(headless=True)
    #page = browser.new_page()
    try:
        print("Visiting (free):", article_url)
        page.goto(article_url, timeout=60000)
        page.wait_for_selector("div.article-content", timeout=10000)

        html = page.locator("div.article-content").evaluate("el => el.outerHTML")
        return BeautifulSoup(html, "html.parser")

    except Exception as ex:
        print("Error fetching free article:", ex)
        return None
    finally:
        pass #browser.close()

def fetch_article_paywall(page, article_url):
    """
    Try to bypass paywall using alternative services.
    Returns BeautifulSoup object or None on failure.
    """
    options = [
        "https://accessarticlenow.com/api/c/full?q=",
        "https://archive.md/20250824050137/"
    ]

    # --- Primary attempt ---
    #browser = p.chromium.launch(headless=True)
    #page = browser.new_page()
    try:
        url = options[0] + article_url
        print("Trying primary bypass:", url)

        page.goto(url, timeout=60000)
        page.wait_for_selector("div.article-content", timeout=10000)

        html = page.locator("div.article-content").evaluate("el => el.outerHTML")
        return BeautifulSoup(html, "html.parser")

    except Exception:
        print("Primary failed, trying archive...")

    finally:
        pass #browser.close()

    # --- Secondary attempt (archive) ---
    #browser = p.chromium.launch(headless=False)  # not headless for archive
    #page = browser.new_page()
    try:
        url = options[1] + article_url
        print("Trying archive:", url)

        page.goto(url, timeout=60000)
        page.wait_for_selector(
            'xpath=/html/body/center/div[4]/div/div[1]/div/div/div[1]/div[2]/div/div/div[3]',
            timeout=10000
        )

        html = page.locator(
            'xpath=/html/body/center/div[4]/div/div[1]/div/div/div[1]/div[2]/div/div/div[3]'
        ).evaluate("el => el.outerHTML")

        return BeautifulSoup(html, "html.parser")

    except Exception as ex:
        print("Archive failed:", ex)
        return None

    finally:
        pass #browser.close()

"""

if __name__ == "__main__":
    
    with sync_playwright() as p:
        article_url = "https://www.ft.com/content/67aebda9-b86d-4be9-a1e1-1df262d745f0"

        if check_paywall(p, article_url):
            soup = fetch_article_paywall(p, article_url)
        else:
            soup = fetch_article_free(p, article_url)

        if soup:
            print("Article fetched successfully")
            print(soup)
        else:
            print("Failed to fetch article")
            print(soup)

"""