"""
Adzuna API client for German data-analyst job listings.

Primary data source: Adzuna Jobs API (https://developer.adzuna.com/)
Fallback: synthetic sample data generated locally when no credentials exist.
"""

import json
import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs/de/search"
SEARCH_TERMS = ["data analyst", "datenanalyst", "business intelligence analyst"]
RAW_DATA_DIR = Path(__file__).parent.parent / "data" / "raw"

# Fallback CSV: a public data-analyst jobs dataset from a well-known portfolio tutorial.
# Used only when no API credentials are configured.
FALLBACK_CSV_URL = (
    "https://raw.githubusercontent.com/picklesueat/data_jobs_data/main/DataAnalyst.csv"
)


# ---------------------------------------------------------------------------
# Adzuna API helpers
# ---------------------------------------------------------------------------


def fetch_page(
    session: requests.Session,
    app_id: str,
    app_key: str,
    search_term: str,
    page: int,
    results_per_page: int = 50,
) -> dict:
    """Fetch one results page from the Adzuna API.

    Args:
        session: Shared requests Session (reuses TCP connections).
        app_id: Adzuna application ID.
        app_key: Adzuna application key.
        search_term: Job search keyword string.
        page: 1-based page number.
        results_per_page: Max results per page (Adzuna max is 50).

    Returns:
        Parsed JSON response dict with a 'results' list.
    """
    url = f"{ADZUNA_BASE_URL}/{page}"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": results_per_page,
        "what": search_term,
        "content-type": "application/json",
    }
    response = session.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_all_listings(max_pages: int = 5) -> list[dict]:
    """Fetch listings from Adzuna for all configured search terms.

    Falls back to synthetic data if no API credentials are present.
    Saves raw results to data/raw/ with a timestamped filename.

    Args:
        max_pages: Maximum pages to fetch per search term (50 results each).

    Returns:
        List of raw listing dicts in a consistent schema.
    """
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")

    if not app_id or not app_key:
        print("No Adzuna credentials found — using fallback data source.")
        return _load_fallback_data()

    all_listings: list[dict] = []
    seen_ids: set[str] = set()

    with requests.Session() as session:
        for term in SEARCH_TERMS:
            print(f"Fetching: '{term}'")
            for page in range(1, max_pages + 1):
                try:
                    data = fetch_page(session, app_id, app_key, term, page)
                    results = data.get("results", [])
                    if not results:
                        break
                    for listing in results:
                        listing_id = str(listing.get("id", ""))
                        if listing_id not in seen_ids:
                            seen_ids.add(listing_id)
                            listing["_source"] = "adzuna"
                            all_listings.append(listing)
                    print(f"  page {page}: {len(results)} results")
                    time.sleep(0.5)  # Stay well within rate limits
                except requests.HTTPError as exc:
                    print(f"  HTTP error on page {page}: {exc}")
                    break

    save_raw_json(all_listings)
    return all_listings


def save_raw_json(listings: list[dict]) -> Path:
    """Persist raw listings to a timestamped JSON file.

    Args:
        listings: List of listing dicts to save.

    Returns:
        Path to the written file.
    """
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RAW_DATA_DIR / f"adzuna_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(listings, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(listings)} listings → {output_path.name}")
    return output_path


def load_most_recent_raw_file() -> Optional[list[dict]]:
    """Load listings from the most recently saved JSON file, or None if none exist.

    Returns:
        List of listing dicts, or None when data/raw/ has no JSON files.
    """
    raw_files = sorted(RAW_DATA_DIR.glob("*.json"), reverse=True)
    if not raw_files:
        return None
    latest = raw_files[0]
    with open(latest, encoding="utf-8") as f:
        data = json.load(f)
    print(f"Loaded {len(data)} listings from cached file: {latest.name}")
    return data


# ---------------------------------------------------------------------------
# Fallback data
# ---------------------------------------------------------------------------


