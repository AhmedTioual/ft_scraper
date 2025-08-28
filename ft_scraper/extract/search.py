from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import json

BASE_URL = "https://www.ft.com"


# -----------------------------
# Article / Section Utilities
# -----------------------------

def get_leaf_articles(p, leaf_url):
    
    """
    Given a leaf section URL, return a list of unique article links.
    """
    links = set()
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    try:
        page.goto(leaf_url, timeout=60000, wait_until="networkidle")
        page.wait_for_selector("#stream", timeout=30000)

        soup = BeautifulSoup(page.content(), "html.parser")
        site_content = soup.find("div", id="stream")

        for a_tag in site_content.find_all("li", href=True):
            href = a_tag['href']
            if href.startswith("/content/"):
                links.add(BASE_URL + href)
        
        return list(links)
    except:
        pass

    finally:
        browser.close()


def get_new_articles(p, leaf_url, latest_db_date: str):
    """
    Scrape articles from a leaf URL and return only articles newer than latest_db_date.

    Args:
        p: Playwright object
        leaf_url (str): The leaf page URL
        latest_db_date (str): Latest published_at in DB (ISO format)

    Returns:
        List[]: 'href'
    """
    articles = []
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Convert DB date string to datetime for comparison
    try:
        latest_dt = datetime.fromisoformat(latest_db_date.replace("Z", "+00:00"))
    except Exception:
        latest_dt = None

    try:
        page.goto(leaf_url, timeout=60000, wait_until="networkidle")
        page.wait_for_selector("#stream", timeout=30000)

        soup = BeautifulSoup(page.content(), "html.parser")
        site_content = soup.find("div", id="stream")
        if not site_content:
            return []

        for li in site_content.find_all("li", class_="o-teaser-collection__item"):
            time_tag = li.find("time")
            a_tag = li.find("a", class_="js-teaser-heading-link")

            if not time_tag or not time_tag.has_attr("datetime") or not a_tag or not a_tag.has_attr("href"):
                continue

            published_at = time_tag["datetime"]
            href = a_tag["href"]
            if not href.startswith("http"):
                href = BASE_URL.rstrip("/") + href

            # Compare article datetime with latest in DB
            try:
                article_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except Exception:
                continue

            if latest_dt and article_dt <= latest_dt:
                # Stop loop: reached already stored articles
                break

            articles.append(href)

        return articles

    except Exception as e:
        print(f"Error fetching articles: {e}")
        return []

    finally:
        browser.close()

def has_subsections(p, url):
    """
    Check if a section has child subsections.
    Returns (True/False, list of <li> items if found).
    """
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    try:
        page.goto(url, timeout=60000)
        subnav_html = page.locator(
            "ul.o-header__subnav-list--children"
        ).evaluate("el => el.outerHTML")

        soup = BeautifulSoup(subnav_html, "html.parser")
        items = soup.find_all("li", class_="o-header__subnav-item")
        return bool(items), items

    except Exception:
        return False, []

    finally:
        browser.close()

def collect_leaf_sections(p, items, base_url=BASE_URL):
    """
    Recursively collect all leaf section URLs starting from given items.
    """
    leaf_urls = set()

    for item in items:
        url = base_url + item.a["href"]
        print("🔎 Searching:", url)

        found, subitems = has_subsections(p, url)

        if not found:
            leaf_urls.add(url)
        else:
            leaf_urls.update(collect_leaf_sections(p, subitems, base_url))

    return list(leaf_urls)

def find_leaf_sections(p, section_url):
    """
    Entry point: given a top-level section, find its leaf subsections.
    """
    found, items = has_subsections(p, section_url)
    return section_url if not found else collect_leaf_sections(p, items, BASE_URL)

# -----------------------------
# Parallel Section Processor
# -----------------------------
def process_section(main_url, href):  
    """
    Worker function to process one top-level section.
    Returns (section_name, leafSections).
    """
    with sync_playwright() as p:
        full_url = main_url + href
        section_name = full_url.strip("/").split("/")[-1]

        leaf_sections = find_leaf_sections(p, full_url)
        return section_name, leaf_sections

def update_sections():
    """
    Crawl FT main nav → resolve to leaf sections → save to JSON.
    """
    results = {
        "last_update": datetime.now().isoformat(),
        "sections": {}
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL, timeout=60000)

        # Extract nav items
        nav_html = page.locator("nav#o-header-nav-desktop").evaluate("el => el.outerHTML")
        soup = BeautifulSoup(nav_html, "html.parser")
        items = soup.find_all("li", class_="o-header__nav-item")
        browser.close()

    # Collect all hrefs except "/"
    hrefs = [item.a["href"] for item in items if item.a and item.a["href"] != "/"]

    # For demo → limit to 1 section
    hrefs = hrefs[:5]

    # Parallel processing
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_section, BASE_URL, href) for href in hrefs]

        for future in as_completed(futures):
            section_name, leaf_sections = future.result()
            results["sections"][section_name] = leaf_sections
            print(f"✅ Leaf Sections of {section_name}: {leaf_sections}")

    # Save JSON
    with open("data/metadata/ft_structure.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print("📂 FT structure saved to data/metadata/ft_structure.json")

# -----------------------------
# Demo
# -----------------------------
if __name__ == "__main__":
    
    # Run crawler for structure
    #update_sections()

    with sync_playwright() as p:

        new_articles = get_new_articles(p=p, leaf_url="https://www.ft.com/global-economy", latest_db_date="2025-08-26T13:19:08.330Z")

        print(new_articles)