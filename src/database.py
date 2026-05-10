"""
SQLite persistence layer for cleaned job listings.

Uses parameterized queries throughout — never string-format SQL with user data.
"""

import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent.parent / "data" / "processed" / "listings.db"

_CREATE_LISTINGS_SQL = """
CREATE TABLE IF NOT EXISTS listings (
    job_id              TEXT PRIMARY KEY,
    title               TEXT,
    company             TEXT,
    location_display    TEXT,
    city                TEXT,
    seniority           TEXT,
    salary_min_eur      REAL,
    salary_max_eur      REAL,
    salary_mid_eur      REAL,
    description         TEXT,
    posted_date         TEXT,
    url                 TEXT,
    latitude            REAL,
    longitude           REAL,
    source              TEXT,
    skills_list         TEXT,
    skill_python        INTEGER,
    skill_sql           INTEGER,
    skill_excel         INTEGER,
    skill_power_bi      INTEGER,
    skill_tableau       INTEGER,
    skill_r             INTEGER,
    skill_sas           INTEGER,
    skill_looker        INTEGER,
    skill_dbt           INTEGER,
    skill_snowflake     INTEGER,
    skill_aws           INTEGER,
    skill_azure         INTEGER
);
"""


def create_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open (or create) a SQLite database file and return the connection.

    Args:
        db_path: Path to the .db file (created if it does not exist).

    Returns:
        Open sqlite3.Connection with row_factory set for dict-like access.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def create_listings_table(conn: sqlite3.Connection) -> None:
    """Create the listings table if it does not already exist.

    Args:
        conn: Open database connection.
    """
    conn.execute(_CREATE_LISTINGS_SQL)
    conn.commit()


def _df_row_to_params(row: pd.Series) -> tuple:
    """Map one DataFrame row to the INSERT parameter tuple."""
    bool_to_int = lambda col: int(bool(row.get(col, False)))
    return (
        row["job_id"], row["title"], row["company"],
        row["location_display"], row["city"], row["seniority"],
        row.get("salary_min_eur"), row.get("salary_max_eur"), row.get("salary_mid_eur"),
        row["description"], str(row.get("posted_date", "")),
        row["url"], row.get("latitude"), row.get("longitude"),
        row["source"], row.get("skills_list", ""),
        bool_to_int("Python"), bool_to_int("SQL"), bool_to_int("Excel"),
        bool_to_int("Power BI"), bool_to_int("Tableau"), bool_to_int("R"),
        bool_to_int("SAS"), bool_to_int("Looker"), bool_to_int("dbt"),
        bool_to_int("Snowflake"), bool_to_int("AWS"), bool_to_int("Azure"),
    )


def insert_listings(conn: sqlite3.Connection, listings_df: pd.DataFrame) -> int:
    """Insert (or replace) all rows from listings_df into the listings table.

    Uses INSERT OR REPLACE so re-running is idempotent.

    Args:
        conn: Open database connection with listings table already created.
        listings_df: Cleaned DataFrame from clean.clean_listings().

    Returns:
        Number of rows inserted.
    """
    placeholders = ", ".join(["?"] * 28)
    sql = f"INSERT OR REPLACE INTO listings VALUES ({placeholders})"

    params_list = [_df_row_to_params(row) for _, row in listings_df.iterrows()]
    conn.executemany(sql, params_list)
    conn.commit()
    print(f"Inserted/replaced {len(params_list)} rows in the database.")
    return len(params_list)


def query_to_dataframe(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple = (),
) -> pd.DataFrame:
    """Run a SELECT query and return results as a DataFrame.

    Args:
        conn: Open database connection.
        sql: Parameterized SQL query string.
        params: Tuple of values for the query placeholders.

    Returns:
        DataFrame with one column per SELECT field.
    """
    return pd.read_sql_query(sql, conn, params=params)


def setup_database(
    listings_df: pd.DataFrame,
    db_path: Path = DB_PATH,
) -> sqlite3.Connection:
    """One-call convenience: create db, table, insert data, return connection.

    Args:
        listings_df: Cleaned DataFrame from clean.clean_listings().
        db_path: Path for the SQLite file (default: data/processed/listings.db).

    Returns:
        Open connection to the populated database.
    """
    conn = create_connection(db_path)
    create_listings_table(conn)
    insert_listings(conn, listings_df)
    print(f"Database ready: {db_path}")
    return conn
