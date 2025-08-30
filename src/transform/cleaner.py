from bs4 import BeautifulSoup
from ft_scraper.extract.fetch import fetch_article_free, fetch_article_paywall, check_paywall
from ft_scraper.load.db import get_db_connection, insert_article
from playwright.sync_api import sync_playwright
import json

def extract_text_or_none(tag, selector=None, attr=None):
    """
    Utility: extract text or attribute from a tag safely.
    """
    if not tag:
        return None
    if attr and tag.has_attr(attr):
        return tag[attr]
    return tag.get_text(" ", strip=True) if tag else None


def extract_figures(soup):
    """
    Extract all figures (images + captions + credits) from the article.
    """
    figures = []
    for fig in soup.find_all("figure"):
        img_src = fig.find("img")["src"] if fig.find("img") else None
        caption_text = fig.find("figcaption").get_text(strip=True) if fig.find("figcaption") else None

        caption, credit = None, None
        if caption_text:
            if "©" in caption_text:
                parts = caption_text.split("©", 1)
                caption = parts[0].strip()
                credit = parts[1].strip()
            else:
                caption = caption_text.strip()

        figures.append({
            "img_src": img_src,
            "caption": caption,
            "credit": credit
        })
    return figures


def extract_paragraphs(article_tag):
    """
    Extract all <p> tags text inside the <article>.
    """
    if not article_tag:
        return []
    paragraphs = []
    for p in article_tag.find_all("p"):
        text = p.get_text(" ", strip=True)
        if text:
            paragraphs.append(text)
    return paragraphs


def get_article_content(article_id, scraped_at, paywall, section,category, soup):
    """
    Extract structured article content from parsed BeautifulSoup object.
    """

    # --- Metadata fields ---
    topper_primary_theme = extract_text_or_none(
        soup.find("div", class_="topper__primary-theme").find("span") if soup.find("div", class_="topper__primary-theme") else None
    )
    topper_headline = extract_text_or_none(soup.find("h1", class_="o-topper__headline"))
    standfirst = extract_text_or_none(soup.find("div", class_="o-topper__standfirst"))
    byline_text = extract_text_or_none(soup.find("p", class_="article-info__byline"))

    # Publication & updated dates
    pub_datetime = extract_text_or_none(soup.find("time", class_="article-info__timestamp"), attr="datetime")
    updated_tag = soup.find("p", class_="article-info__updated-timestamp")
    updated_datetime = None
    if updated_tag:
        updated_datetime = extract_text_or_none(updated_tag.find("time"), attr="datetime")

    # --- Content ---
    article_tag = soup.find("article", id="article-body")
    paragraphs = extract_paragraphs(article_tag)
    figures = extract_figures(soup)

    # --- Final structured data ---
    data = {
        "article_id": article_id,
        "scraped_at": scraped_at,
        "paywall": paywall,
        "section": section,
        "category":category,
        "topper__primary_theme": topper_primary_theme,
        "topper__headline": topper_headline,
        "standfirst": standfirst,
        "byline": byline_text,
        "published_at": pub_datetime,
        "updated_at": updated_datetime,
        "content": paragraphs,
        "media": {
            "images": figures,
            "videos": None  
        }
    }

    return data

def clean_url(url: str) -> str:
    # If multiple protocols exist, keep the last valid one
    if url.count("https://") > 1 or url.count("http://") > 1:
        parts = url.split("http")
        url = "http" + parts[-1]  # take last segment
    
    return url.strip()