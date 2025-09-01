from lxml import html
import re

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

def get_article_content_archive(article_id, scraped_at, paywall, section, category, soup):
    """
    Extract structured article content from 'archive' site using XPath.
    """

    # Convert BeautifulSoup to lxml tree for XPath queries
    parser = html.HTMLParser(encoding="utf-8")
    tree = html.fromstring(str(soup), parser=parser)

    def text_or_none(xpath_expr, attr=None):
        try:
            el = tree.xpath(xpath_expr)
            if not el:
                return None
            el = el[0]
            if attr:
                return el.get(attr)
            return el.text_content().strip()
        except Exception:
            return None

    # --- Metadata fields ---
    topper_primary_theme = text_or_none("//div[@id='o-topper']//span/a")
    topper_headline = text_or_none("//div[@id='o-topper']//h1/span[1]")
    standfirst = text_or_none("//div[@id='o-topper']//div[2]")
    byline_text = text_or_none("//article[@id='site-content']//div[3]/div[1]/div[1]")
    pub_datetime = text_or_none("//article[@id='site-content']//div[3]/div[1]/div[2]/div[1]/div[1]/time", attr="datetime")
    updated_datetime = text_or_none("//article[@id='site-content']//div[3]/div[1]/div[2]/div[1]/div[2]/time", attr="datetime")

    # --- Content ---
    article_nodes = tree.xpath('//*[@id="article-body"]')
    paragraphs = []
    figures_list = []

    if article_nodes:
        article = article_nodes[0]

        # Paragraphs: all <div> children inside article-body
        paragraphs = [
            p.text_content().strip()
            for p in article.xpath(".//div")
            if p.text_content().strip()
        ]

        # Figures: list of dicts with img_src, caption, credit
        figures = article.xpath(".//figure")
        for fig in figures:
            # Image src
            img = fig.xpath(".//img[@currentsourceurl]")
            img_src = img[0].get("currentsourceurl") if img else None

            # Caption text
            figcaption = fig.xpath(".//figcaption")
            caption = figcaption[0].text_content().strip() if figcaption else None

            # Credit (optional)
            credit_span = fig.xpath(".//span[contains(text(),'©') or contains(@class,'credit')]")
            credit = credit_span[0].text_content().strip() if credit_span else None

            if img_src:
                figures_list.append({
                    "img_src": img_src,
                    "caption": caption,
                    "credit": credit
                })

    # --- Final structured data ---
    data = {
        "article_id": article_id,
        "scraped_at": scraped_at,
        "paywall": paywall,
        "section": section,
        "category": category,

        "topper__primary_theme": topper_primary_theme,
        "topper__headline": topper_headline,
        "standfirst": standfirst,
        "byline": byline_text,
        "published_at": pub_datetime,
        "updated_at": updated_datetime,

        "content": paragraphs,
        "media": {
            "images": figures_list,
            "videos": []  # adjust later if video tags exist
        }
    }

    return data

def clean_url(url: str) -> str:
    # If multiple protocols exist, keep the last valid one
    if url.count("https://") > 1 or url.count("http://") > 1:
        parts = url.split("http")
        url = "http" + parts[-1]  # take last segment
    
    return url.strip()

def clean_article_url(url: str) -> str:
    """
    Clean FT article URL by removing trailing colons or invalid characters 
    in the last path segment.
    """
    # Remove trailing colon from URL if present
    url = url.rstrip(':')

    # Ensure the last segment (after the last "/") only keeps valid UUID-like pattern
    url_parts = url.split('/')
    if url_parts[-1]:
        url_parts[-1] = re.sub(r'[^a-zA-Z0-9-]', '', url_parts[-1])
    return '/'.join(url_parts)