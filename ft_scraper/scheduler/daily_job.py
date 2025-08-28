import json
from datetime import datetime, timedelta
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from ft_scraper.extract.fetch import fetch_article_free, fetch_article_paywall, check_paywall
from ft_scraper.extract.search import update_sections, get_leaf_articles,get_new_articles
from ft_scraper.transform.cleaner import get_article_content,clean_url
from ft_scraper.load.db import insert_article, get_db_connection,get_latest_published_at_by_category
from ft_scraper.presentation.generator import presentation_pipeline

def etl_pipeline(section, category, article_url, scraped_at, collection):
    """
    Each ETL pipeline call opens its own Playwright context,
    so it is thread-safe.
    """
    try:
        with sync_playwright() as p:  # each thread gets its own Playwright
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # --- Extract ---
            paywall_status = check_paywall(page, article_url)
            soup = fetch_article_paywall(page, article_url) if paywall_status else fetch_article_free(page, article_url)

            if not soup:
                print(f"Failed to fetch article: {article_url}")
                browser.close()
                return False

            print(f"Article fetched: {article_url}")

            # --- Transform ---
            article = get_article_content(
                article_id=article_url,
                scraped_at=scraped_at,
                paywall=paywall_status,
                section=section,
                category=category,
                soup=soup
            )

            # --- Load ---
            if article:
                insert_article(collection, article)
                browser.close()
                return True

            browser.close()
            return False

    except Exception as e:
        print(f"Exception for article {article_url}: {e}")
        return False

def run_swarm(collection, json_data, max_workers=5):
    """
    Flatten all sections → categories → articles into tasks
    and run the ETL pipeline in parallel, showing progress.
    """
    tasks = []

    # Flatten nested sections → categories → articles
    with sync_playwright() as p:
        
        for section_name, urls in json_data["sections"].items():
            
            for raw_url in tqdm(urls, desc=f"Processing URLs ({section_name})"):
                url = clean_url(url=raw_url)
                category = urlparse(url).path.strip("/").split("/")[-1]

                articles = get_new_articles(p=p, collection=collection, leaf_url=url)

                if articles:
                    for article_url in articles:
                        tasks.append((section_name, category, article_url))
    
    total_tasks = len(tasks)
    print(f"Total articles to process: {total_tasks}")
    
    # Worker wrapper
    def worker(task):
        section, category, article_url = task
        return etl_pipeline(section, category, article_url, datetime.now(), collection)

    # Run in parallel with progress bar
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(worker, t) for t in tasks]

        # Use tqdm to show progress
        for f in tqdm(as_completed(futures), total=total_tasks, desc="Processing articles"):
            result = f.result()  # will also raise exceptions if any

    print("All ETL tasks completed. Running presentation pipeline...")
    presentation_pipeline()

if __name__ == "__main__":
    
    file_path = "data/metadata/ft_structure.json"

    # Load JSON structure
    with open(file_path, "r") as f:
        json_data = json.load(f)

    last_update = datetime.fromisoformat(json_data["last_update"])
    now = datetime.now()

    # Update sections if older than 7 days
    if now - last_update > timedelta(days=7):
        print("Updating sections...")
        update_sections()
        with open(file_path, "r") as f:
            json_data = json.load(f)
    else:
        print("Sections are up-to-date.")

    # Connect to MongoDB
    collection = get_db_connection()

    # Run the parallel swarm
    run_swarm(collection, json_data, max_workers=8)