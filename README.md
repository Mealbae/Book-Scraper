# Book Catalogue Scraper & Streamlit App

A Python web scraper with a Streamlit interface. It collects book titles, prices, ratings and
stock status from [books.toscrape.com](https://books.toscrape.com), a public sandbox site built
for scraping practice, then cleans, validates and deduplicates the data and exports it.

## Features
- Pagination: follows the "next" link across up to 50 pages (1,000 books)
- Retries with exponential backoff on network errors, HTTP 429 and 5xx
- Polite rate limiting (configurable delay) and a custom User-Agent
- robots.txt check before scraping
- Cleaning with Pandas: price parsing, rating conversion, stock flag
- Validation (missing fields, out-of-range values) and URL-based deduplication
- Streamlit app with progress bar, filters, and CSV / JSON / Excel downloads

## Tech stack
Python, requests, BeautifulSoup, Pandas, Streamlit, openpyxl

## Run it
```bash
pip install -r requirements.txt
streamlit run app.py          # web interface
python scraper.py             # command line: saves books.csv
```

## Project structure
- `scraper.py`: fetching, parsing, cleaning, validation
- `app.py`: Streamlit interface
- `requirements.txt`: dependencies

## Ethics and compliance
Only scrapes a site that explicitly exists for scraping practice. Checks robots.txt,
rate-limits requests, and identifies itself with a User-Agent. When adapting it to other
sites, review their robots.txt and terms of service first.
