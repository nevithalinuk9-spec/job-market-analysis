"""
BeautifulSoup demonstration: scraping one Stepstone results page.

THIS IS A DEMONSTRATION MODULE ONLY.
- The notebook does not depend on this succeeding.
- Always check robots.txt before scraping any site.
- The primary data source for this project is the Adzuna API (fetch_adzuna.py).
- Do not run this at high frequency or in production; scraping ToS may apply.
"""

from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

STEPSTONE_BASE = "https://www.stepstone.de"
SEARCH_URL = f"{STEPSTONE_BASE}/jobs/data-analyst/in-deutschland.html"
USER_AGENT = "Mozilla/5.0 (educational-portfolio-project; contact: your@email.com)"


def is_scraping_allowed(base_url: str, target_path: str, user_agent: str = "*") -> bool:
    """Check robots.txt before scraping — this is non-negotiable good practice.

    Args:
        base_url: Root URL of the site (e.g. 'https://www.stepstone.de').
        target_path: Path we intend to scrape (e.g. '/jobs/...').
        user_agent: Our bot's user-agent string to check against rules.

    Returns:
        True if robots.txt permits fetching target_path, False otherwise.
    """
    robots_url = urljoin(base_url, "/robots.txt")
    rp = RobotFileParser(robots_url)
    try:
        rp.read()
        allowed = rp.can_fetch(user_agent, urljoin(base_url, target_path))
    except Exception as exc:
        # If robots.txt is unreachable, err on the side of caution
        print(f"Could not read robots.txt: {exc}. Assuming disallowed.")
        allowed = False
    return allowed


def parse_listing_card(card: BeautifulSoup) -> dict:
    """Extract fields from one job-card element on a Stepstone results page.

    Args:
        card: A BeautifulSoup Tag representing one job card.

    Returns:
        Dict with title, company, location, and url keys (empty string if missing).
    """
    # Stepstone's HTML structure changes frequently; treat selectors as fragile
    title_tag = card.find("a", {"data-at": "job-item-title"}) or card.find("h2")
    company_tag = card.find("span", {"data-at": "job-item-company-name"})
    location_tag = card.find("span", {"data-at": "job-item-location"})
    href = title_tag.get("href", "") if title_tag else ""

    return {
        "title": title_tag.get_text(strip=True) if title_tag else "",
        "company": company_tag.get_text(strip=True) if company_tag else "",
        "location": location_tag.get_text(strip=True) if location_tag else "",
        "url": urljoin(STEPSTONE_BASE, href) if href else "",
    }


def scrape_single_page(url: str = SEARCH_URL) -> list[dict]:
    """Fetch and parse ONE Stepstone results page (demonstration only).

    Respects robots.txt. Returns an empty list rather than raising on failure,
    so the notebook can continue even if the scrape fails.

    Args:
        url: URL of the results page to scrape.

    Returns:
        List of parsed listing dicts (may be empty).
    """
    path = url.replace(STEPSTONE_BASE, "") or "/"
    if not is_scraping_allowed(STEPSTONE_BASE, path, user_agent=USER_AGENT):
        print("robots.txt disallows scraping this path. Skipping.")
        return []

    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Stepstone request failed: {exc}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    # Job cards: Stepstone wraps each listing in an <article> element
    cards = soup.find_all("article")
    if not cards:
        # Fallback: look for any element with a job-item role attribute
        cards = soup.find_all(attrs={"data-at": "job-item"})

    listings = [parse_listing_card(card) for card in cards]
    listings = [lst for lst in listings if lst["title"]]  # drop empty cards

    print(f"Stepstone demo scrape: found {len(listings)} listings on one page.")
    return listings
