"""
Reusable plotting functions for the German data-analyst job-market analysis.

Every function accepts an optional Matplotlib Axes so callers can embed charts
in subplots or save them individually.
"""

from typing import Optional

import folium
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

from src.clean import TRACKED_SKILLS

# City coordinates for the Folium map
_CITY_COORDS: dict[str, tuple[float, float]] = {
    "Berlin": (52.5200, 13.4050),
    "München": (48.1351, 11.5820),
    "Hamburg": (53.5753, 10.0153),
    "Frankfurt": (50.1109, 8.6821),
    "Köln": (50.9333, 6.9500),
    "Stuttgart": (48.7758, 9.1829),
    "Düsseldorf": (51.2217, 6.7762),
    "Leipzig": (51.3397, 12.3731),
    "Dresden": (51.0509, 13.7383),
    "Hannover": (52.3759, 9.7320),
    "Nürnberg": (49.4521, 11.0767),
    "Dortmund": (51.5136, 7.4653),
    "Mannheim": (49.4875, 8.4660),
    "Bonn": (50.7374, 7.0982),
    "Bremen": (53.0793, 8.8017),
}

_PALETTE = sns.color_palette("Blues_r", 15)


def plot_top_cities(
    listings_df: pd.DataFrame,
    top_n: int = 12,
    ax: Optional[plt.Axes] = None,
) -> plt.Axes:
    """Horizontal bar chart: cities with the most data-analyst job listings.

    Args:
        listings_df: Cleaned DataFrame from clean.clean_listings().
        top_n: Number of cities to show.
        ax: Existing Axes to draw on; a new figure is created if None.

    Returns:
        The Axes with the chart drawn.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 5))

    city_counts = (
        listings_df["city"]
        .value_counts()
        .head(top_n)
        .sort_values()  # ascending so longest bar is at top
    )

    colors = sns.color_palette("Blues_r", len(city_counts))
    city_counts.plot(kind="barh", ax=ax, color=colors, edgecolor="white")

    ax.set_xlabel("Number of Listings", fontsize=11)
    ax.set_ylabel("")
    ax.set_title(f"Top {top_n} Cities by Data-Analyst Job Listings", fontsize=13, pad=12)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    # Label bars with counts
    for bar in ax.patches:
        ax.text(
            bar.get_width() + 0.3,
            bar.get_y() + bar.get_height() / 2,
            f"{int(bar.get_width())}",
            va="center",
            fontsize=9,
        )

    plt.tight_layout()
    return ax


def plot_salary_distribution(
    listings_df: pd.DataFrame,
    ax: Optional[plt.Axes] = None,
) -> plt.Axes:
    """Histogram of mid-point salaries with a KDE overlay.

    Only uses rows where salary_mid_eur is not null — the title should
    mention this disclosure rate.

    Args:
        listings_df: Cleaned DataFrame from clean.clean_listings().
        ax: Existing Axes to draw on; a new figure is created if None.

    Returns:
        The Axes with the chart drawn.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 5))

    salary_series = listings_df["salary_mid_eur"].dropna()
    disclosure_pct = 100 * len(salary_series) / len(listings_df)

    sns.histplot(
        salary_series,
        bins=25,
        kde=True,
        color=sns.color_palette("Blues_r")[2],
        ax=ax,
    )

    median_sal = salary_series.median()
    ax.axvline(median_sal, color="firebrick", linestyle="--", linewidth=1.5,
               label=f"Median €{median_sal:,.0f}")
    ax.legend(fontsize=10)

    ax.set_xlabel("Annual Salary (EUR)", fontsize=11)
    ax.set_ylabel("Listings", fontsize=11)
    ax.set_title(
        f"Salary Distribution — Mid-Point (n={len(salary_series)}, "
        f"{disclosure_pct:.0f}% of listings disclose salary)",
        fontsize=12,
        pad=10,
    )
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x/1000:.0f}k"))
    plt.tight_layout()
    return ax


