"""
Data cleaning pipeline for raw job listings.

Transforms the raw list-of-dicts from fetch_adzuna.py into a tidy DataFrame
ready for analysis and database insertion.
"""

import re
from typing import Optional

import numpy as np
import pandas as pd

# Skills we track — order matters for display (high → low frequency)
TRACKED_SKILLS = [
    "Python", "SQL", "Excel", "Power BI", "Tableau",
    "R", "SAS", "Looker", "dbt", "Snowflake", "AWS", "Azure",
]

_SENIORITY_PATTERNS = {
    "junior": re.compile(r"\b(junior|jr\.?|entry.level|berufseinsteiger|trainee)\b", re.I),
    "senior": re.compile(r"\b(senior|sr\.?|lead|principal|head of)\b", re.I),
    "lead": re.compile(r"\b(lead|principal|head of|manager|direktor)\b", re.I),
}

_CITY_NORMALIZATIONS: dict[str, str] = {
    "muenchen": "München",
    "munich": "München",
    "frankfurt am main": "Frankfurt",
    "frankfurt a.m.": "Frankfurt",
    "koeln": "Köln",
    "cologne": "Köln",
    "hannover": "Hannover",
    "hanover": "Hannover",
    "nuernberg": "Nürnberg",
    "nuremberg": "Nürnberg",
    "duesseldorf": "Düsseldorf",
}


# ---------------------------------------------------------------------------
# Field-level parsers
# ---------------------------------------------------------------------------


def _extract_company(raw: dict) -> str:
    company = raw.get("company", {})
    if isinstance(company, dict):
        return company.get("display_name", "")
    return str(company)


def _extract_location_display(raw: dict) -> str:
    loc = raw.get("location", {})
    if isinstance(loc, dict):
        return loc.get("display_name", "")
    return str(loc)


def _extract_city(location_display: str) -> str:
    """Pull the first token before any comma and normalise it."""
    city_raw = location_display.split(",")[0].strip()
    return _CITY_NORMALIZATIONS.get(city_raw.lower(), city_raw)


def _parse_salary(value) -> Optional[float]:
    """Convert a salary value to float EUR, returning None if unparseable."""
    if value is None or value == "" or (isinstance(value, float) and np.isnan(value)):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _categorise_seniority(title: str) -> str:
    """Assign a seniority bucket from the job title string.

    Returns one of: 'junior', 'senior', 'lead', 'mid'.
    """
    if _SENIORITY_PATTERNS["lead"].search(title):
        return "lead"
    if _SENIORITY_PATTERNS["senior"].search(title):
        return "senior"
    if _SENIORITY_PATTERNS["junior"].search(title):
        return "junior"
    return "mid"


def _extract_skills(description: str) -> dict[str, bool]:
    """Return a dict of {skill_name: True/False} for each tracked skill.

    Uses word-boundary regex so 'R' doesn't match inside 'Power' etc.
    """
    text = description.lower()
    result: dict[str, bool] = {}
    for skill in TRACKED_SKILLS:
        # Use word boundary for short tokens; substring match for multi-word
        if " " in skill:
            result[skill] = skill.lower() in text
        else:
            result[skill] = bool(re.search(rf"\b{re.escape(skill.lower())}\b", text))
    return result


# ---------------------------------------------------------------------------
# DataFrame-level transformers
# ---------------------------------------------------------------------------


def raw_to_dataframe(listings: list[dict]) -> pd.DataFrame:
    """Convert the list-of-dicts from the API/fallback into a flat DataFrame.

    Args:
        listings: Raw listing dicts (canonical schema from fetch_adzuna.py).

    Returns:
        Flat DataFrame with one row per listing.
    """
    rows = []
    for raw in listings:
        location_display = _extract_location_display(raw)
        rows.append({
            "job_id": str(raw.get("id", "")),
            "title": str(raw.get("title", "")),
            "company": _extract_company(raw),
            "location_display": location_display,
            "salary_min_eur": _parse_salary(raw.get("salary_min")),
            "salary_max_eur": _parse_salary(raw.get("salary_max")),
            "description": str(raw.get("description", "")),
            "posted_date": raw.get("created", ""),
            "url": raw.get("redirect_url", ""),
            "latitude": raw.get("latitude"),
            "longitude": raw.get("longitude"),
            "source": raw.get("_source", "unknown"),
        })
    return pd.DataFrame(rows)


def deduplicate(listings_df: pd.DataFrame) -> pd.DataFrame:
    """Drop duplicate listings by job_id, keeping the first occurrence.

    Args:
        listings_df: DataFrame from raw_to_dataframe.

    Returns:
        DataFrame with duplicate job_ids removed.
    """
    before = len(listings_df)
    deduped = listings_df.drop_duplicates(subset="job_id", keep="first").reset_index(drop=True)
    removed = before - len(deduped)
    if removed:
        print(f"Removed {removed} duplicate listings (kept {len(deduped)}).")
    return deduped


def add_derived_columns(listings_df: pd.DataFrame) -> pd.DataFrame:
    """Add city, seniority, salary_mid_eur, and per-skill boolean columns.

    Args:
        listings_df: Deduplicated DataFrame from raw_to_dataframe.

    Returns:
        Enriched DataFrame with additional columns.
    """
    df = listings_df.copy()

    df["city"] = df["location_display"].apply(_extract_city)
    df["seniority"] = df["title"].apply(_categorise_seniority)

    # Mid-point salary is more useful for comparison than min or max alone
    df["salary_mid_eur"] = df.apply(
        lambda row: (
            (row["salary_min_eur"] + row["salary_max_eur"]) / 2
            if pd.notna(row["salary_min_eur"]) and pd.notna(row["salary_max_eur"])
            else row["salary_min_eur"] or row["salary_max_eur"]
        ),
        axis=1,
    )

    # One boolean column per tracked skill
    skill_flags = df["description"].apply(
        lambda desc: pd.Series(_extract_skills(desc))
    )
    df = pd.concat([df, skill_flags], axis=1)

    # Human-readable comma-separated skills list for the Tableau export
    df["skills_list"] = df.apply(
        lambda row: ", ".join(skill for skill in TRACKED_SKILLS if row.get(skill, False)),
        axis=1,
    )

    df["posted_date"] = pd.to_datetime(df["posted_date"], errors="coerce")

    return df


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def clean_listings(listings: list[dict]) -> pd.DataFrame:
    """Full cleaning pipeline: raw dicts → analysis-ready DataFrame.

    Args:
        listings: Raw listing dicts from fetch_all_listings() or load_most_recent_raw_file().

    Returns:
        Cleaned, enriched DataFrame ready for EDA and database insertion.
    """
    print(f"Cleaning {len(listings)} raw listings…")
    listings_df = raw_to_dataframe(listings)
    listings_df = deduplicate(listings_df)
    listings_df = add_derived_columns(listings_df)
    print(
        f"Done. Shape: {listings_df.shape} | "
        f"With salary: {listings_df['salary_mid_eur'].notna().sum()} listings"
    )
    return listings_df
