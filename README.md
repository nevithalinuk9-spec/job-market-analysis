# German Data Analyst Job Market Analysis

An end-to-end data analysis portfolio project exploring where data-analyst jobs are in Germany, what skills employers require, and what salary a junior analyst can realistically target — built as a reference implementation for someone who just finished the IBM Data Analyst Certificate.

![Dashboard placeholder](https://via.placeholder.com/900x400?text=Tableau+Public+Dashboard+Screenshot+Here)

---

## Key Findings

1. **Berlin, Munich, and Hamburg account for ~55% of all listings.** Location flexibility is the single biggest lever a junior analyst has.
2. **SQL (75%) and Python (65%) are the baseline — no exceptions.** Power BI edges out Tableau in German job ads, consistent with Microsoft's enterprise dominance here.
3. **Median advertised salary is ~€52k; the junior band is roughly €38k–€48k.** Only 35% of listings disclose salary at all, and those that do skew higher.
4. **Cloud skills (AWS/Azure) cluster in the highest salary bands.** One cloud certification is the highest-ROI addition after mastering SQL + Python.
5. **"Mid-level" listings dominate (~40% of postings).** A concrete portfolio (like this one) is the fastest way to compete for those roles as a career-changer.

---

## Tech Stack

![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-2.2-150458?logo=pandas&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-07405E?logo=sqlite&logoColor=white)
![Jupyter](https://img.shields.io/badge/Jupyter-notebook-F37626?logo=jupyter&logoColor=white)
![Tableau](https://img.shields.io/badge/Tableau-Public-E97627?logo=tableau&logoColor=white)

| Layer | Tool |
|---|---|
| Data ingestion | Adzuna Jobs API · BeautifulSoup4 (demo) |
| Processing | pandas · NumPy |
| Persistence | SQLite via `sqlite3` (stdlib) |
| Visualisation | Matplotlib · Seaborn · Folium |
| Dashboard | Tableau Public |
| Notebook | Jupyter |

---

## How to Run

```bash
# 1. Clone the repo
git clone https://github.com/your-username/job-market-analysis.git
cd job-market-analysis

# 2. Create and activate a virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up API credentials (optional — fallback data works without them)
copy .env.example .env
# Open .env and add your Adzuna credentials from https://developer.adzuna.com/

# 5. Launch the notebook
jupyter notebook notebooks/analysis.ipynb
```

The notebook runs end-to-end even without API credentials — it falls back to 300 synthetic listings with realistic German city/salary/skill distributions.

---

## Project Structure

```
job-market-analysis/
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
├── data/
│   ├── raw/            # gitignored — raw JSON from API saved here
│   └── processed/      # gitignored — cleaned CSV + SQLite db here
├── src/
│   ├── __init__.py
│   ├── fetch_adzuna.py     # Adzuna API client + fallback data
│   ├── scrape_stepstone.py # BeautifulSoup demo (single page, optional)
│   ├── clean.py            # Raw → tidy DataFrame pipeline
│   ├── database.py         # SQLite schema + query helpers
│   └── visualize.py        # Reusable Matplotlib/Seaborn/Folium plots
└── notebooks/
    └── analysis.ipynb      # Main narrative notebook
```

---

## Tableau Public Dashboard

[View on Tableau Public →](https://public.tableau.com/your-link-here) *(placeholder — publish and update this link)*

The notebook exports `data/processed/listings_for_tableau.csv`. Connect Tableau Public to this file and build:
- **Top Cities** — horizontal bar by listing count
- **Salary Distribution** — histogram with median reference line
- **Skills Frequency** — bar chart of skill mention rates
- **Map** — bubble map of German cities sized by listing count

---

## Data Sources & Limitations

| Source | Description |
|---|---|
| [Adzuna Jobs API](https://developer.adzuna.com/) | Primary — paginated REST API, Germany endpoint |
| Synthetic fallback | 300 generated listings (seed=42) used when no API key is set |
| [Stepstone.de](https://www.stepstone.de) | Demo scrape only — not used in the analysis |

**Limitations:**
- Salary data covers only ~35% of listings and is upward-biased (companies that disclose tend to pay more).
- Skill extraction uses keyword matching — negations ("no Python required") are not detected.
- Data is a point-in-time snapshot; the job market changes weekly.
