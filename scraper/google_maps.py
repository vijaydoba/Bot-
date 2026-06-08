"""
Google Maps lead scraper using the Places API.
Set GOOGLE_MAPS_API_KEY in your .env file.
Free tier: 200 USD/month credit (~2,800 searches).
"""

import os
import time
import requests

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
BASE_URL = "https://maps.googleapis.com/maps/api/place"


def search_businesses(query: str, city: str, max_results: int = 20) -> list[dict]:
    """Search for businesses using Google Places Text Search."""
    results = []
    url = f"{BASE_URL}/textsearch/json"
    params = {"query": f"{query} in {city}", "key": API_KEY}

    while len(results) < max_results:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            print(f"[scraper] API error: {data.get('status')} — {data.get('error_message','')}")
            break

        for place in data.get("results", []):
            results.append(_extract_basic(place, city, query))
            if len(results) >= max_results:
                break

        next_page = data.get("next_page_token")
        if not next_page or len(results) >= max_results:
            break
        time.sleep(2)
        params = {"pagetoken": next_page, "key": API_KEY}

    return results


def get_place_details(place_id: str) -> dict:
    """Fetch phone, website, and hours for a single place."""
    url = f"{BASE_URL}/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,formatted_phone_number,website,formatted_address,opening_hours",
        "key": API_KEY,
    }
    resp = requests.get(url, params=params, timeout=10)
    return resp.json().get("result", {})


def enrich_leads(leads: list[dict]) -> list[dict]:
    """Add phone and website to each lead via Places Details API."""
    for lead in leads:
        if not lead.get("place_id"):
            continue
        details = get_place_details(lead["place_id"])
        lead["phone"] = details.get("formatted_phone_number", "")
        lead["website"] = details.get("website", "")
        time.sleep(0.3)
    return leads


def _extract_basic(place: dict, city: str, query: str) -> dict:
    return {
        "place_id": place.get("place_id"),
        "business_name": place.get("name"),
        "address": place.get("formatted_address"),
        "city": city,
        "business_type": query,
        "rating": place.get("rating"),
        "source": "google_maps",
        "phone": "",
        "website": "",
        "email": "",
    }


if __name__ == "__main__":
    import json

    city = input("City: ").strip()
    btype = input("Business type (e.g. dentist, gym): ").strip()
    count = int(input("How many leads? [20]: ").strip() or 20)

    print(f"\nSearching for {btype} in {city}...")
    leads = search_businesses(btype, city, max_results=count)
    print(f"Found {len(leads)} businesses. Enriching with details...")
    leads = enrich_leads(leads)

    out = f"leads_{btype.replace(' ','_')}_{city}.json"
    with open(out, "w") as f:
        json.dump(leads, f, indent=2)
    print(f"Saved to {out}")
