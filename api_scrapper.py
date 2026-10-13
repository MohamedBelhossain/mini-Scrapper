"""Récupère des données depuis une API JSON autorisée."""

import os

import requests

from scrapper import create_session, save_results

API_URL = "api url"
API_KEY = os.getenv("API_KEY")  # facultative : stocke la clé dans cette variable système


def fetch_api():
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    response = create_session().get(API_URL, headers=headers, timeout=15)

    if response.status_code in (401, 403, 429):
        raise RuntimeError(f"Accès refusé ou limite API atteinte ({response.status_code}).")
    response.raise_for_status()
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as error:
        content_type = response.headers.get("content-type", "inconnu")
        raise ValueError(
            f"{API_URL} n'a pas renvoyé du JSON (Content-Type : {content_type}). "
            "Utilise une URL d'API JSON ; pour books.toscrape.com, lance scrapper.py."
        ) from error


if __name__ == "__main__":
    save_results(fetch_api(), "api_results")
