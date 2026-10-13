"""Same-site HTML scraper with optional JavaScript rendering."""

import time
from collections import deque
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from browser_fetcher import BrowserFetcher
from common import BlockedError, check_block_status, create_session, looks_blocked, save_results

# Set these values for the site you are allowed to scrape.
START_URL = "url"
MAX_PAGES = 20
DELAY_SECONDS = 1.5
FETCH_MODE = "auto"  # "requests", "browser", or "auto"
WAIT_SELECTOR = None  # e.g. "article.product_pod" for JavaScript-loaded content


def robots_allow(session, url, cache):
    parts = urlparse(url)
    origin = f"{parts.scheme}://{parts.netloc}"

    if origin not in cache:
        try:
            response = session.get(f"{origin}/robots.txt", timeout=10)
            if response.status_code == 404:
                cache[origin] = None
            elif response.ok:
                rules = RobotFileParser()
                rules.set_url(f"{origin}/robots.txt")
                rules.parse(response.text.splitlines())
                cache[origin] = rules
            else:
                cache[origin] = False
        except requests.RequestException:
            cache[origin] = False
        finally:
            time.sleep(DELAY_SECONDS)

    rules = cache[origin]
    return rules is None or (rules is not False and rules.can_fetch("*", url))


def fetch_with_requests(session, url):
    response = session.get(url, timeout=20)
    check_block_status(response.status_code, url)
    response.raise_for_status()
    if "html" not in response.headers.get("content-type", "").lower():
        return None
    if looks_blocked(response.text):
        raise BlockedError(f"A challenge page was returned: {url}")
    return response.text


def looks_empty(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(("script", "style", "noscript")):
        tag.decompose()
    text = soup.get_text(" ", strip=True).lower()
    return len(text) < 150 or "enable javascript" in text


def fetch_page(session, url, browser=None):
    if FETCH_MODE == "browser":
        browser = browser or BrowserFetcher()
        return browser.get(url, WAIT_SELECTOR), browser

    html = fetch_with_requests(session, url)
    if FETCH_MODE == "requests" or html is None or not looks_empty(html):
        return html, browser

    print(f"Little HTML content; trying JavaScript renderer: {url}")
    browser = browser or BrowserFetcher()
    return browser.get(url, WAIT_SELECTOR), browser


def extract_data(html, url):
    soup = BeautifulSoup(html, "html.parser")
    description = soup.find("meta", attrs={"name": "description"})
    for tag in soup(("script", "style", "noscript")):
        tag.decompose()

    content = soup.find("main") or soup.body or soup
    headings = " | ".join(
        heading.get_text(" ", strip=True)
        for heading in soup.select("h1, h2, h3")
        if heading.get_text(strip=True)
    )
    return {
        "url": url,
        "title": soup.title.get_text(strip=True) if soup.title else "",
        "h1": soup.h1.get_text(strip=True) if soup.h1 else "",
        "headings": headings,
        "description": description.get("content", "") if description else "",
        "content": content.get_text(" ", strip=True)[:5000],
    }


def crawl():
    if FETCH_MODE not in {"requests", "browser", "auto"}:
        raise ValueError("FETCH_MODE must be 'requests', 'browser', or 'auto'.")

    start = urldefrag(START_URL)[0]
    host = urlparse(start).netloc
    queue, seen, results = deque([start]), {start}, []
    session, robots, browser = create_session(), {}, None

    try:
        while queue and len(results) < MAX_PAGES:
            url = queue.popleft()
            if not robots_allow(session, url, robots):
                print(f"Skipped by robots.txt: {url}")
                continue

            try:
                html, browser = fetch_page(session, url, browser)
            except BlockedError as error:
                print(f"Stopping: {error}")
                break
            except Exception as error:
                print(f"Could not fetch {url}: {error}")
                continue
            finally:
                time.sleep(DELAY_SECONDS)

            if not html:
                continue

            results.append(extract_data(html, url))
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.select("a[href]"):
                next_url = urldefrag(urljoin(url, link["href"]))[0]
                if urlparse(next_url).netloc == host and next_url not in seen:
                    seen.add(next_url)
                    queue.append(next_url)
    finally:
        if browser:
            browser.close()
        session.close()

    return results


if __name__ == "__main__":
    save_results(crawl(), "html_results")
