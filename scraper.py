"""Web scraper for books.toscrape.com (a public sandbox site built for scraping practice).

Features: pagination, retries with exponential backoff, polite rate limiting,
robots.txt check, data cleaning, validation and deduplication.
"""
import logging
import re
import time
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
START_URL = urljoin(BASE_URL, "catalogue/page-1.html")
USER_AGENT = "Mozilla/5.0 (compatible; PortfolioScraper/1.0; educational use)"
RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("scraper")


def allowed_by_robots(url: str) -> bool:
    """Return True if robots.txt allows our user agent to fetch the URL."""
    parser = RobotFileParser()
    parser.set_url(urljoin(BASE_URL, "robots.txt"))
    try:
        parser.read()
    except Exception as exc:  # robots.txt unreachable: be conservative but don't crash
        log.warning("Could not read robots.txt (%s); proceeding carefully.", exc)
        return True
    return parser.can_fetch(USER_AGENT, url)


def fetch(session: requests.Session, url: str, retries: int = 3, backoff: float = 2.0) -> str:
    """GET a page, retrying on network errors, 429 and 5xx with exponential backoff."""
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise requests.HTTPError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return resp.text
        except requests.RequestException as exc:
            if attempt == retries:
                raise
            wait = backoff ** attempt
            log.warning("Attempt %d failed for %s (%s). Retrying in %.1fs", attempt, url, exc, wait)
            time.sleep(wait)


def parse_page(html: str, page_url: str):
    """Extract book records from one listing page. Returns (records, next_page_url)."""
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for card in soup.select("article.product_pod"):
        link = card.select_one("h3 a")
        price = card.select_one("p.price_color")
        rating = card.select_one("p.star-rating")
        stock = card.select_one("p.instock.availability")
        rating_word = next((c for c in rating.get("class", []) if c in RATINGS), None) if rating else None
        records.append({
            "title": link.get("title") if link else None,
            "url": urljoin(page_url, link["href"]) if link and link.get("href") else None,
            "price_raw": price.get_text(strip=True) if price else None,
            "rating_raw": rating_word,
            "availability_raw": stock.get_text(strip=True) if stock else None,
        })
    next_link = soup.select_one("li.next a")
    next_url = urljoin(page_url, next_link["href"]) if next_link else None
    return records, next_url


def clean(df: pd.DataFrame):
    """Clean, validate and deduplicate. Returns (clean_df, report_dict)."""
    report = {"rows_scraped": len(df)}
    df = df.copy()
    for col in ("title", "url", "price_raw", "availability_raw"):
        df[col] = df[col].astype("string").str.strip()

    df["price_gbp"] = pd.to_numeric(
        df["price_raw"].str.extract(r"(\d+(?:\.\d+)?)", expand=False), errors="coerce"
    )
    df["rating"] = df["rating_raw"].map(RATINGS)
    df["in_stock"] = df["availability_raw"].str.contains("in stock", case=False, na=False)

    before = len(df)
    df = df.dropna(subset=["title", "url", "price_gbp"])
    report["dropped_missing_fields"] = before - len(df)

    before = len(df)
    df = df.drop_duplicates(subset=["url"]).reset_index(drop=True)
    report["duplicates_removed"] = before - len(df)

    invalid = ~df["price_gbp"].between(0, 1000) | df["rating"].isna()
    report["flagged_invalid"] = int(invalid.sum())
    df = df[~invalid].reset_index(drop=True)

    df = df[["title", "price_gbp", "rating", "in_stock", "url"]]
    report["rows_final"] = len(df)
    return df, report


def scrape(max_pages: int = 5, delay: float = 1.0, progress_callback=None):
    """Scrape up to max_pages listing pages, following the 'next' link."""
    if not allowed_by_robots(START_URL):
        raise PermissionError("robots.txt disallows scraping this site.")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    rows, url, page = [], START_URL, 0
    while url and page < max_pages:
        html = fetch(session, url)
        records, url = parse_page(html, url)
        rows.extend(records)
        page += 1
        log.info("Page %d done: %d records so far", page, len(rows))
        if progress_callback:
            progress_callback(page, max_pages)
        if url:
            time.sleep(delay)  # polite rate limiting

    df, report = clean(pd.DataFrame(rows))
    report["pages_scraped"] = page
    return df, report


if __name__ == "__main__":
    data, rep = scrape(max_pages=3, delay=1.0)
    data.to_csv("books.csv", index=False)
    print(rep)
    print(data.head())
