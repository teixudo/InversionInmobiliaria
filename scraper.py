"""
scraper.py — Extract property data from Idealista listings.

Strategy:
  1. Try curl_cffi with Chrome impersonation to fetch the listing page.
  2. Parse the HTML with BeautifulSoup to extract structured data.
  3. If blocked (403 / captcha), return None so the UI can fall back to manual input.

Also provides a helper to parse property data from raw HTML that the user
can paste into the app manually.
"""

import re
import json
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False


@dataclass
class PropertyData:
    """Structured data extracted from an Idealista listing."""
    title: str = ""
    price: float = 0.0
    sqm: float = 0.0
    rooms: int = 0
    bathrooms: int = 0
    floor: str = ""
    location: str = ""
    description: str = ""
    has_elevator: Optional[bool] = None
    has_garage: Optional[bool] = None
    energy_rating: str = ""
    url: str = ""


# ─── HTML parsing ─────────────────────────────────────────────────────

def _clean_number(text: str) -> float:
    """Extract a numeric value from text like '145.000 €' or '85 m²'."""
    if not text:
        return 0.0
    cleaned = re.sub(r"[^\d.,]", "", text)
    # Handle Spanish formatting: 145.000 -> 145000, or 1.200,50 -> 1200.50
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_idealista_html(html: str, url: str = "") -> Optional[PropertyData]:
    """
    Parse an Idealista property page HTML and extract key data.
    Returns None if the page doesn't look like a valid listing.
    """
    soup = BeautifulSoup(html, "html.parser")
    data = PropertyData(url=url)

    # ── Title ──
    title_el = soup.select_one("span.main-info__title-main, h1, [data-qa='property-title']")
    if title_el:
        data.title = title_el.get_text(strip=True)

    # ── Price ──
    price_els = soup.select(".info-data-price, .price-container .h3-simulated, .price-features__price, .price, [data-qa='property-price']")
    for el in price_els:
        val = _clean_number(el.get_text())
        if val > 1000:
            data.price = val
            break

    # ── Try JSON-LD structured data ──
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            ld = json.loads(script.string or "")
            if isinstance(ld, dict):
                if ld.get("@type") in ("Product", "Residence", "Apartment", "House"):
                    offers = ld.get("offers", {})
                    if isinstance(offers, dict) and offers.get("price"):
                        data.price = float(offers["price"])
                    if ld.get("name"):
                        data.title = data.title or ld["name"]
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
            
    # Fallback regex for price
    if data.price <= 0:
        match = re.search(r'([\d.,]+)\s*€', html)
        if match:
            val = _clean_number(match.group(1))
            if val > 1000:
                data.price = val

    # ── Details (m², rooms, floor, etc.) ──
    details = soup.select(".details-property_features li, .info-features span, [data-qa='property-features'] li, .feature-container span")
    for el in details:
        text = el.get_text(strip=True).lower()
        if ("m²" in text or "m2" in text or "metros" in text) and "parcela" not in text:
            data.sqm = _clean_number(text)
        elif "habitaci" in text or "dormitorio" in text or "hab" in text:
            data.rooms = int(_clean_number(text)) or data.rooms
        elif "baño" in text:
            data.bathrooms = int(_clean_number(text)) or data.bathrooms
        elif "planta" in text or "piso" in text:
            data.floor = text
        elif "ascensor" in text:
            data.has_elevator = "sin" not in text and "no" not in text
        elif "garaje" in text or "parking" in text:
            data.has_garage = "sin" not in text and "no" not in text
            
    # Fallback regex for sqm
    if data.sqm <= 0:
        match = re.search(r'([\d.,]+)\s*(m²|m2)', html, re.IGNORECASE)
        if match:
            data.sqm = _clean_number(match.group(1))

    # ── Location ──
    location_el = soup.select_one("#headerMap .main-info__title-minor")
    if not location_el:
        location_el = soup.select_one(".header-map-info .main-info__title-minor")
    if location_el:
        data.location = location_el.get_text(strip=True)

    # ── Description ──
    desc_el = soup.select_one(".comment .adCommentsBody, .adCommentsBody")
    if desc_el:
        data.description = desc_el.get_text(strip=True)[:500]

    # ── Energy rating ──
    energy_el = soup.select_one(".energy-certificate .energy-certificate__letter")
    if energy_el:
        data.energy_rating = energy_el.get_text(strip=True)

    # Validate we got something useful
    if data.price <= 0 and data.sqm <= 0:
        return None

    return data


# ─── Network fetch ────────────────────────────────────────────────────

def fetch_idealista_listing(url: str) -> Optional[PropertyData]:
    """
    Attempt to fetch and parse an Idealista listing URL.
    Returns PropertyData on success, None if blocked or parsing fails.
    """
    if not HAS_CURL_CFFI:
        return None

    if "idealista.com" not in url:
        return None

    try:
        response = cffi_requests.get(
            url,
            impersonate="chrome",
            timeout=15,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
            },
        )
        if response.status_code != 200:
            return None

        return parse_idealista_html(response.text, url=url)

    except Exception:
        return None


def estimate_rent_from_url(url: str) -> Optional[float]:
    """
    Placeholder: In a full implementation this would search Idealista's
    rental listings for the same zone and property type to estimate
    market rent. For now, returns None — the user provides the rent manually.
    """
    return None
