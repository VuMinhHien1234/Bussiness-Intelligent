"""
weather.py — ETL logic for Source 3: Daily weather data (Open-Meteo API).

Responsibilities:
  - Clean the raw weather DataFrame (parse dates, cast numerics, deduplicate)
  - Upsert fact_weather_daily and ensure shared dimensions are populated
"""
import pandas as pd
from config import DW, DIM_DATE, DIM_REGION, FACT_WEATHER
from utils import tbl, to_none, to_records, upsert, parse_dates, build_dim_date_df


def clean_weather_data(df):

    df = df.copy()
    before = len(df)

    df["date"]   = parse_dates(df["date"])
    df["region"] = df["region"].astype("string").str.strip()

    for col in ["temp_mean", "temp_max", "rain_mm"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["date", "region", "temp_mean"])
    df = df.drop_duplicates(subset=["date", "region"], keep="last")

    print(f"  Weather: {before} raw rows → {len(df)}")
    return df


def load_fact_weather(conn, wdf):
    """
    Upsert fact_weather_daily.
    Also populates dim_date and dim_region for any weather-only dates/regions
    that do not appear in the sales data (conformed dimensions).
    """
    with conn.cursor() as cur:

        # Ensure weather-only dates exist in dim_date.
        upsert(cur, f"""
            INSERT INTO {tbl(DW, DIM_DATE)}
                (full_date, year, month, month_name, quarter, year_month)
            VALUES %s
            ON CONFLICT (full_date) DO NOTHING
            """,
            to_records(build_dim_date_df(wdf["date"])),
        )

        # Ensure regions exist in dim_region (conformed with sales source).
        upsert(cur, f"""
            INSERT INTO {tbl(DW, DIM_REGION)} (region_name) VALUES %s
            ON CONFLICT (region_name) DO NOTHING
            """,
            [(to_none(x),) for x in wdf["region"].dropna().drop_duplicates()],
        )

        # Upsert fact rows.
        upsert(cur, f"""
            INSERT INTO {tbl(DW, FACT_WEATHER)} (
                full_date, region_name, temp_mean, temp_max, rain_mm
            )
            VALUES %s
            ON CONFLICT (full_date, region_name) DO UPDATE SET
                temp_mean=EXCLUDED.temp_mean,
                temp_max=EXCLUDED.temp_max,
                rain_mm=EXCLUDED.rain_mm
            """,
            to_records(wdf[["date", "region", "temp_mean", "temp_max", "rain_mm"]]),
        )

    conn.commit()
