"""
Yelp Fusion API lead scraper.
Set YELP_API_KEY in your .env file.
Free tier: 500 calls/day.
"""

import os
import requests

API_KEY = os.getenv("YELP_API_KEY")
BASE_URL = "https://api.yelp.com/v3/businesses/search"


def search_yelp(term: str, location: str, limit: int = 50) -> list[dict]:
    """Search Yelp for businesses. Max 50 per call, up to 1000 offset."""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    results = []
    offset = 0

    while len(results) < limit:
        params = {
            "term": term,
            "location": location,
            "limit": min(50, limit - len(results)),
            "offset": offset,
        }
        resp = requests.get(BASE_URL, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            print(f"[yelp] Error {resp.status_code}: {resp.text[:200]}")
            break

        businesses = resp.json().get("businesses", [])
        if not businesses:
            break

        for biz in businesses:
            results.append(_extract(biz, term))

        offset += len(businesses)
        if offset >= resp.json().get("total", 0):
            break

    return results


def _extract(biz: dict, term: str) -> dict:
    location = biz.get("location", {})
    address_parts = [
        location.get("address1", ""),
        location.get("city", ""),
        location.get("state", ""),
    ]
    return {
        "business_name": biz.get("name"),
        "business_type": term,
        "phone": biz.get("display_phone", ""),
        "website": biz.get("url", ""),
        "address": ", ".join(p for p in address_parts if p),
        "city": location.get("city", ""),
        "rating": biz.get("rating"),
        "review_count": biz.get("review_count"),
        "email": "",
        "source": "yelp",
        "yelp_id": biz.get("id"),
    }


if __name__ == "__main__":
    import json

    city = input("City: ").strip()
    term = input("Business type (e.g. dentist, gym): ").strip()
    limit = int(input("How many leads? [50]: ").strip() or 50)

    print(f"\nSearching Yelp for {term} in {city}...")
    leads = search_yelp(term, city, limit=limit)
    print(f"Found {len(leads)} businesses.")

    out = f"yelp_{term.replace(' ','_')}_{city}.json"
    with open(out, "w") as f:
        json.dump(leads, f, indent=2)
    print(f"Saved to {out}")