def plot_skills_frequency(
    listings_df: pd.DataFrame,
    ax: Optional[plt.Axes] = None,
) -> plt.Axes:
    """Horizontal bar chart of how often each tracked skill appears in listings.

    Args:
        listings_df: Cleaned DataFrame with boolean skill columns.
        ax: Existing Axes to draw on; a new figure is created if None.

    Returns:
        The Axes with the chart drawn.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 5))

    # Only include columns that exist (safety for partial datasets)
    present_skills = [s for s in TRACKED_SKILLS if s in listings_df.columns]
    skill_counts = (
        listings_df[present_skills]
        .sum()
        .sort_values()
    )
    pct = (skill_counts / len(listings_df) * 100).round(1)

    colors = sns.color_palette("Blues_r", len(skill_counts))
    skill_counts.plot(kind="barh", ax=ax, color=colors, edgecolor="white")

    for bar, (skill, p) in zip(ax.patches, pct.items()):
        ax.text(
            bar.get_width() + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{p}%",
            va="center",
            fontsize=9,
        )

    ax.set_xlabel("Number of Listings", fontsize=11)
    ax.set_ylabel("")
    ax.set_title("Most In-Demand Skills (mentions in job descriptions)", fontsize=13, pad=12)
    plt.tight_layout()
    return ax


def plot_salary_by_skill(
    listings_df: pd.DataFrame,
    skills: Optional[list[str]] = None,
    ax: Optional[plt.Axes] = None,
) -> plt.Axes:
    """Boxplot of mid-point salary grouped by individual skill presence.

    Args:
        listings_df: Cleaned DataFrame with boolean skill columns and salary_mid_eur.
        skills: Subset of skills to show; defaults to all TRACKED_SKILLS.
        ax: Existing Axes to draw on; a new figure is created if None.

    Returns:
        The Axes with the chart drawn.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 6))

    if skills is None:
        skills = TRACKED_SKILLS

    salary_df = listings_df[listings_df["salary_mid_eur"].notna()].copy()
    present_skills = [s for s in skills if s in salary_df.columns]

    # Melt to long format: one row per (listing × skill) where listing has the skill
    rows = []
    for skill in present_skills:
        skill_salary = salary_df.loc[salary_df[skill] == True, "salary_mid_eur"]
        for val in skill_salary:
            rows.append({"skill": skill, "salary_mid_eur": val})

    long_df = pd.DataFrame(rows)
    if long_df.empty:
        ax.text(0.5, 0.5, "No salary data available", ha="center", va="center",
                transform=ax.transAxes)
        return ax

    # Order by median salary descending
    order = (
        long_df.groupby("skill")["salary_mid_eur"]
        .median()
        .sort_values(ascending=False)
        .index.tolist()
    )

    sns.boxplot(data=long_df, x="skill", y="salary_mid_eur", order=order,
                palette="Blues_r", ax=ax, flierprops={"marker": "o", "markersize": 3})

    ax.set_xlabel("")
    ax.set_ylabel("Annual Salary — Mid-Point (EUR)", fontsize=11)
    ax.set_title("Salary Distribution by Required Skill", fontsize=13, pad=12)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"€{x/1000:.0f}k"))
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    return ax


def build_city_map(listings_df: pd.DataFrame) -> folium.Map:
    """Build a Folium choropleth-style bubble map of job postings by city.

    Args:
        listings_df: Cleaned DataFrame with a 'city' column.

    Returns:
        Folium Map object (display in Jupyter by evaluating it as the last expression).
    """
    city_counts = listings_df["city"].value_counts()

    germany_map = folium.Map(
        location=[51.1657, 10.4515],  # Geographic centre of Germany
        zoom_start=6,
        tiles="CartoDB positron",
    )

    max_count = city_counts.max() if not city_counts.empty else 1

    for city, count in city_counts.items():
        coords = _CITY_COORDS.get(city)
        if coords is None:
            continue  # Skip cities we don't have coordinates for

        # Scale bubble radius between 8 and 40 pixels
        radius = 8 + 32 * (count / max_count)

        folium.CircleMarker(
            location=coords,
            radius=radius,
            color="#1565C0",
            fill=True,
            fill_color="#1E88E5",
            fill_opacity=0.65,
            popup=folium.Popup(f"<b>{city}</b><br>{count} listings", max_width=150),
            tooltip=f"{city}: {count} listings",
        ).add_to(germany_map)

    return germany_map
