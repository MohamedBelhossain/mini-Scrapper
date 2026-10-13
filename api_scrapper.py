"""Fetch JSON from a documented API and save a separate result set."""

import os

import requests

from common import BlockedError, check_block_status, create_session, save_results

# Set this to an API endpoint that returns JSON, not the website's HTML page.
API_URL = "api url"
API_KEY = os.getenv("API_KEY")


def fetch_api():
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    with create_session() as session:
        response = session.get(API_URL, headers=headers, timeout=20)
        check_block_status(response.status_code, API_URL)
        response.raise_for_status()

        try:
            return response.json()
        except requests.exceptions.JSONDecodeError as error:
            content_type = response.headers.get("content-type", "unknown")
            raise ValueError(
                f"API returned non-JSON data (Content-Type: {content_type}). "
                "Set API_URL to a JSON endpoint."
            ) from error


if __name__ == "__main__":
    try:
        save_results(fetch_api(), "api_results")
    except BlockedError as error:
        print(f"Stopped: {error}")
    except (requests.RequestException, ValueError) as error:
        print(f"API error: {error}")
