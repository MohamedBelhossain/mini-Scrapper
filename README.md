# Simple web scraper

## Install

```bash
pip install -r requirements.txt
```

For JavaScript-rendered pages, install the optional browser support:

```bash
pip install playwright
playwright install chromium
```

## HTML scraping

Set `START_URL` in `scrapper.py`. Choose `FETCH_MODE`:

- `requests`: download the page HTML directly.
- `browser`: render pages with Chromium.
- `auto`: use requests first and render pages that look empty.

For dynamic pages, set `WAIT_SELECTOR` to a CSS selector that appears when the data is loaded, such as `article.product_pod`.

Run:

```bash
python scrapper.py
```

## API scraping

Set `API_URL` in `api_scrapper.py` to an endpoint that returns JSON. A normal website URL that returns HTML is not an API endpoint. If authentication is needed, set the `API_KEY` environment variable.

Run:

```bash
python api_scrapper.py
```

Each run writes a new timestamped JSON and CSV file under `data/`. HTML and API outputs use separate filename prefixes.

The scraper follows `robots.txt`, waits between page requests, and stops on access denials, rate limits, or challenge pages. It does not attempt to bypass those protections.
