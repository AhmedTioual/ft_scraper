from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from src.transform.cleaner import get_article_content,get_article_content_archive

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
        return BeautifulSoup(html, "html.parser"),1

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
            timeout=30000
        )

        html = page.locator(
            'xpath=/html/body/center/div[4]/div/div[1]/div/div/div[1]/div[2]/div/div/div[3]'
        ).evaluate("el => el.outerHTML")

        return BeautifulSoup(html, "html.parser"),2

    except Exception as ex:
        print("Archive failed:", ex)
        return None

    finally:
        pass #browser.close()

if __name__ == "__main__":
    
    with sync_playwright() as p:
        article_url = "https://www.ft.com/content/db7251da-137d-43eb-a9c9-a27221ad2716"
        
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        soup = fetch_article_paywall(page=page,article_url=article_url)

        print(get_article_content_archive(
            article_id=article_url,
            scraped_at="date",
            paywall=True,
            section="Art",
            category="Art",
            soup=soup
        ))