def _load_fallback_data() -> list[dict]:
    """Try downloading the public fallback CSV; generate synthetic data on failure."""
    print(f"Attempting download from {FALLBACK_CSV_URL}")
    try:
        import csv
        import io

        response = requests.get(FALLBACK_CSV_URL, timeout=20)
        response.raise_for_status()
        reader = csv.DictReader(io.StringIO(response.text))
        listings = [_csv_row_to_listing(i, row) for i, row in enumerate(reader)]
        save_raw_json(listings)
        print(f"Downloaded {len(listings)} listings from fallback CSV.")
        return listings
    except Exception as exc:
        print(f"Fallback download failed ({exc}) — generating synthetic demo data.")
        listings = generate_synthetic_data()
        save_raw_json(listings)
        return listings


def _csv_row_to_listing(index: int, row: dict) -> dict:
    """Convert one row of the fallback CSV into our canonical listing schema."""
    return {
        "id": str(index),
        "title": row.get("Job Title", ""),
        "company": {"display_name": row.get("Company Name", "")},
        "location": {
            "display_name": row.get("Location", ""),
            "area": [row.get("Location", "")],
        },
        "salary_min": None,
        "salary_max": None,
        "salary_is_predicted": False,
        "description": row.get("Job Description", ""),
        "created": datetime.now().isoformat(),
        "redirect_url": "",
        "latitude": None,
        "longitude": None,
        "_source": "fallback_csv",
    }


# ---------------------------------------------------------------------------
# Synthetic data generator (always-available last resort)
# ---------------------------------------------------------------------------

_CITIES = {
    "Berlin": (52.5200, 13.4050, 0.25),
    "München": (48.1351, 11.5820, 0.18),
    "Hamburg": (53.5753, 10.0153, 0.12),
    "Frankfurt": (50.1109, 8.6821, 0.10),
    "Köln": (50.9333, 6.9500, 0.08),
    "Stuttgart": (48.7758, 9.1829, 0.07),
    "Düsseldorf": (51.2217, 6.7762, 0.05),
    "Leipzig": (51.3397, 12.3731, 0.04),
    "Dresden": (51.0509, 13.7383, 0.03),
    "Hannover": (52.3759, 9.7320, 0.03),
    "Nürnberg": (49.4521, 11.0767, 0.03),
    "Remote": (None, None, 0.02),
}

_COMPANIES = [
    "SAP SE", "Siemens AG", "BMW Group", "Deutsche Bank",
    "Zalando SE", "HelloFresh SE", "N26 GmbH", "Delivery Hero SE",
    "Otto GmbH", "Volkswagen AG", "Deutsche Telekom", "Robert Bosch GmbH",
    "REWE Digital GmbH", "Allianz SE", "adidas AG", "Bayer AG",
    "BASF SE", "Lufthansa Group", "Axel Springer SE", "Wirecard (Insolvency)",
    "ProSiebenSat.1 Media", "Scout24 SE", "Trivago NV", "Celonis SE",
]

_TITLE_TEMPLATES = {
    "junior": [
        "Junior Data Analyst (m/f/d)",
        "Data Analyst (Berufseinsteiger) (m/w/d)",
        "Junior Business Analyst",
        "Data Analyst Trainee (m/f/d)",
    ],
    "mid": [
        "Data Analyst (m/f/d)",
        "Business Intelligence Analyst",
        "Datenanalyst (m/w/d)",
        "Analytics Specialist (m/f/d)",
        "BI Analyst (m/f/d)",
        "Data & Analytics Analyst",
    ],
    "senior": [
        "Senior Data Analyst (m/f/d)",
        "Senior BI Analyst",
        "Senior Datenanalyst (m/w/d)",
        "Lead Data Analyst (m/f/d)",
    ],
    "lead": [
        "Lead Data Analyst (m/f/d)",
        "Principal Data Analyst",
        "Data Analytics Manager (m/f/d)",
        "Head of Analytics",
    ],
}

