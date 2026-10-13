"""Crawler HTML simple. Modifie START_URL et MAX_PAGES avant de le lancer."""

import csv
import json
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

START_URL = "url"
MAX_PAGES = 20
DELAY_SECONDS = 1.5
USER_AGENT = "SimpleCrawler/1.0 (contact: you@example.com)"
DATA_DIR = Path(__file__).resolve().parent / "data"


def create_session():
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def save_results(rows, name="results"):
    if not rows:
        print("Aucune donnée collectée.")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    json_path = DATA_DIR / f"{name}_{stamp}.json"
    csv_path = DATA_DIR / f"{name}_{stamp}.csv"

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(rows, file, ensure_ascii=False, indent=2)

    records = rows if isinstance(rows, list) else [rows]
    if all(isinstance(row, dict) for row in records):
        with csv_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)
        print(f"Résultats enregistrés dans :\n{json_path}\n{csv_path}")
    else:
        print(f"Résultats enregistrés dans : {json_path}")


def robots_allow(session, url, cache):
    parts = urlparse(url)
    origin = f"{parts.scheme}://{parts.netloc}"

    if origin not in cache:
        try:
            response = session.get(f"{origin}/robots.txt", timeout=10)
            if response.status_code == 404:
                cache[origin] = None
            elif response.ok:
                parser = RobotFileParser()
                parser.set_url(f"{origin}/robots.txt")
                parser.parse(response.text.splitlines())
                cache[origin] = parser
            else:
                cache[origin] = False
            time.sleep(DELAY_SECONDS)
        except requests.RequestException:
            cache[origin] = False

    rules = cache[origin]
    return rules is None or (rules is not False and rules.can_fetch(USER_AGENT, url))


def crawl():
    start = urldefrag(START_URL)[0]
    host = urlparse(start).netloc
    queue, seen, rows = deque([start]), {start}, []
    session, robots = create_session(), {}

    while queue and len(rows) < MAX_PAGES:
        url = queue.popleft()
        if not robots_allow(session, url, robots):
            print(f"Ignoré par robots.txt : {url}")
            continue

        try:
            response = session.get(url, timeout=15)
            if response.status_code in (401, 403, 429):
                print(f"Accès refusé ou limite atteinte ({response.status_code}) : arrêt.")
                break
            response.raise_for_status()
        except requests.RequestException as error:
            print(f"Erreur pour {url} : {error}")
            continue
        finally:
            time.sleep(DELAY_SECONDS)

        if "html" not in response.headers.get("content-type", "").lower():
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        description = soup.find("meta", attrs={"name": "description"})
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        content = soup.find("main") or soup.body or soup
        headings = " | ".join(
            heading.get_text(" ", strip=True)
            for heading in soup.select("h1, h2, h3")
            if heading.get_text(strip=True)
        )
        rows.append({
            "url": url,
            "title": soup.title.get_text(strip=True) if soup.title else "",
            "h1": soup.h1.get_text(strip=True) if soup.h1 else "",
            "headings": headings,
            "description": description.get("content", "") if description else "",
            "content": content.get_text(" ", strip=True)[:5000],
        })

        for link in soup.select("a[href]"):
            next_url = urldefrag(urljoin(url, link["href"]))[0]
            if urlparse(next_url).netloc == host and next_url not in seen:
                seen.add(next_url)
                queue.append(next_url)

    return rows


if __name__ == "__main__":
    save_results(crawl(), "html_results")
