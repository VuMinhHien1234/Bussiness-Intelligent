"""
utils.py — Shared SQL helpers, type converters, and date parsing utilities.
"""
import re
import pandas as pd
from psycopg2.extras import execute_values
from config import CAMPAIGN_TYPE_MAP


# ── SQL helpers ───────────────────────────────────────────────────────────────

def q(name):
    return '"' + name.replace('"', '""') + '"'

def tbl(schema, table):
    """Return a fully qualified, double-quoted table reference: "schema"."table"."""
    return f"{q(schema)}.{q(table)}"

def upsert(cur, sql, rows):
    if rows:
        execute_values(cur, sql, rows)


# ── Type conversion ───────────────────────────────────────────────────────────

def to_none(value):    return None if pd.isna(value) else value

def to_records(df):
    """Convert a DataFrame to a list of tuples, replacing all NA values with None."""
    return [tuple(to_none(v) for v in row) for row in df.itertuples(index=False, name=None)]


# ── Column name normalization ─────────────────────────────────────────────────

def normalize_col(name):
    return re.sub(r"[^a-z0-9]", "", str(name).strip().lower())


# ── Business logic helpers ────────────────────────────────────────────────────

def classify_campaign(name):
    if name is None or pd.isna(name):
        return None
    return CAMPAIGN_TYPE_MAP.get(str(name), "Other")


# ── Date parsing ──────────────────────────────────────────────────────────────

def parse_dates(series):
    """
    Parse a text date Series robustly, in order of precedence:
      1. ISO format  yyyy-mm-dd  (unambiguous — always tried first)
      2. dd/mm/yyyy  (dayfirst=True)
      3. mm/dd/yyyy  (fallback for remaining NaT values)

    Returns a Series of datetime.date objects (NaT where parsing fails).
    """
    text   = series.astype("string").str.strip()
    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")

    iso   = text.str.match(r"^\d{4}-\d{1,2}-\d{1,2}$", na=False)
    result.loc[iso]  = pd.to_datetime(text.loc[iso],  errors="coerce", format="%Y-%m-%d")
    result.loc[~iso] = pd.to_datetime(text.loc[~iso], errors="coerce", dayfirst=True)

    fallback = ~iso & result.isna()
    result.loc[fallback] = pd.to_datetime(text.loc[fallback], errors="coerce", dayfirst=False)

    return result.dt.date

def build_dim_date_df(date_col):
 
    dt = pd.to_datetime(date_col)
    return pd.DataFrame({
        "full_date":  date_col,
        "year":       dt.dt.year,
        "month":      dt.dt.month,
        "month_name": dt.dt.month_name(),
        "quarter":    dt.dt.quarter,
        "year_month": dt.dt.strftime("%Y-%m"),
    }).drop_duplicates(subset=["full_date"])
