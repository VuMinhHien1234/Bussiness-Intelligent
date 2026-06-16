import os
import sys
import io
import psycopg2
import pandas as pd

# Fix console encoding on Windows.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from config import (
    DB_CONFIG,
    STG, STG_SALES, STG_ADS, STG_WEATHER,
    DW, FACT_SALES, FACT_ADS, FACT_WEATHER,
    EXCEL_PATH, FB_ADS_CSV_PATH, WEATHER_CSV_PATH,
)
from utils import tbl
from staging import load_file_to_staging
from sales import clean_sales_data, load_dimensions, load_fact_sales
from ads import clean_ads_data, load_fact_ad_spend
from weather import clean_weather_data, load_fact_weather


def main():
    with psycopg2.connect(**DB_CONFIG) as conn:
        print("Connected to PostgreSQL")

        # ── Source 1: Sales Excel ──────────────────────────────────────────────
        print("\n[Source 1] Sales Excel")
        load_file_to_staging(conn, EXCEL_PATH, STG_SALES, reader="excel")
        raw_df = pd.read_sql(f"SELECT * FROM {tbl(STG, STG_SALES)}", conn)
        print(f"  Raw rows: {len(raw_df)}")
        clean_df = clean_sales_data(raw_df)
        print(f"  Clean rows: {len(clean_df)}")
        load_dimensions(conn, clean_df)
        load_fact_sales(conn, clean_df)
        print("  fact_marketing_sales: OK")

        # ── Source 2: Facebook Ads CSV ─────────────────────────────────────────
        print("\n[Source 2] Facebook Ads CSV")
        load_file_to_staging(conn, FB_ADS_CSV_PATH, STG_ADS, reader="csv")
        ads_raw = pd.read_sql(f"SELECT * FROM {tbl(STG, STG_ADS)}", conn)
        print(f"  Raw rows: {len(ads_raw)}")
        ads_df = clean_ads_data(ads_raw)
        load_fact_ad_spend(conn, ads_df)
        print("  fact_ad_spend: OK")

        # ── Source 3: Weather CSV ──────────────────────────────────────────────
        print("\n[Source 3] Weather CSV")
        if os.path.exists(WEATHER_CSV_PATH):
            load_file_to_staging(conn, WEATHER_CSV_PATH, STG_WEATHER, reader="csv")
            weather_raw = pd.read_sql(f"SELECT * FROM {tbl(STG, STG_WEATHER)}", conn)
            weather_df = clean_weather_data(weather_raw)
            load_fact_weather(conn, weather_df)
            print("  fact_weather_daily: OK")
        else:
            print(f"  Skipped: {os.path.basename(WEATHER_CSV_PATH)} not found. "
                  "Run 'python3 etl/fetch_weather.py' first.")

        print(f"\nETL complete. Schema: {DW}")
        print(f"Facts loaded: {FACT_SALES}, {FACT_ADS}, {FACT_WEATHER}")


if __name__ == "__main__":
    main()