_SKILL_POOL = [
    "Python", "SQL", "Excel", "Power BI", "Tableau",
    "R", "SAS", "Looker", "dbt", "Snowflake", "AWS", "Azure",
]

_SENIORITY_SALARY = {
    "junior": (34_000, 48_000),
    "mid": (46_000, 65_000),
    "senior": (62_000, 85_000),
    "lead": (78_000, 105_000),
}


def _random_skills(seniority: str, rng: random.Random) -> list[str]:
    """Pick a realistic set of skills for a given seniority level."""
    probabilities = {
        "Python": 0.65, "SQL": 0.80, "Excel": 0.60, "Power BI": 0.35,
        "Tableau": 0.30, "R": 0.20, "SAS": 0.10, "Looker": 0.15,
        "dbt": 0.15, "Snowflake": 0.12, "AWS": 0.20, "Azure": 0.18,
    }
    # Senior/lead roles skew toward cloud and advanced tools
    if seniority in ("senior", "lead"):
        probabilities.update({"AWS": 0.35, "Azure": 0.32, "dbt": 0.25, "Snowflake": 0.22})

    return [skill for skill, prob in probabilities.items() if rng.random() < prob]


def _build_description(skills: list[str], seniority: str) -> str:
    """Build a job description that mentions the required skills naturally."""
    skill_str = ", ".join(skills) if skills else "SQL, Excel"
    exp_map = {"junior": "0-2", "mid": "2-5", "senior": "5+", "lead": "7+"}
    exp = exp_map.get(seniority, "3+")
    return (
        f"We are looking for a {seniority}-level Data Analyst to join our growing team. "
        f"Required skills: {skill_str}. "
        f"You will analyse large datasets, build dashboards, and present insights to stakeholders. "
        f"{exp} years of relevant experience expected. "
        f"Fluency in German and English is a plus."
    )


def _make_synthetic_listing(listing_id: int, rng: random.Random) -> dict:
    """Create one synthetic job listing in our canonical schema."""
    city_names = list(_CITIES.keys())
    city_weights = [v[2] for v in _CITIES.values()]
    city = rng.choices(city_names, weights=city_weights, k=1)[0]
    lat, lon, _ = _CITIES[city]

    seniority = rng.choices(
        ["junior", "mid", "senior", "lead"], weights=[20, 42, 28, 10]
    )[0]
    title = rng.choice(_TITLE_TEMPLATES[seniority])
    company = rng.choice(_COMPANIES)
    skills = _random_skills(seniority, rng)

    # Only ~35 % of real listings publish salary — mirror that here
    if rng.random() < 0.35:
        low, high = _SENIORITY_SALARY[seniority]
        sal_min = float(rng.randint(low // 1000, (high - 5_000) // 1000) * 1000)
        sal_max = float(sal_min + rng.randint(5, 20) * 1000)
    else:
        sal_min, sal_max = None, None

    days_ago = rng.randint(0, 89)
    posted = (datetime.now() - timedelta(days=days_ago)).isoformat()

    return {
        "id": f"synth_{listing_id:04d}",
        "title": title,
        "company": {"display_name": company},
        "location": {
            "display_name": f"{city}, Deutschland",
            "area": ["Deutschland", city],
        },
        "salary_min": sal_min,
        "salary_max": sal_max,
        "salary_is_predicted": False,
        "description": _build_description(skills, seniority),
        "created": posted,
        "redirect_url": "",
        "latitude": lat,
        "longitude": lon,
        "_source": "synthetic",
    }


def generate_synthetic_data(n: int = 300, seed: int = 42) -> list[dict]:
    """Generate n synthetic job listings for demo/offline use.

    Args:
        n: Number of listings to generate.
        seed: Random seed for reproducible output.

    Returns:
        List of listing dicts in canonical schema.
    """
    rng = random.Random(seed)
    listings = [_make_synthetic_listing(i, rng) for i in range(n)]
    print(f"Generated {len(listings)} synthetic listings (seed={seed}).")
    return listings
