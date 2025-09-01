import json
from datetime import datetime, timedelta
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from src.extract.fetch import fetch_article_free, fetch_article_paywall, check_paywall
from src.extract.search import update_sections, get_leaf_articles,get_new_articles
from src.transform.cleaner import get_article_content,get_article_content_archive,clean_url,clean_article_url
from src.load.db import insert_article, get_db_connection,get_latest_published_at_by_category
from src.presentation.generator import presentation_pipeline

def etl_pipeline(section, category, article_url, scraped_at, collection):
    """
    Each ETL pipeline call opens its own Playwright context,
    so it is thread-safe.
    """
    try:
        with sync_playwright() as p:  # each thread gets its own Playwright
            
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
            
            # --- Extract ---
            paywall_status = check_paywall(page, article_url)
            soup,opt = fetch_article_paywall(page, article_url) if paywall_status else fetch_article_free(page, article_url)

            if not soup:
                print(f"Failed to fetch article: {article_url}")
                browser.close()
                return False

            print(f"Article fetched: {article_url}")

            # --- Transform ---
            
            if opt == 1 :
                article = get_article_content(
                    article_id=article_url,
                    scraped_at=scraped_at,
                    paywall=paywall_status,
                    section=section,
                    category=category,
                    soup=soup
                )
            else :
                article = get_article_content_archive(
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

def process_section(section_name, urls, collection):
        local_tasks = []
        
        with sync_playwright() as p:
            for raw_url in tqdm(urls, desc=f"Processing {section_name}", leave=False):
                
                url = clean_url(url=raw_url)
                
                category = urlparse(url).path.strip("/").split("/")[-1]
                
                articles = get_new_articles(p=p, collection=collection, leaf_url=url)
                articles = [clean_article_url(a) for a in articles]
                
                if articles:
                    for article_url in articles:
                        local_tasks.append((section_name, category, article_url))
        
        return local_tasks

def run_swarm(collection, json_data, max_workers=4):
    
    """
    Flatten all sections → categories → articles into tasks
    and run the ETL pipeline in parallel, showing progress.
    """

    tasks = []
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(process_section, section_name, urls, collection): section_name
            for section_name, urls in json_data["sections"].items()
        }

        for future in as_completed(futures):
            tasks.extend(future.result())
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
    run_swarm(collection, json_data, max_workers=4)