"""Shared HTTP and output helpers for both scrapers."""

import csv
import json
from datetime import datetime
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DATA_DIR = Path(__file__).resolve().parent / "data"
USER_AGENT = "SimpleCrawler/1.0 (contact: you@example.com)"
BLOCKED_STATUSES = {401, 403, 429, 503}


class BlockedError(RuntimeError):
    """Raised when a site refuses a request or presents an access challenge."""


def create_session():
    retry = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods={"GET"},
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def check_block_status(status, url):
    if status in BLOCKED_STATUSES:
        raise BlockedError(f"Site refused access or is unavailable (HTTP {status}): {url}")


def looks_blocked(html):
    text = (html or "").lower()
    markers = ("captcha", "verify you are human", "access denied", "checking your browser")
    return len(text) < 50000 and any(marker in text for marker in markers)


def save_results(rows, name):
    if not rows:
        print("No data collected.")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    json_path = DATA_DIR / f"{name}_{stamp}.json"
    csv_path = DATA_DIR / f"{name}_{stamp}.csv"
    records = rows if isinstance(rows, list) else [rows]

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(rows, file, ensure_ascii=False, indent=2)

    if all(isinstance(row, dict) for row in records):
        fields = list(dict.fromkeys(key for row in records for key in row))
        with csv_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)
        print(f"Saved results:\n{json_path}\n{csv_path}")
    else:
        print(f"Saved results: {json_path}")
