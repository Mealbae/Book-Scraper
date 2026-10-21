"""Streamlit front end for the book scraper. Run with: streamlit run app.py"""
import io

import streamlit as st

from scraper import scrape

st.set_page_config(page_title="Book Scraper", page_icon="📚", layout="wide")
st.title("📚 Book Catalogue Scraper")
st.caption("Scrapes books.toscrape.com (a public practice site) and exports clean data.")

with st.sidebar:
    st.header("Settings")
    max_pages = st.slider("Pages to scrape (20 books per page)", 1, 50, 5)
    delay = st.slider("Delay between requests (seconds)", 0.5, 3.0, 1.0, 0.5)
    run = st.button("Run scraper", type="primary", use_container_width=True)

if run:
    bar = st.progress(0, text="Starting...")
    try:
        df, report = scrape(
            max_pages=max_pages,
            delay=delay,
            progress_callback=lambda p, t: bar.progress(p / t, text=f"Scraping page {p} of {t}"),
        )
        st.session_state["df"], st.session_state["report"] = df, report
        bar.empty()
    except Exception as exc:
        bar.empty()
        st.error(f"Scraping failed: {exc}")

if "df" in st.session_state:
    df, report = st.session_state["df"], st.session_state["report"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pages scraped", report["pages_scraped"])
    c2.metric("Rows scraped", report["rows_scraped"])
    c3.metric("Duplicates removed", report["duplicates_removed"])
    c4.metric("Final clean rows", report["rows_final"])

    st.subheader("Filter results")
    f1, f2, f3 = st.columns(3)
    price_range = f1.slider(
        "Price (£)", float(df["price_gbp"].min()), float(df["price_gbp"].max()),
        (float(df["price_gbp"].min()), float(df["price_gbp"].max())),
    )
    min_rating = f2.slider("Minimum rating", 1, 5, 1)
    in_stock_only = f3.checkbox("In stock only", value=False)

    view = df[df["price_gbp"].between(*price_range) & (df["rating"] >= min_rating)]
    if in_stock_only:
        view = view[view["in_stock"]]

    st.dataframe(view, use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(view)} of {len(df)} rows")

    d1, d2, d3 = st.columns(3)
    d1.download_button("Download CSV", view.to_csv(index=False), "books.csv", "text/csv")
    d2.download_button("Download JSON", view.to_json(orient="records", indent=2), "books.json", "application/json")
    buf = io.BytesIO()
    view.to_excel(buf, index=False)
    d3.download_button(
        "Download Excel", buf.getvalue(), "books.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.info("Choose your settings in the sidebar and click **Run scraper**.")
